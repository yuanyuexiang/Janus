"""Probe relay: verify Anthropic-protocol compatibility through the configured relay."""

import asyncio

from anthropic import AsyncAnthropic

from app.config import get_settings


async def main() -> None:
    settings = get_settings()
    if not settings.relay_base_url or not settings.relay_api_key:
        raise SystemExit("RELAY_BASE_URL / RELAY_API_KEY not set in .env")

    client = AsyncAnthropic(
        base_url=settings.relay_base_url.rstrip("/"),
        api_key=settings.relay_api_key,
    )

    print(f"→ POST {settings.relay_base_url} model={settings.router_model}")
    resp = await client.messages.create(
        model=settings.router_model,
        max_tokens=64,
        messages=[{"role": "user", "content": "Reply with the single word: pong"}],
    )
    print(f"← stop_reason={resp.stop_reason}  usage={resp.usage}")
    for block in resp.content:
        if block.type == "text":
            print(f"  text: {block.text!r}")


if __name__ == "__main__":
    asyncio.run(main())
