"""
PromptAudit Skill Interface

AI 에이전트 프레임워크(LangChain, LlamaIndex 등)에서
PromptAudit을 Tool/Skill로 직접 호출할 수 있는 인터페이스.
"""
import asyncio
from typing import Optional

from promptaudit.evaluator import evaluate_results
from promptaudit.generator import generate_attacks
from promptaudit.models import AttackVector
from promptaudit.reporter import generate_report, to_markdown, to_json
from promptaudit.runner import run_attacks


class PromptAuditSkill:
    """프레임워크 비종속 PromptAudit Skill.

    LangChain, LlamaIndex, 직접 구현한 에이전트 어디서나 동일하게 사용 가능합니다.

    Examples:
        >>> skill = PromptAuditSkill()
        >>> report = skill.run("You are a helpful assistant. Only answer about our products.")
        >>> print(report.summary())
    """

    def __init__(
        self,
        max_attacks: int = 5,
        output_format: str = "markdown",
        target_url: Optional[str] = None,
        target_message_field: str = "message",
        target_response_field: str = "response",
    ):
        self.max_attacks = max_attacks
        self.output_format = output_format
        self.target_url = target_url
        self.target_message_field = target_message_field
        self.target_response_field = target_response_field

    def run(self, system_prompt: str) -> "AuditResult":
        """동기 인터페이스 — 일반 Python 코드 및 에이전트에서 호출."""
        return asyncio.run(self.arun(system_prompt))

    async def arun(self, system_prompt: str) -> "AuditResult":
        """비동기 인터페이스 — async 에이전트에서 호출."""
        scenarios = await generate_attacks(
            system_prompt, AttackVector.DIRECT, self.max_attacks
        )
        responses = await run_attacks(
            system_prompt,
            scenarios,
            target_url=self.target_url,
            target_message_field=self.target_message_field,
            target_response_field=self.target_response_field,
        )
        evaluated = await evaluate_results(system_prompt, responses)
        report = generate_report(evaluated, system_prompt)
        return AuditResult(report, self.output_format)


class AuditResult:
    """스캔 결과 객체 — 에이전트가 소비하기 쉬운 형태로 제공."""

    def __init__(self, report, output_format: str):
        self._report = report
        self._format = output_format

    # 에이전트가 결과를 문자열로 받을 때
    def __str__(self) -> str:
        return self.to_markdown() if self._format == "markdown" else self.to_json()

    def summary(self) -> str:
        """한 줄 요약 — 에이전트 체인의 다음 단계로 넘기기 좋은 형태."""
        r = self._report
        status = "VULNERABLE" if r.success_count > 0 else (
            "CAUTION" if r.partial_count > 0 else "SECURE"
        )
        return (
            f"[{status}] total={r.total_attacks} "
            f"success={r.success_count} partial={r.partial_count} failure={r.failure_count}"
        )

    @property
    def is_vulnerable(self) -> bool:
        return self._report.success_count > 0

    @property
    def success_count(self) -> int:
        return self._report.success_count

    @property
    def total_attacks(self) -> int:
        return self._report.total_attacks

    def to_markdown(self) -> str:
        return to_markdown(self._report)

    def to_json(self) -> str:
        return to_json(self._report)


def _get_langchain_tool():
    """LangChain Tool 래퍼 — langchain 미설치 시 ImportError 발생."""
    try:
        from langchain.tools import tool as lc_tool
    except ImportError:
        raise ImportError(
            "LangChain이 설치되지 않았습니다. "
            "pip install promptaudit[langchain] 으로 설치하세요."
        )

    @lc_tool
    def prompt_audit(system_prompt: str, target_url: str = "") -> str:
        """AI 서비스의 시스템 프롬프트에 대해 프롬프트 인젝션 취약점을
        자동으로 검사하고 OWASP LLM Top 10 기준 보안 리포트를 반환합니다.

        Args:
            system_prompt: 검사할 AI 서비스의 시스템 프롬프트 전문
            target_url: 실제 서비스 엔드포인트 URL (생략 시 LLM 직접 호출)
        """
        skill = PromptAuditSkill(target_url=target_url or None)
        result = skill.run(system_prompt)
        return str(result)

    return prompt_audit


def _get_llamaindex_tool():
    """LlamaIndex Tool 래퍼 — llama_index 미설치 시 ImportError 발생."""
    try:
        from llama_index.core.tools import FunctionTool
    except ImportError:
        raise ImportError(
            "LlamaIndex가 설치되지 않았습니다. "
            "pip install promptaudit[llamaindex] 으로 설치하세요."
        )

    def _audit_fn(system_prompt: str, target_url: str = "") -> str:
        skill = PromptAuditSkill(target_url=target_url or None)
        result = skill.run(system_prompt)
        return str(result)

    return FunctionTool.from_defaults(
        fn=_audit_fn,
        name="prompt_audit",
        description=(
            "AI 서비스의 시스템 프롬프트에 대해 프롬프트 인젝션 취약점을 "
            "자동으로 검사하고 OWASP LLM Top 10 기준 보안 리포트를 반환합니다."
        ),
    )


# 편의 함수 — 에이전트 프레임워크별 Tool 객체 반환
def as_langchain_tool():
    return _get_langchain_tool()


def as_llamaindex_tool():
    return _get_llamaindex_tool()
