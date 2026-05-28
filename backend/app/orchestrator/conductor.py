"""执棋 Conductor —— 编排 mini / full 圆桌：

  1. 并行 spawn N 位顾问
  2. 把各顾问的事件流 fan-in 合成单一 SSE 流
  3. 收集每位顾问最终的 AdvisorOpinion
  4. 把 opinions 交给 synthesizer 产出综合结论
  5. 最后吐 'council_done' 收尾

所有从顾问冒上来的事件都会被加上 `advisor: <name>` 字段，方便前端路由到
对应的气泡。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from anthropic import APIStatusError

from app.orchestrator.advisors.base import BaseAdvisor
from app.orchestrator.protocol import AdvisorOpinion
from app.orchestrator.runner import run_advisor
from app.orchestrator.synthesizer import synthesize

logger = logging.getLogger(__name__)

_END = object()


async def _advisor_producer(
    advisor: BaseAdvisor,
    question: str,
    queue: asyncio.Queue,
) -> None:
    name = advisor.profile.name
    try:
        async for event in run_advisor(advisor, question):
            await queue.put((name, event))
    except APIStatusError:
        # 透传给上层：让 chat.py 输出**一条**友好的 RELAY_* 错误，避免每个并行
        # 顾问都吐一份 ADVISOR_CRASHED 噪音。
        raise
    except Exception as e:
        logger.exception("Advisor %s failed", name)
        await queue.put(
            (
                name,
                {
                    "type": "error",
                    "code": "ADVISOR_CRASHED",
                    "message": f"{type(e).__name__}: {e}",
                },
            )
        )
    finally:
        await queue.put((name, _END))


async def run_council(
    advisors: list[BaseAdvisor],
    question: str,
) -> AsyncIterator[dict[str, Any]]:
    """驱动一轮圆桌讨论。事件凡涉及具体顾问的都会带上 `advisor` 字段。"""
    advisor_names = [a.profile.name for a in advisors]
    yield {"type": "council_start", "advisors": advisor_names}

    queue: asyncio.Queue = asyncio.Queue()
    tasks = [
        asyncio.create_task(_advisor_producer(a, question, queue)) for a in advisors
    ]
    pending = set(advisor_names)
    opinions: dict[str, AdvisorOpinion] = {}

    try:
        while pending:
            name, event = await queue.get()
            if event is _END:
                pending.discard(name)
                yield {"type": "advisor_done", "advisor": name}
                continue

            # 给事件打上 advisor 标签，方便前端路由。
            # advisor_start 自带 advisor 字段；其它事件可能没有，统一补齐。
            tagged = dict(event)
            tagged.setdefault("advisor", name)
            yield tagged

            if event.get("type") == "opinion":
                try:
                    opinions[name] = AdvisorOpinion.model_validate(event["full"])
                except Exception:
                    logger.exception("顾问 %s 的 opinion 校验失败", name)
    finally:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 把 relay 级错误（比如 402 余额不足）抛出去，让 chat.py 给出友好的
        # RELAY_* 提示，而不是假装一切正常。
        for r in results:
            if isinstance(r, APIStatusError):
                raise r

    if not opinions:
        yield {
            "type": "error",
            "code": "NO_OPINIONS",
            "message": "没有顾问产出有效观点；跳过综合阶段",
        }
        yield {"type": "council_done"}
        return

    yield {"type": "synthesis_start", "opinion_count": len(opinions)}

    async for ev in synthesize(question=question, opinions=list(opinions.values())):
        yield ev

    yield {"type": "council_done"}
