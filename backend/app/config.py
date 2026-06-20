from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "圆桌投研"
    env: str = "dev"

    database_url: str = "postgresql+asyncpg://yuanzhuo:yuanzhuo@127.0.0.1:5432/yuanzhuo"
    redis_url: str = "redis://127.0.0.1:6379/0"

    # LLM 模型经 LiteLLM 调用，配置在「模型配置」页（DB）里按角色填，不走 env。
    # 此密钥用于把前端填的 API key 落库前 Fernet 加密：务必设成稳定的强随机串，
    # 改了会导致已存的 key 解不开。留空则回退到 ACCESS_PASSWORD / 固定兜底（仅开发）。
    llm_config_secret: str = ""

    # 数据源凭据 —— Choice 账密在 choice-gateway/.env 里，backend 仅通过 HTTP 调 gateway
    # Gateway 地址留空 → ChoiceProvider 不启用，链上直接落到 Tushare / Mock
    choice_gateway_url: str = ""
    tushare_token: str = ""

    # 允许的前端来源（CORS 白名单）
    cors_origins: list[str] = ["http://localhost:3000"]

    # 访问密钥：防陌生人滥用。为空 → 不设防（开发）；非空 → /api/chat 等
    # 受保护接口必须带 X-Access-Key 头且匹配，否则 401。
    access_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
