# Voir le module en local

Une API jetable sur SQLite, avec des entreprises inventées sur des domaines réservés (`.test`) : aucun vrai site
n'est lu ni cité. Le cœur est cloné à côté de ce dépôt et le module est installé dans son venv (`pip install -e`).

1. Dans un dossier vide hors du dépôt, un `.env` minimal, sans aucune clé externe :

   ```
   DATABASE_URL=sqlite:///./site_care_local.db
   SECRET_KEY=<une chaîne au hasard>
   CORS_ORIGINS=http://localhost:5173,http://localhost:3001
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=<une chaîne au hasard>
   FRONTEND_URL=http://localhost:5173
   DEMO_HOST_BASE_URL=http://localhost:3001
   R2_PUBLIC_BASE_URL_DEV=http://localhost:8899
   ```

2. Depuis ce dossier, avec `PYTHONPATH` sur `api/` du cœur : `python seed.py` crée les tables, un utilisateur, le
   module allumé et vingt-huit sites avec le contrôle qu'ils auraient eu. La dernière ligne affichée est un jeton de
   connexion : l'écrire dans `token.txt` à côté de `shoot_pages.py`.
3. L'API : `python -m uvicorn main:app --port 8040` (même dossier, même `PYTHONPATH`).
4. Le dashboard et l'hôte des démos du cœur, avec `DLH_PRODUCT_MODULES_DIR` sur le dossier des clones et
   `NUXT_PUBLIC_API_BASE=http://localhost:8040` : ports 5173 et 3001.
5. `python shoot_pages.py [list|drawer|search|watch|care|settings|page]` capture les écrans dans `shots/`, le jeton
   posé dans le navigateur (aucun mot de passe tapé).

Une recherche lancée en local lit les domaines `.test` du vivier : ils ne répondent pas, les sites arrivent donc dans
« À revoir ». C'est attendu.
