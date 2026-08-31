import unittest
from urllib.request import Request
from unittest.mock import patch

from ai_product_insight.sources import FetchError, SafeRedirectHandler, is_safe_public_url, _validate_fetch_target


class SourceSafetyTests(unittest.TestCase):
    def test_rejects_private_redirect(self):
        handler = SafeRedirectHandler()
        with self.assertRaises(FetchError):
            handler.redirect_request(Request("https://www.producthunt.com/r/p/1"), None, 302, "Found", {},
                                     "http://169.254.169.254/latest/meta-data")

    def test_rejects_userinfo_and_malformed_hosts(self):
        for url in ("https://user:password@site.example/", "https://[broken/", "https://example.com:bad/", "http://127.1/"):
            with self.subTest(url=url):
                self.assertFalse(is_safe_public_url(url))

    def test_rejects_public_hostname_resolving_to_private_address(self):
        with patch("ai_product_insight.sources.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
            with self.assertRaises(FetchError):
                _validate_fetch_target("https://looks-public.example/")

    def test_allows_public_redirect(self):
        with patch("ai_product_insight.sources.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
            request = SafeRedirectHandler().redirect_request(Request("https://www.producthunt.com/r/p/1"),
                None, 302, "Found", {}, "https://product.example/")
            self.assertEqual(request.full_url, "https://product.example/")


if __name__ == "__main__":
    unittest.main()
