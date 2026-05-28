"""Skill 注册表：解析每次顾问发言要注入哪些 Skill 包到 system prompt。

每个 Skill 是一个目录，里面放 SKILL.md。三种加载策略：

- always-on：每次发言都加载（合规规则 / 输出协议）
- trigger-based：根据 question + 任务上下文做关键词匹配
- agent-bound：由顾问自己声明绑定哪些 Skill
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

SKILLS_ROOT = Path(__file__).parent


class SkillRegistry:
    ALWAYS_ON: list[str] = [
        "common/no-fabrication",
        "common/evidence-citation",
        "common/structured-opinion",
    ]

    TRIGGER_BASED: dict[str, list[str]] = {
        "methodology/risk-assessment": [
            "风险", "压力测试", "下行", "黑天鹅", "系统性", "波动",
        ],
        # 占位：v2 §8.5 规划的 Skill —— 文件未写时会被静默跳过
        # "output-templates/dcf-valuation": ["DCF", "估值", "内在价值", "自由现金流"],
        # "output-templates/earnings-review": ["财报", "季报", "年报", "业绩"],
        # "output-templates/industry-landscape": ["行业", "赛道", "竞争格局", "产业链"],
    }

    AGENT_BOUND: dict[str, list[str]] = {
        "ming_ge": ["agent-bound/value-methodology"],
        "rui_feng": ["agent-bound/trend-methodology"],
        "ling_du": ["agent-bound/quant-backtesting"],
    }

    def resolve(
        self,
        *,
        question: str,
        agent: str,
        task_context: str = "",
        force_skills: list[str] | None = None,
    ) -> list[str]:
        skills = list(self.ALWAYS_ON)
        haystack = (question + " " + task_context).lower()

        for skill_path, keywords in self.TRIGGER_BASED.items():
            if any(kw.lower() in haystack for kw in keywords):
                skills.append(skill_path)

        skills.extend(self.AGENT_BOUND.get(agent, []))

        if force_skills:
            skills.extend(force_skills)

        # 保持顺序去重；丢弃磁盘上不存在的 Skill
        seen: set[str] = set()
        out: list[str] = []
        for s in skills:
            if s in seen:
                continue
            if not (SKILLS_ROOT / s / "SKILL.md").exists():
                continue
            seen.add(s)
            out.append(s)
        return out

    def load_texts(self, skill_paths: Iterable[str]) -> list[str]:
        texts: list[str] = []
        for p in skill_paths:
            path = SKILLS_ROOT / p / "SKILL.md"
            texts.append(path.read_text(encoding="utf-8"))
        return texts


_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
