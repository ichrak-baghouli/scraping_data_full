from odoo.tests import common
from unittest.mock import patch

class TestScrapeByKeyword(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.scraper = self.env["scraper.key"].create({"keyword_input": 'voiture'})

    @patch("requests.get")
    def test_scrape_by_keyword(self, mock_get):
        # faux HTML retourné par mock
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = """
            <html>
             <body>
               <div class='company'>Company A</div>
               <div class='email'>contact@companyA.com</div>
             </body>
            </html>
        """

        results = self.scraper.scrape_by_keyword()

        self.assertTrue(len(results) > 0)
        self.assertIn("Company A", results[0]["name"])
        self.assertIn("@", results[0]["email"])
