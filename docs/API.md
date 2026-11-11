# Entretien de sites — contrat HTTP du module

Toutes les routes vivent sous `/api/v1/site-care`. Elles répondent 404 « Module désactivé » tant que le module est
coupé. Sauf la page publique, chaque route demande l'utilisateur connecté (jeton du dashboard) et ne voit que ses
données. Les dates sont en UTC naïf, sans `Z` (contrat du cœur). Les libellés affichés sont écrits par l'API : le
dashboard ne recompose aucune phrase.

## Vocabulaire

- **Site** : une entreprise qui a déjà un site, entrée dans le module. C'est la ligne de « Mes prospects ».
- **Point** : une des douze choses regardées sur un site. État : `fix` (à corriger), `watch` (à surveiller), `ok`,
  `unknown` (pas visible de l'extérieur).
- **Type de souci** (`kind`) : `hack` Site piraté, `security` Sécurité, `risk` Version à risque, `late` Mise à jour en
  retard, `mail` E-mails, `mobile` Sur téléphone, `contact` Coordonnées, `dated` Site daté, `google` Dans Google,
  plus `ok` (rien à signaler) et `review` (site à revoir) pour l'étiquette d'une ligne.

```ts
type PointKey =
  | 'https' | 'php' | 'cms' | 'hacked' | 'contact_mail' | 'spf'
  | 'dmarc' | 'google_phone' | 'tel_link' | 'year' | 'mobile' | 'search'
type IssueKind = 'hack' | 'security' | 'risk' | 'late' | 'mail' | 'mobile' | 'contact' | 'dated' | 'google'
type LeadKind = IssueKind | 'ok' | 'review'
type Tone = 'red' | 'amber' | 'green' | 'neutral' | 'ink' | 'violet'
type SiteTab = 'to_write' | 'written' | 'no_email' | 'nothing' | 'review'
```

## Objets

### `SiteLead`

```ts
type SiteLead = {
  kind: LeadKind
  kind_label: string
  tone: Tone
  tech: string | null // null quand aucune technologie n'est à nommer
  sentence: string
}
```

```json
{ "kind": "risk", "kind_label": "Version à risque", "tone": "red", "tech": "PHP 7.4", "sentence": "Plus de correctif de sécurité depuis 2022" }
```

### `SiteState`

```ts
type SiteState = {
  key: 'to_write' | 'no_email' | 'written' | 'replied' | 'care' | 'nothing' | 'review' | 'do_not_contact'
  label: string
  tone: Tone
}
```

```json
{ "key": "to_write", "label": "À écrire", "tone": "ink" }
```

### `SiteListItem`

```ts
type SiteListItem = {
  id: number
  business_name: string
  trade_label: string
  city: string | null
  country: string // code du pays, deux lettres
  domain: string
  website: string
  email: string | null
  tab: SiteTab // l'onglet où le site est rangé
  state: SiteState
  lead: SiteLead
  also: string | null // les autres soucis du site, null quand il n'y en a qu'un
  checked_at: string
}
```

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

### `SitePoint`

```ts
type SitePoint = {
  key: PointKey
  kind: IssueKind
  kind_label: string
  tech: string | null
  fact: string
}
```

```json
{ "key": "php", "kind": "risk", "kind_label": "Version à risque", "tech": "PHP 7.4", "fact": "Le site tourne avec PHP 7.4, qui ne reçoit plus de correctifs de sécurité depuis novembre 2022." }
```

### `SiteDetail`

```ts
type SiteDetail = {
  id: number
  business_name: string
  trade_label: string
  city: string | null
  country: string
  domain: string
  website: string
  email: string | null
  tab: SiteTab
  state: SiteState
  lead: SiteLead
  also: string | null
  checked_at: string
  phone: string | null
  google_rating: number | null
  google_reviews_count: number | null
  google_maps_url: string | null
  unread_text: string | null // la phrase affichée quand le site n'a pas pu être lu (tab = review)
  fixes: SitePoint[]
  watches: SitePoint[]
  good_line: string | null
  hidden_line: string | null
  offer: { label: string; price_label: string }[]
  monthly_label: string
  message: { subject: string; paragraphs: string[]; paragraphs_with_link: string[] } | null
  page_url: string | null
  can_send: boolean
  send_refusal: string | null // pourquoi l'envoi est refusé, en clair
  sent_messages: {
    kind: 'first' | 'report'
    kind_label: string
    subject: string
    sent_at: string
    status_label: string
  }[]
  care_plan: { id: number; monthly_price_cents: number; started_at: string } | null
}
```

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
  "tab": "written",
  "state": { "key": "written", "label": "Écrit le 9 nov.", "tone": "neutral" },
  "lead": { "kind": "risk", "kind_label": "Version à risque", "tone": "red", "tech": "PHP 7.4", "sentence": "Plus de correctif de sécurité depuis 2022" },
  "also": null,
  "checked_at": "2026-11-11T15:40:00",
  "phone": "02 99 00 00 00",
  "google_rating": 4.7,
  "google_reviews_count": 31,
  "google_maps_url": "https://maps.google.com/?cid=1",
  "unread_text": null,
  "fixes": [
    { "key": "php", "kind": "risk", "kind_label": "Version à risque", "tech": "PHP 7.4", "fact": "Le site tourne avec PHP 7.4, qui ne reçoit plus de correctifs de sécurité depuis novembre 2022." }
  ],
  "watches": [],
  "good_line": "11 points sont bons : le cadenas, le logiciel du site, aucun piratage, l’adresse e-mail, l’expéditeur des e-mails, la protection du nom, le numéro de la fiche Google, le numéro cliquable, l’année en bas de page, la lecture sur téléphone, la présentation dans Google.",
  "hidden_line": null,
  "offer": [ { "label": "Passage à une version de PHP suivie", "price_label": "190 €" } ],
  "monthly_label": "100 € par mois",
  "message": {
    "subject": "La version de PHP de votre site",
    "paragraphs": [
      "Bonjour,",
      "Je suis Camille Morel, développeur web à Rennes. En regardant le site de Jardins Guillot, j’ai vu que le site tourne avec PHP 7.4, qui ne reçoit plus de correctifs de sécurité depuis novembre 2022.",
      "Vous pouvez le vérifier vous-même : demandez à votre hébergeur quelle version de PHP fait tourner votre site.",
      "J’ai regardé le reste de votre site, comme un visiteur : 11 points sur 12 sont bons.",
      "La correction coûte 190 €, une seule fois. Si cela ne vous intéresse pas, dites-le-moi et je ne vous recontacte plus.",
      "Bonne journée,"
    ],
    "paragraphs_with_link": [
      "Bonjour,",
      "Je suis Camille Morel, développeur web à Rennes. En regardant le site de Jardins Guillot, j’ai vu que le site tourne avec PHP 7.4, qui ne reçoit plus de correctifs de sécurité depuis novembre 2022.",
      "Vous pouvez le vérifier vous-même : demandez à votre hébergeur quelle version de PHP fait tourner votre site.",
      "J’ai regardé le reste de votre site, comme un visiteur. Tout est noté sur cette page : https://demo.dibodev.fr/bilan/jardins-guillot",
      "La correction coûte 190 €, une seule fois. Si cela ne vous intéresse pas, dites-le-moi et je ne vous recontacte plus.",
      "Bonne journée,"
    ]
  },
  "page_url": "https://demo.dibodev.fr/bilan/jardins-guillot",
  "can_send": false,
  "send_refusal": "Déjà écrit le 9 novembre.",
  "sent_messages": [
    { "kind": "first", "kind_label": "Premier message", "subject": "La version de PHP de votre site", "sent_at": "2026-11-09T09:20:00", "status_label": "Ouvert" }
  ],
  "care_plan": null
}
```

- Quand le site n'a pas pu être lu, `fixes`, `watches` et `offer` sont vides et `message` vaut `null`.
- `can_send` est faux quand il n'y a pas d'adresse, que le message est déjà parti, ou que le cœur interdit le
  contact.

## Routes

### Mes prospects

| Méthode et chemin | Corps ou paramètres | Réponse |
| --- | --- | --- |
| `GET /site-care/sites` | `tab` (défaut `to_write` ; `all` = tous les onglets), `trade` (clé de métier), `kind`, `q`, `limit` (défaut 100, max 500), `offset` | `SiteListResponse` |
| `GET /site-care/sites/{id}` | | `SiteDetail` |
| `PATCH /site-care/sites/{id}` | `{ "email": "contact@exemple.fr" }` (une adresse vide retire celle du site) | `SiteDetail` |
| `POST /site-care/sites/{id}/find-email` | | `SiteDetail` (son `email` est rempli quand une adresse est trouvée) |
| `POST /site-care/sites/{id}/recheck` | | `SiteDetail` |
| `POST /site-care/sites/{id}/send` | `{ "with_page_link": false }` | `SiteDetail` ; 409 avec la raison en `detail` quand l'envoi est refusé |
| `DELETE /site-care/sites/{id}` | | 204 (le site sort de la liste) |

```ts
type SiteListResponse = {
  counts: { total: number; with_email: number; to_fix: number; written: number } // tous les sites de l'utilisateur
  tab_counts: Record<SiteTab | 'all', number> // tous les sites de l'utilisateur
  trades: { key: string; label: string }[] // les métiers présents, pour le filtre
  matching_count: number // l'onglet et les filtres demandés
  sites: SiteListItem[]
}
```

```json
{
  "counts": { "total": 136, "with_email": 67, "to_fix": 32, "written": 9 },
  "tab_counts": { "to_write": 11, "written": 9, "no_email": 12, "nothing": 89, "review": 15, "all": 136 },
  "trades": [ { "key": "paysagiste", "label": "Paysagistes" } ],
  "matching_count": 11,
  "sites": [ SiteListItem ]
}
```

### Nouvelle recherche

| Méthode et chemin | Corps | Réponse |
| --- | --- | --- |
| `GET /site-care/search-options` | | `SearchOptions` |
| `POST /site-care/searches` | `SearchCreateBody` | `Search` ; 409 quand une recherche tourne déjà |
| `GET /site-care/searches/current` | | `Search` ou `null` (la recherche en cours, sinon la dernière) |

```ts
type SearchOptions = {
  countries: { code: string; label: string; available_count: number }[]
  trades: { key: string; label: string; available_by_country: Record<string, number> }[] // par code de pays
}

type SearchCreateBody = {
  trades: string[] // vide = tous les métiers
  country: string
  cities: string[] // vide = toutes les villes du pays
  count: number // de 1 à 300
}

type Search = {
  id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  status_label: string
  requested_count: number
  checked_count: number
  imported_count: number
  trades_label: string
  zone_label: string
  note: string | null // pourquoi la recherche a ramené moins d'entreprises, ou pourquoi elle a échoué
  created_at: string
  completed_at: string | null
}
```

```json
// SearchOptions
{
  "countries": [ { "code": "FR", "label": "France", "available_count": 1153 } ],
  "trades": [ { "key": "paysagiste", "label": "Paysagiste", "available_by_country": { "FR": 512, "CH": 340 } } ]
}
// SearchCreateBody
{ "trades": ["paysagiste"], "country": "FR", "cities": ["Reims"], "count": 50 }
// Search
{ "id": 4, "status": "running", "status_label": "En cours", "requested_count": 50, "checked_count": 12, "imported_count": 11,
  "trades_label": "Paysagiste, Garage", "zone_label": "France", "note": null, "created_at": "2026-11-11T16:00:00", "completed_at": null }
```

### Veille

`GET /site-care/watch` → `WatchResponse`

```ts
type WatchEvent = {
  key: string
  kind: LeadKind
  tone: Tone
  title: string
  detail: string
  when_label: string
  site_count: number
  action_label: string
  target: {
    site_id: number | null // ouvre la fiche de ce site
    tab: SiteTab | 'all' | null // sinon, « Mes prospects » sur cet onglet
    kind: IssueKind | null // et ce type de souci
  }
}

type WatchResponse = {
  today: WatchEvent[]
  deadlines: WatchEvent[]
}
```

```json
// WatchResponse
{
  "today": [ WatchEvent ],
  "deadlines": [ WatchEvent ]
}
// WatchEvent
{ "key": "hacked-12", "kind": "hack", "tone": "red", "title": "Un site piraté", "detail": "Bellanger Électricité, à Mulhouse : des liens cachés vers des casinos sur la page d’accueil.",
  "when_label": "Vu aujourd’hui", "site_count": 1, "action_label": "Voir ce prospect", "target": { "site_id": 12, "tab": null, "kind": null } }
```

### Suivis

| Méthode et chemin | Corps | Réponse |
| --- | --- | --- |
| `GET /site-care/care-plans` | | `CarePlanListResponse` |
| `POST /site-care/sites/{id}/care-plan` | `{ "monthly_price_cents": 10000 }` | `SiteDetail` |
| `DELETE /site-care/care-plans/{id}` | | 204 (le suivi s'arrête) |
| `POST /site-care/care-plans/{id}/report` | | `CarePlan` (le rapport du mois est parti) ; 409 avec la raison sinon |

```ts
type CarePlan = {
  id: number
  site_id: number
  business_name: string
  trade_label: string
  city: string | null
  domain: string
  last_check_summary: string
  last_checked_label: string
  report_state: 'due' | 'sent'
  report_label: string
  report_detail: string
  monthly_label: string
  since_label: string
  can_send_report: boolean
}

type CarePlanListResponse = {
  stats: { client_count: number; monthly_revenue_label: string; reports_due_count: number }
  plans: CarePlan[]
}
```

```json
// CarePlanListResponse
{ "stats": { "client_count": 3, "monthly_revenue_label": "350 €", "reports_due_count": 1 }, "plans": [ CarePlan ] }
// CarePlan
{ "id": 3, "site_id": 12, "business_name": "Quéré Espaces Verts", "trade_label": "Paysagiste", "city": "Cébazat", "domain": "quere-espaces-verts.example",
  "last_check_summary": "Tout est en ordre.", "last_checked_label": "Regardé le 10 novembre",
  "report_state": "due", "report_label": "À envoyer", "report_detail": "Premier rapport le 1er décembre",
  "monthly_label": "100 € par mois", "since_label": "Depuis le 10 novembre", "can_send_report": true }
```

### Réglages

`GET /site-care/settings` et `PUT /site-care/settings` (même forme, `PUT` renvoie les réglages enregistrés) :

```ts
type Settings = {
  prices: {
    key: 'cleanup' | 'php' | 'cms' | 'https' | 'mail' | 'search' | 'touchup' | 'mobile'
    label: string
    price_cents: number | null // null pour une correction sur devis
  }[]
  monthly_price_cents: number
  trigger: 'fix' | 'watch' // écrire dès qu'un point est à corriger, ou aussi quand trois points sont à surveiller
  points: { key: PointKey; family_label: string; label: string; is_enabled: boolean }[]
  presenter: {
    name: string
    role: string // suit « je suis {name}, » dans le message et sur la page
    tagline: string // la phrase qui le présente sur la page
    site_url: string
    photo_url: string
  }
  sender_email: string | null // en lecture seule, null quand l'envoi n'est pas configuré
}
```

```json
{
  "prices": [ { "key": "cleanup", "label": "Nettoyage du site après piratage", "price_cents": 39000 } ],
  "monthly_price_cents": 10000,
  "trigger": "fix",
  "points": [ { "key": "https", "family_label": "Sécurité", "label": "Cadenas de sécurité (https)", "is_enabled": true } ],
  "presenter": { "name": "Camille Morel", "role": "développeur web à Rennes", "tagline": "Je travaille seul, à distance, pour des entreprises comme la vôtre.", "site_url": "https://camille-morel.example", "photo_url": "" },
  "sender_email": "camille@mail.example.com"
}
```

### Page pour le prospect (publique)

`GET /site-care/public/pages/{slug}` → `PublicPage` ; 404 quand la page n'existe pas.

```ts
type PublicPage = {
  business_name: string
  domain: string
  title: { start: string; mark: string; end: string }
  intro: string // contient le domaine, que la page met en gras
  seen: { label: string; lead: string; rest: string }
  changes: string[]
  proof_steps: string[]
  offer: {
    label: string
    price_label: string
    note: string
    tag_label: string | null // null pour une correction sur devis
    reassurances: string[] // changent avec la correction : sur le site, ou sur les réglages du nom de domaine
  }
  goods: string[]
  other_fixes: string[]
  watches: string[]
  other_points_count: number
  presenter: { name: string; tagline: string; site_url: string; site_label: string; photo_url: string }
  reply_mailto: string // vide quand aucune adresse de réponse n'est connue
  forward_mailto: string
}
```

```json
{
  "business_name": "Élagage Renaud",
  "domain": "elagage-renaud.example",
  "title": { "start": "Le moteur de votre site n’est plus corrigé ", "mark": "depuis 2022", "end": "." },
  "intro": "Bonjour, je suis Camille Morel, développeur web à Rennes. J’ai regardé votre site elagage-renaud.example comme le ferait un visiteur, sans rien y toucher.",
  "seen": { "label": "Point à corriger", "lead": "Votre site tourne avec PHP 7.4, une version qui n’est plus corrigée.", "rest": "PHP est le logiciel qui fait fonctionner votre site. La version 7.4 ne reçoit plus aucun correctif de sécurité depuis novembre 2022." },
  "changes": ["Une faille découverte aujourd’hui dans cette version ne sera jamais réparée. C’est une des portes d’entrée habituelles des pirates.", "Votre hébergeur peut retirer cette version. Le site s’arrêterait alors du jour au lendemain."],
  "proof_steps": ["Appelez votre hébergeur, ou écrivez-lui.", "Demandez-lui : « Quelle version de PHP fait tourner mon site ? »"],
  "offer": { "label": "Je passe votre site sur une version de PHP suivie.", "price_label": "190 €", "note": "Une seule fois. Vous payez après la correction.", "tag_label": "Prix fixe", "reassurances": ["Je fais d’abord une sauvegarde complète.", "Je travaille sur une copie, pas sur votre site.", "Votre site garde la même présentation."] },
  "goods": ["Le cadenas de sécurité est en place."],
  "other_fixes": ["La page n’est pas prévue pour les téléphones : elle s’y affiche en tout petit."],
  "watches": ["Google n’a pas de fiche à lire sur votre entreprise."],
  "other_points_count": 3,
  "presenter": { "name": "Camille Morel", "tagline": "Développeur web à Rennes. Je travaille seul, à distance, pour des entreprises comme la vôtre.", "site_url": "https://camille-morel.example", "site_label": "camille-morel.example", "photo_url": "" },
  "reply_mailto": "mailto:camille@mail.example.com?subject=Re%3A%20La%20version%20de%20PHP%20de%20votre%20site",
  "forward_mailto": "mailto:camille@mail.example.com?subject=Re%3A%20La%20version%20de%20PHP%20de%20votre%20site&body=Bonjour%2C%0A%0ACe%20n%E2%80%99est%20pas%20moi%20qui%20g%C3%A8re%20le%20site.%20La%20personne%20%C3%A0%20contacter%20est%20%3A%20"
}
```

La page signale son ouverture par le beacon du cœur : `POST /api/v1/demo-events` avec
`{ "demo_slug": "<slug>", "event": "site_care_page_opened" }`, puis `site_care_page_reply_clicked` et
`site_care_page_forward_clicked` au clic sur ses deux boutons.
