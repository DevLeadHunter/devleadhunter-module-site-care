"""Watch event model — something that changed on a site, a reason to write today."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.clock import naive_utc_now
from core.database import UTF8MB4_TABLE_OPTIONS, Base


class SiteCareWatchEvent(Base):
    """
    A change a check found on a site: it was hacked, it stopped answering, a point got worse.

    Attributes:
        user_id: The owner.
        site_id: The site.
        kind: ``hacked``, ``unreachable`` or ``worse``.
        point_key: The point that got worse, for the ``worse`` kind.
        created_at: When the check saw it.
    """

    __tablename__ = "site_care_watch_events"
    __table_args__ = (UTF8MB4_TABLE_OPTIONS,)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    site_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    point_key: Mapped[str | None] = mapped_column(String(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=naive_utc_now, nullable=False, index=True)
