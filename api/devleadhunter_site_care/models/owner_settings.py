"""Owner settings model — one user's prices, writing rules and presentation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.clock import naive_utc_now
from core.database import UTF8MB4_TABLE_OPTIONS, Base


class SiteCareOwnerSettings(Base):
    """
    What one owner chose for the module. A user without a row has the catalogue's defaults.

    Attributes:
        user_id: The owner.
        prices: His price of each correction, in cents, by correction key.
        monthly_price_cents: His price of the monthly care.
        trigger: When a site deserves a message (``fix`` or ``watch``).
        disabled_points: The points he does not want looked at.
        presenter_name: Who writes, as the message and the page name him.
        presenter_role: What he does, in a few words (« développeur web à Rennes »).
        presenter_tagline: One line about him on the page.
        presenter_site_url: His own site.
        presenter_photo_url: His portrait on the page.
    """

    __tablename__ = "site_care_owner_settings"
    __table_args__ = (UTF8MB4_TABLE_OPTIONS,)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    prices: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    monthly_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger: Mapped[str] = mapped_column(String(8), nullable=False)
    disabled_points: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    presenter_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    presenter_role: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    presenter_tagline: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    presenter_site_url: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    presenter_photo_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(default=naive_utc_now, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=naive_utc_now, nullable=True)
