"""Structured opinion protocol — what every advisor must return as final output."""

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
