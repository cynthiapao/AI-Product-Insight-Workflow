import unittest

from ai_product_insight.config import SourceConfig
from ai_product_insight.discovery import deduplicate
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


if __name__ == "__main__":
    unittest.main()

