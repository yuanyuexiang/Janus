from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "圆桌投研"
    env: str = "dev"

    database_url: str = "postgresql+asyncpg://yuanzhuo:yuanzhuo@127.0.0.1:5432/yuanzhuo"
    redis_url: str = "redis://127.0.0.1:6379/0"

    # Claude 中转配置（M1 以后填）
    relay_base_url: str = ""
    relay_api_key: str = ""

    # 三档模型路由：主持人 / 默认顾问 / 路由分类器
    conductor_model: str = "claude-opus-4-7"
    default_advisor_model: str = "claude-sonnet-4-6"
    router_model: str = "claude-haiku-4-5"

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
