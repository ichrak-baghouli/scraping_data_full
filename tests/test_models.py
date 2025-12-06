from odoo.tests.common import TransactionCase


class TestScraperContactModel(TransactionCase):

    def test_create_contact(self):
        rec = self.env['scraper.contact'].create({
            "name": "SARL Meuble Plus",
            "email": "contact@meubleplus.tn",
            "phone": "71234567",
            "keyword": "meubles",
            "source": "tunisieindex",
            "website": "https://meubleplus.tn",
        })
        self.assertTrue(rec.id)
        self.assertEqual(rec.name, "SARL Meuble Plus")
        self.assertEqual(rec.email, "contact@meubleplus.tn")
        self.assertEqual(rec.phone, "71234567")