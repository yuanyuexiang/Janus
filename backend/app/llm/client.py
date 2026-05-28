from functools import lru_cache

from anthropic import AsyncAnthropic

from app.config import get_settings


@lru_cache
def get_client() -> AsyncAnthropic:
    settings = get_settings()
    if not settings.relay_base_url or not settings.relay_api_key:
        raise RuntimeError("RELAY_BASE_URL / RELAY_API_KEY 未配置")
    return AsyncAnthropic(
        base_url=settings.relay_base_url.rstrip("/"),
        api_key=settings.relay_api_key,
    )
