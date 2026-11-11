"""The « Entretien de sites » module as the core sees it, through the ``devleadhunter.product_modules`` entry point.

Everything the hooks hand over is imported here, when the registry loads the module: the registry catches a module
that fails to import and runs without it, whereas a hook failing later (while the core mounts its routes) would take
the core down.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import select

from core.clock import naive_utc_now
from core.product_modules.contract import BackgroundLoop, ProductModule
from services.notification_service import notification_service

from devleadhunter_site_care import MODULE_KEY, MODULE_LABEL
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.routes import care_plans, owner_settings, public_pages, searches, sites, watch
from devleadhunter_site_care.services.worker import site_care_worker

if TYPE_CHECKING:
    from fastapi import APIRouter
    from sqlalchemy.orm import Session

    from schemas.notification import DemoEventIn

logger = logging.getLogger(__name__)

_MIGRATIONS_PACKAGE: str = "devleadhunter_site_care.migrations"
PAGE_OPENED_EVENT: str = "site_care_page_opened"
PAGE_REPLY_CLICKED_EVENT: str = "site_care_page_reply_clicked"
PAGE_FORWARD_CLICKED_EVENT: str = "site_care_page_forward_clicked"
_CLICK_WORDINGS: dict[str, str] = {
    PAGE_REPLY_CLICKED_EVENT: "a cliqué sur « Me répondre » depuis sa page",
    PAGE_FORWARD_CLICKED_EVENT: "a cliqué sur « Ce n’est pas moi qui gère le site » depuis sa page",
}


class SiteCareModule(ProductModule):
    """
    Entretien de sites: businesses that already have a website, checked from the outside and written to one by one.

    Installed in production switched off (``enabled_by_default``): its routes answer 404 and its loop stays stopped
    until the super admin switches it on. It sells nothing through the campaigns: each message leaves by hand,
    from a site's sheet.
    """

    key: ClassVar[str] = MODULE_KEY
    label: ClassVar[str] = MODULE_LABEL
    description: ClassVar[str] = (
        "Les entreprises qui ont déjà un site : contrôle du site vu de l'extérieur, message à son propriétaire "
        "sur le point à corriger, veille et suivi mensuel."
    )
    enabled_by_default: ClassVar[bool] = False
    notification_tag: ClassVar[str] = "🛠️ Entretien de sites"
    demo_beacon_prefix: ClassVar[str | None] = "site_care_"

    # Tracked by name in schema_migrations: a name never changes once it ran in production.
    MIGRATION_NAMES: ClassVar[tuple[str, ...]] = ("add_site_care_tables", "add_site_care_open_map_search")

    def load(self) -> None:
        """Register the module's tables on the core's metadata, before ``init_db()`` creates the missing ones."""
        import devleadhunter_site_care.models  # noqa: F401

    def routers(self) -> list[APIRouter]:
        """
        The list and its sheets, the searches, the watch, the care plans, the settings and the public page.

        Returns:
            The six routers, mounted under the API prefix.
        """
        return [
            sites.router,
            searches.router,
            watch.router,
            care_plans.router,
            owner_settings.router,
            public_pages.router,
        ]

    def background_loops(self) -> list[BackgroundLoop]:
        """
        The worker that runs the searches and keeps the old checks fresh.

        Returns:
            Its loop.
        """
        return [site_care_worker.run_forever]

    def migrations(self) -> list[tuple[str, str]]:
        """
        The module's tracked migrations, run after the core's.

        Returns:
            (name, dotted module path) pairs, in order.
        """
        return [(name, f"{_MIGRATIONS_PACKAGE}.{name}") for name in self.MIGRATION_NAMES]

    async def handle_demo_beacon(self, db: Session, payload: DemoEventIn) -> None:
        """
        Note that a business owner opened the page prepared for him, and tell the module's owner the first time.

        Args:
            db: Active database session.
            payload: The event the page beaconed.
        """
        if payload.is_automated_browser or payload.event not in (PAGE_OPENED_EVENT, *_CLICK_WORDINGS):
            return
        site: SiteCareSite | None = db.execute(
            select(SiteCareSite).where(SiteCareSite.page_slug == payload.demo_slug, SiteCareSite.archived_at.is_(None))
        ).scalar_one_or_none()
        if site is None:
            return
        click_wording: str | None = _CLICK_WORDINGS.get(payload.event)
        is_button_click: bool = click_wording is not None
        is_first_open: bool = not is_button_click and site.page_opened_at is None
        if not is_button_click:
            site.page_opened_at = site.page_opened_at or naive_utc_now()
            site.page_open_count += 1
            db.commit()
        if not (is_first_open or is_button_click):
            return
        try:
            await notification_service.notify_module_event(
                user_id=site.user_id,
                category=MODULE_KEY,
                level="success" if is_button_click else "info",
                title=site.business_name,
                body=(
                    f"{self.notification_tag} · {click_wording}"
                    if click_wording is not None
                    else f"{self.notification_tag} · a ouvert la page préparée pour lui"
                ),
                url=f"/dashboard/site-care?tab=all&site={site.id}",
                tag=f"site-care-page-{site.id}",
            )
        except Exception:
            logger.warning("[SiteCare] could not notify the page event of site %s", site.id, exc_info=True)
