"""Skill registry: resolves which Skill packs to inject into an advisor's system prompt.

Each Skill lives in a directory containing SKILL.md. Three load strategies:

- always-on: every advisor turn loads it (compliance / output protocol)
- trigger-based: keyword match against question + task context
- agent-bound: declared by the advisor itself
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

SKILLS_ROOT = Path(__file__).parent


class SkillRegistry:
    ALWAYS_ON: list[str] = [
        "common/no_fabrication",
        "common/evidence_citation",
        "common/structured_opinion",
    ]

    TRIGGER_BASED: dict[str, list[str]] = {
        "methodology/risk_assessment": [
            "风险", "压力测试", "下行", "黑天鹅", "系统性", "波动",
        ],
        # placeholders for v2 §8.5 — Skills not yet written are silently skipped
        # "output_templates/dcf_valuation": ["DCF", "估值", "内在价值", "自由现金流"],
        # "output_templates/earnings_review": ["财报", "季报", "年报", "业绩"],
        # "output_templates/industry_landscape": ["行业", "赛道", "竞争格局", "产业链"],
    }

    AGENT_BOUND: dict[str, list[str]] = {
        "ming_ge": ["agent_bound/value_methodology"],
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

        # de-dup preserving order; drop missing
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
