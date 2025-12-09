import os
import re
import base64
import shutil
import time
import requests
from bs4 import BeautifulSoup
from odoo.exceptions import UserError
from urllib.parse import urljoin
from datetime import datetime
from PIL import Image
from io import BytesIO
import pytesseract
from soupsieve.util import lower

from odoo import models, fields, api


# Tesseract path
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
def setup_tesseract():
    """Configure pytesseract automatiquement selon l'OS – zéro config manuelle"""
    # Cas 1 : déjà dans le PATH → parfait
    if shutil.which("tesseract"):
        return

    # Cas 2 : Windows – chemins classiques
    if os.name == "nt":
        possible = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Tesseract-OCR\tesseract.exe",
        ]
        for path in possible:
            if os.path.isfile(path):
                pytesseract.pytesseract.tesseract_cmd = path
                return

    # Cas 3 : Linux/Docker – on espère qu’il est installé
    for path in ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]:
        if os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return

    # Cas 4 : variable d’environnement de secours
    custom = os.getenv("TESSERACT_CMD")
    if custom and os.path.isfile(custom):
        pytesseract.pytesseract.tesseract_cmd = custom
        return

    # Rien trouvé → message clair pour l’utilisateur
    raise UserError(
        "Tesseract OCR est introuvable !\n\n"
        "Solutions rapides :\n"
        "• Windows → Téléchargez et installez : https://github.com/UB-Mannheim/tesseract/wiki\n"
        "• Linux / Docker → Exécutez : sudo apt install tesseract-ocr\n"
        "• Ou définissez la variable d’environnement TESSERACT_CMD=/chemin/vers/tesseract"
    )

# Configuration automatique au chargement du module
setup_tesseract()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}
IGNORED = {
    "Accueil", "Annuaire Entreprises", "Actualités économiques",
    "Convertisseur de Monnaies", "Ajoutez une entreprise", "Annuaire  web",
    "Inviter un(e) ami(e)", "Nous Contacter", "Syndication RSS", "Popularité"
}

# 2) UTILITAIRES EMAIL
# =========================

COMMON_DOMAIN_FIXES = {
    # fautes courantes de domaines
    "gamil.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gmail.con": "gmail.com",
    "gmail.co": "gmail.com",

    "hotnail.com": "hotmail.com",
    "hotmai.com": "hotmail.com",
    "hotmial.com": "hotmail.com",
    "hotmail.co": "hotmail.com",
    "hotmail.con": "hotmail.com",

    "yaho.com": "yahoo.com",
    "yahou.com": "yahoo.com",
    "yaoo.com": "yahoo.com",
    "yhoo.com": "yahoo.com",

    "ymail.com": "gmail.com",   # demande: ymail -> gmail
    "outlok.com": "outlook.com",
    "outlook.co": "outlook.com",
}

FAKE_EMAILS = {
    "test@test.com", "example@example.com", "fake@fake.com",
    "a@a.com", "demo@demo.com", "no@no.com",
}

EMAIL_REGEX = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")

TLD_SET = {"com", "fr", "tn", "net", "org", "co", "info", "io", "biz", "dz", "ma", "de", "it", "es"}

class ScraperContact(models.Model):
    _name = "scraper.key"
    _description = "Scraper KEY"
    _rec_name = "keyword_input"


    keyword_input = fields.Char("Mot-clé à rechercher")
    is_scraped = fields.Boolean("Scraped", default=False)

    @api.model
    def clean_email(self, email):
        match = re.search(r'[a-zA-Z][\w\.-]*@[\w\.-]+\.\w+', email.strip())
        return lower(match.group(0)) if match else ""

    @api.model
    def today_date(self):
        return datetime.now().strftime("%Y-%m-%d")

    @api.model
    def extract_email_from_img(self, img_tag, base_url):
        if not img_tag or not img_tag.get("src"):
            return ""
        img_url = img_tag["src"]
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        elif img_url.startswith("/"):
            img_url = urljoin(base_url, img_url)
        try:
            resp = requests.get(img_url, headers=HEADERS)
            img = Image.open(BytesIO(resp.content))
            email = pytesseract.image_to_string(img, config='--psm 7').strip()
            return self.clean_email(email)
        except Exception:
            return ""

    @api.model
    def extract_mobile_from_html(self, soup):
        all_text = soup.get_text(" ", strip=True)
        phones_found = re.findall(r'\(?\+216\)?\s*[29]\d{2}\s*\d{3}\s*\d{3}', all_text)
        for num in phones_found:
            cleaned = re.sub(r'\D', '', num)
            if cleaned.startswith("216"):
                cleaned = cleaned[3:]
            if len(cleaned) == 8 and cleaned.startswith(("2", "9")):
                return cleaned
        return ""

    @api.model
    def extract_category_from_url(self, url):
        match = re.search(r"/annuaire-entreprises/([^/?#]+)", url)
        return match.group(1) if match else "inconnu"

    @api.model
    def get_all_category_links(self):
        url = "https://www.tunisieindex.com/"
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        table = soup.find("table", id="technoltb")
        if table:
            for a in table.find_all("a", href=True):
                href = a["href"]
                if "/annuaire-entreprises/" in href:
                    if href.startswith("//"):
                        href = "https:" + href
                    elif href.startswith("/"):
                        href = "https://www.tunisieindex.com" + href
                    links.append(href)
        return links

    @api.model
    def get_all_subcategory_links(self, category_url):
        response = requests.get(category_url, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/annuaire-entreprises/" in href and href != category_url:
                if href.startswith("//"):
                    href = "https:" + href
                elif href.startswith("/"):
                    href = "https://www.tunisieindex.com" + href
                links.append(href)
        return links if links else [category_url]

    @api.model
    def ocr_base64_image(self, base64_str):
        try:
            image_data = base64.b64decode(base64_str)
            image = Image.open(BytesIO(image_data))
            text = pytesseract.image_to_string(image, config='--psm 7').strip()
            return text
        except Exception:
            return ""

    @api.model
    def process_tunisieindex(self, url, noms_vus, category):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"[Erreur] Impossible de charger {url} : {e}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.find_all("tr")

        if not rows:
            print(f"⚠️ Aucune ligne trouvée sur {url}")
            return None

        for row in rows:
            td = row.find("td")
            if not td:
                continue

            a_tag = td.find("a", href=True)
            if not a_tag:
                continue

            name_text = a_tag.get_text(strip=True)
            if name_text in IGNORED or len(name_text) < 4 or name_text in noms_vus:
                continue

            noms_vus.add(name_text)
            detail_link = urljoin(url, a_tag["href"])
            email_text, mobile_text = "", ""

            try:
                detail_resp = requests.get(detail_link, headers=HEADERS, timeout=10)
                detail_resp.raise_for_status()
                detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

                # Email via image
                email_img = detail_soup.find("img", src=lambda x: x and "mailimage-entreprise.php" in x)
                if email_img:
                    email_text = self.extract_email_from_img(email_img, detail_link)

                # Téléphone
                mobile_text = self.extract_mobile_from_html(detail_soup)

            except Exception as e:
                print(f"[Erreur détail] {detail_link} : {e}")

            # On enregistre uniquement si email existe
            if self.clean_email(email_text):
                self.env['scraper.contact'].create({
                    "name": name_text,
                    "email": email_text,
                    "phone": mobile_text,
                    "keyword": category,
                    "date_scraping": self.today_date(),
                    "source": "TunisieIndex"
                })
                print(f" Ajouté: {name_text} | {email_text} | {mobile_text}")

        # Pagination sécurisée
        next_link = soup.find("a", title=lambda t: t and "page suivante" in t.lower())
        if next_link and next_link.get("href"):
            return urljoin(url, next_link["href"])
        return None

    @api.model
    def scrape_pagesjaunes(self, keyword):
        base_url = "https://pagesjaunes.com.tn/"
        url = f"{base_url}?s={keyword.replace(' ', '%20')}&c_type=c&c_id=&postalcode=tunisie"
        index = 1

        while url:
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                response.raise_for_status()
            except Exception as e:
                print(f"[Erreur] Impossible de charger {url} : {e}")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            results = soup.find_all("div", class_="listing_box")

            if not results:
                print(f" Aucun résultat trouvé sur {url}")
                break

            for item in results:
                name_tag = item.find("h2", class_="listing-title")
                name_text = name_tag.a.get_text(strip=True) if name_tag and name_tag.a else "N/A"

                address = item.find("div", class_="listing-adress")
                address_text = address.get_text(strip=True) if address else ""

                detail_link = urljoin(url, name_tag.a["href"]) if name_tag and name_tag.a else None
                phone_text = ""
                email_text = ""

                if detail_link:
                    try:
                        detail_resp = requests.get(detail_link, headers=HEADERS, timeout=10)
                        detail_resp.raise_for_status()
                        detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

                        # Téléphone
                        phone_div = detail_soup.find("div", class_="box-phone")
                        if phone_div:
                            phone_img = phone_div.find("img")
                            if phone_img and "base64" in phone_img.get("src", ""):
                                phone_text = self.ocr_base64_image(phone_img["src"].split(",")[1])
                            else:
                                phone_text = phone_div.get_text(strip=True)

                        # Email
                        email_div = detail_soup.find("div", class_="box-mail") or detail_soup.find("div", class_="box-email")
                        if email_div:
                            email_img = email_div.find("img")
                            if email_img and "base64" in email_img.get("src", ""):
                                email_text = self.ocr_base64_image(email_img["src"].split(",")[1])
                            else:
                                email_text = email_div.get_text(strip=True)

                    except Exception as e:
                        print(f"[Erreur détail] {detail_link} : {e}")

                # Sauvegarde dans Odoo
                if self.clean_email(email_text) :
                    self.env['scraper.contact'].create({
                        "name": name_text,
                        "email": self.clean_email(email_text),
                        "phone": phone_text,
                        "address": address_text,
                        "keyword": keyword,
                        "date_scraping": self.today_date(),
                        "source": "PagesJaunes"
                    })
                    print(f" Ajouté: {name_text} | {phone_text} | {email_text}")

            # Pagination
            next_link = soup.find("a", string=lambda x: x and "Suivant" in x)
            if not next_link:
                next_link = soup.find("a", class_="next") or soup.find("a", class_="next page-numbers")
            url = urljoin(base_url, next_link["href"]) if next_link and next_link.get("href") else None
            index += len(results)
            time.sleep(1)

    def scrape_by_keyword(self):
        if not self.keyword_input:
            raise UserError("Veuillez entrer un mot-clé avant de lancer le scraping.")
        self.is_scraped = False
        kw = self.keyword_input.strip().lower()
        print(f"🔎 Scraping pour le mot-clé : {kw}")

        # PagesJaunes
        self.scrape_pagesjaunes(kw)

        # TunisieIndex
        categories = self.get_all_category_links()
        for cat_url in categories:
            category_name = self.extract_category_from_url(cat_url)
            if kw in category_name.lower():
                try:
                    sub_urls = self.get_all_subcategory_links(cat_url)
                except Exception:
                    sub_urls = [cat_url]

                for sub_url in sub_urls:
                    page_url = sub_url
                    noms_vus = set()
                    while page_url:
                        try:
                            page_url = self.process_tunisieindex(page_url, noms_vus, category_name)
                        except Exception as e:
                            print(f"[Erreur] Problème avec {page_url} : {e}")
                            break
                        time.sleep(1)
            self.is_scraped = True
        return True

    def run_scraping(self):
        # pagejaune

        for kw in ["meubles", "meuble",
                   "informatique",
                   "location voiture", "location voitures",
                   "restaurant", "restaurants",
                   "bâtiment", "bâtiments",
                   "immobilier",
                   "santé",
                   "hôpital", "hôpitaux",
                   "dentiste", "dentistes",
                   "banque", "banques",
                   "coiffure", "coiffures",
                   "cosmétique", "cosmétiques",
                   "pharmacie", "pharmacies",
                   "voyage", "voyages",
                   "auto", "autos",
                   "pièces", "pièce",
                   "plomberie", "plomberies",
                   "déménagement", "déménagements",
                   "nettoyage", "nettoyages",
                   "impression", "impressions",
                   "mécanique", "mécaniques",
                   "agence", "agences",
                   "marketing",
                   "publicité", "publicités",
                   "vêtements", "vêtement",
                   "chaussures", "chaussure",
                   "bijouterie", "bijouteries",
                   "café", "cafés",
                   "salon de thé", "salons de thé",
                   "garage", "garages",
                   "assurance", "assurances",
                   "avocat", "avocats",
                   "notaire", "notaires",
                   "boulangerie", "boulangeries",
                   "pâtisserie", "pâtisseries",
                   "boissons", "boisson",
                   "chauffage", "chauffages",
                   "climatisation",
                   "peinture", "peintures",
                   "sécurité",
                   "alarmes", "alarme",
                   "entretien", "entretiens",
                   "décorateur", "décorateurs",
                   "menuiserie", "menuiseries",
                   "plâtrier", "plâtriers",
                   "carrelage", "carrelages",
                   "développeur", "développeurs",
                   "site web", "sites web",
                   "SEO",
                   "référencement",
                   "designer", "designers",
                   "photo", "photos",
                   "vidéo", "vidéos",
                   "traducteur", "traducteurs",
                   "enseignant", "enseignants",
                   "formateur", "formateurs",
                   "soutien scolaire",
                   "lingerie",
                   "esthétique",
                   "massage", "massages",
                   "fitness",
                   "musculation",
                   "club sport", "clubs sport",
                   "boucherie", "boucheries",
                   "charcuterie", "charcuteries",
                   "supermarché", "supermarchés",
                   "alimentaire", "alimentaires",
                   "textile", "textiles",
                   "matériel médical", "matériels médicaux",
                   "opticien", "opticiens",
                   "téléphonie",
                   "accessoires", "accessoire",
                   "béton",
                   "construction", "constructions",
                   "terrassement", "terrassements",
                   "électricien", "électriciens",
                   "mariage", "mariages",
                   "traiteur", "traiteurs",
                   "location salle", "locations salle",
                   "cours particulier", "cours particuliers",
                   "nourrice", "nourrices",
                   "jardinage", "jardinages",
                   "plantes", "plante",
                   "piscine", "piscines",
                   "vétérinaire", "vétérinaires",
                   "animaux", "animal",
                   "garage auto", "garages auto",
                   "peinture auto", "peintures auto",
                   "réparation", "réparations",
                   "voitures", "voiture",
                   "camion", "camions",
                   "transport", "transports",
                   "livraison", "livraisons",
                   "commerce", "commerces",
                   "grossiste", "grossistes",
                   "import export",
                   "freelance", "freelances",
                   "formation", "formations",
                   "cours", "cour",
                   "université", "universités",
                   "ecole", "ecoles",
                   "institut", "instituts",
                   "centre", "centres",
                   "artisan", "artisans",
                   "ouvrier", "ouvriers",
                   "propriétaire", "propriétaires",
                   "fournisseur", "fournisseurs",
                   "clim", "clims",
                   "radiateur", "radiateurs",
                   "chauffe-eau", "chauffe-eaux",
                   "technicien", "techniciens",
                   "plombier", "plombiers",
                   "menuisier", "menuisiers",
                   "carreleur", "carreleurs",
                   "agent immobilier", "agents immobiliers",
                   "réseau", "réseaux",
                   "câblage",
                   "antivirus", "antiviru",
                   "boutique", "boutiques",
                   "tissus", "tissu",
                   "rideaux", "rideau",
                   "linge maison", "linges maison"]:  # tu peux ajouter plus de mots clés
            self.scrape_pagesjaunes(kw)
        # TunisieIndex
        try:
            categories = self.get_all_category_links()
        except Exception as e:
            print(f"[Erreur] Impossible de récupérer les catégories : {e}")
            categories = []

        for cat_url in categories:
            category_name = self.extract_category_from_url(cat_url)
            try:
                sub_urls = self.get_all_subcategory_links(cat_url)
            except Exception:
                sub_urls = [cat_url]

            for sub_url in sub_urls:
                page_url = sub_url
                noms_vus = set()
                while page_url:
                    try:
                        page_url = self.process_tunisieindex(page_url, noms_vus, category_name)
                    except Exception as e:
                        print(f"[Erreur] Problème avec {page_url} : {e}")
                        break
                    time.sleep(1)

    @api.model
    def action_global_cleanup_all_contacts(self):
        """Nettoyage complet + anti-doublons + enrichissement + log propre"""
        Contact = self.env['scraper.contact']
        Cleanup = self.env['scraping.cleanup']

        start_time = time.time()

        # On travaille sur les IDs pour éviter MissingError après unlink()
        all_ids = Contact.search([]).ids
        total_processed = len(all_ids)

        corrected_count = 0
        enriched_count = 0
        deleted_invalid_count = 0
        deleted_duplicates_count = 0
        seen_emails = {}

        for contact_id in all_ids:
            rec = Contact.browse(contact_id)
            if not rec.exists():
                continue  # déjà supprimé entre-temps

            original_email = rec.email or ""
            email = original_email.strip().lower()

            # 1. Enrichissement si pas d'email mais site web présent
            if not email and rec.website:
                candidate = rec._enrich_email_from_website(rec)  # ← ta méthode que je t'ai donnée
                if candidate:
                    rec.write({'email': candidate})
                    email = candidate.strip().lower()
                    enriched_count += 1

            # 2. Correction du domaine (gamil.com → gmail.com, etc.)
            if email and "@" in email:
                local_part, domain = email.split("@", 1)
                if domain in COMMON_DOMAIN_FIXES:
                    email = f"{local_part}@{COMMON_DOMAIN_FIXES[domain]}"
                    rec.write({'email': email})  # garde la casse propre
                    corrected_count += 1

            # 3. Validation email (regex + pas fake)
            if not email or not EMAIL_REGEX.match(email) or email in FAKE_EMAILS:
                rec.unlink()
                deleted_invalid_count += 1
                continue

            # 4. Détection doublon (on garde le premier vu)
            if email in seen_emails:
                rec.unlink()
                deleted_duplicates_count += 1
            else:
                seen_emails[email] = True

        # Calcul du temps
        duration_sec = round(time.time() - start_time, 3)

        # Création du log dans scraping.cleanup (tout est bien rempli !)
        Cleanup.create({
            'name': f'Nettoyage automatique {len(Cleanup.search([])) + 1}',
            'status': 'done',
            'date_run': fields.Datetime.now(),
            'total_processed': total_processed,
            'corrected_count': corrected_count,
            'enriched_count': enriched_count,
            'deleted_duplicates_count': deleted_duplicates_count,
            'deleted_invalid_count': deleted_invalid_count,
            'duration_sec': duration_sec,
            'notes': 'Nettoyage automatique lancé via Action automatisé',
        })

        print(f"Nettoyage terminé : {total_processed} traités | "
              f"{corrected_count} corrigés | {enriched_count} enrichis | "
              f"{deleted_duplicates_count} doublons supprimés | {deleted_invalid_count} invalides supprimés "
              f"en {duration_sec}s")
        return True
