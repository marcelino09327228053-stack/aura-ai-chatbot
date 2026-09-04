import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.website_profile_importer import (
    _candidate_urls,
    _combine_profile_pages,
    _discover_important_links,
    _extract_profile_text,
    _profile_completeness,
    _validated_public_url,
)


class WebsiteProfileImporterTests(unittest.TestCase):
    def test_extracts_company_content_and_removes_noise_and_duplicates(self):
        html = """
        <html><head><title>Example Manufacturing</title><style>ignore me</style></head>
        <body><nav>Home About Contact</nav><h1>Example Manufacturing</h1>
        <p>We manufacture durable building products for businesses.</p>
        <p>We manufacture durable building products for businesses.</p>
        <h2>Contact Information</h2><p>Email: hello@example.com</p>
        <footer>Cookie settings Privacy policy</footer></body></html>
        """
        result = _extract_profile_text(html)
        self.assertIn("Example Manufacturing", result)
        self.assertIn("hello@example.com", result)
        self.assertNotIn("Cookie settings", result)
        self.assertEqual(result.count("We manufacture durable"), 1)

    def test_rejects_local_network_url(self):
        with self.assertRaises(ValueError):
            _validated_public_url("http://127.0.0.1/private")

    def test_builds_https_www_and_http_fallbacks(self):
        candidates = _candidate_urls("https://example.com/about?source=test")
        self.assertEqual(candidates[0], "https://example.com/about?source=test")
        self.assertIn("https://www.example.com/about?source=test", candidates)
        self.assertIn("http://example.com/about?source=test", candidates)

    def test_discovers_only_ranked_internal_company_pages(self):
        html = """
        <a href='/about-us'>About Us</a><a href='/products'>Products</a>
        <a href='/product-category/roofing'>Roofing products</a><a href='/contact-us'>Contact Us</a>
        <a href='/blog/news'>Latest news</a><a href='https://other.test/services'>Services</a>
        <a href='/catalog.pdf'>Product catalog</a>
        """
        links = _discover_important_links(html, "https://example.com/")
        self.assertEqual(links[:2], ["https://example.com/about-us", "https://example.com/products"])
        self.assertLess(
            links.index("https://example.com/contact-us"),
            links.index("https://example.com/product-category/roofing"),
        )
        self.assertNotIn("https://example.com/blog/news", links)

    def test_combines_pages_and_removes_cross_page_duplicates(self):
        pages = [
            ("https://example.com/", "<h1>Example Company</h1><p>We manufacture durable building products for companies worldwide.</p>"),
            ("https://example.com/about", "<h1>About Us</h1><p>We manufacture durable building products for companies worldwide.</p><p>Founded in 1990 in Davao City.</p>"),
        ]
        result = _combine_profile_pages(pages)
        self.assertIn("SOURCE PAGE: Home", result)
        self.assertIn("SOURCE PAGE: About", result)
        self.assertEqual(result.count("We manufacture durable"), 1)

    def test_extracts_public_contact_and_social_channels(self):
        html = """
        <h1>Example Company</h1><p>We provide durable construction services worldwide.</p>
        <a href="mailto:hello@example.com">Email</a><a href="tel:+6312345678">Call</a>
        <a href="https://facebook.com/example-company">Facebook</a>
        """
        result = _extract_profile_text(html, "https://example.com/")
        self.assertIn("mailto:hello@example.com", result)
        self.assertIn("tel:+6312345678", result)
        self.assertIn("facebook.com/example-company", result)

    def test_reports_found_and_missing_information_categories(self):
        status = _profile_completeness(
            "About Us. Our products and services. Contact us by email. "
            "Our mission and core values. Visit facebook.com/example."
        )
        self.assertTrue(status["company overview"])
        self.assertTrue(status["products or services"])
        self.assertTrue(status["mission, vision or values"])
        self.assertFalse(status["business hours"])


if __name__ == "__main__":
    unittest.main()
