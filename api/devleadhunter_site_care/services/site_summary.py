"""
What a site's points add up to: whether it deserves a message, the point that leads it, the other issues.

Pure: it reads stored points and the owner's choices, so a change of settings is applied without reading the site again.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from devleadhunter_site_care.catalog import (
    CORRECTION_BY_KEY,
    CORRECTION_ORDER,
    FIX_LEAD_ORDER,
    KIND_LABELS,
    KIND_WORDS,
    POINT_BY_KEY,
    SECURITY_POINT_KEYS,
    WATCH_LEAD_ORDER,
    WATCH_POINTS_WORTH_A_MESSAGE,
    CorrectionKey,
    IssueKind,
    PointKey,
    PointState,
    SiteStatus,
    WritingTrigger,
)
from devleadhunter_site_care.services.site_points import SitePoint


@dataclass(frozen=True)
class WritingRules:
    """
    The owner's choices that decide what a check means.

    Attributes:
        trigger: When a site deserves a message.
        disabled_points: The points the owner does not want looked at.
    """

    trigger: WritingTrigger = WritingTrigger.FIX
    disabled_points: frozenset[PointKey] = frozenset()


@dataclass(frozen=True)
class OfferLine:
    """A correction offered for one site, with the price the owner set (None: quoted)."""

    correction: CorrectionKey
    label: str
    price_cents: int | None


@dataclass
class SiteSummary:
    """
    A site's check, summed up.

    Attributes:
        status: Where the site stands.
        lead: The point that leads the sheet and the message, None when nothing is worth a line.
        fixes: The points to fix, in the catalogue's order.
        watches: The points to watch.
        good_words: How the points that are fine are named.
        hidden_words: How the points that cannot be seen from outside are named.
        also_words: The other issues, in words, without the lead's own.
        kinds: Every kind of issue the site has, for the list's filter.
        corrections: The corrections that fix the site's points, the most pressing first.
    """

    status: SiteStatus
    lead: SitePoint | None = None
    fixes: list[SitePoint] = field(default_factory=list)
    watches: list[SitePoint] = field(default_factory=list)
    good_words: list[str] = field(default_factory=list)
    hidden_words: list[str] = field(default_factory=list)
    also_words: list[str] = field(default_factory=list)
    kinds: list[IssueKind] = field(default_factory=list)
    corrections: list[CorrectionKey] = field(default_factory=list)

    @property
    def lead_kind(self) -> IssueKind:
        """The kind of the list's tag: the lead's, or what the status says when no point leads."""
        if self.lead is not None and self.lead.kind is not None:
            return self.lead.kind
        return IssueKind.OK if self.status == SiteStatus.NOTHING else IssueKind.REVIEW

    @property
    def has_security_issue(self) -> bool:
        """Whether a point to fix or to watch is a security matter: a hack, the padlock, PHP, a site software left behind."""
        return any(
            point.key in SECURITY_POINT_KEYS or (point.key == PointKey.CMS and point.state == PointState.FIX)
            for point in (*self.fixes, *self.watches)
        )

    @property
    def lead_kind_label(self) -> str:
        """The word of the list's tag."""
        return KIND_LABELS[self.lead_kind]

    @property
    def also_line(self) -> str | None:
        """« Aussi : … », None when the lead is the site's only issue."""
        return f"Aussi : {', '.join(self.also_words)}" if self.also_words else None

    @property
    def kinds_filter_value(self) -> str:
        """The kinds as one searchable column value: « ,risk,mail, »."""
        return f",{','.join(kind.value for kind in self.kinds)}," if self.kinds else ""


class SiteSummarizer:
    """Sums the points of a site up, with the owner's writing rules."""

    @classmethod
    def summarize(
        cls,
        points: list[SitePoint],
        rules: WritingRules,
        *,
        was_reached: bool,
        was_read: bool,
        is_address_doubtful: bool,
    ) -> SiteSummary:
        """
        Sum a check up.

        Args:
            points: The site's twelve points.
            rules: The owner's choices.
            was_reached: Whether the site answered at all.
            was_read: Whether its home page was read.
            is_address_doubtful: Whether the address may no longer be the business's own.

        Returns:
            The summary; a site that was not read, or whose address is doubtful, has no lead and waits for a
            look by hand.
        """
        if not was_read:
            return SiteSummary(status=SiteStatus.UNREADABLE if was_reached else SiteStatus.UNREACHABLE)
        if is_address_doubtful:
            return SiteSummary(status=SiteStatus.DOUBTFUL_ADDRESS)
        looked_at: list[SitePoint] = [point for point in points if point.key not in rules.disabled_points]
        fixes: list[SitePoint] = [point for point in looked_at if point.state == PointState.FIX]
        watches: list[SitePoint] = [point for point in looked_at if point.state == PointState.WATCH]
        lead: SitePoint | None = cls._lead_of(fixes, watches)
        summary: SiteSummary = SiteSummary(
            status=SiteStatus.TO_WRITE if cls._deserves_a_message(fixes, watches, rules) else SiteStatus.NOTHING,
            lead=lead,
            fixes=fixes,
            watches=watches,
            good_words=[POINT_BY_KEY[point.key].good_words for point in looked_at if point.state == PointState.OK],
            hidden_words=[
                POINT_BY_KEY[point.key].good_words for point in looked_at if point.state == PointState.UNKNOWN
            ],
        )
        issues: list[SitePoint] = fixes + watches
        summary.kinds = list(dict.fromkeys(point.kind for point in issues if point.kind is not None))
        summary.also_words = cls._also_words(issues, lead)
        summary.corrections = cls._corrections_of(fixes, watches)
        if not summary.corrections and lead is not None and summary.status == SiteStatus.TO_WRITE:
            summary.corrections = [POINT_BY_KEY[lead.key].correction]
        return summary

    @staticmethod
    def words_of(point: SitePoint) -> str:
        """How « Aussi : … » names a point: its kind, and its technology when it has one."""
        if point.kind is None:
            return ""
        return f"{KIND_WORDS[point.kind]} ({point.tech})" if point.tech else KIND_WORDS[point.kind]

    @staticmethod
    def offer_lines(corrections: list[CorrectionKey], prices: dict[CorrectionKey, int | None]) -> list[OfferLine]:
        """
        The corrections of a site with the owner's prices.

        Args:
            corrections: The corrections that fix the site's points.
            prices: The owner's price of each correction, None for a quoted one.

        Returns:
            One line per correction.
        """
        return [
            OfferLine(correction, CORRECTION_BY_KEY[correction].label, prices.get(correction))
            for correction in corrections
        ]

    @staticmethod
    def _deserves_a_message(fixes: list[SitePoint], watches: list[SitePoint], rules: WritingRules) -> bool:
        """A point to fix is always worth a message, like a date coming up; several points to watch only on request."""
        if fixes or any(point.key == PointKey.PHP for point in watches):
            return True
        return rules.trigger == WritingTrigger.WATCH and len(watches) >= WATCH_POINTS_WORTH_A_MESSAGE

    @staticmethod
    def _lead_of(fixes: list[SitePoint], watches: list[SitePoint]) -> SitePoint | None:
        """The most pressing point: a fix before a watch, each in the catalogue's lead order."""
        for ordered_keys, candidates in ((FIX_LEAD_ORDER, fixes), (WATCH_LEAD_ORDER, watches)):
            for key in ordered_keys:
                for point in candidates:
                    if point.key == key:
                        return point
        return None

    @classmethod
    def _also_words(cls, issues: list[SitePoint], lead: SitePoint | None) -> list[str]:
        """The other issues in words, once each, without what the lead already says."""
        lead_words: str = cls.words_of(lead) if lead is not None else ""
        words: list[str] = []
        for point in issues:
            point_words: str = cls.words_of(point)
            if point is lead or not point_words or point_words == lead_words or point_words in words:
                continue
            words.append(point_words)
        return words

    @staticmethod
    def _corrections_of(fixes: list[SitePoint], watches: list[SitePoint]) -> list[CorrectionKey]:
        """The corrections of the points to fix, plus the PHP move while its date is coming up."""
        needed: set[CorrectionKey] = {POINT_BY_KEY[point.key].correction for point in fixes}
        needed.update(POINT_BY_KEY[point.key].correction for point in watches if point.key == PointKey.PHP)
        return [correction for correction in CORRECTION_ORDER if correction in needed]
