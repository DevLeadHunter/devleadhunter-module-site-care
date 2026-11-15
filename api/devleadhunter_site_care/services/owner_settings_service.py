"""
The owner's settings: prices, writing rules and points looked at, with the catalogue's defaults, and how he is presented.

His name, his site and his photo come from his profile, which every module shares; this module only keeps the two
lines that present him in its message and on its page.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings as core_settings
from models.user import User
from services.r2_storage_service import r2_storage

from devleadhunter_site_care.catalog import (
    CORRECTION_BY_KEY,
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
        name: His name, from his profile.
        role: What he does, in a few words that follow « je suis {name}, ».
        tagline: One line about him.
        site_url: His own site, from his profile.
        photo_url: His portrait, from his profile.
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

    def price_of(self, correction: CorrectionKey) -> int | None:
        """
        The price of a correction.

        Args:
            correction: The correction.

        Returns:
            The owner's price in cents, None for a correction quoted case by case.
        """
        return None if CORRECTION_BY_KEY[correction].is_quoted else self.prices.get(correction)


class OwnerSettingsService:
    """Reads and stores the owners' settings."""

    def get(self, db: Session, user_id: int) -> OwnerSettings:
        """
        An owner's settings.

        Args:
            db: Active database session.
            user_id: The owner.

        Returns:
            His settings, the catalogue's defaults while he stored none, and his presentation read from his profile.
        """
        row: SiteCareOwnerSettings | None = self._row(db, user_id)
        presenter: Presenter = self._presenter(db.get(User, user_id), row)
        if row is None:
            return OwnerSettings(presenter=presenter)
        settings: OwnerSettings = OwnerSettings(
            monthly_price_cents=row.monthly_price_cents,
            trigger=WritingTrigger(row.trigger),
            disabled_points=frozenset(PointKey(key) for key in row.disabled_points or [] if key in POINT_KEY_VALUES),
            presenter=presenter,
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
            settings: What he chose; of his presentation, only the two lines of this module are stored, the rest
                being his profile's.

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
        row.presenter_role = settings.presenter.role.strip()[:160]
        row.presenter_tagline = settings.presenter.tagline.strip()[:300]
        db.commit()
        return self.get(db, user_id)

    @staticmethod
    def _row(db: Session, user_id: int) -> SiteCareOwnerSettings | None:
        """The owner's stored row, when he saved his settings once."""
        return db.execute(
            select(SiteCareOwnerSettings).where(SiteCareOwnerSettings.user_id == user_id)
        ).scalar_one_or_none()

    @classmethod
    def _presenter(cls, user: User | None, row: SiteCareOwnerSettings | None) -> Presenter:
        """
        Who writes: the name, the site and the photo of the owner's profile, and the two lines of this module.

        Args:
            user: The owner's account.
            row: His stored settings, when he saved them once.

        Returns:
            The presenter. A site or a photo typed in this module before it read the profile stays the fallback while
            the profile has none.
        """
        profile_site_url: str = ((user.company_website_url if user else None) or "").strip()
        return Presenter(
            name=(user.name if user else "").strip(),
            role=row.presenter_role if row else "",
            tagline=row.presenter_tagline if row else _DEFAULT_TAGLINE,
            site_url=profile_site_url or (row.presenter_site_url if row else ""),
            photo_url=cls._profile_photo_url(user) or (row.presenter_photo_url if row else ""),
        )

    @staticmethod
    def _profile_photo_url(user: User | None) -> str:
        """The public address of the profile photo, empty without a photo or without public storage."""
        if user is None or not user.profile_photo_path or not (core_settings.r2_public_base_url or "").strip():
            return ""
        return r2_storage.public_url(user.profile_photo_path)

    @staticmethod
    def _clamped_price(price_cents: int | None) -> int | None:
        """A price kept between zero and a ceiling no correction reaches."""
        return None if price_cents is None else max(0, min(int(price_cents), _MAX_PRICE_CENTS))


owner_settings_service = OwnerSettingsService()
