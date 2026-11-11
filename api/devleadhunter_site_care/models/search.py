"""Search model — one request to bring businesses that have a website into the module."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.clock import naive_utc_now
from core.database import UTF8MB4_TABLE_OPTIONS, Base

from devleadhunter_site_care.catalog import KeepRule, SearchSource


class SiteCareSearch(Base):
    """
    A search of the module.

    It draws either from the owner's base (the businesses the core's searches discarded for having a website) or
    from the open map, one French département after another.

    Attributes:
        user_id: The owner.
        source: Where the businesses come from (:class:`SearchSource`).
        trades: The trade keys asked for in the base; empty means every trade.
        country: The country asked for.
        cities: The cities asked for in the base; empty means the whole country.
        departments: The French départements asked for on the open map.
        families: The families of businesses asked for on the open map.
        keep_rule: Which of the sites read enter the list (:class:`KeepRule`).
        collected_departments: The départements whose businesses were already fetched from the open map.
        requested_count: How many sites the owner wants in his list.
        status: ``pending``, ``running``, ``completed`` or ``failed``.
        checked_count: How many sites were read so far.
        imported_count: How many sites entered the module so far.
        last_candidate_id: The last core candidate looked at, where the next batch starts.
        note: What the owner should know once it ended (the source ran short, the search failed or was stopped).
    """

    __tablename__ = "site_care_searches"
    __table_args__ = (UTF8MB4_TABLE_OPTIONS,)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source: Mapped[str] = mapped_column(
        String(8), nullable=False, default=SearchSource.OWN_BASE.value, server_default=SearchSource.OWN_BASE.value
    )
    trades: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="FR")
    cities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    # Nullable: a JSON column takes no default on MySQL, so the searches made before the migration hold NULL.
    departments: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    families: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    collected_departments: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    keep_rule: Mapped[str] = mapped_column(
        String(12), nullable=False, default=KeepRule.EVERY_SITE.value, server_default=KeepRule.EVERY_SITE.value
    )
    requested_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending", index=True)
    checked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_candidate_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=naive_utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
