from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"

    # 端口
    port: int = 9001

    # SDK 在容器 / 本地的物理位置（运行时通过 PYTHONPATH 加进 sys.path）
    # 同时这个目录也是 ServerList.json.e + userInfo 的存放处
    sdk_path: str = "/sdk"  # 容器默认；本地跑改 .env

    # 短信激活模式下的手机号（一次性参数，不强制）
    choice_phone: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
