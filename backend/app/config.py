from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "圆桌投研"
    env: str = "dev"

    database_url: str = "postgresql+asyncpg://yuanzhuo:yuanzhuo@127.0.0.1:5432/yuanzhuo"
    redis_url: str = "redis://127.0.0.1:6379/0"

    # Claude relay (M1+ 填)
    relay_base_url: str = ""
    relay_api_key: str = ""

    conductor_model: str = "claude-opus-4-7"
    default_advisor_model: str = "claude-sonnet-4-6"
    router_model: str = "claude-haiku-4-5"

    # 数据源
    choice_user: str = ""
    choice_password: str = ""
    tushare_token: str = ""

    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
