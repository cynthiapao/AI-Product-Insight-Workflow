import unittest

from ai_product_insight.models import EvidenceItem, ProductCandidate
from ai_product_insight.sources import FetchedPage
from ai_product_insight.research import (
    collect_research_evidence,
    has_required_evidence_mix,
    is_safe_public_url,
    missing_evidence_requirements,
)


class FakeFetcher:
    def __init__(self) -> None:
        self.texts = {
            "https://demo.ai/": """
                <html><head><title>Demo AI</title></head><body>
                <p>Demo AI turns a research question into a traceable product workflow.</p>
                <a href="/docs/how-it-works">How it works</a>
                <a href="/changelog">Changelog</a>
                <a href="https://evil.example/claim">External claim</a>
                </body></html>
            """,
            "https://demo.ai/docs/how-it-works": """
                <html><head><title>How Demo AI works</title></head><body>
                <p>The documentation describes review checkpoints and the evidence panel.</p>
                </body></html>
            """,
            "https://demo.ai/changelog": """
                <html><head><title>Demo AI changelog</title></head><body>
                <p>The August release added source comparison and export controls.</p>
                </body></html>
            """,
        }

    def fetch_text(self, url: str) -> str:
        if url.startswith("https://news.google.com/rss/search"):
            return "<rss><channel></channel></rss>"
        if url not in self.texts:
            raise AssertionError(f"Unexpected URL: {url}")
        return self.texts[url]

    def fetch_page(self, url: str) -> FetchedPage:
        return FetchedPage(url, self.fetch_text(url))

    def fetch_json(self, url: str):
        if url.startswith("https://hn.algolia.com/api/v1/search?"):
            return {
                "hits": [
                    {
                        "objectID": "123",
                        "author": "maker",
                        "title": "Show HN: Demo AI for traceable research",
                        "url": "https://demo.ai/",
                        "story_text": "The maker explains how the product exposes its research steps.",
                        "points": 18,
                        "num_comments": 3,
                    }
                ]
            }
        if url == "https://hn.algolia.com/api/v1/items/123":
            return {
                "author": "maker",
                "children": [
                    {"author": "reader1", "text": "I tested the source panel and found the comparison useful for checking my sources."},
                    {"author": "reader2", "text": "The workflow still needs clearer controls for correcting a source."},
                ]
            }
        raise AssertionError(f"Unexpected JSON URL: {url}")


class ResearchEvidenceTests(unittest.TestCase):
    def test_collects_official_release_and_independent_evidence(self):
        candidate = ProductCandidate(
            name="Demo AI",
            url="https://demo.ai/",
            source="Product Hunt",
            summary="A launch note about a traceable AI research workflow.",
        )

        collection = collect_research_evidence(candidate, FakeFetcher(), max_items=5)

        self.assertFalse(collection.errors)
        self.assertTrue(has_required_evidence_mix(collection.items))
        self.assertIn("official", {item.source_type for item in collection.items})
        self.assertIn("release", {item.source_type for item in collection.items})
        self.assertIn("community", {item.source_type for item in collection.items})
        self.assertNotIn("evil.example", " ".join(str(item.url) for item in collection.items))

    def test_reports_missing_independent_evidence(self):
        items = [
            EvidenceItem(
                title="Product page",
                url="https://demo.ai/",
                excerpt="The official page describes the product workflow in sufficient detail.",
                source_type="official",
            ),
            EvidenceItem(
                title="Product docs",
                url="https://demo.ai/docs",
                excerpt="The official documentation describes the review and export controls.",
                source_type="release",
            ),
        ]

        self.assertFalse(has_required_evidence_mix(items))
        self.assertEqual(missing_evidence_requirements(items), ["missing independent community or report evidence"])

    def test_blocks_private_and_non_http_urls(self):
        self.assertFalse(is_safe_public_url("http://127.0.0.1/admin"))
        self.assertFalse(is_safe_public_url("http://169.254.169.254/latest/meta-data"))
        self.assertFalse(is_safe_public_url("file:///etc/passwd"))
        self.assertTrue(is_safe_public_url("https://demo.ai/docs"))


if __name__ == "__main__":
    unittest.main()


