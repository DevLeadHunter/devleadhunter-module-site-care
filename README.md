# DevLeadHunter · module Entretien de sites

Module produit optionnel de DevLeadHunter (clé `site-care`, libellé « Entretien de sites »). Il s'adresse aux
entreprises qui ont déjà un site : le site est regardé de l'extérieur, comme le ferait un visiteur, et son propriétaire
reçoit un message sur le point qui mérite une correction, avec le moyen de le vérifier lui-même et le prix. Le module
vend deux choses : une correction à prix fixe et un suivi mensuel.

## État : installé, désactivé par défaut

- `enabled_by_default = False` : l'interrupteur `site-care` reste à `false` dans `product_modules` tant que le super
  admin ne l'allume pas (Paramètres → Administration → Modules). Coupé, ses routes répondent 404 et sa boucle de fond
  est arrêtée.
- Il ne vend rien par les campagnes : chaque message part à la main, depuis la fiche d'un prospect.

## Ce que fait le module

| Écran | Rôle |
| --- | --- |
| Mes prospects (`/dashboard/site-care`) | La seule liste du module. Chaque ligne dit le type de souci (Site piraté, Sécurité, Version à risque, Mise à jour en retard, E-mails…), la technologie (« PHP 7.4 ») et le fait en une phrase. La fiche prépare le message et l'envoie. |
| Nouvelle recherche (`/dashboard/site-care/search`) | Fait entrer des entreprises dans le module : depuis la base du compte (métier, pays, ville) ou depuis OpenStreetMap (département, type d'entreprise, sites à garder). |
| Veille (`/dashboard/site-care/watch`) | Ce qui vient de changer sur les sites suivis et les dates qui approchent. |
| Suivis (`/dashboard/site-care/care-plans`) | Les clients en suivi mensuel et leur rapport du mois. |
| Réglages (`/dashboard/settings/site-care`) | Prix, quand écrire, points regardés, qui écrit. |
| Page pour le prospect (`/bilan/<adresse>` sur l'hôte des démos) | Ce qui a été vu sur son site, en clair. Facultative : le message part sans lien, sauf demande. |

### D'où viennent les entreprises

Une recherche puise dans l'une de ces deux sources.

**La base du compte.** La recherche du cœur écarte une entreprise dès qu'elle a un site en ligne
(`prospect_search_candidates`, raison `has_website`). Ces entreprises sont déjà nommées, situées, avec leur fiche
Google : la recherche du module les fait entrer, toutes. Chaque recherche du module Sites web en apporte de nouvelles.

**OpenStreetMap.** La carte libre liste, département par département, les entreprises qui ont un site : artisans,
commerces, bureaux et services, restaurants et cafés, hébergements. Le module lui pose une question par département
(serveur public Overpass) et n'en garde que le nom, le métier, la ville, le téléphone, l'email et le site
(`site_care_map_businesses`). Sont laissés de côté : les enseignes (étiquette de marque), une adresse qui pointe à
l'intérieur d'un site (« …/magasins/rennes »), un site partagé par trois entreprises ou plus du département, les
organismes publics et les associations. La recherche lit ensuite chaque site et garde ce que
l'utilisateur a choisi : tous les sites, ceux qui ont un souci, ou ceux qui ont un souci de sécurité (site piraté, pas
de cadenas, PHP ou WordPress qui n'est plus suivi ou qui s'arrête bientôt). Un site lu n'est jamais relu par une
recherche suivante, gardé ou non. La ville qui manque sur la carte est retrouvée par la position (geo.api.gouv.fr),
pour les sites gardés seulement ; quand ce service ne répond pas, la boucle de fond la rattrape entre deux recherches.
Les données d'OpenStreetMap sont sous licence ODbL : l'écran crédite ses contributeurs. Les départements
d'outre-mer ne sont pas proposés.

Dans les deux cas, un site de réseau, une page Facebook ou un mini-site d'annuaire sont laissés de côté, et un site
gardé sans adresse e-mail reçoit celle que montrent ses pages de contact et de mentions légales.

Une entreprise ne vit que dans le module (`site_care_sites`) jusqu'au premier message. À ce moment elle devient un
prospect du cœur : par le chemin du cœur lui-même (« garder à la main » un candidat écarté) quand elle vient de la
base, par une création de prospect quand elle vient d'OpenStreetMap. Les règles du cœur s'appliquent alors à elle
comme à tout prospect (« ne plus contacter », verrou entre modules, désinscription, capture des réponses).

### Ce qui est lu sur un site

Une seule lecture de la page d'accueil, et les réglages publics du nom de domaine (MX, SPF, DMARC). Rien n'est envoyé
au site, aucun dossier caché n'est demandé, aucune connexion n'est essayée. Les requêtes ne sortent que vers
l'internet public (`PublicOnlyAsyncTransport` du cœur). Douze points en sortent, en quatre familles : sécurité
(cadenas, moteur PHP, logiciel du site, piratage), e-mails (adresse affichée, expéditeur reconnu, protection du nom),
coordonnées (numéro de la fiche Google, numéro cliquable, année en bas de page), visibilité (lecture sur téléphone,
présentation dans Google). « Chercher son email » lit en plus la page de contact et les mentions légales du site.

Un site trop lent à répondre est rangé « à revoir », jamais annoncé comme disparu.

Un piratage n'est retenu que sur des liens **cachés au visiteur** (bloc non affiché, de taille nulle ou poussé hors
de l'écran) vers des sites de jeux d'argent ; le mot « casino » seul ne suffit pas. Des jeux d'argent montrés
ouvertement disent autre chose : l'adresse renvoie vers un site de jeux sur un autre domaine, le titre de la page
vend des jeux, ou un lien de casino est laissé visible. Le nom de domaine a alors sans doute été repris (nom expiré
racheté, site refait par un vendeur de liens). Ces sites sont rangés « à revoir » avec ce qui a été vu, sans message :
rien de ce qui se lit là ne peut être reproché à l'entreprise.

**Ce dépôt est public : aucun vrai site n'y est associé à ce qui a été vu chez lui.** Les tests n'utilisent que des
noms et des domaines inventés ; aucun fichier de résultats réels n'est commité (`data/` est ignoré).

## Contenu

| Dossier | Rôle |
| --- | --- |
| `api/` | Paquet Python `devleadhunter-site-care` (`devleadhunter_site_care/`) : `catalog.py` (les douze points, les types de souci, les corrections et leurs prix), `services/` (lecture d'un site, points, résumé, textes, liste, recherche, envoi, veille, suivis, boucle de fond), `routes/`, `schemas/`, `models/`, `migrations/`, `module.py` (`SiteCareModule`). |
| `web/` | Layer Nuxt du dashboard (`$meta.name: site-care`) : les cinq écrans, le sélecteur de module, la page de réglages. |
| `demo-host/` | Layer Nuxt de l'hôte des démos : la page pour le prospect, `/bilan/[slug]`. |
| `docs/API.md` | Le contrat HTTP du module, que suivent les deux layers. |

## Branchement au cœur

Le contrat est décrit dans `docs/PRODUCT_MODULES.md` du cœur : le cœur n'importe jamais le module, il le découvre.

- **API** : le `pyproject.toml` déclare l'entry point `devleadhunter.product_modules` :
  `site-care = "devleadhunter_site_care.module:SiteCareModule"`. Le module fournit ses six routers, sa boucle de fond
  (`SiteCareWorker` : les recherches, puis le recontrôle des sites dont le contrôle a plus de sept jours), ses
  migrations (`add_site_care_tables` puis `add_site_care_open_map_search`, après celles du cœur) et le traitement du
  beacon de sa page (`site_care_page_opened`).
  Il n'ajoute aucune dépendance : `httpx` et `dnspython` sont déjà dans `api/requirements.txt` du cœur.
- **Envoi** : `SendService` passe par `EmailSendingService.send_via_user_identity` du cœur (expéditeur du compte,
  signature par défaut, pied de désinscription, adresse de réponse captée, journal `email_logs`). Avant d'écrire, il
  applique lui-même ce que la file des campagnes applique d'habitude : « ne plus contacter », prospect écarté, adresse
  en erreur, verrou de 45 jours entre modules, désinscription.
- **Web et démos** : `web/` et `demo-host/` du cœur étendent les layers (`productModuleLayers`). Dans un layer, les
  imports vers le cœur restent en `~/…`, ceux entre fichiers du module sont relatifs.

## Développer et tester

Cloner ce dépôt à côté du cœur, puis depuis le dossier `api/` du cœur, dans son venv :

```bash
pip install -e ../../devleadhunter-module-site-care/api
python -m pytest ../../devleadhunter-module-site-care/api/tests -q
python -m ruff check ../../devleadhunter-module-site-care/api
python -m ruff format --check ../../devleadhunter-module-site-care/api
```

Les tests réutilisent les fixtures du cœur (`tests/conftest.py` du cœur, base SQLite en mémoire) : leur dossier n'a
pas de `__init__.py`, pour que `tests` reste le paquet de tests du cœur. Le module y est installé et coupé, comme en
production ; un test qui le veut allumé demande la fixture `site_care_module_switched_on`. Aucun test ne lit un vrai
site : un contrôle reçoit la lecture qu'il aurait faite (`reading_of` dans `tests/conftest.py`).

Pour les layers : `DLH_PRODUCT_MODULES_DIR` pointe sur le dossier qui contient les clones, et une jonction
`web/node_modules` (et `demo-host/node_modules`) vers celles du cœur résout les dépendances. Sous Windows, la retirer
avec `cmd /c rmdir`, jamais `rm -rf`.
