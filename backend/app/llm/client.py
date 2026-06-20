"""LLM 调用层 —— 基于 LiteLLM 的统一封装（OpenAI 格式）。

为什么用 LiteLLM：一套 OpenAI 风格的调用对接 100+ 厂商（OpenAI / Anthropic /
通义 / DeepSeek / 文心 / Ollama 本地模型 …），客户改配置即可换模型，不碰代码。

本模块对外暴露两个入口：
  - stream_chat(...)  流式，yield 文本增量；最后一个 done 事件带完整文本 + 工具调用 + usage
  - complete(...)     非流式，返回 (文本, usage)

模型/凭据由 resolve_target(role) 解析。
  阶段 A：从环境变量（现有 relay，Anthropic 兼容端点）解析 —— 行为对齐，先把库换掉。
  阶段 B：改成优先读 DB 里的前端配置（按角色存 model/api_key/api_base）。
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import litellm
from litellm.exceptions import (
    APIError as LLMAPIError,  # noqa: F401  统一的 LLM API 错误基类（含 status_code）
)

logger = logging.getLogger(__name__)

__all__ = [
    "stream_chat",
    "complete",
    "resolve_target",
    "is_configured",
    "configured_model_name",
    "test_target",
    "LLMAPIError",
    "LLMNotConfigured",
]

# LiteLLM 全局开关：少打日志、不上报遥测、自动丢弃某模型不支持的参数（避免 400）
litellm.suppress_debug_info = True
litellm.telemetry = False
litellm.drop_params = True


@dataclass
class LLMTarget:
    model: str          # 完整 litellm 模型串，如 "openai/gpt-4o"
    api_base: str | None
    api_key: str | None


class LLMNotConfigured(RuntimeError):
    """该角色还没在「模型配置」页接入模型。"""

    def __init__(self, role: str) -> None:
        super().__init__(f"角色「{role}」未配置模型，请在模型配置页接入")
        self.role = role


def configured_model_name(role: str) -> str | None:
    """该角色当前配置的模型串（仅用于展示/落库标签），未配置返回 None。"""
    from app.llm import settings_store

    cfg = settings_store.get(role)
    return cfg.get("model") if cfg else None


def resolve_target(role: str, model_override: str | None = None) -> LLMTarget:
    """role ∈ {conductor, advisor, router}。读前端「模型配置」（DB）里该角色的
    model/api_key/api_base。未配置则抛 LLMNotConfigured。
    模型串用「厂商/模型」形式（openai/gpt-4o…）；裸名默认按 openai 兼容端点。"""
    from app.llm import settings_store

    cfg = settings_store.get(role)
    if not (cfg and cfg.get("model")):
        raise LLMNotConfigured(role)
    model = model_override or cfg["model"]
    model = model if "/" in model else f"openai/{model}"
    return LLMTarget(
        model=model,
        api_base=(cfg.get("api_base") or None),
        api_key=(cfg.get("api_key") or None),
    )


def _build_messages(system: str | None, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """OpenAI 格式把 system 当成一条消息放最前。"""
    if system:
        return [{"role": "system", "content": system}, *messages]
    return list(messages)


def _common_kwargs(target: LLMTarget) -> dict[str, Any]:
    kw: dict[str, Any] = {"model": target.model}
    if target.api_base:
        kw["api_base"] = target.api_base
    if target.api_key:
        kw["api_key"] = target.api_key
    return kw


async def stream_chat(
    *,
    role: str,
    messages: list[dict[str, Any]],
    system: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int = 2048,
    model_override: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """流式对话。事件：
      {"type": "text", "chunk": "..."}            文本增量
      {"type": "done", "text", "tool_calls", "finish_reason", "tokens_in", "tokens_out"}
        tool_calls: [{"id", "name", "args": dict}]  —— 已把 OpenAI 分片累积好、参数解析成 dict
    """
    target = resolve_target(role, model_override)
    kwargs = _common_kwargs(target)
    kwargs.update(
        messages=_build_messages(system, messages),
        max_tokens=max_tokens,
        stream=True,
        stream_options={"include_usage": True},
    )
    if tools:
        kwargs["tools"] = tools

    resp = await litellm.acompletion(**kwargs)

    text_parts: list[str] = []
    tool_acc: dict[int, dict[str, Any]] = {}
    tokens_in = 0
    tokens_out = 0
    finish_reason: str | None = None

    async for chunk in resp:
        choices = getattr(chunk, "choices", None) or []
        if choices:
            choice = choices[0]
            delta = getattr(choice, "delta", None)
            if delta is not None:
                content = getattr(delta, "content", None)
                if content:
                    text_parts.append(content)
                    yield {"type": "text", "chunk": content}
                for tc in getattr(delta, "tool_calls", None) or []:
                    idx = getattr(tc, "index", 0) or 0
                    slot = tool_acc.setdefault(idx, {"id": None, "name": None, "args": ""})
                    if getattr(tc, "id", None):
                        slot["id"] = tc.id
                    fn = getattr(tc, "function", None)
                    if fn is not None:
                        if getattr(fn, "name", None):
                            slot["name"] = fn.name
                        if getattr(fn, "arguments", None):
                            slot["args"] += fn.arguments
            if getattr(choice, "finish_reason", None):
                finish_reason = choice.finish_reason
        usage = getattr(chunk, "usage", None)
        if usage:
            tokens_in = getattr(usage, "prompt_tokens", 0) or tokens_in
            tokens_out = getattr(usage, "completion_tokens", 0) or tokens_out

    tool_calls: list[dict[str, Any]] = []
    for idx in sorted(tool_acc):
        slot = tool_acc[idx]
        if not slot["name"]:
            continue
        raw_args = (slot["args"] or "").strip()
        try:
            args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError:
            logger.warning("工具调用参数非合法 JSON：%r", raw_args[:200])
            args = {}
        tool_calls.append(
            {"id": slot["id"] or f"call_{idx}", "name": slot["name"], "args": args}
        )

    yield {
        "type": "done",
        "text": "".join(text_parts),
        "tool_calls": tool_calls,
        "finish_reason": finish_reason,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


async def complete(
    *,
    role: str,
    messages: list[dict[str, Any]],
    system: str | None = None,
    max_tokens: int = 256,
    model_override: str | None = None,
) -> tuple[str, dict[str, int]]:
    """非流式。返回 (文本, {"tokens_in", "tokens_out"})。"""
    target = resolve_target(role, model_override)
    kwargs = _common_kwargs(target)
    kwargs.update(
        messages=_build_messages(system, messages),
        max_tokens=max_tokens,
        stream=False,
    )
    resp = await litellm.acompletion(**kwargs)
    text = (resp.choices[0].message.content or "") if resp.choices else ""
    usage_obj = getattr(resp, "usage", None)
    usage = {
        "tokens_in": getattr(usage_obj, "prompt_tokens", 0) or 0,
        "tokens_out": getattr(usage_obj, "completion_tokens", 0) or 0,
    }
    return text, usage


def is_configured(role: str | None = None) -> bool:
    """前端是否配过模型。role=None 表示「任一角色配过」。"""
    from app.llm import settings_store

    roles = (role,) if role else ("conductor", "advisor", "router")
    return any((settings_store.get(r) or {}).get("model") for r in roles)


async def test_target(model: str, api_base: str | None, api_key: str | None) -> tuple[bool, str]:
    """用给定模型/凭据做一次最小调用，测连通性。返回 (是否成功, 提示)。"""
    full = model if "/" in model else f"openai/{model}"
    try:
        await litellm.acompletion(
            model=full,
            api_base=(api_base or None),
            api_key=(api_key or None),
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
            stream=False,
        )
        return True, "连接成功"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:200]}"
