# Entretien de sites — contrat HTTP du module

Toutes les routes vivent sous `/api/v1/site-care`. Elles répondent 404 « Module désactivé » tant que le module est
coupé. Sauf la page publique, chaque route demande l'utilisateur connecté (jeton du dashboard) et ne voit que ses
données. Les dates sont en UTC naïf, sans `Z` (contrat du cœur). Les libellés affichés sont écrits par l'API : le
dashboard ne recompose aucune phrase.

## Vocabulaire

- **Site** : une entreprise qui a déjà un site, entrée dans le module. C'est la ligne de « Mes prospects ».
- **Point** : une des douze choses regardées sur un site (`https`, `php`, `cms`, `hacked`, `contact_mail`, `spf`,
  `dmarc`, `google_phone`, `tel_link`, `year`, `mobile`, `search`). État : `fix` (à corriger), `watch` (à surveiller),
  `ok`, `unknown` (pas visible de l'extérieur).
- **Type de souci** (`kind`) : `hack` Site piraté, `security` Sécurité, `risk` Version à risque, `late` Mise à jour en
  retard, `mail` E-mails, `mobile` Sur téléphone, `contact` Coordonnées, `dated` Site daté, `google` Dans Google,
  plus `ok` (rien à signaler) et `review` (site à revoir) pour l'étiquette d'une ligne.
- **Ton** (`tone`) : `red`, `amber`, `green`, `neutral`, `ink`, `violet`.

## Objets

### `SiteLead`

```json
{ "kind": "risk", "kind_label": "Version à risque", "tone": "red", "tech": "PHP 7.4", "sentence": "Plus de correctif de sécurité depuis 2022" }
```

`tech` vaut `null` quand aucune technologie n'est à nommer.

### `SiteState`

```json
{ "key": "to_write", "label": "À écrire", "tone": "ink" }
```

`key` : `to_write`, `no_email`, `written`, `replied`, `care`, `nothing`, `review`, `do_not_contact`.

### `SiteListItem`

```json
{
  "id": 12,
  "business_name": "Jardins Guillot",
  "trade_label": "Paysagiste",
  "city": "Moulins-lès-Metz",
  "country": "FR",
  "domain": "jardins-guillot.example",
  "website": "https://www.jardins-guillot.example/",
  "email": "contact@jardins-guillot.example",
  "tab": "to_write",
  "state": { "key": "to_write", "label": "À écrire", "tone": "ink" },
  "lead": { "kind": "risk", "kind_label": "Version à risque", "tone": "red", "tech": "PHP 7.1", "sentence": "Plus de correctif de sécurité depuis 2019" },
  "also": "Aussi : version à risque (WordPress 4.9), e-mails",
  "checked_at": "2026-11-11T15:40:00"
}
```

`tab` : `to_write`, `written`, `no_email`, `nothing`, `review` (l'onglet où le site est rangé). `email` et `also`
peuvent valoir `null`.

### `SitePoint`

```json
{ "key": "php", "kind": "risk", "kind_label": "Version à risque", "tech": "PHP 7.4", "fact": "Le site tourne avec PHP 7.4, qui ne reçoit plus de correctifs de sécurité depuis novembre 2022." }
```

### `SiteDetail`

Les champs de `SiteListItem`, plus :

```json
{
  "phone": "02 99 00 00 00",
  "google_rating": 4.7,
  "google_reviews_count": 31,
  "google_maps_url": "https://maps.google.com/?cid=1",
  "unread_text": null,
  "fixes": [ { "key": "php", "kind": "risk", "kind_label": "Version à risque", "tech": "PHP 7.4", "fact": "…" } ],
  "watches": [ { "key": "dmarc", "kind": "mail", "kind_label": "E-mails", "tech": null, "fact": "…" } ],
  "good_line": "7 points sont bons : le cadenas, aucun piratage…",
  "hidden_line": "Pas visible de l’extérieur, donc pas contrôlé : l’adresse e-mail.",
  "offer": [ { "label": "Passage à une version de PHP suivie", "price_label": "190 €" } ],
  "monthly_label": "100 € par mois",
  "message": { "subject": "La version de PHP de votre site", "paragraphs": ["Bonjour,", "…"], "paragraphs_with_link": ["Bonjour,", "…"] },
  "page_url": "https://demo.dibodev.fr/bilan/jardins-guillot",
  "can_send": true,
  "send_refusal": null,
  "sent_messages": [ { "kind": "first", "kind_label": "Premier message", "subject": "…", "sent_at": "2026-11-09T09:20:00", "status_label": "Ouvert" } ],
  "care_plan": null
}
```

- `unread_text` : la phrase affichée quand le site n'a pas pu être lu (`tab` = `review`), sinon `null`. Dans ce cas
  `fixes`, `watches` et `offer` sont vides et `message` vaut `null`.
- `good_line`, `hidden_line`, `message`, `page_url`, `send_refusal` peuvent valoir `null`.
- `can_send` est faux quand il n'y a pas d'adresse, que le message est déjà parti, ou que le cœur interdit le
  contact ; `send_refusal` dit alors pourquoi, en clair.
- `care_plan` : `null` ou `{ "id": 3, "monthly_price_cents": 10000, "started_at": "2026-11-10T08:00:00" }`.

## Routes

### Mes prospects

| Méthode et chemin | Corps ou paramètres | Réponse |
| --- | --- | --- |
| `GET /site-care/sites` | `tab` (défaut `to_write` ; `all` = tous les onglets), `trade` (clé de métier), `kind`, `q`, `limit` (défaut 100, max 500), `offset` | `SiteListResponse` |
| `GET /site-care/sites/{id}` | | `SiteDetail` |
| `PATCH /site-care/sites/{id}` | `{ "email": "contact@exemple.fr" }` | `SiteDetail` |
| `POST /site-care/sites/{id}/find-email` | | `SiteDetail` (son `email` est rempli quand une adresse est trouvée) |
| `POST /site-care/sites/{id}/recheck` | | `SiteDetail` |
| `POST /site-care/sites/{id}/send` | `{ "with_page_link": false }` | `SiteDetail` ; 409 avec la raison en `detail` quand l'envoi est refusé |
| `DELETE /site-care/sites/{id}` | | 204 (le site sort de la liste) |

`SiteListResponse` :

```json
{
  "counts": { "total": 136, "with_email": 67, "to_fix": 32, "written": 9 },
  "tab_counts": { "to_write": 11, "written": 9, "no_email": 12, "nothing": 89, "review": 15, "all": 136 },
  "trades": [ { "key": "paysagiste", "label": "Paysagistes" } ],
  "matching_count": 11,
  "sites": [ SiteListItem ]
}
```

`counts` et `tab_counts` portent sur tous les sites de l'utilisateur ; `matching_count` sur l'onglet et les filtres
demandés ; `trades` liste les métiers présents, pour le filtre.

### Nouvelle recherche

| Méthode et chemin | Corps | Réponse |
| --- | --- | --- |
| `GET /site-care/search-options` | | `SearchOptions` |
| `POST /site-care/searches` | `{ "trades": ["paysagiste"], "country": "FR", "cities": ["Reims"], "count": 50 }` | `Search` ; 409 quand une recherche tourne déjà |
| `GET /site-care/searches/current` | | `Search` ou `null` (la recherche en cours, sinon la dernière) |

`trades` vide = tous les métiers ; `cities` vide = toutes les villes du pays.

```json
// SearchOptions
{
  "countries": [ { "code": "FR", "label": "France", "available_count": 1153 } ],
  "trades": [ { "key": "paysagiste", "label": "Paysagiste", "available_by_country": { "FR": 512, "CH": 340 } } ]
}
// Search
{ "id": 4, "status": "running", "status_label": "En cours", "requested_count": 50, "checked_count": 12, "imported_count": 11,
  "trades_label": "Paysagiste, Garage", "zone_label": "France", "note": null, "created_at": "2026-11-11T16:00:00", "completed_at": null }
```

`status` : `pending`, `running`, `completed`, `failed`. `note` porte une phrase quand la base n'avait pas assez
d'entreprises ou que la recherche a échoué.

### Veille

`GET /site-care/watch` →

```json
{
  "today": [ WatchEvent ],
  "deadlines": [ WatchEvent ]
}
// WatchEvent
{ "key": "hacked-12", "kind": "hack", "tone": "red", "title": "Un site piraté", "detail": "Bellanger Électricité, à Mulhouse : des liens cachés vers des casinos sur la page d’accueil.",
  "when_label": "Vu aujourd’hui", "site_count": 1, "action_label": "Voir ce prospect", "target": { "site_id": 12, "tab": null, "kind": null } }
```

`target` : `site_id` ouvre la fiche d'un site ; sinon `tab` (souvent `all`) et `kind` ouvrent « Mes prospects » filtré.

### Suivis

| Méthode et chemin | Corps | Réponse |
| --- | --- | --- |
| `GET /site-care/care-plans` | | `CarePlanListResponse` |
| `POST /site-care/sites/{id}/care-plan` | `{ "monthly_price_cents": 10000 }` | `SiteDetail` |
| `DELETE /site-care/care-plans/{id}` | | 204 (le suivi s'arrête) |
| `POST /site-care/care-plans/{id}/report` | | `CarePlan` (le rapport du mois est parti) ; 409 avec la raison sinon |

```json
// CarePlanListResponse
{ "stats": { "client_count": 3, "monthly_revenue_label": "350 €", "reports_due_count": 1 }, "plans": [ CarePlan ] }
// CarePlan
{ "id": 3, "site_id": 12, "business_name": "Quéré Espaces Verts", "trade_label": "Paysagiste", "city": "Cébazat", "domain": "quere-espaces-verts.example",
  "last_check_summary": "Tout est en ordre.", "last_checked_label": "Regardé le 10 novembre",
  "report_state": "due", "report_label": "À envoyer", "report_detail": "Premier rapport le 1er décembre",
  "monthly_label": "100 € par mois", "since_label": "Depuis le 10 novembre", "can_send_report": true }
```

`report_state` : `due` ou `sent`.

### Réglages

`GET /site-care/settings` et `PUT /site-care/settings` (même forme, `PUT` renvoie les réglages enregistrés) :

```json
{
  "prices": [ { "key": "cleanup", "label": "Nettoyage du site après piratage", "price_cents": 39000 } ],
  "monthly_price_cents": 10000,
  "trigger": "fix",
  "points": [ { "key": "https", "family_label": "Sécurité", "label": "Cadenas de sécurité (https)", "is_enabled": true } ],
  "presenter": { "name": "Léo Guillaume", "role": "développeur web à Rennes", "tagline": "Je travaille seul, à distance, pour des entreprises comme la vôtre.", "site_url": "https://dibodev.fr", "photo_url": "" },
  "sender_email": "leo@mail.example.com"
}
```

- `prices[].price_cents` vaut `null` pour une correction sur devis. Clés : `cleanup`, `php`, `cms`, `https`, `mail`,
  `search`, `touchup`, `mobile`.
- `trigger` : `fix` (écrire dès qu'un point est à corriger) ou `watch` (aussi quand trois points sont à surveiller).
- `presenter.role` suit « je suis {name}, » dans le message et sur la page (« développeur web à Rennes ») ;
  `presenter.tagline` est la phrase qui le présente sur la page.
- `sender_email` est en lecture seule : l'adresse d'envoi du compte (`null` quand l'envoi n'est pas configuré).

### Page pour le prospect (publique)

`GET /site-care/public/pages/{slug}` → 404 quand la page n'existe pas.

```json
{
  "business_name": "Élagage Renaud",
  "domain": "elagage-renaud.example",
  "title": { "start": "Le moteur de votre site n’est plus corrigé ", "mark": "depuis 2022", "end": "." },
  "intro": "Bonjour, je suis Léo Guillaume, développeur web à Rennes. J’ai regardé votre site comme le ferait un visiteur, sans rien y toucher.",
  "seen": { "label": "Point à corriger", "lead": "Votre site tourne avec PHP 7.4, une version qui n’est plus corrigée.", "rest": "PHP est le logiciel qui fait fonctionner votre site. La version 7.4 ne reçoit plus aucun correctif de sécurité depuis novembre 2022." },
  "changes": ["Une faille découverte aujourd’hui…", "Votre hébergeur peut retirer cette version…"],
  "proof_steps": ["Appelez votre hébergeur, ou écrivez-lui.", "Demandez-lui : « Quelle version de PHP fait tourner mon site ? »"],
  "offer": { "label": "Je passe votre site sur une version de PHP suivie.", "price_label": "190 €", "note": "Une seule fois. Vous payez après la correction.", "tag_label": "Prix fixe", "reassurances": ["Je fais d’abord une sauvegarde complète.", "Je travaille sur une copie, pas sur votre site.", "Votre site garde la même présentation."] },
  "goods": ["Le cadenas de sécurité est en place."],
  "other_fixes": ["La page n’est pas prévue pour les téléphones : elle s’y affiche en tout petit."],
  "watches": ["Google n’a pas de fiche à lire sur votre entreprise."],
  "other_points_count": 11,
  "presenter": { "name": "Léo Guillaume", "tagline": "Développeur web à Rennes. Je travaille seul, à distance, pour des entreprises comme la vôtre.", "site_url": "https://dibodev.fr", "site_label": "dibodev.fr", "photo_url": "" },
  "reply_mailto": "mailto:…?subject=…",
  "forward_mailto": "mailto:…?subject=…&body=…"
}
```

`offer.tag_label` vaut `null` pour une correction sur devis ; `offer.reassurances` change avec la correction (sur le
site, ou sur les réglages du nom de domaine). `intro` contient le domaine, que la page met en gras.

La page signale son ouverture par le beacon du cœur : `POST /api/v1/demo-events` avec
`{ "demo_slug": "<slug>", "event": "site_care_page_opened" }`, puis `site_care_page_reply_clicked` et
`site_care_page_forward_clicked` au clic sur ses deux boutons.
