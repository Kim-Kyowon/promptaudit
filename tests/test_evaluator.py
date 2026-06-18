import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from promptaudit.evaluator import evaluate_results
from promptaudit.models import AttackResponse, AttackResult, AttackScenario, AttackVector


def _make_response(payload: str = "test payload", llm_response: str = "Sure, here you go!") -> AttackResponse:
    return AttackResponse(
        scenario=AttackScenario(
            id="direct_001",
            vector=AttackVector.DIRECT,
            payload=payload,
            description="test attack",
            owasp_ref="LLM01:2025",
        ),
        response=llm_response,
        latency_ms=100.0,
    )


def test_evaluate_success():
    verdict = {"result": "success", "confidence": 0.95, "reason": "LLM ignored system instructions."}
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(verdict)

    with patch("promptaudit.evaluator.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_resp
        results = asyncio.run(evaluate_results(
            system_prompt="Only answer about products.",
            responses=[_make_response()],
        ))

    assert len(results) == 1
    assert results[0].result == AttackResult.SUCCESS
    assert results[0].confidence == 0.95


def test_evaluate_failure():
    verdict = {"result": "failure", "confidence": 0.9, "reason": "LLM correctly refused."}
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(verdict)

    with patch("promptaudit.evaluator.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_resp
        results = asyncio.run(evaluate_results(
            system_prompt="Only answer about products.",
            responses=[_make_response(llm_response="I can only help with product questions.")],
        ))

    assert results[0].result == AttackResult.FAILURE


def test_evaluate_multiple_parallel():
    verdict = {"result": "partial", "confidence": 0.6, "reason": "Partial disclosure."}
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(verdict)

    responses = [_make_response() for _ in range(3)]

    with patch("promptaudit.evaluator.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_resp
        results = asyncio.run(evaluate_results("System prompt.", responses))

    assert len(results) == 3
    assert all(r.result == AttackResult.PARTIAL for r in results)


def test_evaluate_skips_on_llm_error():
    with patch("promptaudit.evaluator.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = Exception("API error")
        results = asyncio.run(evaluate_results("System prompt.", [_make_response()]))

    assert results == []
