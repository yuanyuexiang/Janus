"""Advisor base class. M1 only ships 明哥; M2 adds the rest."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AdvisorProfile:
    name: str          # internal id, e.g. "ming_ge"
    display: str       # public-facing name, e.g. "明哥"
    role: str          # role tag, e.g. "价值"
    color: str         # accent color (hex), used in frontend
    tagline: str       # one-line motto


class BaseAdvisor(ABC):
    profile: AdvisorProfile
    model: str | None = None  # None means use settings.default_advisor_model
    allowed_tools: list[str] = []

    @abstractmethod
    def system_prompt(self) -> str: ...
