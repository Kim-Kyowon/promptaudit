import argparse
import asyncio
import io
import sys
from pathlib import Path

# Windows 콘솔 UTF-8 강제
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from promptaudit.defaults import BLACKBOX_MODE_NOTICE, DEFAULT_SYSTEM_PROMPT
from promptaudit.evaluator import evaluate_results
from promptaudit.generator import generate_attacks
from promptaudit.models import AttackVector
from promptaudit.reporter import generate_report, to_json, to_markdown
from promptaudit.runner import run_attacks


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="promptaudit",
        description="AI-Powered Prompt Injection Red-Team Automation Skill",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="시스템 프롬프트 보안 스캔")
    p_scan.add_argument(
        "--system-prompt",
        required=False,
        default=None,
        help="시스템 프롬프트 파일 경로 (생략 시 범용 기본 프롬프트로 블랙박스 테스트)",
    )
    p_scan.add_argument(
        "--attack-types",
        default="direct",
        help="공격 벡터 (쉼표 구분, 기본값: direct)",
    )
    p_scan.add_argument("--max-attacks", type=int, default=5, help="최대 공격 시나리오 수 (기본값: 5)")
    p_scan.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="출력 형식 (기본값: markdown)",
    )
    p_scan.add_argument("--out", help="결과를 저장할 파일 경로 (생략 시 stdout)")
    p_scan.add_argument(
        "--fail-on",
        choices=["success", "partial"],
        default="success",
        help="해당 결과 발견 시 exit 1 (CI/CD 게이트, 기본값: success)",
    )
    p_scan.add_argument(
        "--target-url",
        help="실제 서비스 엔드포인트 URL (예: http://127.0.0.1:8001/chat). "
             "지정하면 LLM 직접 호출 대신 해당 URL에 HTTP POST로 공격을 전송합니다.",
    )
    p_scan.add_argument(
        "--target-message-field",
        default="message",
        help="서비스 API의 메시지 필드명 (기본값: message)",
    )
    p_scan.add_argument(
        "--target-response-field",
        default="response",
        help="서비스 API의 응답 필드명 (기본값: response)",
    )

    args = parser.parse_args()

    if args.command == "scan":
        asyncio.run(_scan(args))


async def _scan(args: argparse.Namespace) -> None:
    blackbox = args.system_prompt is None
    if blackbox:
        system_prompt = DEFAULT_SYSTEM_PROMPT
        print(f"[!] {BLACKBOX_MODE_NOTICE}", file=sys.stderr)
    else:
        prompt_path = Path(args.system_prompt)
        if not prompt_path.exists():
            print(f"ERROR: 파일을 찾을 수 없습니다: {args.system_prompt}", file=sys.stderr)
            sys.exit(1)
        system_prompt = prompt_path.read_text(encoding="utf-8").strip()
        if not system_prompt:
            print("ERROR: 시스템 프롬프트가 비어 있습니다.", file=sys.stderr)
            sys.exit(1)

    vectors = [AttackVector(v.strip()) for v in args.attack_types.split(",")]

    print(f"[*] 시스템 프롬프트 로드 완료 ({len(system_prompt)}자)", file=sys.stderr)
    print(f"[*] 공격 벡터: {[v.value for v in vectors]}", file=sys.stderr)

    # 공격 시나리오 생성
    all_scenarios = []
    for vector in vectors:
        print(f"[*] {vector.value} 공격 시나리오 생성 중...", file=sys.stderr)
        scenarios = await generate_attacks(system_prompt, vector, args.max_attacks)
        all_scenarios.extend(scenarios)
    print(f"[*] 총 {len(all_scenarios)}개 시나리오 생성 완료", file=sys.stderr)

    # 공격 실행
    target_url = getattr(args, "target_url", None)
    if target_url:
        print(f"[*] HTTP 모드 — 공격 대상: {target_url}", file=sys.stderr)
    print("[*] 공격 실행 중...", file=sys.stderr)
    responses = await run_attacks(
        system_prompt,
        all_scenarios,
        target_url=target_url,
        target_message_field=getattr(args, "target_message_field", "message"),
        target_response_field=getattr(args, "target_response_field", "response"),
    )
    print(f"[*] {len(responses)}개 응답 수집 완료", file=sys.stderr)

    # LLM-as-Judge 평가
    print("[*] 결과 평가 중 (LLM-as-Judge)...", file=sys.stderr)
    evaluated = await evaluate_results(system_prompt, responses)

    # 리포트 생성
    report = generate_report(evaluated, system_prompt)
    output = to_markdown(report) if args.format == "markdown" else to_json(report)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"[*] 리포트 저장 완료: {args.out}", file=sys.stderr)
    else:
        print(output)

    # CI/CD 게이트
    if args.fail_on == "success" and report.success_count > 0:
        sys.exit(1)
    if args.fail_on == "partial" and (report.success_count + report.partial_count) > 0:
        sys.exit(1)
