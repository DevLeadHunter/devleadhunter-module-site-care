"""The current WordPress branch, asked to wordpress.org once a day."""

from __future__ import annotations

import logging
import re
import time
from typing import ClassVar

import httpx

from devleadhunter_site_care.catalog import WORDPRESS_FALLBACK_BRANCH

logger = logging.getLogger(__name__)


class WordPressReleases:
    """Knows which WordPress branch is current, so a site's version is compared with the real one."""

    _VERSION_CHECK_URL: ClassVar[str] = "https://api.wordpress.org/core/version-check/1.7/"
    _CACHE_SECONDS: ClassVar[float] = 24 * 3600.0
    _RETRY_SECONDS: ClassVar[float] = 3600.0

    def __init__(self) -> None:
        self._branch: tuple[int, int] = WORDPRESS_FALLBACK_BRANCH
        self._asked_again_after: float = 0.0

    async def current_branch(self) -> tuple[int, int]:
        """
        The current WordPress branch.

        Returns:
            (major, minor) of the latest release; the last known branch when wordpress.org does not answer.
        """
        now: float = time.monotonic()
        if now < self._asked_again_after:
            return self._branch
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response: httpx.Response = await client.get(self._VERSION_CHECK_URL)
                response.raise_for_status()
                version: str = str(response.json()["offers"][0]["version"])
            parsed: re.Match[str] | None = re.match(r"(\d+)\.(\d+)", version)
            if parsed is None:
                raise ValueError(f"unreadable version {version!r}")
            self._branch = (int(parsed.group(1)), int(parsed.group(2)))
            self._asked_again_after = now + self._CACHE_SECONDS
        except Exception as exc:
            logger.warning("[SiteCare] wordpress.org did not give its current version: %s", exc)
            self._asked_again_after = now + self._RETRY_SECONDS
        return self._branch


wordpress_releases = WordPressReleases()
