"""What the routes of « Mes prospects » receive and return (see ``docs/API.md``)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SiteLead(BaseModel):
    """The tag and the sentence that lead a line of the list."""

    kind: str
    kind_label: str
    tone: str
    tech: str | None = None
    sentence: str


class SiteState(BaseModel):
    """Where the owner stands with a site."""

    key: str
    label: str
    tone: str


class SiteListItem(BaseModel):
    """One line of « Mes prospects »."""

    id: int
    business_name: str
    trade_label: str
    city: str | None = None
    country: str
    domain: str
    website: str
    email: str | None = None
    tab: str
    state: SiteState
    lead: SiteLead
    also: str | None = None
    checked_at: datetime


class SitePointView(BaseModel):
    """A point of a sheet, to fix or to watch."""

    key: str
    kind: str
    kind_label: str
    tech: str | None = None
    fact: str


class OfferLineView(BaseModel):
    """A correction offered, with its price."""

    label: str
    price_label: str


class MessageView(BaseModel):
    """The first message, with and without the link of the page prepared for the owner."""

    subject: str
    paragraphs: list[str]
    paragraphs_with_link: list[str]


class SentMessageView(BaseModel):
    """A message that left about the site."""

    kind: str
    kind_label: str
    subject: str
    sent_at: datetime
    status_label: str


class CarePlanBrief(BaseModel):
    """The running care plan of a site."""

    id: int
    monthly_price_cents: int
    started_at: datetime


class SiteDetail(SiteListItem):
    """The sheet of a site."""

    phone: str | None = None
    google_rating: float | None = None
    google_reviews_count: int | None = None
    google_maps_url: str | None = None
    unread_text: str | None = None
    fixes: list[SitePointView] = Field(default_factory=list)
    watches: list[SitePointView] = Field(default_factory=list)
    good_line: str | None = None
    hidden_line: str | None = None
    offer: list[OfferLineView] = Field(default_factory=list)
    monthly_label: str
    message: MessageView | None = None
    page_url: str | None = None
    can_send: bool
    send_refusal: str | None = None
    sent_messages: list[SentMessageView] = Field(default_factory=list)
    care_plan: CarePlanBrief | None = None


class SiteCounts(BaseModel):
    """The four figures above the list."""

    total: int
    with_email: int
    to_fix: int
    written: int


class TradeOption(BaseModel):
    """A trade of the list's filter."""

    key: str
    label: str


class SiteListResponse(BaseModel):
    """A page of « Mes prospects » with the counts of the whole list."""

    counts: SiteCounts
    tab_counts: dict[str, int]
    trades: list[TradeOption]
    matching_count: int
    sites: list[SiteListItem]


class SiteEmailBody(BaseModel):
    """The address the owner types for a site; empty removes it."""

    email: str = Field(default="", max_length=255)


class SiteSendBody(BaseModel):
    """How the first message leaves."""

    with_page_link: bool = False


class CarePlanStartBody(BaseModel):
    """The price of a site's monthly care."""

    monthly_price_cents: int = Field(..., ge=100, le=100_000)
