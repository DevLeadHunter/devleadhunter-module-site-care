"""What the watch route returns (see ``docs/API.md``)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from devleadhunter_site_care.schemas.site import SiteState


class WatchTarget(BaseModel):
    """Where a line's button leads: one site's sheet, or « Mes prospects » filtered."""

    site_id: int | None = None
    tab: str | None = None
    kind: str | None = None


class WatchEventView(BaseModel):
    """One line of the watch page as the applications before v1.6.0 show it."""

    key: str
    kind: str
    tone: str
    title: str
    detail: str
    when_label: str
    site_count: int
    action_label: str
    target: WatchTarget


class WatchSiteCard(BaseModel):
    """
    One site of the watch: what the last readings found on it, and where the owner stands with it.

    Attributes:
        key: A stable identifier of the card.
        site_id: The site its page opens.
        kind: The kind of issue, which picks the icon of the tag.
        kind_label: The word of the tag (« Site piraté », « Site disparu »).
        tone: The colour of the tag.
        tech: The technology named next to the tag (« PHP 7.4 »), None when there is none.
        sentence: What was seen, in one short sentence.
        business_name: The business.
        trade_label: Its trade, empty when unknown.
        city: Its city, None when unknown.
        seen_label: When the reading saw it (« Vu il y a 3 jours »).
        state: Where the owner stands with the site (« À écrire », « Sans email », « Écrit le 9 nov. »).
    """

    key: str
    site_id: int
    kind: str
    kind_label: str
    tone: str
    tech: str | None = None
    sentence: str
    business_name: str
    trade_label: str
    city: str | None = None
    seen_label: str
    state: SiteState


class WatchDateCard(BaseModel):
    """
    One date after which some sites will have a problem.

    Attributes:
        key: The date's key, which « Mes prospects » filters on (``?watch_date=``).
        kind: The kind of issue, which picks the icon.
        kind_label: The word of the tag (« Mise à jour en retard »).
        tone: The colour of the tag.
        title: What happens and when (« PHP 8.2 s’arrête le 31 décembre 2026 »).
        detail: What the date changes for its sites, without their count.
        countdown_label: How far the date is (« Dans 46 jours »).
        sites_label: How many sites, and how many can be written to (« 339 sites, dont 212 avec une adresse email »).
        action_label: The wording of its link (« Voir ces 339 prospects »).
        site_id: The single site concerned, None when there are several.
    """

    key: str
    kind: str
    kind_label: str
    tone: str
    title: str
    detail: str
    countdown_label: str
    sites_label: str
    action_label: str
    site_id: int | None = None


class WatchResponse(BaseModel):
    """
    The watch page.

    Attributes:
        summary_line: What the week's readings add up to, None while the owner has no site.
        new_issues: The sites with an issue the reading before had not found.
        upcoming_dates: The dates coming up, the nearest first.
        gone_sites: The sites that stopped answering.
        today: The same changes as lines, read by the applications before v1.6.0.
        deadlines: The same dates as lines, read by the applications before v1.6.0.
    """

    summary_line: str | None = None
    new_issues: list[WatchSiteCard] = Field(default_factory=list)
    upcoming_dates: list[WatchDateCard] = Field(default_factory=list)
    gone_sites: list[WatchSiteCard] = Field(default_factory=list)
    today: list[WatchEventView]
    deadlines: list[WatchEventView]
