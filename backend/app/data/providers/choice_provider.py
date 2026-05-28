"""ChoiceProvider —— 东方财富 EmQuantAPI 的占位实现。

状态（2026-05-28）：**尚未启用**。原因：

1. `EmQuantAPI` 没发布到 PyPI —— 走 `quant.eastmoney.com` 官网按平台下载
   tarball（需要登录）。
2. Mac 版本仅有 x86_64 构建，且绑定特定 Python 版本；Apple Silicon
   （M1/M2/M4）需要 Rosetta + 对应版本的 Python。
3. SDK 用的是持久登录会话，更适合本地桌面客户端在跑 —— 服务器无头登录稳定性
   问题已被多人吐过。

后续启用路径（Windows 虚拟机或 x86 环境）：
  1. 从东方财富官网下载 EmQuantAPI tarball
  2. 在 venv 里执行 `pip install ./EmQuantAPI-*.tar.gz`
  3. 在 `.env` 中配置 `CHOICE_USER` 和 `CHOICE_PASSWORD`
  4. 取消下方 `try: from EmQuantAPI ...` 代码块的注释
  5. 把 ChoiceProvider 加进 DataSource 链（datasource.py:_build_chain）
"""

from __future__ import annotations

import logging

from app.data.providers.base import DataProvider

logger = logging.getLogger(__name__)


class ChoiceProvider(DataProvider):
    """未激活的占位 provider。所有方法返回 None，让 DataSource 自动落到下一个 provider。"""

    name = "choice"

    def __init__(self, user: str, password: str) -> None:
        self.user = user
        self.password = password
        # try:
        #     from EmQuantAPI import c
        #     result = c.start("ForceLogin=1", "", f"UserName={user},Password={password}")
        #     if result.ErrorCode != 0:
        #         raise RuntimeError(f"Choice 登录失败: {result.ErrorMsg}")
        #     self._c = c
        # except ImportError:
        #     logger.warning("EmQuantAPI 未安装；ChoiceProvider 处于未激活状态")
        #     self._c = None
        logger.info("ChoiceProvider 已初始化（未激活；SDK 未安装）")
