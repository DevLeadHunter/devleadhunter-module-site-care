"""What a reading means: the twelve points, their kind of issue, their technology, and what they add up to."""

from __future__ import annotations

from datetime import date, datetime

from conftest import CHECK_DAY, reading_of

from devleadhunter_site_care.catalog import IssueKind, PointKey, PointState, SiteStatus, WritingTrigger
from devleadhunter_site_care.services.site_points import SitePoint, SitePointReader
from devleadhunter_site_care.services.site_reader import HomePageFacts, SiteReading
from devleadhunter_site_care.services.site_summary import SiteSummarizer, SiteSummary, WritingRules


def _points(reading: SiteReading, *, today: date = CHECK_DAY.date(), listing_phone: str | None = "02 99 00 00 00"):
    reader = SitePointReader(today=today, wordpress_branch=(7, 1), listing_phone=listing_phone)
    return {point.key: point for point in reader.points_of(reading)}


def _summary(reading: SiteReading, rules: WritingRules | None = None) -> SiteSummary:
    return SiteSummarizer.summarize(
        list(_points(reading).values()),
        rules or WritingRules(),
        was_reached=reading.was_reached,
        was_read=reading.was_read,
    )


class TestPhp:
    def test_a_branch_without_fixes_is_a_version_at_risk(self) -> None:
        php = _points(reading_of(powered_by="PHP/7.4.33"))[PointKey.PHP]

        assert (php.state, php.kind, php.tech) == (PointState.FIX, IssueKind.RISK, "PHP 7.4")
        assert php.sentence == "Plus de correctif de sécurité depuis 2022"
        assert "novembre 2022" in php.fact

    def test_a_branch_ending_soon_is_a_date_coming_up(self) -> None:
        php = _points(reading_of(powered_by="PHP/8.2.20"))[PointKey.PHP]

        assert (php.state, php.kind, php.tech) == (PointState.WATCH, IssueKind.LATE, "PHP 8.2")
        assert php.data["end_date"] == "31 décembre 2026"

    def test_the_same_branch_is_fine_a_year_before_its_end(self) -> None:
        php = _points(reading_of(powered_by="PHP/8.2.20"), today=date(2025, 12, 1))[PointKey.PHP]

        assert php.state == PointState.OK

    def test_a_server_that_hides_its_version_is_not_judged(self) -> None:
        assert _points(reading_of(powered_by=None))[PointKey.PHP].state == PointState.UNKNOWN


class TestSoftware:
    def test_wordpress_one_branch_behind_is_late(self) -> None:
        cms = _points(reading_of(generators=["WordPress 6.5.2"]))[PointKey.CMS]

        assert (cms.state, cms.kind, cms.tech) == (PointState.WATCH, IssueKind.LATE, "WordPress 6.5")
        assert cms.sentence == "La version actuelle est la 7.1"

    def test_an_old_wordpress_is_at_risk(self) -> None:
        cms = _points(reading_of(generators=["WordPress 4.9.8"]))[PointKey.CMS]

        assert (cms.state, cms.kind) == (PointState.FIX, IssueKind.RISK)

    def test_a_hosted_builder_updates_itself(self) -> None:
        assert _points(reading_of(generators=[], cms="Wix"))[PointKey.CMS].state == PointState.OK


class TestPadlock:
    def test_a_site_without_https_is_to_fix(self) -> None:
        https = _points(reading_of(https="absent", certificate_end=None))[PointKey.HTTPS]

        assert (https.state, https.kind, https.data["variant"]) == (PointState.FIX, IssueKind.SECURITY, "absent")

    def test_a_certificate_about_to_expire_is_to_watch(self) -> None:
        https = _points(reading_of(certificate_end=datetime(2026, 11, 29)))[PointKey.HTTPS]

        assert (https.state, https.data["end_date"], https.data["days"]) == (PointState.WATCH, "29 novembre", 18)

    def test_a_certificate_valid_for_months_is_fine(self) -> None:
        assert _points(reading_of())[PointKey.HTTPS].state == PointState.OK


class TestHackedPage:
    def test_an_outside_gambling_link_marks_a_hacked_page(self) -> None:
        html = '<a href="https://guncel-bahis-siteleri.example/giris">deneme bonusu veren siteler</a>'

        assert HomePageFacts.outside_gambling_links(html, "bellanger-electricite.test") == [
            "guncel-bahis-siteleri.example"
        ]

    def test_a_supermarket_or_a_town_called_casino_is_not_a_hack(self) -> None:
        html = (
            '<a href="https://www.supermarche-casino.test/magasin">Géant Casino, notre partenaire</a>'
            '<a href="https://www.ville-betton.test">Mairie de Betton</a>'
        )

        assert HomePageFacts.outside_gambling_links(html, "garage-fabre.test") == []

    def test_the_site_s_own_links_never_count(self) -> None:
        html = '<a href="https://www.bahis-club.test/slot-gacor">slot gacor</a>'

        assert HomePageFacts.outside_gambling_links(html, "www.bahis-club.test") == []

    def test_a_hacked_page_leads_everything_else(self) -> None:
        summary = _summary(reading_of(gambling_links=["bahis.example"], powered_by="PHP/7.4.33"))

        assert summary.lead is not None and summary.lead.key == PointKey.HACKED
        assert summary.also_words == ["version à risque (PHP 7.4)"]


class TestListingPhone:
    def test_the_listing_number_is_found_whatever_its_prefix(self) -> None:
        points = _points(reading_of(page_digits="33299000000"), listing_phone="02 99 00 00 00")

        assert points[PointKey.GOOGLE_PHONE].state == PointState.OK

    def test_another_number_on_the_page_is_to_watch(self) -> None:
        points = _points(reading_of(page_digits="0612345678"), listing_phone="02 99 00 00 00")

        assert (points[PointKey.GOOGLE_PHONE].state, points[PointKey.GOOGLE_PHONE].kind) == (
            PointState.WATCH,
            IssueKind.CONTACT,
        )


class TestSummary:
    def test_a_healthy_site_has_nothing_to_report(self) -> None:
        summary = _summary(reading_of())

        assert (summary.status, summary.lead, summary.kinds) == (SiteStatus.NOTHING, None, [])
        assert summary.lead_kind == IssueKind.OK

    def test_a_point_to_fix_deserves_a_message(self) -> None:
        summary = _summary(reading_of(has_spf=False, has_dmarc=False))

        assert summary.status == SiteStatus.TO_WRITE
        assert summary.lead is not None and summary.lead.key == PointKey.SPF
        # The other e-mail issue says the same words as the lead: it is not repeated.
        assert summary.also_line is None
        assert summary.kinds_filter_value == ",mail,"

    def test_points_to_watch_are_only_worth_a_message_on_request(self) -> None:
        reading = reading_of(has_dmarc=False, copyright_years=[2015], has_description=False)

        assert _summary(reading).status == SiteStatus.NOTHING
        assert _summary(reading, WritingRules(trigger=WritingTrigger.WATCH)).status == SiteStatus.TO_WRITE

    def test_a_point_the_owner_switched_off_is_not_looked_at(self) -> None:
        rules = WritingRules(disabled_points=frozenset({PointKey.SPF}))

        assert _summary(reading_of(has_spf=False), rules).status == SiteStatus.NOTHING

    def test_a_site_that_does_not_answer_waits_for_a_look_by_hand(self) -> None:
        gone = SiteReading(host="jardins-hubert.test", read_at=CHECK_DAY, error="ConnectError")
        refused = SiteReading(host="garage-thibault.test", read_at=CHECK_DAY, status_code=403)

        assert _summary(gone).status == SiteStatus.UNREACHABLE
        assert _summary(refused).status == SiteStatus.UNREADABLE

    def test_a_point_survives_its_storage(self) -> None:
        php = _points(reading_of(powered_by="PHP/7.4.33"))[PointKey.PHP]

        assert SitePoint.from_json(php.to_json()) == php


class TestHomePage:
    def test_the_facts_of_a_home_page_are_read_from_its_html(self) -> None:
        html = """
        <html><head><title>Jardins Guillot</title>
        <meta name="viewport" content="width=device-width">
        <meta name="generator" content="WordPress 6.5.2">
        <meta name="description" content="Paysagiste à Metz">
        <script type="application/ld+json">{"@type":"LocalBusiness"}</script></head>
        <body><a href="tel:+33387000000">03 87 00 00 00</a>
        <a href="mailto:contact@jardins-guillot.test">Écrire</a>
        <a href="/contact">Contact</a><a href="/mentions-legales">Mentions légales</a>
        <a href="https://studio-web.test/contact">Agence</a>
        <footer>© 2019 Jardins Guillot - site réalisé par agence@studio-web.test</footer></body></html>
        """
        reading = SiteReading(host="www.jardins-guillot.test", read_at=CHECK_DAY, status_code=200)

        HomePageFacts.read_into(reading, html, "https://www.jardins-guillot.test/")

        assert reading.generators == ["WordPress 6.5.2"]
        assert (reading.has_viewport, reading.has_description, reading.has_structured_data) == (True, True, True)
        assert (reading.has_tel_link, reading.shows_phone) == (True, True)
        assert "33387000000" in reading.page_digits
        assert reading.emails == ["agence@studio-web.test", "contact@jardins-guillot.test"]
        assert reading.copyright_years == [2019]
        assert reading.contact_page_urls == [
            "https://www.jardins-guillot.test/contact",
            "https://www.jardins-guillot.test/mentions-legales",
        ]

    def test_a_reading_survives_its_storage(self) -> None:
        reading = reading_of(certificate_end=datetime(2026, 11, 29))

        restored = SiteReading.from_json(reading.to_json())

        assert (restored.certificate_end, restored.read_at, restored.emails) == (
            reading.certificate_end,
            reading.read_at,
            reading.emails,
        )
