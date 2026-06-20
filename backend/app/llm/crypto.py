"""API key 落库加密（Fernet）。

Fernet 密钥由 LLM_CONFIG_SECRET 派生（sha256 → urlsafe base64）。
密钥必须稳定：改了会导致已存的密文解不开。生产务必设 LLM_CONFIG_SECRET。
"""

from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def _fernet() -> Fernet:
    s = get_settings()
    secret = s.llm_config_secret or s.access_password or "janus-default-dev-secret"
    if not s.llm_config_secret:
        logger.warning("LLM_CONFIG_SECRET 未设置，回退派生密钥 —— 生产请务必设置稳定强随机串")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    """解密；失败（密钥变了 / 密文损坏）返回空串。"""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except Exception:
        logger.warning("API key 解密失败（密钥可能已变更）")
        return ""
