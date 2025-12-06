from odoo.tests.common import TransactionCase


class TestSendToMailingList(TransactionCase):

    def setUp(self):
        super().setUp()
        self.mailing_list = self.env["mailing.list"].create({"name": "Test List"})

        self.contact1 = self.env["scraper.contact"].create({
            "name": "Ahmed",
            "email": "ahmed@test.com",
            "mailing_list_id": self.mailing_list.id
        })
        self.contact2 = self.env["scraper.contact"].create({
            "name": "Sans email",
            "phone": "22123456"
        })

    def test_action_send_to_mailing_list(self):
        self.contact1.action_send_to_mailing_list()

        mailing_contact = self.env["mailing.contact"].search([("email", "=", "ahmed@test.com")])
        self.assertTrue(mailing_contact)
        self.assertIn(self.mailing_list, mailing_contact.list_ids)

    def test_wizard_send_to_mailing_list(self):
        wizard = self.env["scraper.send.to.mailing.wizard"].create({
            "mailing_list_id": self.mailing_list.id
        })

        wizard.with_context(active_ids=self.contact1.ids).action_send()

        mailing_contact = self.env["mailing.contact"].search([("email", "=", "ahmed@test.com")])
        self.assertEqual(len(mailing_contact), 1)
