import json
from datetime import datetime, timezone

from promptaudit.defaults import DEFAULT_SYSTEM_PROMPT
from promptaudit.models import AttackResult, AuditReport, EvaluatedResult

_OWASP_LABELS = {
    "LLM01:2025": "Prompt Injection",
    "LLM06:2025": "Sensitive Information Disclosure",
}


def generate_report(results: list[EvaluatedResult], system_prompt: str) -> AuditReport:
    owasp_findings: dict[str, list[EvaluatedResult]] = {k: [] for k in _OWASP_LABELS}
    for r in results:
        bucket = owasp_findings.setdefault(r.scenario.owasp_ref, [])
        bucket.append(r)

    return AuditReport(
        system_prompt_preview=system_prompt[:100],
        total_attacks=len(results),
        success_count=sum(1 for r in results if r.result == AttackResult.SUCCESS),
        partial_count=sum(1 for r in results if r.result == AttackResult.PARTIAL),
        failure_count=sum(1 for r in results if r.result == AttackResult.FAILURE),
        results=results,
        owasp_findings=owasp_findings,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _is_blackbox(report: AuditReport) -> bool:
    return report.system_prompt_preview == DEFAULT_SYSTEM_PROMPT[:100]


def to_markdown(report: AuditReport) -> str:
    blackbox = _is_blackbox(report)
    lines = [
        "# PromptAudit Report",
        f"Generated: {report.generated_at}",
        "",
    ]

    if blackbox:
        lines += [
            "> **[블랙박스 모드]** 시스템 프롬프트 미제공 — 범용 AI 서비스 기준(OWASP LLM Top 10)으로 테스트했습니다.",
            "> 실제 시스템 프롬프트를 제공하면 더 정밀한 특화 공격 시나리오로 재스캔할 수 있습니다.",
            "",
        ]

    lines += [
        "## System Prompt (preview)",
        f"> {report.system_prompt_preview}{'...' if len(report.system_prompt_preview) == 100 else ''}",
        "",
        "## Summary",
        "| Total | Success | Partial | Failure |",
        "|-------|---------|---------|---------|",
        f"| {report.total_attacks} | {report.success_count} | {report.partial_count} | {report.failure_count} |",
        "",
    ]

    # 위험도 배너
    if report.success_count > 0:
        lines.append(f"> **VULNERABLE** — {report.success_count} attack(s) succeeded.")
    elif report.partial_count > 0:
        lines.append(f"> **CAUTION** — {report.partial_count} partial success(es) detected.")
    else:
        lines.append("> **SECURE** — All attacks were blocked.")
    lines.append("")

    # OWASP 항목별 결과
    lines.append("## Findings by OWASP LLM Top 10")
    for owasp_ref, label in _OWASP_LABELS.items():
        findings = report.owasp_findings.get(owasp_ref, [])
        if not findings:
            continue
        vulnerable = [f for f in findings if f.result != AttackResult.FAILURE]
        lines.append(f"\n### {owasp_ref} — {label}")
        lines.append(f"Attacks: {len(findings)} | Vulnerable: {len(vulnerable)}")

    # 전체 결과 상세
    lines.append("\n## Attack Details")
    for r in report.results:
        icon = {"success": "FAIL", "partial": "WARN", "failure": "PASS"}[r.result.value]
        lines += [
            f"\n### [{icon}] {r.scenario.id} — {r.scenario.description}",
            f"- **Vector**: {r.scenario.vector.value}",
            f"- **OWASP**: {r.scenario.owasp_ref}",
            f"- **Result**: {r.result.value} (confidence: {r.confidence:.0%})",
            f"- **Reason**: {r.reason}",
            "\n**Payload:**",
            "```",
            r.scenario.payload,
            "```",
            "\n**LLM Response:**",
            "```",
            r.response[:500] + ("..." if len(r.response) > 500 else ""),
            "```",
        ]

    return "\n".join(lines)


def to_json(report: AuditReport) -> str:
    return json.dumps(report.model_dump(), indent=2, ensure_ascii=False)
