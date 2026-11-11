"""What is written to a business owner: the first message, the page prepared for him, a client's report."""

from __future__ import annotations

from conftest import CHECK_DAY, reading_of

from devleadhunter_site_care.catalog import CorrectionKey
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings, Presenter
from devleadhunter_site_care.services.site_message import Money, OutgoingMessage, SiteMessageWriter, SiteSubject
from devleadhunter_site_care.services.site_points import SitePointReader
from devleadhunter_site_care.services.site_reader import SiteReading
from devleadhunter_site_care.services.site_summary import SiteSummarizer

_PAGE_URL = "https://demo.example.com/bilan/elagage-renaud-1a2b3c4d"


def _settings() -> OwnerSettings:
    return OwnerSettings(
        presenter=Presenter(
            name="Léo Guillaume",
            role="développeur web à Rennes",
            tagline="Je travaille seul, à distance.",
            site_url="https://dibodev.fr",
        )
    )


def _writer(reading: SiteReading, business_name: str = "Élagage Renaud", settings: OwnerSettings | None = None):
    points = SitePointReader(today=CHECK_DAY.date(), wordpress_branch=(7, 1), listing_phone="02 99 00 00 00").points_of(
        reading
    )
    summary = SiteSummarizer.summarize(
        points, (settings or _settings()).writing_rules, was_reached=reading.was_reached, was_read=reading.was_read
    )
    return SiteMessageWriter(
        SiteSubject(business_name=business_name, domain="elagage-renaud.test", page_url=_PAGE_URL),
        summary,
        settings or _settings(),
    )


class TestFirstMessage:
    def test_it_says_who_writes_what_was_seen_how_to_check_the_price_and_how_to_refuse(self) -> None:
        message = _writer(reading_of(powered_by="PHP/7.4.33")).first_message(with_page_link=False)

        assert message is not None
        assert message.subject == "La version de PHP de votre site"
        assert message.paragraphs == [
            "Bonjour,",
            "Je suis Léo Guillaume, développeur web à Rennes. En regardant le site d’Élagage Renaud, j’ai vu que "
            "le site tourne avec PHP 7.4, qui ne reçoit plus de correctifs de sécurité depuis novembre 2022.",
            "Vous pouvez le vérifier vous-même : demandez à votre hébergeur quelle version de PHP fait tourner "
            "votre site.",
            "J’ai regardé le reste de votre site, comme un visiteur : 11 points sur 12 sont bons.",
            "La correction coûte 190 €, une seule fois. Si cela ne vous intéresse pas, dites-le-moi et je ne vous "
            "recontacte plus.",
            "Bonne journée,",
        ]

    def test_the_link_of_the_page_replaces_the_count_of_good_points(self) -> None:
        message = _writer(reading_of(powered_by="PHP/7.4.33")).first_message(with_page_link=True)

        assert message is not None
        assert message.paragraphs[3].endswith(f"Tout est noté sur cette page : {_PAGE_URL}")
        assert f'<a href="{_PAGE_URL}">{_PAGE_URL}</a>' in message.body_html

    def test_the_owner_s_price_is_the_one_written(self) -> None:
        settings = _settings()
        settings.prices[CorrectionKey.PHP] = 24900

        message = _writer(reading_of(powered_by="PHP/7.4.33"), settings=settings).first_message(with_page_link=False)

        assert message is not None and "La correction coûte 249 €, une seule fois." in message.paragraphs[4]

    def test_a_quoted_correction_promises_its_price_before_any_work(self) -> None:
        message = _writer(reading_of(has_viewport=False)).first_message(with_page_link=False)

        assert message is not None
        assert message.paragraphs[4].startswith("Je vous donne le prix de la correction avant de commencer.")

    def test_the_business_is_named_the_way_french_does(self) -> None:
        reading = reading_of(has_spf=False)

        assert (
            "le site des Jardins du Lac,"
            in _writer(reading, "Les Jardins du Lac").first_message(with_page_link=False).paragraphs[1]
        )
        assert (
            "le site de Garage Fabre,"
            in _writer(reading, "Garage Fabre").first_message(with_page_link=False).paragraphs[1]
        )

    def test_a_healthy_site_gets_no_message(self) -> None:
        assert _writer(reading_of()).first_message(with_page_link=False) is None

    def test_the_body_escapes_what_it_carries(self) -> None:
        body = OutgoingMessage(subject="x", paragraphs=["Bonjour,", "Tapez <site:exemple.test> & lisez\nla suite"])

        assert body.body_html == "<p>Bonjour,</p><p>Tapez &lt;site:exemple.test&gt; &amp; lisez<br>la suite</p>"


class TestPage:
    def test_the_page_tells_the_finding_then_the_rest_of_the_site(self) -> None:
        page = _writer(reading_of(powered_by="PHP/7.4.33", has_dmarc=False, has_viewport=False)).page(
            reply_address="reply-12@reply.example.com"
        )

        assert page is not None
        assert page["title"] == {
            "start": "Le moteur de votre site n’est plus corrigé ",
            "mark": "depuis 2022",
            "end": ".",
        }
        assert page["seen"]["label"] == "Point à corriger"
        assert page["offer"] == {
            "label": "Je passe votre site sur une version de PHP suivie.",
            "price_label": "190 €",
            "note": "Une seule fois. Vous payez après la correction.",
            "tag_label": "Prix fixe",
            "reassurances": [
                "Je fais d’abord une sauvegarde complète.",
                "Je travaille sur une copie, pas sur votre site.",
                "Votre site garde la même présentation.",
            ],
        }
        assert page["watches"] == ["Rien n’empêche quelqu’un d’envoyer des e-mails au nom du domaine."]
        assert page["other_fixes"] == ["La page n’est pas prévue pour les téléphones : elle s’y affiche en tout petit."]
        assert page["other_points_count"] == 11
        assert "Le cadenas de sécurité est en place." in page["goods"]
        assert page["intro"].startswith("Bonjour, je suis Léo Guillaume, développeur web à Rennes.")
        assert page["presenter"]["site_label"] == "dibodev.fr"
        assert page["presenter"]["tagline"] == "Développeur web à Rennes. Je travaille seul, à distance."
        assert page["reply_mailto"].startswith("mailto:reply-12@reply.example.com?subject=Re%3A%20La%20version")
        assert "body=Bonjour" in page["forward_mailto"]

    def test_a_quoted_correction_carries_no_fixed_price_tag_and_a_domain_setting_reassures_differently(self) -> None:
        quoted = _writer(reading_of(has_viewport=False)).page(reply_address=None)
        domain_setting = _writer(reading_of(has_spf=False)).page(reply_address=None)

        assert quoted is not None and domain_setting is not None
        assert (quoted["offer"]["price_label"], quoted["offer"]["tag_label"]) == ("Sur devis", None)
        assert domain_setting["offer"]["reassurances"][0] == "Je ne touche pas à votre site."
        assert "elagage-renaud.test" in domain_setting["intro"]

    def test_a_site_with_nothing_to_report_has_no_page(self) -> None:
        assert _writer(reading_of()).page(reply_address=None) is None


class TestMonthlyReport:
    def test_a_site_in_order_is_told_so(self) -> None:
        report = _writer(reading_of()).monthly_report(CHECK_DAY)

        assert report.subject == "Le rapport du mois pour elagage-renaud.test"
        assert report.paragraphs[1].endswith("Je l’ai regardé le 11 novembre 2026.")
        assert report.paragraphs[2].startswith("Tout est en ordre : 12 points sont bons")

    def test_what_was_found_is_listed(self) -> None:
        report = _writer(reading_of(copyright_years=[2015])).monthly_report(CHECK_DAY)

        assert report.paragraphs[2] == (
            "Ce que j’ai relevé :\n- Le bas de page affiche « © 2015 » : le site paraît à l’abandon."
        )


def test_prices_are_written_the_french_way() -> None:
    assert (Money.euros(19000), Money.euros(1990), Money.label(None)) == ("190 €", "19,90 €", "Sur devis")
