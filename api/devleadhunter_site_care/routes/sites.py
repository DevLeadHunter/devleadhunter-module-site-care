"""« Mes prospects »: the owner's sites, their sheet, their check, the message that leaves for them.

The core closes every route (404) while the module is switched off.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from services.auth_service import get_current_active_user

from devleadhunter_site_care.catalog import IssueKind, SiteTab
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.schemas.site import (
    CarePlanStartBody,
    SiteDetail,
    SiteEmailBody,
    SiteListResponse,
    SiteSendBody,
)
from devleadhunter_site_care.services.care_plan_service import care_plan_service
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings, owner_settings_service
from devleadhunter_site_care.services.send_service import send_service
from devleadhunter_site_care.services.site_service import SiteCareError, site_service
from devleadhunter_site_care.services.site_views import site_views

router = APIRouter(prefix="/site-care/sites", tags=["site-care-sites"])


def _owned_site(db: Session, user: User, site_id: int) -> SiteCareSite:
    """
    The user's site, or a 404.

    Args:
        db: Active database session.
        user: The connected user.
        site_id: The site asked for.

    Returns:
        The site.
    """
    site: SiteCareSite | None = site_service.get(db, user.id, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect introuvable")
    return site


@router.get("", response_model=SiteListResponse)
async def list_sites(
    tab: SiteTab = Query(SiteTab.TO_WRITE),
    trade: str | None = Query(None, max_length=80),
    kind: IssueKind | None = Query(None),
    q: str | None = Query(None, max_length=120),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SiteListResponse:
    """A page of the user's sites, with the counts of the whole list."""
    settings: OwnerSettings = owner_settings_service.get(db, current_user.id)
    listing = site_service.list_sites(
        db,
        current_user.id,
        tab=tab,
        trade=trade,
        kind=kind.value if kind else None,
        text=q,
        limit=limit,
        offset=offset,
    )
    return site_views.list_response(db, listing, settings)


@router.get("/{site_id}", response_model=SiteDetail)
async def get_site(
    site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SiteDetail:
    """The sheet of one site."""
    site: SiteCareSite = _owned_site(db, current_user, site_id)
    return site_views.detail(db, site, owner_settings_service.get(db, current_user.id))


@router.patch("/{site_id}", response_model=SiteDetail)
async def set_site_email(
    site_id: int,
    body: SiteEmailBody,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SiteDetail:
    """Store the address the user typed for a site."""
    site: SiteCareSite = _owned_site(db, current_user, site_id)
    try:
        site_service.set_email(db, site, body.email)
    except SiteCareError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return site_views.detail(db, site, owner_settings_service.get(db, current_user.id))


@router.post("/{site_id}/find-email", response_model=SiteDetail)
async def find_site_email(
    site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SiteDetail:
    """Look for an address on the site's own pages; the sheet comes back with it when one was found."""
    site: SiteCareSite = _owned_site(db, current_user, site_id)
    await site_service.find_email(db, site)
    return site_views.detail(db, site, owner_settings_service.get(db, current_user.id))


@router.post("/{site_id}/recheck", response_model=SiteDetail)
async def recheck_site(
    site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SiteDetail:
    """Read the site again and return its sheet with the new check."""
    site: SiteCareSite = _owned_site(db, current_user, site_id)
    settings: OwnerSettings = owner_settings_service.get(db, current_user.id)
    await site_service.recheck(db, site, settings)
    return site_views.detail(db, site, settings)


@router.post("/{site_id}/send", response_model=SiteDetail)
async def send_first_message(
    site_id: int,
    body: SiteSendBody,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SiteDetail:
    """Send the first message about the site; 409 with the reason when it cannot leave."""
    site: SiteCareSite = _owned_site(db, current_user, site_id)
    settings: OwnerSettings = owner_settings_service.get(db, current_user.id)
    try:
        await send_service.send_first_message(db, site, settings, with_page_link=body.with_page_link)
    except SiteCareError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return site_views.detail(db, site, settings)


@router.post("/{site_id}/care-plan", response_model=SiteDetail)
async def start_care_plan(
    site_id: int,
    body: CarePlanStartBody,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SiteDetail:
    """Put the site under monthly care."""
    site: SiteCareSite = _owned_site(db, current_user, site_id)
    try:
        care_plan_service.start(db, site, body.monthly_price_cents)
    except SiteCareError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return site_views.detail(db, site, owner_settings_service.get(db, current_user.id))


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_site(
    site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    """Take the site out of the list."""
    site_service.archive(db, _owned_site(db, current_user, site_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
