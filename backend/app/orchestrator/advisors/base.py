"""顾问基类。M1 只有明哥；M2 起补齐其余顾问。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AdvisorProfile:
    name: str          # 内部标识，例如 "ming_ge"
    display: str       # 展示名，例如 "明哥"
    role: str          # 角色标签，例如 "价值"
    color: str         # 强调色（hex），前端用
    tagline: str       # 一句话座右铭


class BaseAdvisor(ABC):
    profile: AdvisorProfile
    model: str | None = None  # None 表示采用 settings.default_advisor_model
    allowed_tools: list[str] = []

    @abstractmethod
    def system_prompt(self) -> str: ...
