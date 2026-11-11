"""What a search carries of a business between the database and the network, whatever its source."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SiteToRead:
    """
    A business whose site a search is about to read, kept once the database connection is given back.

    Attributes:
        business_name: The business.
        trade: Its trade as a site stores it: the core's key, else its French name.
        city: Its town, when the source gives it.
        country: Its country.
        website: Its site's address.
        host: The site's host without « www. ».
        phone: Its phone number.
        email: Its email address, when the source gives it.
        google_rating: The rating of its Google listing.
        google_reviews_count: How many reviews its Google listing has.
        google_maps_url: Its Google listing.
        candidate_id: The core candidate it comes from, for a business of the owner's base.
        map_business_id: The open map's business it comes from.
        latitude: Where it is, when the source places it.
        longitude: Where it is.
    """

    business_name: str
    trade: str
    city: str | None
    country: str
    website: str
    host: str
    phone: str | None = None
    email: str | None = None
    google_rating: float | None = None
    google_reviews_count: int | None = None
    google_maps_url: str | None = None
    candidate_id: int | None = None
    map_business_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None
