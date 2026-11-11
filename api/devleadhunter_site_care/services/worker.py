"""The module's background loop: it runs the searches, and between two searches keeps the old checks fresh."""

from __future__ import annotations

import asyncio
import logging
from typing import ClassVar

from devleadhunter_site_care.services.search_service import search_service
from devleadhunter_site_care.services.watch_service import watch_service

logger = logging.getLogger(__name__)


class SiteCareWorker:
    """
    Works while the module is switched on: the core starts :meth:`run_forever` and cancels it with the switch.

    A search is worked on batch after batch without a pause; once none is waiting, a few old checks are refreshed
    and a few towns the open map left unnamed are looked up.
    """

    _IDLE_SECONDS: ClassVar[float] = 20.0
    _BUSY_SECONDS: ClassVar[float] = 1.0

    async def run_forever(self) -> None:
        """Loop until the core cancels the task."""
        while True:
            is_search_running: bool = await self.run_once()
            await asyncio.sleep(self._BUSY_SECONDS if is_search_running else self._IDLE_SECONDS)

    async def run_once(self) -> bool:
        """
        One pass of the loop.

        Returns:
            True when a search was worked on (the next pass should follow at once).
        """
        try:
            if await search_service.run_next_batch():
                return True
            await watch_service.recheck_due_sites()
            await search_service.name_missing_towns()
        except Exception:
            logger.exception("[SiteCare] background pass failed")
        return False


site_care_worker = SiteCareWorker()
