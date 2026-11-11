"""The page prepared for a business owner: public, reached by an address nobody can guess."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_db

from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.schemas.public_page import PublicPage
from devleadhunter_site_care.services.owner_settings_service import owner_settings_service
from devleadhunter_site_care.services.send_service import send_service

router = APIRouter(prefix="/site-care/public", tags=["site-care-public"])


@router.get("/pages/{slug}", response_model=PublicPage)
async def get_public_page(slug: str, response: Response, db: Session = Depends(get_db)) -> PublicPage:
    """
    The content of the page of one site, for the demo host to render.

    Args:
        slug: The page's address, as the message carries it.
        response: The HTTP response, told never to be indexed.
        db: Active database session.

    Returns:
        The page's content (see ``docs/API.md``).
    """
    site: SiteCareSite | None = db.execute(
        select(SiteCareSite).where(SiteCareSite.page_slug == slug, SiteCareSite.archived_at.is_(None))
    ).scalar_one_or_none()
    page: dict[str, object] | None = (
        send_service.writer_for(site, owner_settings_service.get(db, site.user_id)).page(
            reply_address=send_service.reply_address(db, site)
        )
        if site is not None
        else None
    )
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page introuvable")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return PublicPage.model_validate(page)
