import unittest
from datetime import datetime, timezone
from urllib.request import Request
from unittest.mock import patch

from ai_product_insight.config import SourceConfig
from ai_product_insight.sources import (
    FetchError, SafeRedirectHandler, fetch_hackernews_search, is_safe_public_url, _validate_fetch_target,
)


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

    def test_recent_show_hn_source_keeps_direct_link_and_story_identity(self):
        requested_urls = []

        class Fetcher:
            def fetch_json(self, url):
                requested_urls.append(url)
                return {"hits": [
                    {"objectID": "123", "title": "Show HN: Demo AI – Research with citations",
                     "url": "https://demo.ai/", "story_text": "A research app with source review.",
                     "created_at_i": 1789500000, "num_comments": 8, "points": 15},
                    {"objectID": "124", "title": "Show HN: Missing website", "url": None,
                     "num_comments": 20},
                ]}

        source = SourceConfig(name="Hacker News Show", kind="hackernews_search",
                              url="https://hn.algolia.com/api/v1/search_by_date", limit=10)
        candidates = fetch_hackernews_search(source, Fetcher())
        self.assertEqual(len(requested_urls), 3)
        self.assertTrue(all(url.startswith("https://hn.algolia.com/api/v1/search_by_date?") for url in requested_urls))
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].name, "Demo AI")
        self.assertEqual(candidates[0].hn_story_id, 123)
        self.assertEqual(str(candidates[0].url), "https://demo.ai/")
        self.assertEqual(candidates[0].published_at, datetime.fromtimestamp(1789500000, timezone.utc))


if __name__ == "__main__":
    unittest.main()
