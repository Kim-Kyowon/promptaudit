from enum import Enum
from pydantic import BaseModel, Field


class AttackVector(str, Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    JAILBREAK = "jailbreak"


class AttackResult(str, Enum):
    SUCCESS = "success"    # 공격 성공 — 시스템 지시 무력화
    PARTIAL = "partial"    # 부분 성공 — 정보 누설
    FAILURE = "failure"    # 방어 성공


class AttackScenario(BaseModel):
    id: str
    vector: AttackVector
    payload: str
    description: str
    owasp_ref: str


class AttackResponse(BaseModel):
    scenario: AttackScenario
    response: str
    latency_ms: float


class EvaluatedResult(BaseModel):
    scenario: AttackScenario
    response: str
    result: AttackResult
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class AuditReport(BaseModel):
    system_prompt_preview: str
    total_attacks: int
    success_count: int
    partial_count: int
    failure_count: int
    results: list[EvaluatedResult]
    owasp_findings: dict[str, list[EvaluatedResult]]
    generated_at: str
