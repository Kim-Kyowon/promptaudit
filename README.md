# PromptAudit

**AI-Powered Prompt Injection Red-Team Automation Skill**

AI 서비스의 시스템 프롬프트를 대상으로 Direct Injection 공격 시나리오를 자동 생성·실행·평가하여 OWASP LLM Top 10 기준 취약점 리포트를 출력하는 보안 자동화 Skill 패키지.

## 설치

```bash
pip install promptaudit
```

## 빠른 시작

```bash
# 환경변수 설정
export OPENAI_API_KEY="sk-..."
export PROMPTAUDIT_LLM_PROVIDER="openai"   # openai | anthropic | gemini | ollama

# 시스템 프롬프트 파일 준비
echo "You are a helpful customer service assistant. Only answer about our products." > prompt.txt

# 스캔 실행
promptaudit scan --system-prompt prompt.txt
```

## 사용법

```bash
# 기본 스캔 (LLM 직접 호출)
promptaudit scan --system-prompt prompt.txt

# 실제 서비스 엔드포인트 대상 스캔 (HTTP 모드)
promptaudit scan --system-prompt prompt.txt --target-url http://localhost:8001/chat

# 공격 수 조정 (비용/시간 제어)
promptaudit scan --system-prompt prompt.txt --max-attacks 10

# 결과를 파일로 저장
promptaudit scan --system-prompt prompt.txt --format markdown --out report.md

# JSON 형식 출력
promptaudit scan --system-prompt prompt.txt --format json --out report.json

# CI/CD 게이트 (success 발견 시 exit 1)
promptaudit scan --system-prompt prompt.txt --fail-on success
```

## LLM Provider 전환

```bash
# Google Gemini 무료 티어
export PROMPTAUDIT_LLM_PROVIDER="gemini"
export GEMINI_API_KEY="AIza..."

# Anthropic Claude
export PROMPTAUDIT_LLM_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="sk-ant-..."

# 사내 LLM 게이트웨이
export PROMPTAUDIT_LLM_PROVIDER="enterprise-gateway"
export PROMPTAUDIT_GATEWAY_URL="https://internal-llm.example.com/v1"
export PROMPTAUDIT_GATEWAY_API_KEY="..."
```

## Python 코드에서 Skill로 사용

```python
import asyncio
from promptaudit.generator import generate_attacks
from promptaudit.runner import run_attacks
from promptaudit.evaluator import evaluate_results
from promptaudit.reporter import generate_report, to_markdown
from promptaudit.models import AttackVector

async def audit(system_prompt: str):
    scenarios = await generate_attacks(system_prompt, AttackVector.DIRECT, max_attacks=5)
    responses = await run_attacks(system_prompt, scenarios)
    evaluated = await evaluate_results(system_prompt, responses)
    report = generate_report(evaluated, system_prompt)
    print(to_markdown(report))

asyncio.run(audit("You are a helpful assistant. Only answer about our products."))
```

## OWASP LLM Top 10 대응

| OWASP 항목 | 설명 | 탐지 여부 |
|---|---|---|
| LLM01:2025 | Prompt Injection | ✅ |
| LLM06:2025 | Sensitive Information Disclosure | ✅ |

## 공격 벡터 (MVP)

- **Direct Injection**: 사용자 입력으로 시스템 지시를 직접 무력화하는 공격
  - 역할 무력화 ("Ignore all previous instructions")
  - 시스템 프롬프트 누설 요청
  - DAN (Do Anything Now) 역할 전환
  - SYSTEM UPDATE 사칭
  - 개발자 모드 활성화 시도
  - 토큰 구조 조작
  - 권한 위임 사칭

## 라이선스

Apache 2.0
