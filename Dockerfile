FROM odoo:18.0

USER root

# Copie du module dans le dossier des addons externes
COPY . /mnt/extra-addons/scraping_data_full-master

# Chemin addons incluant le module
ENV ADDONS_PATH="/mnt/extra-addons/scraping_data_full-master,/usr/lib/python3/dist-packages/odoo/addons"

EXPOSE 8069

# Commande par défaut: Odoo avec le chemin addons étendu
CMD ["odoo", "--addons-path", "/mnt/extra-addons/scraping_data_full-master,/usr/lib/python3/dist-packages/odoo/addons"]

