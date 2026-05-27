"""Conductor (执棋) — orchestrates mini/full council:

  1. Spawns N advisors in parallel
  2. Fan-in each advisor's event stream into a single tagged SSE stream
  3. Collects each advisor's final AdvisorOpinion
  4. Hands opinions to the synthesizer for the council summary
  5. Yields final 'council_done' marker

All events bubbled from advisors are tagged with `advisor: <name>` so the frontend
can route them to the right bubble.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

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
    """Drive a council turn. Yields events tagged with `advisor` field where applicable."""
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

            # Tag event with advisor for frontend routing.
            # advisor_start already carries its own advisor field; others may not.
            tagged = dict(event)
            tagged.setdefault("advisor", name)
            yield tagged

            if event.get("type") == "opinion":
                try:
                    opinions[name] = AdvisorOpinion.model_validate(event["full"])
                except Exception:
                    logger.exception("Invalid opinion from %s", name)
    finally:
        await asyncio.gather(*tasks, return_exceptions=True)

    if not opinions:
        yield {
            "type": "error",
            "code": "NO_OPINIONS",
            "message": "No advisor produced a valid opinion; skipping synthesis",
        }
        yield {"type": "council_done"}
        return

    yield {"type": "synthesis_start", "opinion_count": len(opinions)}

    async for ev in synthesize(question=question, opinions=list(opinions.values())):
        yield ev

    yield {"type": "council_done"}
