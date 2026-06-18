import asyncio
import os
import time

import httpx
from litellm import acompletion

from promptaudit.models import AttackResponse, AttackScenario

_PROVIDER = os.getenv("PROMPTAUDIT_LLM_PROVIDER", "openai")
_MODEL_MAP = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini/gemini-2.5-flash",
    "ollama": "ollama/llama3",
    "enterprise-gateway": os.getenv("PROMPTAUDIT_GATEWAY_MODEL", "gpt-4o"),
}


def _model(provider: str | None = None) -> str:
    p = provider or _PROVIDER
    return _MODEL_MAP.get(p, "gpt-4o-mini")


async def run_attacks(
    system_prompt: str,
    scenarios: list[AttackScenario],
    target_provider: str | None = None,
    target_url: str | None = None,
    target_message_field: str = "message",
    target_response_field: str = "response",
) -> list[AttackResponse]:
    """공격 시나리오를 실행합니다.

    target_url이 주어지면 해당 HTTP 엔드포인트에 공격을 전송합니다.
    없으면 LLM을 직접 호출합니다.
    """
    tasks = [
        _run_single(
            system_prompt, s, target_provider,
            target_url, target_message_field, target_response_field,
        )
        for s in scenarios
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]


async def _run_single(
    system_prompt: str,
    scenario: AttackScenario,
    provider: str | None,
    target_url: str | None,
    target_message_field: str,
    target_response_field: str,
) -> AttackResponse:
    start = time.monotonic()

    if target_url:
        # HTTP 모드 — 실제 서비스 엔드포인트에 공격 전송
        response_text = await _run_http(
            target_url, scenario.payload,
            target_message_field, target_response_field,
        )
    else:
        # LLM 직접 호출 모드
        response_text = await _run_llm(system_prompt, scenario.payload, provider)

    latency_ms = (time.monotonic() - start) * 1000
    return AttackResponse(
        scenario=scenario,
        response=response_text,
        latency_ms=round(latency_ms, 1),
    )


async def _run_llm(system_prompt: str, payload: str, provider: str | None) -> str:
    resp = await acompletion(
        model=_model(provider),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload},
        ],
    )
    return resp.choices[0].message.content or ""


async def _run_http(
    url: str,
    payload: str,
    message_field: str,
    response_field: str,
) -> str:
    """DemoSystem 같은 실제 서비스 엔드포인트에 공격 페이로드를 POST로 전송합니다."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json={message_field: payload})
        resp.raise_for_status()
        data = resp.json()
        # 응답 필드가 없으면 전체 JSON을 문자열로 반환
        return str(data.get(response_field, data))
