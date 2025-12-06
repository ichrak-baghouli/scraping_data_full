from odoo import models, fields, api
import time

class ScrapingCleanup(models.Model):
    _name = "scraping.cleanup"
    _description = "Nettoyage & enrichissement des emails"

    name = fields.Char("Nom de la tâche", default="Nettoyage Emails")
    status = fields.Selection([
        ('pending', 'En attente'),
        ('running', 'En cours'),
        ('done', 'Terminé')
    ], default='pending', string="Statut")
    date_run = fields.Datetime("Date d'exécution")
    total_processed = fields.Integer("Enregistrements traités")
    corrected_count = fields.Integer("Emails corrigés")
    enriched_count = fields.Integer("Emails enrichis")
    deleted_duplicates_count = fields.Integer("Doublons supprimés")
    deleted_invalid_count = fields.Integer("Invalides/fake supprimés")
    duration_sec = fields.Float("Durée (sec)")
    notes = fields.Text("Notes")

    @api.model
    def _run_email_cleanup(self):
        self.ensure_one()
        self.status = 'running'
        start = time.time()

        Contact = self.env["scraper.contact"]
        records = Contact.search([])
        total = len(records)
        corrected = enriched = deleted_invalid = 0

        for rec in records:
            if not rec.email and rec.website:
                candidate = Contact._enrich_email_from_website(rec)
                if candidate:
                    rec.email = candidate
                    enriched += 1

            if rec.email:
                cleaned, was_corrected = Contact._clean_one_email(rec.email)
                if cleaned != rec.email:
                    rec.email = cleaned
                    if was_corrected:
                        corrected += 1
                if Contact._looks_fake(rec.email):
                    rec.unlink()
                    deleted_invalid += 1

        deleted_dupes = Contact._delete_duplicates_by_email()
        duration = time.time() - start

        self.write({
            "status": 'done',
            "date_run": fields.Datetime.now(),
            "total_processed": total,
            "corrected_count": corrected,
            "enriched_count": enriched,
            "deleted_duplicates_count": deleted_dupes,
            "deleted_invalid_count": deleted_invalid,
            "duration_sec": round(duration, 3),
            "notes": "Nettoyage emails effectué"
        })

    def action_clean_emails_now(self):
        self._run_email_cleanup()
        return True

    @api.model
    def cron_clean_emails(self):
        task = self.create({})
        task._run_email_cleanup()
        return True
