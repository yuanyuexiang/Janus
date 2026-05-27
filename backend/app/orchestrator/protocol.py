"""Structured protocols — advisor opinion + conductor's council summary."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    claim: str
    detail: str
    source_tool: str | None = None


class AdvisorOpinion(BaseModel):
    agent: str
    stance: Literal["bullish", "neutral", "bearish", "conditional"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary_for_user: str
    key_points: list[Evidence] = []
    concerns: list[str] = []
    what_could_change_my_mind: list[str] = []


class RiskItem(BaseModel):
    risk: str
    severity: int = Field(ge=1, le=5)
    mitigation: str | None = None


class DisagreementItem(BaseModel):
    point: str
    sides: dict[str, list[str]]  # {"bullish": [...], "bearish": [...], "conditional": [...]}


class CouncilSummary(BaseModel):
    verdict: Literal["strong_consensus", "weak_consensus", "split"]
    consensus: list[str] = []
    disagreements: list[DisagreementItem] = []
    key_variables: list[str] = []
    risk_map: list[RiskItem] = []
    final_summary: str  # 100 字左右，强调决策权在用户


OPINION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["stance", "confidence", "summary_for_user"],
    "properties": {
        "stance": {"enum": ["bullish", "neutral", "bearish", "conditional"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "summary_for_user": {"type": "string"},
        "key_points": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["claim", "detail"],
                "properties": {
                    "claim": {"type": "string"},
                    "detail": {"type": "string"},
                    "source_tool": {"type": ["string", "null"]},
                },
            },
        },
        "concerns": {"type": "array", "items": {"type": "string"}},
        "what_could_change_my_mind": {"type": "array", "items": {"type": "string"}},
    },
}
