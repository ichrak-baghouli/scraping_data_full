from odoo import models, fields, api
from odoo.exceptions import UserError

class ScraperSendToMailingWizard(models.TransientModel):
    _name = "scraper.send.to.mailing.wizard"
    _description = "Assistant envoi vers liste Email Marketing"

    mailing_list_id = fields.Many2one(
        "mailing.list",
        string="Liste de diffusion",
        required=True,
        help="Choisissez une liste de diffusion où ajouter les contacts."
    )

    def action_send(self):
        active_ids = self.env.context.get("active_ids")
        contacts = self.env["scraper.contact"].browse(active_ids)

        if not contacts:
            raise UserError("Aucun contact sélectionné.")

        for contact in contacts:
            if contact.email:
                self.env["mailing.contact"].create({
                    "name": contact.name or "Sans nom",
                    "email": contact.email,
                    "list_ids": [(4, self.mailing_list_id.id)],
                })
        return {'type': 'ir.actions.act_window_close'}
