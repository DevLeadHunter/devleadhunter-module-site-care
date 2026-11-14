"""What the list and the sheet say of a site whose address may no longer be the business's own."""

from __future__ import annotations

from typing import ClassVar

from devleadhunter_site_care.catalog import AddressDoubt
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.services.site_reader import SiteReading


class AddressDoubtWording:
    """Writes why a site waits for a look by hand instead of a message."""

    _LIST_LINES: ClassVar[dict[AddressDoubt, str]] = {
        AddressDoubt.LEADS_TO_GAMBLING_SITE: "L’adresse renvoie vers un site de jeux d’argent",
        AddressDoubt.TITLE_SELLS_GAMBLING: "Le site affiche des jeux d’argent",
        AddressDoubt.VISIBLE_GAMBLING_LINK: "Lien visible vers un site de jeux d’argent",
    }
    _LIST_LINE_WITHOUT_REASON: ClassVar[str] = "Adresse à vérifier à la main"
    _DO_NOT_WRITE_ADVICE: ClassVar[str] = (
        "N’écrivez pas à l’entreprise au sujet de ce site. Si elle est toujours ouverte, c’est peut-être un "
        "prospect pour le module Sites web."
    )

    @classmethod
    def list_line_of(cls, site: SiteCareSite) -> str:
        """
        The sentence of the site's line in the list.

        Args:
            site: The site, with what its last check read.

        Returns:
            What the address shows, in a few words.
        """
        doubt: AddressDoubt | None = cls._last_reading_of(site).address_doubt
        return cls._LIST_LINES[doubt] if doubt is not None else cls._LIST_LINE_WITHOUT_REASON

    @classmethod
    def sheet_text_of(cls, site: SiteCareSite) -> str | None:
        """
        What the sheet says in place of the site's points.

        Args:
            site: The site, with what its last check read.

        Returns:
            What was seen and what to do about it, None when the address raises no doubt.
        """
        reading: SiteReading = cls._last_reading_of(site)
        doubt: AddressDoubt | None = reading.address_doubt
        if doubt == AddressDoubt.LEADS_TO_GAMBLING_SITE:
            return (
                f"L’adresse du site renvoie aujourd’hui vers {reading.host_on_another_domain}, un site de jeux "
                f"d’argent. Le nom de domaine n’est sans doute plus à l’entreprise. {cls._DO_NOT_WRITE_ADVICE}"
            )
        if doubt == AddressDoubt.TITLE_SELLS_GAMBLING:
            return (
                "Le site affiche aujourd’hui des jeux d’argent à la place de l’entreprise. Le nom de domaine a "
                f"sans doute été repris. {cls._DO_NOT_WRITE_ADVICE}"
            )
        if doubt == AddressDoubt.VISIBLE_GAMBLING_LINK:
            return (
                f"La page d’accueil montre des liens de jeux d’argent vers {', '.join(reading.gambling_links)}. "
                "Un pirate cache ses liens : des liens laissés visibles viennent plutôt d’un nom de domaine repris "
                "par un vendeur de liens. Ouvrez le site pour voir s’il est encore tenu par l’entreprise : le "
                "module ne prépare pas de message pour ce cas."
            )
        return None

    @staticmethod
    def _last_reading_of(site: SiteCareSite) -> SiteReading:
        """What the site's last check read."""
        return SiteReading.from_json(site.reading)
