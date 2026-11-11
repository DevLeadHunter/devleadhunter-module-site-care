"""Sent message model — the link between a message of the module and the core's email log."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.clock import naive_utc_now
from core.database import UTF8MB4_TABLE_OPTIONS, Base


class SiteCareSentMessage(Base):
    """
    A message the module sent about a site. The core's ``email_logs`` row carries its delivery and its reply.

    Attributes:
        user_id: The owner.
        site_id: The site the message is about.
        email_log_id: The core's log of the send.
        kind: ``first`` (the message to a prospect) or ``report`` (a client's monthly report).
        subject: Its subject.
        with_page_link: Whether it carried the link of the page prepared for the owner.
        sent_at: When it left.
    """

    __tablename__ = "site_care_sent_messages"
    __table_args__ = (UTF8MB4_TABLE_OPTIONS,)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    site_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    email_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    with_page_link: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sent_at: Mapped[datetime] = mapped_column(default=naive_utc_now, nullable=False)
