"""顾问注册表。M2.5 起 6 位顾问全部就位；mini（3 人）和 full（6 人）两种圆桌可选。"""

from app.orchestrator.advisors.base import BaseAdvisor
from app.orchestrator.advisors.lan_jie import LanJie
from app.orchestrator.advisors.leng_chuan import LengChuan
from app.orchestrator.advisors.ling_du import LingDu
from app.orchestrator.advisors.ming_ge import MingGe
from app.orchestrator.advisors.rui_feng import RuiFeng
from app.orchestrator.advisors.tao_shu import TaoShu

_INSTANCES: list[BaseAdvisor] = [
    TaoShu(),
    LanJie(),
    MingGe(),
    RuiFeng(),
    LengChuan(),
    LingDu(),
]

ALL_ADVISORS: dict[str, BaseAdvisor] = {a.profile.name: a for a in _INSTANCES}

MINI_COUNCIL: list[str] = ["tao_shu", "lan_jie", "ming_ge"]
FULL_COUNCIL: list[str] = ["tao_shu", "lan_jie", "ming_ge", "rui_feng", "leng_chuan", "ling_du"]


def get_advisor(name: str) -> BaseAdvisor | None:
    return ALL_ADVISORS.get(name)


def get_mini_council() -> list[BaseAdvisor]:
    return [ALL_ADVISORS[n] for n in MINI_COUNCIL]


def get_full_council() -> list[BaseAdvisor]:
    return [ALL_ADVISORS[n] for n in FULL_COUNCIL]
