"""
The words written to a business owner about the point that leads his site's check: the message and the page.

One entry per point and state that can lead. Each says the same thing in the same order: what was seen, what it
changes for him, how he can check it himself, what is offered. No jargon is left unexplained.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from devleadhunter_site_care.catalog import PointKey, PointState
from devleadhunter_site_care.services.site_points import SitePoint


@dataclass(frozen=True)
class LeadWording:
    """
    How one leading point is told to the owner.

    Attributes:
        subject: The subject of the message.
        title: The page's title in three parts, the middle one highlighted.
        seen_label: The label of the finding card.
        seen_lead: The finding in one sentence.
        seen_rest: Its explanation.
        changes: What it changes for the owner.
        proof_steps: How he can check it himself.
        proof_sentence: The same check in one sentence, for the message.
        offer_label: What is offered, in the first person.
    """

    subject: str
    title: tuple[str, str, str]
    seen_label: str
    seen_lead: str
    seen_rest: str
    changes: tuple[str, ...]
    proof_steps: tuple[str, ...]
    proof_sentence: str
    offer_label: str


_TO_FIX: str = "Point à corriger"
_TO_WATCH: str = "Point à surveiller"
_DATE_COMING_UP: str = "Date qui approche"
_QUICK_FIX: str = "La correction prend quelques minutes."
_HOSTER_SETTING: str = "Le réglage se fait une fois, chez l’hébergeur du nom de domaine."
_PHP_PROOF_STEPS: tuple[str, ...] = (
    "Appelez votre hébergeur, ou écrivez-lui.",
    "Demandez-lui : « Quelle version de PHP fait tourner mon site ? »",
)
_PHP_PROOF_SENTENCE: str = "Demandez à votre hébergeur quelle version de PHP fait tourner votre site."
_CMS_PROOF_STEPS: tuple[str, ...] = (
    "Connectez-vous à l’administration de votre site.",
    "Ouvrez « Mises à jour » : la version y est écrite.",
)
_CMS_PROOF_SENTENCE: str = "Dans l’administration de votre site, ouvrez « Mises à jour » : la version y est écrite."
_MAIL_OFFER: str = "Je règle les e-mails de votre nom de domaine."
_TOUCHUP_OFFER: str = "Je corrige les petites choses qui datent sur votre site."


class LeadWordings:
    """Finds the wording of a leading point."""

    @classmethod
    def of(cls, point: SitePoint, domain: str) -> LeadWording:
        """
        The wording of the point that leads a site.

        Args:
            point: The leading point, with what the check read (a version, a date).
            domain: The site's address without « www. », for the checks the owner types.

        Returns:
            The wording, the point's own facts filled in.
        """
        data: dict[str, Any] = point.data
        builders = {
            PointKey.HACKED: cls._hacked,
            PointKey.HTTPS: cls._https,
            PointKey.PHP: cls._php,
            PointKey.CMS: cls._cms,
            PointKey.CONTACT_MAIL: cls._contact_mail,
            PointKey.SPF: cls._spf,
            PointKey.DMARC: cls._dmarc,
            PointKey.GOOGLE_PHONE: cls._google_phone,
            PointKey.TEL_LINK: cls._tel_link,
            PointKey.YEAR: cls._year,
            PointKey.MOBILE: cls._mobile,
            PointKey.SEARCH: cls._search,
        }
        return builders[point.key](point.state, data, domain)

    @staticmethod
    def _hacked(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        return LeadWording(
            subject="Des liens de casino sur votre site",
            title=("Votre site contient ", "des liens vers des casinos", ". Ce n’est pas vous qui les avez mis."),
            seen_label="À corriger sans attendre",
            seen_lead="Votre page d’accueil contient des liens cachés vers des sites de casino.",
            seen_rest=(
                "Un visiteur ne les voit pas, mais Google les lit. Quelqu’un est entré dans votre site pour les y mettre."
            ),
            changes=(
                "Google finit par afficher un avertissement à côté de votre nom, ou par retirer votre site de ses "
                "résultats.",
                "Tant que la porte d’entrée n’est pas refermée, les liens reviennent.",
            ),
            proof_steps=("Ouvrez Google.", f"Tapez : site:{domain} casino"),
            proof_sentence=(
                f"Dans Google, tapez « site:{domain} casino » : les pages ajoutées à votre insu apparaissent."
            ),
            offer_label="Je nettoie votre site et je referme la porte d’entrée.",
        )

    @staticmethod
    def _https(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        variant: str = data.get("variant", "absent")
        if variant == "expiring":
            end_date: str = data.get("end_date", "")
            return LeadWording(
                subject="Le cadenas de sécurité de votre site",
                title=("Le cadenas de sécurité de votre site ", f"expire le {end_date}", "."),
                seen_label=_DATE_COMING_UP,
                seen_lead=f"Le certificat de sécurité de votre site expire le {end_date}.",
                seen_rest="Il se renouvelle d’habitude tout seul, un mois avant. Ici, il ne l’a pas été.",
                changes=(
                    "Le jour de l’expiration, le navigateur affichera un avertissement à vos visiteurs.",
                    "Un renouvellement fait à temps ne se voit pas : rien ne change pour eux.",
                ),
                proof_steps=(
                    "Ouvrez votre site et appuyez sur le cadenas, à gauche de l’adresse.",
                    "Lisez la date de fin du certificat.",
                ),
                proof_sentence=(
                    "Ouvrez votre site, appuyez sur le cadenas à gauche de l’adresse et lisez la date de fin du "
                    "certificat."
                ),
                offer_label="Je renouvelle le cadenas et je règle son renouvellement automatique.",
            )
        if variant == "invalid":
            return LeadWording(
                subject="L’avertissement de sécurité sur votre site",
                title=("Votre site affiche ", "un avertissement de sécurité", " avant de s’ouvrir."),
                seen_label=_TO_FIX,
                seen_lead="Le certificat de sécurité de votre site n’est pas valable.",
                seen_rest=(
                    "Avant d’ouvrir la page, le navigateur prévient le visiteur que la connexion n’est pas sûre."
                ),
                changes=(
                    "La plupart des visiteurs ferment la page quand ils voient cet avertissement.",
                    "Google met en avant les sites dont le cadenas est en règle.",
                ),
                proof_steps=("Ouvrez votre site dans un navigateur.", "Lisez l’avertissement affiché avant la page."),
                proof_sentence="Ouvrez votre site dans un navigateur et lisez l’avertissement affiché avant la page.",
                offer_label="Je remets le cadenas de sécurité en règle.",
            )
        return LeadWording(
            subject="L’avertissement de sécurité sur votre site",
            title=("Votre site s’ouvre avec la mention ", "« Non sécurisé »", "."),
            seen_label=_TO_FIX,
            seen_lead="Votre site n’a pas le cadenas de sécurité (https).",
            seen_rest="À gauche de votre adresse, le navigateur écrit « Non sécurisé » à chaque visiteur.",
            changes=(
                "Un visiteur qui lit « Non sécurisé » hésite à vous appeler ou à vous écrire. Certains repartent.",
                "Google met en avant les sites qui ont le cadenas.",
            ),
            proof_steps=(
                "Ouvrez votre site sur votre téléphone.",
                "Regardez à gauche de l’adresse : « Non sécurisé ».",
            ),
            proof_sentence=(
                "Ouvrez votre site et regardez à gauche de l’adresse : un cadenas, ou la mention « Non sécurisé »."
            ),
            offer_label="Je mets le cadenas de sécurité en place.",
        )

    @staticmethod
    def _php(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        version: str = data.get("version", "")
        if state == PointState.WATCH:
            end_date: str = data.get("end_date", "")
            return LeadWording(
                subject="La version de PHP de votre site",
                title=("Le moteur de votre site ne sera plus corrigé ", f"après le {end_date}", "."),
                seen_label=_DATE_COMING_UP,
                seen_lead=f"Votre site tourne avec PHP {version}, dont les correctifs s’arrêtent le {end_date}.",
                seen_rest=(
                    "PHP est le logiciel qui fait fonctionner votre site. Après cette date, la version "
                    f"{version} ne reçoit plus de correctif de sécurité."
                ),
                changes=(
                    "Après cette date, une faille découverte dans cette version ne sera plus réparée.",
                    "Changer de version avant la date se fait sans urgence, au moment que vous choisissez.",
                ),
                proof_steps=_PHP_PROOF_STEPS,
                proof_sentence=_PHP_PROOF_SENTENCE,
                offer_label="Je passe votre site sur une version de PHP suivie.",
            )
        end_year: str = data.get("end_year", "")
        return LeadWording(
            subject="La version de PHP de votre site",
            title=("Le moteur de votre site n’est plus corrigé ", f"depuis {end_year}", "."),
            seen_label=_TO_FIX,
            seen_lead=f"Votre site tourne avec PHP {version}, une version qui n’est plus corrigée.",
            seen_rest=(
                f"PHP est le logiciel qui fait fonctionner votre site. La version {version} ne reçoit plus aucun "
                f"correctif de sécurité depuis {data.get('end_month_year', end_year)}."
            ),
            changes=(
                "Une faille découverte aujourd’hui dans cette version ne sera jamais réparée. C’est une des portes "
                "d’entrée habituelles des pirates.",
                "Votre hébergeur peut retirer cette version. Le site s’arrêterait alors du jour au lendemain.",
            ),
            proof_steps=_PHP_PROOF_STEPS,
            proof_sentence=_PHP_PROOF_SENTENCE,
            offer_label="Je passe votre site sur une version de PHP suivie.",
        )

    @staticmethod
    def _cms(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        name: str = data.get("name", "une ancienne version de son logiciel")
        software: str = name.split(" ")[0]
        if state == PointState.WATCH:
            return LeadWording(
                subject="La version de votre site",
                title=("Le logiciel de votre site ", "a des mises à jour en attente", "."),
                seen_label=_TO_WATCH,
                seen_lead=f"Votre site utilise {name}, alors que la version actuelle est la {data.get('current', '')}.",
                seen_rest=(
                    f"{software} est le logiciel qui sert à gérer votre site. Chaque mise à jour corrige des "
                    "failles de sécurité."
                ),
                changes=(
                    "Les failles corrigées depuis votre version sont publiques : elles deviennent faciles à exploiter.",
                    "Une mise à jour faite régulièrement prend peu de temps.",
                ),
                proof_steps=_CMS_PROOF_STEPS,
                proof_sentence=_CMS_PROOF_SENTENCE,
                offer_label="Je mets à jour votre site et ses extensions.",
            )
        return LeadWording(
            subject="La version de votre site",
            title=("Le logiciel de votre site ", "n’est plus mis à jour", "."),
            seen_label=_TO_FIX,
            seen_lead=f"Votre site utilise {name}, une version qui n’est plus suivie.",
            seen_rest=(
                f"{software} est le logiciel qui sert à gérer votre site. Seules ses versions récentes reçoivent "
                "les correctifs de sécurité."
            ),
            changes=(
                "Les failles connues de cette version restent ouvertes. Des robots les cherchent en permanence.",
                "Plus la mise à jour attend, plus elle est longue à faire.",
            ),
            proof_steps=_CMS_PROOF_STEPS,
            proof_sentence=_CMS_PROOF_SENTENCE,
            offer_label="Je mets à jour votre site et ses extensions.",
        )

    @staticmethod
    def _contact_mail(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        return LeadWording(
            subject="L’adresse e-mail de votre site",
            title=("L’adresse e-mail affichée sur votre site ", "ne reçoit pas les messages", "."),
            seen_label=_TO_FIX,
            seen_lead="L’adresse e-mail affichée sur votre site ne peut pas recevoir de messages.",
            seen_rest=(
                "Son nom de domaine n’a pas de messagerie : un message envoyé à cette adresse revient à son expéditeur."
            ),
            changes=(
                "Un client qui vous écrit à cette adresse n’a jamais de réponse.",
                "Il suffit d’afficher une adresse qui fonctionne, ou de rebrancher la messagerie.",
            ),
            proof_steps=(
                "Depuis une autre boîte, écrivez à l’adresse affichée sur votre site.",
                "Regardez si le message arrive.",
            ),
            proof_sentence="Écrivez à l’adresse affichée sur votre site depuis une autre boîte.",
            offer_label=_MAIL_OFFER,
        )

    @staticmethod
    def _spf(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        return LeadWording(
            subject="Les e-mails de votre nom de domaine",
            title=("Vos e-mails risquent d’arriver ", "dans les indésirables", "."),
            seen_label=_TO_FIX,
            seen_lead="Votre nom de domaine envoie des e-mails sans dire qui en a le droit.",
            seen_rest=(
                "Les messageries comme Gmail vérifient ce réglage, appelé SPF. Sans lui, vos messages peuvent être "
                "classés en indésirables ou refusés."
            ),
            changes=(
                "Un devis ou une facture envoyés à un client peuvent ne jamais arriver dans sa boîte de réception.",
                _HOSTER_SETTING,
            ),
            proof_steps=(
                "Envoyez-vous un e-mail vers une adresse Gmail.",
                "Ouvrez-le, puis « Afficher l’original » : lisez la ligne SPF.",
            ),
            proof_sentence="Envoyez-vous un e-mail vers une adresse Gmail, puis ouvrez « Afficher l’original ».",
            offer_label=_MAIL_OFFER,
        )

    @staticmethod
    def _dmarc(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        return LeadWording(
            subject="Les e-mails de votre nom de domaine",
            title=("N’importe qui peut envoyer des e-mails ", "à votre nom", "."),
            seen_label=_TO_WATCH,
            seen_lead="Rien n’empêche quelqu’un d’envoyer des e-mails au nom de votre domaine.",
            seen_rest=(
                "Un réglage appelé DMARC dit aux messageries de refuser ces faux messages. Il n’est pas en place."
            ),
            changes=("Un escroc peut écrire à vos clients avec votre adresse d’expéditeur.", _HOSTER_SETTING),
            proof_steps=(
                "Envoyez-vous un e-mail vers une adresse Gmail.",
                "Ouvrez-le, puis « Afficher l’original » : lisez la ligne DMARC.",
            ),
            proof_sentence="Envoyez-vous un e-mail vers une adresse Gmail, puis ouvrez « Afficher l’original ».",
            offer_label=_MAIL_OFFER,
        )

    @staticmethod
    def _google_phone(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        return LeadWording(
            subject="Le numéro affiché sur votre site",
            title=("Le numéro de votre fiche Google ", "n’est pas celui de votre site", "."),
            seen_label=_TO_WATCH,
            seen_lead="Le numéro de votre fiche Google n’apparaît pas sur votre page d’accueil.",
            seen_rest="Votre page en affiche un autre. Un client ne sait pas lequel appeler.",
            changes=("Un des deux numéros est peut-être ancien : des appels se perdent.", _QUICK_FIX),
            proof_steps=(
                "Cherchez votre entreprise dans Google.",
                "Comparez le numéro de la fiche et celui de votre page d’accueil.",
            ),
            proof_sentence="Comparez le numéro de votre fiche Google et celui de votre page d’accueil.",
            offer_label="Je corrige les coordonnées de votre site.",
        )

    @staticmethod
    def _tel_link(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        if data.get("variant") == "no_number":
            return LeadWording(
                subject="Le numéro de téléphone sur votre site",
                title=("Votre page d’accueil ", "n’affiche aucun numéro de téléphone", "."),
                seen_label=_TO_WATCH,
                seen_lead="Aucun numéro de téléphone n’apparaît sur votre page d’accueil.",
                seen_rest="Un visiteur qui veut vous appeler doit le chercher ailleurs.",
                changes=("Chaque geste en plus fait perdre des appels.", _QUICK_FIX),
                proof_steps=("Ouvrez votre site.", "Cherchez votre numéro sur la page d’accueil."),
                proof_sentence="Ouvrez votre site et cherchez votre numéro sur la page d’accueil.",
                offer_label="Je corrige les coordonnées de votre site.",
            )
        return LeadWording(
            subject="Le numéro affiché sur votre site",
            title=("Sur téléphone, votre numéro ", "ne se compose pas d’un appui", "."),
            seen_label=_TO_WATCH,
            seen_lead="Sur un téléphone, il faut recopier votre numéro pour vous appeler.",
            seen_rest="Un appui sur le numéro devrait lancer l’appel. Ce n’est pas le cas sur votre page d’accueil.",
            changes=("Chaque geste en plus fait perdre des appels.", _QUICK_FIX),
            proof_steps=("Ouvrez votre site sur votre téléphone.", "Appuyez sur votre numéro."),
            proof_sentence="Sur votre téléphone, appuyez sur le numéro affiché sur votre site.",
            offer_label="Je corrige les coordonnées de votre site.",
        )

    @staticmethod
    def _year(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        year: str = str(data.get("year", ""))
        return LeadWording(
            subject="Le bas de page de votre site",
            title=("Le bas de votre site affiche encore ", f"« © {year} »", "."),
            seen_label=_TO_WATCH,
            seen_lead=f"Le bas de votre page d’accueil affiche « © {year} ».",
            seen_rest=(
                "Un visiteur en déduit que le site n’est plus tenu à jour, et se demande si l’entreprise travaille "
                "encore."
            ),
            changes=("Un site qui paraît à l’abandon fait perdre des demandes.", _QUICK_FIX),
            proof_steps=("Ouvrez votre site.", "Regardez tout en bas de la page d’accueil."),
            proof_sentence="Regardez tout en bas de votre page d’accueil.",
            offer_label=_TOUCHUP_OFFER,
        )

    @staticmethod
    def _mobile(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        return LeadWording(
            subject="Votre site sur téléphone",
            title=("Votre site ", "ne s’adapte pas aux téléphones", "."),
            seen_label=_TO_FIX,
            seen_lead="Votre page d’accueil n’est pas prévue pour les téléphones.",
            seen_rest="Elle s’y affiche en tout petit : il faut zoomer pour lire et pour appuyer sur un lien.",
            changes=(
                "Plus d’une visite sur deux se fait depuis un téléphone. Ces visiteurs repartent vite.",
                "Google classe moins bien les sites qui ne s’adaptent pas aux téléphones.",
            ),
            proof_steps=("Ouvrez votre site sur votre téléphone.", "Essayez de lire un texte sans zoomer."),
            proof_sentence="Ouvrez votre site sur votre téléphone.",
            offer_label="J’adapte votre site aux téléphones.",
        )

    @staticmethod
    def _search(state: PointState, data: dict[str, Any], domain: str) -> LeadWording:
        if data.get("variant") == "structured":
            seen_lead: str = "Il manque à votre site la fiche d’entreprise lue par Google et les IA."
            seen_rest: str = (
                "Cette fiche, invisible pour un visiteur, leur donne votre métier, votre adresse et vos horaires."
            )
        else:
            seen_lead = "Il manque à votre site la description que Google affiche sous son titre."
            seen_rest = "Sans elle, Google écrit lui-même ce texte, à partir de morceaux de la page."
        return LeadWording(
            subject="Votre site dans Google",
            title=("Google n’a pas ", "tout ce qu’il lui faut", " pour présenter votre site."),
            seen_label=_TO_WATCH,
            seen_lead=seen_lead,
            seen_rest=seen_rest,
            changes=(
                "Un texte clair sous votre nom donne envie de cliquer.",
                "Les assistants comme ChatGPT s’appuient sur ces informations pour citer une entreprise.",
            ),
            proof_steps=("Ouvrez Google.", f"Tapez : site:{domain} et lisez le texte sous votre titre."),
            proof_sentence=f"Dans Google, tapez « site:{domain} » et regardez le texte sous votre titre.",
            offer_label="Je rédige la présentation de votre site pour Google.",
        )
