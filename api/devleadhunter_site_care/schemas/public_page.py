"""What the public page route returns (see ``docs/API.md``)."""

from __future__ import annotations

from pydantic import BaseModel


class PublicPageTitle(BaseModel):
    """The page's title, cut around the words it marks."""

    start: str
    mark: str
    end: str


class PublicPageFinding(BaseModel):
    """What was seen on the site: the fact in one sentence, then its explanation."""

    label: str
    lead: str
    rest: str


class PublicPageOffer(BaseModel):
    """The correction offered; ``tag_label`` is None for a correction that is quoted."""

    label: str
    price_label: str
    note: str
    tag_label: str | None = None
    reassurances: list[str]


class PublicPagePresenter(BaseModel):
    """Who writes; ``site_url`` and ``photo_url`` are empty when the owner set none."""

    name: str
    tagline: str
    site_url: str
    site_label: str
    photo_url: str


class PublicPage(BaseModel):
    """The page prepared for a business owner; a mailto link is empty when no reply address is known."""

    business_name: str
    domain: str
    title: PublicPageTitle
    intro: str
    seen: PublicPageFinding
    changes: list[str]
    proof_steps: list[str]
    offer: PublicPageOffer
    goods: list[str]
    other_fixes: list[str]
    watches: list[str]
    other_points_count: int
    presenter: PublicPagePresenter
    reply_mailto: str
    forward_mailto: str
