{
    "name": "Scraping Data - Multi Source",
    "version": "1.0",
    "category": "Tools",
    "summary": "Scraping PagesJaunes, TunisieIndex, Facebook (public) - enrichit mailing lists by keyword",
    "author": "Ichrak",
    "depends": ["base_automation", "mass_mailing"],
    "data": [
        "security/ir.model.access.csv",
        "data/scraper_key_data.xml",
        "data/cron.xml",
        "data/base_automation.xml",
        "views/scraper_key_views.xml",
        "views/scraper_contact_views.xml",
        "views/scraping_cleanup_views.xml",
        "views/scraper_wizard_views.xml"

    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "external_dependencies": {
        "python": ["bs4", "requests", "pytesseract", "PIL"]
    },

}
