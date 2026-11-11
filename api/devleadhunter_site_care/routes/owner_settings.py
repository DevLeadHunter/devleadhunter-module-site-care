"""« Réglages »: the user's prices, writing rules, points looked at and presentation."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from services.auth_service import get_current_active_user

from devleadhunter_site_care.catalog import CORRECTIONS, POINTS, CorrectionKey, PointKey, WritingTrigger
from devleadhunter_site_care.schemas.owner_settings import OwnerSettingsView, PointSwitch, PresenterView, PriceLine
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings, Presenter, owner_settings_service
from devleadhunter_site_care.services.send_service import send_service
from devleadhunter_site_care.services.site_service import site_service

router = APIRouter(prefix="/site-care/settings", tags=["site-care-settings"])


def _settings_view(db: Session, user_id: int, settings: OwnerSettings) -> OwnerSettingsView:
    """
    The settings as the dashboard shows them.

    Args:
        db: Active database session.
        user_id: The owner.
        settings: His settings.

    Returns:
        The view, every correction and every point listed.
    """
    return OwnerSettingsView(
        prices=[
            PriceLine(
                key=correction.key.value,
                label=correction.label,
                price_cents=None if correction.is_quoted else settings.prices.get(correction.key),
            )
            for correction in CORRECTIONS
        ],
        monthly_price_cents=settings.monthly_price_cents,
        trigger=settings.trigger.value,
        points=[
            PointSwitch(
                key=point.key.value,
                family_label=point.family_label,
                label=point.label,
                is_enabled=point.key not in settings.disabled_points,
            )
            for point in POINTS
        ],
        presenter=PresenterView(
            name=settings.presenter.name,
            role=settings.presenter.role,
            tagline=settings.presenter.tagline,
            site_url=settings.presenter.site_url,
            photo_url=settings.presenter.photo_url,
        ),
        sender_email=send_service.sender_email(db, user_id),
    )


@router.get("", response_model=OwnerSettingsView)
async def get_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OwnerSettingsView:
    """The user's settings, the catalogue's defaults where he chose nothing."""
    return _settings_view(db, current_user.id, owner_settings_service.get(db, current_user.id))


@router.put("", response_model=OwnerSettingsView)
async def save_settings(
    body: OwnerSettingsView,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OwnerSettingsView:
    """Store the user's settings and apply his writing rules to the sites already checked."""
    current: OwnerSettings = owner_settings_service.get(db, current_user.id)
    prices: dict[CorrectionKey, int | None] = dict(current.prices)
    for line in body.prices:
        if line.key in CorrectionKey and line.price_cents is not None:
            prices[CorrectionKey(line.key)] = line.price_cents
    saved: OwnerSettings = owner_settings_service.save(
        db,
        current_user.id,
        OwnerSettings(
            prices=prices,
            monthly_price_cents=body.monthly_price_cents,
            trigger=WritingTrigger(body.trigger),
            disabled_points=frozenset(
                PointKey(point.key) for point in body.points if point.key in PointKey and not point.is_enabled
            ),
            presenter=Presenter(
                name=body.presenter.name,
                role=body.presenter.role,
                tagline=body.presenter.tagline,
                site_url=body.presenter.site_url,
                photo_url=body.presenter.photo_url,
            ),
        ),
    )
    site_service.apply_rules_to_all(db, current_user.id, saved.writing_rules)
    return _settings_view(db, current_user.id, saved)
