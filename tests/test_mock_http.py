from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase


class TestScraperMockHttp(TransactionCase):

    @patch('requests.get')
    @patch('PIL.Image.open')
    @patch('pytesseract.image_to_string')
    def test_extract_email_from_img(self, mock_tesseract, mock_image_open, mock_get):
        # Mock response
        mock_get.return_value.content = b"fakeimagebytes"
        mock_image = MagicMock()
        mock_image_open.return_value = mock_image
        mock_tesseract.return_value = "  contact@entreprise.tn  "

        img_tag = {"src": "https://site.com/protected-email.png"}
        ScraperKey = self.env['scraper.key']

        result = ScraperKey.extract_email_from_img(img_tag, "https://site.com")

        self.assertEqual(result, "contact@entreprise.tn")