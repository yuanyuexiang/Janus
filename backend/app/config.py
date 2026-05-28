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

    # 数据源凭据
    # CHOICE_USER / CHOICE_PASSWORD 已废弃 —— Choice SDK 不支持账密直登，
    # 现在通过独立的 choice-gateway 服务 + 短信激活方式登录。
    # 保留字段是为了 .env 不报错。
    choice_user: str = ""
    choice_password: str = ""
    # Choice Gateway 服务地址；为空表示不启用 ChoiceProvider，链上直接落到 Tushare/Mock
    choice_gateway_url: str = ""
    tushare_token: str = ""

    # 允许的前端来源（CORS 白名单）
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
