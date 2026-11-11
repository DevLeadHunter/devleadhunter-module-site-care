"""Site model — one business that already has a website, as the module follows it."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.clock import naive_utc_now
from core.database import UTF8MB4_TABLE_OPTIONS, Base


class SiteCareSite(Base):
    """
    A business with a website, the line of the module's « Mes prospects ».

    The business becomes a prospect of the core (``prospect_id``) the first time it is written to: until then it
    lives here only, so the other modules' lists never show it.

    Attributes:
        user_id: The owner.
        search_id: The module search that brought it.
        candidate_id: The core search candidate it comes from (discarded there for having a website).
        prospect_id: Its prospect in the core, once it was written to.
        business_name: The business.
        trade: The trade it was searched for (the core's trade key).
        website: Its site's address.
        host: The site's host without « www. », one per owner.
        phone: The number of its Google listing.
        email: The address a message goes to.
        email_source: Where the address comes from: ``listing``, ``site`` or ``manual``.
        status: Where the site stands after its check.
        lead_point: The point that leads its sheet.
        lead_rank: How pressing that point is, the most pressing first in the list (999 without one).
        kinds_filter: Its kinds of issue as one searchable value (« ,risk,mail, »).
        search_text: Name, city and host in lower case, for the list's search field.
        points: The twelve points of the last check.
        reading: What the last check read.
        checked_at: When it was last checked.
        page_slug: The address of the page prepared for its owner, unguessable.
        page_opened_at: When a visitor first opened that page.
        page_open_count: How many times it was opened.
        written_at: When the first message left.
        last_email_log_id: The core's log of the last message sent.
        archived_at: When the owner took it out of the list.
    """

    __tablename__ = "site_care_sites"
    __table_args__ = (UniqueConstraint("user_id", "host", name="uq_site_care_sites_user_host"), UTF8MB4_TABLE_OPTIONS)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    search_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="FR")
    website: Mapped[str] = mapped_column(String(500), nullable=False)
    host: Mapped[str] = mapped_column(String(190), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    google_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    google_reviews_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    google_maps_url: Mapped[str | None] = mapped_column(String(700), nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    lead_point: Mapped[str | None] = mapped_column(String(24), nullable=True)
    lead_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=999)
    kinds_filter: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    search_text: Mapped[str] = mapped_column(String(600), nullable=False, default="")
    points: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    reading: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    checked_at: Mapped[datetime] = mapped_column(default=naive_utc_now, nullable=False, index=True)

    page_slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    page_opened_at: Mapped[datetime | None] = mapped_column(nullable=True)
    page_open_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    written_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_email_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=naive_utc_now, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=naive_utc_now, nullable=True)

    def __repr__(self) -> str:
        """String representation of the site."""
        return f"<SiteCareSite id={self.id} host={self.host} status={self.status}>"
