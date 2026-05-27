"""Probe which model IDs this relay accepts."""

import asyncio

from anthropic import AsyncAnthropic, NotFoundError, PermissionDeniedError

from app.config import get_settings

CANDIDATES = [
    # Haiku family
    "claude-haiku-4-5",
    "claude-haiku-4-5-20251001",
    "claude-3-5-haiku-latest",
    "claude-3-5-haiku-20241022",
    # Sonnet family
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-sonnet-4-20250514",
    "claude-3-5-sonnet-latest",
    "claude-3-5-sonnet-20241022",
    # Opus family
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-opus-4-5",
    "claude-opus-4-1-20250805",
    "claude-opus-4-20250514",
]


async def try_model(client: AsyncAnthropic, model: str) -> str:
    try:
        resp = await client.messages.create(
            model=model,
            max_tokens=8,
            messages=[{"role": "user", "content": "say: ok"}],
        )
        text = next((b.text for b in resp.content if b.type == "text"), "")
        return f"  ✓ {model}  → {text!r}  (input={resp.usage.input_tokens} output={resp.usage.output_tokens})"
    except PermissionDeniedError as e:
        return f"  ✗ {model}  PERM: {e.body.get('error', {}).get('message', str(e))[:120]}"
    except NotFoundError as e:
        return f"  ✗ {model}  404:  {e.body.get('error', {}).get('message', str(e))[:120]}"
    except Exception as e:
        return f"  ✗ {model}  ERR:  {type(e).__name__}: {str(e)[:120]}"


async def main() -> None:
    settings = get_settings()
    client = AsyncAnthropic(
        base_url=settings.relay_base_url.rstrip("/"),
        api_key=settings.relay_api_key,
    )
    print(f"Relay: {settings.relay_base_url}\n")
    results = await asyncio.gather(*(try_model(client, m) for m in CANDIDATES))
    for line in results:
        print(line)


if __name__ == "__main__":
    asyncio.run(main())
