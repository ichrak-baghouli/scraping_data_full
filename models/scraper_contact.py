from odoo.exceptions import UserError

from odoo import models, fields, api


class ScraperContact(models.Model):
    _name = "scraper.contact"
    _description = "Contacts scrappés"

    name = fields.Char("Nom")
    email = fields.Char("Email")
    phone = fields.Char("Téléphone")
    address = fields.Char("Adresse")
    keyword = fields.Char("Keyword")
    date_scraping = fields.Date("Date scraping")
    source = fields.Char("Source")
    website = fields.Char("Site web")

    mailing_list_id = fields.Many2one(
        "mailing.list",
        string="Liste de diffusion cible",
        help="Les contacts scrapés seront envoyés dans cette liste."
    )

    run_datetime = fields.Datetime("Date d'exécution", default=fields.Datetime.now)
    total_processed = fields.Integer("Enregistrements traités")
    corrected_count = fields.Integer("Emails corrigés")
    enriched_count = fields.Integer("Emails enrichis")
    deleted_duplicates_count = fields.Integer("Doublons supprimés")
    deleted_invalid_count = fields.Integer("Invalides/fake supprimés")
    duration_sec = fields.Float("Durée (sec)")
    notes = fields.Text("Notes")

    def action_send_to_mailing_list(self):
        """Ajouter les contacts sélectionnés à une liste Email Marketing"""
        mailing_list = self.env["mailing.list"].search([], limit=1)  # ⚡ tu peux remplacer par un choix de liste
        if not mailing_list:
            raise UserError("Aucune liste de diffusion trouvée. Créez-en une dans Email Marketing.")

        for contact in self:
            if contact.email:
                self.env["mailing.contact"].create({
                    "name": contact.name or "Sans nom",
                    "email": contact.email,
                    "list_ids": [(4, mailing_list.id)],  # ajout à la liste
                })
        return {'type': 'ir.actions.act_window_close'}
