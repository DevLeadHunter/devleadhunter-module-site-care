"""
Seed a throwaway local database for the « Entretien de sites » module: one user, invented businesses on reserved
`.test` domains, each with the reading a check would have made. Nothing here is a real site.

Run with cwd = this folder and PYTHONPATH = the core's api/.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from core.clock import naive_utc_now
from core.database import Base, SessionLocal, engine
from core.product_modules.registry import product_module_registry
from enums.prospect_search import CandidateRejectReason, CandidateStatus
from enums.user_role import UserRole
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from models.prospect_search import ProspectSearch
from models.prospect_search_candidate import ProspectSearchCandidate
from models.user import User
from services.auth_service import AuthService
from services.product_module_service import product_module_service

import models  # noqa: F401  (every core table on the metadata)

product_module_registry.installed()

from devleadhunter_site_care.models.care_plan import SiteCarePlan  # noqa: E402
from devleadhunter_site_care.models.sent_message import SiteCareSentMessage  # noqa: E402
from devleadhunter_site_care.models.site import SiteCareSite  # noqa: E402
from devleadhunter_site_care.services.owner_settings_service import (  # noqa: E402
    OwnerSettings,
    Presenter,
    owner_settings_service,
)
from devleadhunter_site_care.services.site_reader import SiteReading  # noqa: E402
from devleadhunter_site_care.services.site_service import site_service  # noqa: E402
from devleadhunter_site_care.services.wordpress_releases import WordPressReleases  # noqa: E402

NOW: datetime = naive_utc_now().replace(microsecond=0)


def reading_of(host: str, **facts: Any) -> SiteReading:
    """A reading of a healthy home page, with the facts a site changes."""
    healthy: dict[str, Any] = {
        "host": host,
        "read_at": NOW,
        "status_code": 200,
        "https": "ok",
        "certificate_end": NOW + timedelta(days=80),
        "powered_by": "PHP/8.4.1",
        "generators": ["WordPress 7.1"],
        "cms": "WordPress",
        "has_viewport": True,
        "has_description": True,
        "has_structured_data": True,
        "has_tel_link": True,
        "shows_phone": True,
        "page_digits": "0299000000",
        "emails": [f"contact@{host}"],
        "copyright_years": [NOW.year],
        "has_mail_server": True,
        "has_spf": True,
        "has_dmarc": True,
        "shown_mail_domains": {host: True},
    }
    healthy.update(facts)
    return SiteReading(**healthy)


# (name, trade, city, facts of the reading; "no_email" drops the address)
SITES: list[tuple[str, str, str, dict[str, Any]]] = [
    (
        "Bellanger Électricité",
        "electricien",
        "Mulhouse",
        {"gambling_links": ["bahis-giris.test"], "has_description": False},
    ),
    (
        "Élagage Tessier",
        "paysagiste",
        "Clermont-Ferrand",
        {"https": "absent", "certificate_end": None, "has_dmarc": False},
    ),
    (
        "Les Jardins du Lac",
        "paysagiste",
        "Chartres",
        {"https": "invalid_certificate", "certificate_end": None, "has_viewport": False},
    ),
    (
        "Jardins Guillot",
        "paysagiste",
        "Moulins-lès-Metz",
        {"powered_by": "PHP/7.1.33", "generators": ["WordPress 4.9.8"], "has_spf": False},
    ),
    ("Entreprise Royer", "electricien", "Germaine", {"powered_by": "PHP/8.1.29", "generators": ["WordPress 6.8"]}),
    (
        "Jardins Imbert",
        "paysagiste",
        "Reims",
        {"powered_by": "PHP/8.1.12", "has_dmarc": False, "page_digits": "0612345678"},
    ),
    (
        "Élagage Renaud",
        "paysagiste",
        "Schœlcher",
        {"powered_by": "PHP/7.4.33", "has_dmarc": False, "has_tel_link": False, "no_email": True},
    ),
    ("Jardins Jacquet", "paysagiste", "Reims", {"has_spf": False, "has_dmarc": False, "copyright_years": [2015]}),
    ("Garage Fabre", "garage", "Mont-de-Marsan", {"has_spf": False, "has_dmarc": False}),
    (
        "Lemoine Paysage",
        "paysagiste",
        "Besançon",
        {"has_spf": False, "shows_phone": False, "has_tel_link": False, "no_email": True},
    ),
    ("Fabre Paysage", "paysagiste", "Saint-Max", {"has_viewport": False, "has_dmarc": False}),
    ("Quéré Espaces Verts", "paysagiste", "Cébazat", {"powered_by": "PHP/8.2.20", "generators": ["WordPress 6.5"]}),
    ("Garage Jacquet", "garage", "Niort", {"powered_by": "PHP/8.2.12", "has_structured_data": False, "no_email": True}),
    ("Auto Daniel", "garage", "Draguignan", {"powered_by": "PHP/8.2.25", "has_dmarc": False}),
    (
        "Élec Thibault",
        "electricien",
        "Bergerac",
        {"certificate_end": NOW + timedelta(days=12), "has_structured_data": False},
    ),
    (
        "Garage Ollivier",
        "garage",
        "Nîmes",
        {"generators": ["WordPress 6.2"], "copyright_years": [2014], "has_dmarc": False},
    ),
    ("Verdier Paysage", "paysagiste", "Saint-Apollinaire", {"generators": ["WordPress 6.1"], "has_tel_link": False}),
    ("Jardins Blanchard", "paysagiste", "Périgny", {"has_dmarc": False}),
    ("Bellanger Paysage", "paysagiste", "Mont-de-Marsan", {}),
    ("Picard Électricité", "electricien", "Reims", {}),
    ("Jardins Noël", "paysagiste", "Caen", {"generators": [], "cms": "Hostinger", "powered_by": None}),
    ("Coste Électricité", "electricien", "Chambéry", {"unreachable": True}),
    ("Jardins Hubert", "paysagiste", "Périgny", {"unreachable": True}),
    ("Garage Thibault", "garage", "Nîmes", {"refused": True}),
    # Already written to
    (
        "Jardins Hamel",
        "paysagiste",
        "La Rochelle",
        {"powered_by": "PHP/7.4.33", "generators": ["WordPress 4.9"], "has_spf": False, "written": "replied"},
    ),
    (
        "Hubert Automobiles",
        "garage",
        "Agen",
        {"powered_by": "PHP/7.4.33", "generators": ["WordPress 6.6"], "written": "opened"},
    ),
    (
        "Élagage Daniel",
        "paysagiste",
        "Bretteville-sur-Odon",
        {"powered_by": "PHP/7.4.33", "copyright_years": [2015], "written": "sent"},
    ),
    ("Atelier Paysage Morin", "paysagiste", "Castres", {"copyright_years": [2019], "written": "care"}),
]
VIVIER: list[tuple[str, str, str, str]] = [
    ("Jardins Perrot", "paysagiste", "Rennes", "FR"),
    ("Garage Lebrun", "garage", "Rennes", "FR"),
    ("Élec Marchand", "electricien", "Nantes", "FR"),
    ("Jardins Rolland", "paysagiste", "Lausanne", "CH"),
    ("Garage Schmitt", "garage", "Genève", "CH"),
]


async def wordpress_branch(_self: WordPressReleases) -> tuple[int, int]:
    """The branch the invented readings are written against."""
    return (7, 1)


async def main() -> None:
    WordPressReleases.current_branch = wordpress_branch  # type: ignore[method-assign]
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        owner = User(
            name="Camille Martin",
            email="owner@example.com",
            hashed_password=AuthService.hash_password("local-only-never-typed"),
            role=UserRole.SUPER_ADMIN.value,
            onboarding_completed=True,
            company_website_url="https://camille-martin.example",
        )
        db.add(owner)
        db.commit()
        product_module_service.set_enabled(db, "site-care", True, user_id=owner.id)
        settings: OwnerSettings = owner_settings_service.save(
            db,
            owner.id,
            OwnerSettings(
                presenter=Presenter(
                    name="Camille Martin",
                    role="développeuse web à Nantes",
                    tagline="Je travaille seul, à distance, pour des entreprises comme la vôtre.",
                    site_url="https://camille-martin.example",
                    photo_url="",
                )
            ),
        )
        search = ProspectSearch(user_id=owner.id, trades=["paysagiste", "garage", "electricien"], status="completed")
        db.add(search)
        db.commit()
        for name, trade, city, country in VIVIER:
            host = site_service.new_page_slug(name).rsplit("-", 1)[0] + ".test"
            db.add(
                ProspectSearchCandidate(
                    search_id=search.id,
                    user_id=owner.id,
                    trade=trade,
                    origin="google",
                    name=name,
                    city=city,
                    country=country,
                    phone="02 99 00 00 00",
                    website=f"https://www.{host}/",
                    website_status="live",
                    status=CandidateStatus.REJECTED.value,
                    reject_reason=CandidateRejectReason.HAS_WEBSITE.value,
                )
            )
        db.commit()

        for name, trade, city, facts in SITES:
            facts = dict(facts)
            host = site_service.new_page_slug(name).rsplit("-", 1)[0] + ".test"
            written: str | None = facts.pop("written", None)
            has_email: bool = not facts.pop("no_email", False)
            if facts.pop("unreachable", False):
                reading = SiteReading(host=host, read_at=NOW, error="ConnectError: Nom de domaine introuvable")
            elif facts.pop("refused", False):
                reading = SiteReading(host=host, read_at=NOW, status_code=403)
            else:
                reading = reading_of(host, **facts)
                if not has_email:
                    reading.emails, reading.shown_mail_domains = [], {}
            site = SiteCareSite(
                user_id=owner.id,
                business_name=name,
                trade=trade,
                city=city,
                country="FR",
                website=f"https://www.{host}/",
                host=host,
                phone="02 99 00 00 00",
                google_rating=4.7,
                google_reviews_count=31,
                status="",
                page_slug=site_service.new_page_slug(name),
                search_text=site_service.search_text_of(name, city, host),
            )
            db.add(site)
            await site_service.apply_reading(db, site, reading, settings)
            db.commit()
            if written is None:
                continue
            sent_at = NOW - timedelta(days=2)
            prospect = ProspectDB(
                user_id=owner.id,
                name=name,
                city=city,
                country="FR",
                email=site.email,
                website=site.website,
                category=trade,
                source="search",
                confidence=3,
                contacted=True,
                contacted_by_module="site-care",
                contacted_by_module_at=sent_at,
            )
            db.add(prospect)
            db.flush()
            log = EmailLog(
                user_id=owner.id,
                prospect_id=prospect.id,
                recipient_email=site.email or "",
                recipient_name=name,
                subject="La version de PHP de votre site",
                body_html="<p>Bonjour,</p>",
                provider="resend",
                status={"replied": "replied", "opened": "opened"}.get(written, "delivered"),
                sent_at=sent_at,
                replied_at=sent_at + timedelta(hours=5) if written == "replied" else None,
            )
            db.add(log)
            db.flush()
            site.prospect_id, site.written_at, site.last_email_log_id = prospect.id, sent_at, log.id
            db.add(
                SiteCareSentMessage(
                    user_id=owner.id,
                    site_id=site.id,
                    email_log_id=log.id,
                    kind="first",
                    subject=log.subject,
                    sent_at=sent_at,
                )
            )
            if written == "care":
                db.add(SiteCarePlan(user_id=owner.id, site_id=site.id, monthly_price_cents=10000, started_at=sent_at))
            db.commit()
        print("sites:", db.query(SiteCareSite).count())
    print("TOKEN", AuthService.create_access_token({"sub": "owner@example.com"}, expires_delta=timedelta(days=2)))


asyncio.run(main())
