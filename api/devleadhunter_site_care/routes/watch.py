"""« Veille »: what changed on the user's sites and the dates coming up."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.database import get_db
from models.user import User
from services.auth_service import get_current_active_user

from devleadhunter_site_care.schemas.watch import WatchResponse
from devleadhunter_site_care.services.watch_views import watch_views

router = APIRouter(prefix="/site-care/watch", tags=["site-care-watch"])


@router.get("", response_model=WatchResponse)
async def get_watch(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> WatchResponse:
    """The watch page of the user."""
    return watch_views.response(db, current_user.id, naive_utc_now())
