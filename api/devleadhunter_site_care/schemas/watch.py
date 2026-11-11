"""What the watch route returns (see ``docs/API.md``)."""

from __future__ import annotations

from pydantic import BaseModel


class WatchTarget(BaseModel):
    """Where a line's button leads: one site's sheet, or « Mes prospects » filtered."""

    site_id: int | None = None
    tab: str | None = None
    kind: str | None = None


class WatchEventView(BaseModel):
    """One line of the watch page."""

    key: str
    kind: str
    tone: str
    title: str
    detail: str
    when_label: str
    site_count: int
    action_label: str
    target: WatchTarget


class WatchResponse(BaseModel):
    """The watch page."""

    today: list[WatchEventView]
    deadlines: list[WatchEventView]
