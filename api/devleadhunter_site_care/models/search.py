"""Search model — one request to bring businesses that have a website into the module."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.clock import naive_utc_now
from core.database import UTF8MB4_TABLE_OPTIONS, Base


class SiteCareSearch(Base):
    """
    A search of the module: it draws from the businesses the core's searches discarded for having a website.

    Attributes:
        user_id: The owner.
        trades: The trade keys asked for; empty means every trade.
        country: The country asked for.
        cities: The cities asked for; empty means the whole country.
        requested_count: How many sites the owner wants.
        status: ``pending``, ``running``, ``completed`` or ``failed``.
        checked_count: How many businesses were looked at so far.
        imported_count: How many sites entered the module so far.
        last_candidate_id: The last core candidate looked at, where the next batch starts.
        note: What the owner should know once it ended (the base ran short, the search failed).
    """

    __tablename__ = "site_care_searches"
    __table_args__ = (UTF8MB4_TABLE_OPTIONS,)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    trades: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="FR")
    cities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    requested_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending", index=True)
    checked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_candidate_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=naive_utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
