"""The owner's settings: prices, writing rules, points looked at and presentation, with the catalogue's defaults."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user import User

from devleadhunter_site_care.catalog import (
    CORRECTIONS,
    DEFAULT_MONTHLY_PRICE_CENTS,
    POINT_KEY_VALUES,
    CorrectionKey,
    PointKey,
    WritingTrigger,
)
from devleadhunter_site_care.models.owner_settings import SiteCareOwnerSettings
from devleadhunter_site_care.services.site_summary import WritingRules

_DEFAULT_TAGLINE: str = "Je travaille seul, à distance, pour des entreprises comme la vôtre."
_MAX_PRICE_CENTS: int = 10_000_00


@dataclass
class Presenter:
    """
    Who writes, as the message and the page show him.

    Attributes:
        name: His name.
        role: What he does, in a few words that follow « je suis {name}, ».
        tagline: One line about him.
        site_url: His own site.
        photo_url: His portrait.
    """

    name: str = ""
    role: str = ""
    tagline: str = _DEFAULT_TAGLINE
    site_url: str = ""
    photo_url: str = ""


@dataclass
class OwnerSettings:
    """
    One owner's settings, defaults filled in.

    Attributes:
        prices: The price of each correction in cents, None for a quoted one.
        monthly_price_cents: The price of the monthly care.
        trigger: When a site deserves a message.
        disabled_points: The points not looked at.
        presenter: Who writes.
    """

    prices: dict[CorrectionKey, int | None] = field(
        default_factory=lambda: {correction.key: correction.default_price_cents for correction in CORRECTIONS}
    )
    monthly_price_cents: int = DEFAULT_MONTHLY_PRICE_CENTS
    trigger: WritingTrigger = WritingTrigger.FIX
    disabled_points: frozenset[PointKey] = frozenset()
    presenter: Presenter = field(default_factory=Presenter)

    @property
    def writing_rules(self) -> WritingRules:
        """The part of the settings that decides what a check means."""
        return WritingRules(trigger=self.trigger, disabled_points=self.disabled_points)


class OwnerSettingsService:
    """Reads and stores the owners' settings."""

    def get(self, db: Session, user_id: int) -> OwnerSettings:
        """
        An owner's settings.

        Args:
            db: Active database session.
            user_id: The owner.

        Returns:
            His settings; the catalogue's defaults, and his account's name, while he stored none.
        """
        row: SiteCareOwnerSettings | None = self._row(db, user_id)
        if row is None:
            return OwnerSettings(presenter=Presenter(name=self._account_name(db, user_id)))
        settings: OwnerSettings = OwnerSettings(
            monthly_price_cents=row.monthly_price_cents,
            trigger=WritingTrigger(row.trigger),
            disabled_points=frozenset(PointKey(key) for key in row.disabled_points or [] if key in POINT_KEY_VALUES),
            presenter=Presenter(
                name=row.presenter_name or self._account_name(db, user_id),
                role=row.presenter_role,
                tagline=row.presenter_tagline,
                site_url=row.presenter_site_url,
                photo_url=row.presenter_photo_url,
            ),
        )
        for correction in CORRECTIONS:
            stored: object = (row.prices or {}).get(correction.key.value)
            if not correction.is_quoted and isinstance(stored, int):
                settings.prices[correction.key] = stored
        return settings

    def save(self, db: Session, user_id: int, settings: OwnerSettings) -> OwnerSettings:
        """
        Store an owner's settings.

        Args:
            db: Active database session.
            user_id: The owner.
            settings: What he chose.

        Returns:
            The settings as stored.
        """
        row: SiteCareOwnerSettings | None = self._row(db, user_id)
        if row is None:
            row = SiteCareOwnerSettings(user_id=user_id)
            db.add(row)
        row.prices = {
            correction.key.value: self._clamped_price(settings.prices.get(correction.key))
            for correction in CORRECTIONS
            if not correction.is_quoted
        }
        row.monthly_price_cents = self._clamped_price(settings.monthly_price_cents) or DEFAULT_MONTHLY_PRICE_CENTS
        row.trigger = settings.trigger.value
        row.disabled_points = sorted(point.value for point in settings.disabled_points)
        row.presenter_name = settings.presenter.name.strip()[:120]
        row.presenter_role = settings.presenter.role.strip()[:160]
        row.presenter_tagline = settings.presenter.tagline.strip()[:300]
        row.presenter_site_url = settings.presenter.site_url.strip()[:300]
        row.presenter_photo_url = settings.presenter.photo_url.strip()[:500]
        db.commit()
        return self.get(db, user_id)

    @staticmethod
    def _row(db: Session, user_id: int) -> SiteCareOwnerSettings | None:
        """The owner's stored row, when he saved his settings once."""
        return db.execute(
            select(SiteCareOwnerSettings).where(SiteCareOwnerSettings.user_id == user_id)
        ).scalar_one_or_none()

    @staticmethod
    def _account_name(db: Session, user_id: int) -> str:
        """The name of the owner's account, the presenter's name until he types one."""
        user: User | None = db.get(User, user_id)
        return (getattr(user, "full_name", None) or getattr(user, "name", None) or "").strip() if user else ""

    @staticmethod
    def _clamped_price(price_cents: int | None) -> int | None:
        """A price kept between zero and a ceiling no correction reaches."""
        return None if price_cents is None else max(0, min(int(price_cents), _MAX_PRICE_CENTS))


owner_settings_service = OwnerSettingsService()
