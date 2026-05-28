"""ChoiceProvider — placeholder for East Money's EmQuantAPI integration.

Status (2026-05-28): NOT YET ACTIVATED. The reasons:

1. `EmQuantAPI` is not published on PyPI — it's distributed as a per-platform
   tarball from `quant.eastmoney.com` (官网下载需登录).
2. The Mac build is x86_64 only and historically tied to specific Python
   versions; Apple Silicon (M1/M2/M4) needs Rosetta + a matching Python.
3. The SDK uses a persistent login session that prefers a desktop client to
   be running — server-side headless login flakiness is well documented.

To activate later (Windows VM or x86 environment):
  1. Download the EmQuantAPI tarball from East Money
  2. `pip install ./EmQuantAPI-*.tar.gz` inside the venv
  3. Set `CHOICE_USER` and `CHOICE_PASSWORD` in `.env`
  4. Uncomment the `try: from EmQuantAPI ...` block in this file
  5. Add ChoiceProvider to the DataSource chain (datasource.py:_build_chain)
"""

from __future__ import annotations

import logging

from app.data.providers.base import DataProvider

logger = logging.getLogger(__name__)


class ChoiceProvider(DataProvider):
    """Inactive stub. Returns None for every method so the chain falls through."""

    name = "choice"

    def __init__(self, user: str, password: str) -> None:
        self.user = user
        self.password = password
        # try:
        #     from EmQuantAPI import c
        #     result = c.start("ForceLogin=1", "", f"UserName={user},Password={password}")
        #     if result.ErrorCode != 0:
        #         raise RuntimeError(f"Choice login failed: {result.ErrorMsg}")
        #     self._c = c
        # except ImportError:
        #     logger.warning("EmQuantAPI not installed; ChoiceProvider inert")
        #     self._c = None
        logger.info("ChoiceProvider initialised (inert; SDK not installed)")
