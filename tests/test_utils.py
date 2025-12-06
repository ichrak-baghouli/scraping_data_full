from odoo.tests.common import TransactionCase


class TestScraperUtils(TransactionCase):

    def setUp(self):
        super().setUp()
        self.ScraperKey = self.env['scraper.key']

    def test_clean_email(self):
        self.assertEqual(self.ScraperKey.clean_email("  abc.gmail@GMAIL.COM  "), "abc.gmail@gmail.com")
        self.assertEqual(self.ScraperKey.clean_email("invalid@@email"), "")
        self.assertEqual(self.ScraperKey.clean_email("contact+gamil.com"), "")

    def test_today_date(self):
        result = self.ScraperKey.today_date()
        self.assertRegex(result, r"^\d{4}-\d{2}-\d{2}$")

    def test_extract_category_from_url(self):
        url = "https://www.tunisieindex.com/annuaire-entreprises/plomberie-sanitaire?page=2"
        self.assertEqual(self.ScraperKey.extract_category_from_url(url), "plomberie-sanitaire")