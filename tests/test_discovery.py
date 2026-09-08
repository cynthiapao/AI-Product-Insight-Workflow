import unittest

from ai_product_insight.config import SourceConfig, WorkflowConfig
from ai_product_insight.discovery import DiscoveryAgent, deduplicate
from ai_product_insight.models import ProductCandidate
from ai_product_insight.sources import parse_feed


class DiscoveryTests(unittest.TestCase):
    def test_parse_atom_feed(self):
        source = SourceConfig(name="Demo", kind="rss", url="https://example.com/feed", limit=5)
        xml = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>New AI Tool</title><link href="https://example.com/tool"/><summary>A useful product description for testing.</summary></entry></feed>"""
        items = parse_feed(xml, source)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "New AI Tool")

    def test_deduplicate_uses_canonical_url(self):
        items = [
            ProductCandidate(name="One", url="https://example.com/a?utm_source=x", source="a"),
            ProductCandidate(name="One duplicate", url="https://example.com/a", source="b"),
        ]
        self.assertEqual(len(deduplicate(items)), 1)

    def test_manual_discovery_returns_only_the_requested_product(self):
        class FailIfFetched:
            def fetch_text(self, url):
                raise AssertionError(f"Manual discovery must not fetch {url}")

        config = WorkflowConfig(
            sources=[SourceConfig(name="Demo", kind="rss", url="https://example.com/feed")]
        )
        manual = ProductCandidate(
            name="Chosen AI",
            url="https://example.com/chosen",
            source="manual",
            manual=True,
        )

        candidates, errors = DiscoveryAgent(config, FailIfFetched()).discover(manual=manual)

        self.assertEqual(candidates, [manual])
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()

