"""Builds what the watch route returns: every label of the page is written here."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from devleadhunter_site_care.catalog import KIND_LABELS, KIND_TONES
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.schemas.site import SiteState
from devleadhunter_site_care.schemas.watch import (
    WatchDateCard,
    WatchEventView,
    WatchResponse,
    WatchSiteCard,
    WatchTarget,
)
from devleadhunter_site_care.services.site_views import site_views
from devleadhunter_site_care.services.watch_service import (
    NotedChange,
    WatchDate,
    WatchLine,
    WatchSiteChange,
    watch_service,
)


class WatchViews:
    """Turns what the watch found into the page: the week's summary, the sites that changed, the dates coming up."""

    def response(self, db: Session, user_id: int, now: datetime) -> WatchResponse:
        """
        The watch page of an owner.

        Args:
            db: Active database session.
            user_id: The owner.
            now: The current instant (naive UTC).

        Returns:
            The response of ``GET /site-care/watch``.
        """
        noted_changes: list[NotedChange] = watch_service.changes_that_still_hold(db, user_id, now)
        new_issues: list[WatchSiteChange] = watch_service.new_issues(noted_changes)
        gone_sites: list[WatchSiteChange] = watch_service.gone_sites(noted_changes)
        upcoming_dates: list[WatchDate] = watch_service.upcoming_dates(db, user_id, now)
        state_by_site_id: dict[int, SiteState] = site_views.states_of(
            db, [change.site for change in (*new_issues, *gone_sites)]
        )
        return WatchResponse(
            summary_line=self._summary_line(
                followed_count=watch_service.followed_site_count(db, user_id, now, is_reread_only=False),
                reread_count=watch_service.followed_site_count(db, user_id, now, is_reread_only=True),
                new_issue_count=len(new_issues),
                gone_count=len(gone_sites),
                upcoming_dates=upcoming_dates,
            ),
            new_issues=[self._site_card(change, state_by_site_id[change.site.id], now) for change in new_issues],
            upcoming_dates=[self._date_card(watch_date) for watch_date in upcoming_dates],
            gone_sites=[self._site_card(change, state_by_site_id[change.site.id], now) for change in gone_sites],
            today=[self._event_view(line) for line in watch_service.recent_changes(noted_changes, now)],
            deadlines=[self._event_view(watch_date.line) for watch_date in upcoming_dates],
        )

    @staticmethod
    def _summary_line(
        *,
        followed_count: int,
        reread_count: int,
        new_issue_count: int,
        gone_count: int,
        upcoming_dates: list[WatchDate],
    ) -> str | None:
        """
        « 2865 sites relus ces sept derniers jours. 5 nouveaux soucis, 3 sites disparus. Prochaine date dans 7 jours. »

        Returns:
            What the week's readings add up to, None while the owner follows no site.
        """
        if followed_count == 0:
            return None
        if reread_count == 0:
            reread: str = "Aucun site relu ces sept derniers jours."
        elif reread_count == 1:
            reread = "1 site relu ces sept derniers jours."
        else:
            reread = f"{reread_count} sites relus ces sept derniers jours."
        news: list[str] = []
        if new_issue_count:
            news.append(f"{new_issue_count} nouveaux soucis" if new_issue_count > 1 else "1 nouveau souci")
        if gone_count:
            news.append(f"{gone_count} sites disparus" if gone_count > 1 else "1 site disparu")
        sentences: list[str] = [reread, f"{', '.join(news)}." if news else "Rien de nouveau sur ces sites."]
        if upcoming_dates:
            days_left: int = upcoming_dates[0].days_left
            sentences.append(f"Prochaine date dans {days_left} jours." if days_left > 1 else "Prochaine date demain.")
        return " ".join(sentences)

    @staticmethod
    def _site_card(change: WatchSiteChange, state: SiteState, now: datetime) -> WatchSiteCard:
        """One site that changed, as its card shows it."""
        site: SiteCareSite = change.site
        return WatchSiteCard(
            key=change.key,
            site_id=site.id,
            kind=change.kind.value,
            kind_label=change.kind_label,
            tone=KIND_TONES[change.kind],
            tech=change.tech or None,
            sentence=change.sentence,
            business_name=site.business_name,
            trade_label=site_views.trade_label_of(site),
            city=site.city,
            seen_label=watch_service.seen_label(change.seen_at, now),
            state=state,
        )

    @staticmethod
    def _date_card(watch_date: WatchDate) -> WatchDateCard:
        """One date coming up, as its card shows it."""
        line: WatchLine = watch_date.line
        return WatchDateCard(
            key=watch_date.key,
            kind=line.kind.value,
            kind_label=KIND_LABELS[line.kind],
            tone=line.tone,
            title=line.title,
            detail=line.consequence,
            countdown_label=line.when_label,
            sites_label=WatchViews._sites_label(watch_date.sites),
            action_label=line.action_label,
            site_id=line.site_id,
        )

    @staticmethod
    def _sites_label(sites: list[SiteCareSite]) -> str:
        """« 339 sites, dont 212 avec une adresse email », or the business's name when the date concerns one site."""
        count: int = len(sites)
        if count == 1:
            return sites[0].business_name
        with_email_count: int = sum(1 for site in sites if site.email)
        if with_email_count == 0:
            return f"{count} sites, aucun avec une adresse email"
        if with_email_count == count:
            return f"{count} sites, tous avec une adresse email"
        return f"{count} sites, dont {with_email_count} avec une adresse email"

    @staticmethod
    def _event_view(line: WatchLine) -> WatchEventView:
        """A line of the watch as the applications before v1.6.0 show it."""
        return WatchEventView(
            key=line.key,
            kind=line.kind.value,
            tone=line.tone,
            title=line.title,
            detail=line.detail,
            when_label=line.when_label,
            site_count=line.site_count,
            action_label=line.action_label,
            target=WatchTarget(site_id=line.site_id, tab=line.tab, kind=line.kind_filter),
        )


watch_views = WatchViews()
