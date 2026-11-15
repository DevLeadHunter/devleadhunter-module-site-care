"""The assistant's answer about the sites: the shared parts, and the lines of the sites found."""

from __future__ import annotations

from pydantic import Field

from schemas.module_assistant import AssistantAnswer

from devleadhunter_site_care.schemas.site import SiteListItem


class SiteCareAssistantAnswer(AssistantAnswer):
    """
    An answer of the assistant.

    Attributes:
        cards: The sites found, the most pressing first, the same lines as « Mes prospects ».
    """

    cards: list[SiteListItem] = Field(default_factory=list[SiteListItem])
