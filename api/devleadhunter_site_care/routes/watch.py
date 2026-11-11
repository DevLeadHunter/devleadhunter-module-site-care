"""« Veille »: what changed on the user's sites and the dates coming up."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.database import get_db
from models.user import User
from services.auth_service import get_current_active_user

from devleadhunter_site_care.schemas.watch import WatchEventView, WatchResponse, WatchTarget
from devleadhunter_site_care.services.watch_service import WatchLine, watch_service

router = APIRouter(prefix="/site-care/watch", tags=["site-care-watch"])


def _event_view(line: WatchLine) -> WatchEventView:
    """
    A line of the watch as the dashboard shows it.

    Args:
        line: The line built by the service.

    Returns:
        Its view.
    """
    return WatchEventView(
        key=line.key,
        kind=line.kind.value,
        tone=line.tone,
        title=line.title,
        detail=line.detail,
        when_label=line.when_label,
        site_count=line.site_count,
        action_label=line.action_label,
        target=WatchTarget(site_id=line.site_id, tab=line.tab, kind=line.kind_filter),
    )


@router.get("", response_model=WatchResponse)
async def get_watch(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> WatchResponse:
    """The watch page of the user."""
    now: datetime = naive_utc_now()
    return WatchResponse(
        today=[_event_view(line) for line in watch_service.recent_changes(db, current_user.id, now)],
        deadlines=[_event_view(line) for line in watch_service.dates_coming_up(db, current_user.id, now)],
    )
