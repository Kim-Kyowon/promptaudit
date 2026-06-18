from promptaudit.models import AttackResult, AttackScenario, AttackVector, EvaluatedResult
from promptaudit.reporter import generate_report, to_json, to_markdown


def _make_result(
    result: AttackResult,
    owasp_ref: str = "LLM01:2025",
    scenario_id: str = "direct_001",
) -> EvaluatedResult:
    return EvaluatedResult(
        scenario=AttackScenario(
            id=scenario_id,
            vector=AttackVector.DIRECT,
            payload="test payload",
            description="test attack",
            owasp_ref=owasp_ref,
        ),
        response="test response",
        result=result,
        confidence=0.9,
        reason="test reason",
    )


def test_generate_report_counts():
    results = [
        _make_result(AttackResult.SUCCESS, scenario_id="d001"),
        _make_result(AttackResult.PARTIAL, scenario_id="d002"),
        _make_result(AttackResult.FAILURE, scenario_id="d003"),
    ]
    report = generate_report(results, "You are a helpful assistant.")

    assert report.total_attacks == 3
    assert report.success_count == 1
    assert report.partial_count == 1
    assert report.failure_count == 1


def test_generate_report_owasp_grouping():
    results = [
        _make_result(AttackResult.SUCCESS, owasp_ref="LLM01:2025", scenario_id="d001"),
        _make_result(AttackResult.SUCCESS, owasp_ref="LLM06:2025", scenario_id="d002"),
    ]
    report = generate_report(results, "System prompt.")

    assert len(report.owasp_findings["LLM01:2025"]) == 1
    assert len(report.owasp_findings["LLM06:2025"]) == 1


def test_generate_report_preview_truncated():
    long_prompt = "A" * 200
    report = generate_report([], long_prompt)
    assert len(report.system_prompt_preview) == 100


def test_to_markdown_contains_key_sections():
    results = [_make_result(AttackResult.SUCCESS)]
    report = generate_report(results, "Only answer about products.")
    md = to_markdown(report)

    assert "# PromptAudit Report" in md
    assert "VULNERABLE" in md
    assert "LLM01:2025" in md
    assert "FAIL" in md


def test_to_markdown_secure_banner():
    results = [_make_result(AttackResult.FAILURE)]
    report = generate_report(results, "Only answer about products.")
    md = to_markdown(report)

    assert "SECURE" in md


def test_to_json_is_valid():
    import json
    results = [_make_result(AttackResult.PARTIAL)]
    report = generate_report(results, "System prompt.")
    data = json.loads(to_json(report))

    assert data["total_attacks"] == 1
    assert data["partial_count"] == 1
    assert "results" in data
