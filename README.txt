Module Odoo: scraping_data (multi-source)
---------------------------------------

Contenu:
 - Modèles: scraping.result, scraping.email, scraping.keyword, scraping.source
 - Scrapers: PagesJaunes, TunisieIndex, Facebook (scraping public)
 - Détection keywords + mapping vers mailing.list
 - Ajout automatique dans mailing.contact + création de mailing.list par keyword
 - Cron example (disabled by default)

Requirements (server):
 - python3 packages: requests, beautifulsoup4
 - optional: rapidfuzz (for fuzzy keyword matching)

Install:
 - copier le dossier dans addons de ton Odoo 18
 - installer les dépendances python sur le serveur:
     pip install requests beautifulsoup4
 - redémarrer Odoo, mettre à jour la liste des modules et installer 'Scraping Data - Multi Source'

Notes:
 - Facebook public scraping is best-effort and may break or be rate-limited.
 - Respecte robots.txt et conditions des sites.