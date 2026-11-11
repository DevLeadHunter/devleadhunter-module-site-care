"""The trades of the open map, named in French from the tags OpenStreetMap gives a business."""

from __future__ import annotations

from typing import ClassVar

from devleadhunter_site_care.catalog import BusinessFamily


class OpenMapTrades:
    """Tells the family and the French trade of a business from its tags on the open map."""

    FOOD_PLACE_LABELS: ClassVar[dict[str, str]] = {
        "restaurant": "Restaurant",
        "cafe": "Café",
        "bar": "Bar",
        "pub": "Bar",
        "fast_food": "Restauration rapide",
        "ice_cream": "Glacier",
    }
    LODGING_LABELS: ClassVar[dict[str, str]] = {
        "hotel": "Hôtel",
        "motel": "Hôtel",
        "guest_house": "Chambres d’hôtes",
        "chalet": "Gîte",
        "camp_site": "Camping",
        "hostel": "Auberge",
        "apartment": "Location de vacances",
    }
    _CRAFT_LABELS: ClassVar[dict[str, str]] = {
        "agricultural_engines": "Machines agricoles",
        "bakery": "Boulangerie",
        "beekeeper": "Apiculteur",
        "blacksmith": "Ferronnier",
        "boatbuilder": "Chantier naval",
        "brewery": "Brasserie artisanale",
        "builder": "Maçon",
        "cabinet_maker": "Ébéniste",
        "car_repair": "Garage automobile",
        "carpenter": "Charpentier",
        "caterer": "Traiteur",
        "chimney_sweeper": "Ramoneur",
        "cleaning": "Entreprise de nettoyage",
        "confectionery": "Confiserie",
        "distillery": "Distillerie",
        "dressmaker": "Couturier",
        "electrician": "Électricien",
        "electronics_repair": "Réparation électronique",
        "floorer": "Poseur de sols",
        "gardener": "Paysagiste",
        "glaziery": "Vitrier",
        "handicraft": "Artisan d’art",
        "hvac": "Chauffagiste",
        "insulation": "Isolation",
        "jeweller": "Bijoutier",
        "joiner": "Menuisier",
        "key_cutter": "Serrurier",
        "locksmith": "Serrurier",
        "metal_construction": "Métallier",
        "painter": "Peintre en bâtiment",
        "photographer": "Photographe",
        "plasterer": "Plâtrier",
        "plumber": "Plombier",
        "pottery": "Potier",
        "printer": "Imprimeur",
        "roofer": "Couvreur",
        "sawmill": "Scierie",
        "sculptor": "Sculpteur",
        "shoemaker": "Cordonnier",
        "signmaker": "Fabricant d’enseignes",
        "stonemason": "Tailleur de pierre",
        "tailor": "Couturier",
        "tiler": "Carreleur",
        "upholsterer": "Tapissier",
        "watchmaker": "Horloger",
        "window_construction": "Menuiserie",
        "winery": "Domaine viticole",
    }
    _SHOP_LABELS: ClassVar[dict[str, str]] = {
        "agrarian": "Fournitures agricoles",
        "alcohol": "Cave à vin",
        "antiques": "Antiquaire",
        "art": "Galerie d’art",
        "bakery": "Boulangerie",
        "bathroom_furnishing": "Salle de bains",
        "beauty": "Institut de beauté",
        "bed": "Literie",
        "beverages": "Boissons",
        "bicycle": "Magasin de vélos",
        "books": "Librairie",
        "butcher": "Boucherie",
        "car": "Vente automobile",
        "car_parts": "Pièces auto",
        "car_repair": "Garage automobile",
        "caravan": "Camping-cars",
        "cheese": "Fromagerie",
        "chocolate": "Chocolaterie",
        "clothes": "Boutique de vêtements",
        "coffee": "Thé et café",
        "computer": "Magasin d’informatique",
        "confectionery": "Confiserie",
        "convenience": "Épicerie",
        "copyshop": "Reprographie",
        "cosmetics": "Cosmétiques",
        "craft": "Loisirs créatifs",
        "deli": "Épicerie fine",
        "doityourself": "Magasin de bricolage",
        "dry_cleaning": "Pressing",
        "electronics": "Magasin d’électronique",
        "fabric": "Tissus",
        "farm": "Vente à la ferme",
        "florist": "Fleuriste",
        "frame": "Encadreur",
        "funeral_directors": "Pompes funèbres",
        "furniture": "Magasin de meubles",
        "garden_centre": "Jardinerie",
        "gift": "Boutique de cadeaux",
        "greengrocer": "Primeur",
        "hairdresser": "Coiffeur",
        "hardware": "Quincaillerie",
        "hearing_aids": "Audioprothésiste",
        "herbalist": "Herboristerie",
        "interior_decoration": "Décoration",
        "jewelry": "Bijouterie",
        "kitchen": "Cuisiniste",
        "laundry": "Laverie",
        "locksmith": "Serrurier",
        "massage": "Massage",
        "medical_supply": "Matériel médical",
        "mobile_phone": "Téléphonie",
        "motorcycle": "Magasin de motos",
        "motorcycle_repair": "Garage moto",
        "music": "Magasin de musique",
        "musical_instrument": "Instruments de musique",
        "optician": "Opticien",
        "paint": "Magasin de peinture",
        "pastry": "Pâtisserie",
        "perfumery": "Parfumerie",
        "pet": "Animalerie",
        "pet_grooming": "Toilettage",
        "photo": "Photographe",
        "rental": "Location",
        "seafood": "Poissonnerie",
        "second_hand": "Dépôt-vente",
        "sewing": "Mercerie",
        "shoes": "Magasin de chaussures",
        "sports": "Magasin de sport",
        "stationery": "Papeterie",
        "storage_rental": "Location de box",
        "supermarket": "Supermarché",
        "tailor": "Retoucherie",
        "tattoo": "Tatoueur",
        "tea": "Thé et café",
        "tiles": "Carrelage",
        "tobacco": "Tabac",
        "toys": "Magasin de jouets",
        "trade": "Négoce de matériaux",
        "travel_agency": "Agence de voyages",
        "tyres": "Pneus",
        "wine": "Cave à vin",
    }
    _OFFICE_LABELS: ClassVar[dict[str, str]] = {
        "accountant": "Expert-comptable",
        "advertising_agency": "Agence de communication",
        "architect": "Architecte",
        "company": "Entreprise",
        "construction_company": "Entreprise de construction",
        "consulting": "Conseil",
        "coworking": "Espace de coworking",
        "engineer": "Bureau d’études",
        "estate_agent": "Agence immobilière",
        "event_management": "Événementiel",
        "financial": "Finance",
        "financial_advisor": "Conseil financier",
        "graphic_design": "Graphiste",
        "insurance": "Assurance",
        "it": "Informatique",
        "lawyer": "Avocat",
        "logistics": "Logistique",
        "moving_company": "Déménageur",
        "newspaper": "Journal",
        "notary": "Notaire",
        "property_management": "Gestion immobilière",
        "publisher": "Éditeur",
        "security": "Sécurité",
        "surveyor": "Géomètre",
        "tax_advisor": "Conseil fiscal",
        "telecommunication": "Télécommunications",
        "travel_agent": "Agence de voyages",
        "tutoring": "Soutien scolaire",
        "web_design": "Agence web",
    }
    _OFFICES_THAT_ARE_NO_BUSINESS: ClassVar[frozenset[str]] = frozenset(
        {
            "administrative",
            "association",
            "charity",
            "diplomatic",
            "educational_institution",
            "foundation",
            "government",
            "ngo",
            "political_party",
            "politician",
            "quango",
            "religion",
            "research",
            "union",
        }
    )
    _SHOPS_THAT_ARE_NO_BUSINESS: ClassVar[frozenset[str]] = frozenset({"vacant", "no"})

    @classmethod
    def trade_of(
        cls, *, craft: str, shop: str, office: str, amenity: str, tourism: str
    ) -> tuple[BusinessFamily, str] | None:
        """
        The family and the French trade of a business.

        Args:
            craft: Its ``craft`` tag, empty when it has none.
            shop: Its ``shop`` tag.
            office: Its ``office`` tag.
            amenity: Its ``amenity`` tag.
            tourism: Its ``tourism`` tag.

        Returns:
            The family and the trade, a general word when the map's own is not in the lists; None for an object
            that is no business of a known family (a public body, an empty shop, a school).
        """
        if craft:
            return BusinessFamily.CRAFT, cls._CRAFT_LABELS.get(craft, "Artisan")
        if shop:
            if shop in cls._SHOPS_THAT_ARE_NO_BUSINESS:
                return None
            return BusinessFamily.SHOP, cls._SHOP_LABELS.get(shop, "Commerce")
        if office:
            if office in cls._OFFICES_THAT_ARE_NO_BUSINESS:
                return None
            return BusinessFamily.OFFICE, cls._OFFICE_LABELS.get(office, "Entreprise")
        if amenity in cls.FOOD_PLACE_LABELS:
            return BusinessFamily.FOOD, cls.FOOD_PLACE_LABELS[amenity]
        if tourism in cls.LODGING_LABELS:
            return BusinessFamily.LODGING, cls.LODGING_LABELS[tourism]
        return None
