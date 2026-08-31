import unittest

from ai_product_insight.models import ProductCandidate
from ai_product_insight.research import collect_research_evidence, has_required_evidence_mix, _same_product_site
from ai_product_insight.research import _hit_matches_candidate
from ai_product_insight.sources import FetchError, FetchedPage, classify_source_type


class IdentityFetcher:
    def __init__(self, name="oMLX", summary="Mac LLM server that cuts coding agent wait times"):
        self.name = name
        self.summary = summary
        self.official = "https://github.com/maker/omlx"
        self.launch = "https://www.producthunt.com/products/omlx"
        self.outbound = "https://www.producthunt.com/r/p/123?app_id=339"
        self.pages = {
            self.official: FetchedPage(self.official, f"<title>{name}</title><p>{name}: {summary}. Built for local inference with a persistent cache and explicit user controls.</p>"),
        }
        self.hits = [{"objectID": "123", "title": f"Show HN: {name} – {summary}",
                      "url": self.official, "author": "maker", "points": 10, "num_comments": 1}]
        self.details = {"123": {"author": "maker", "children": [
            {"author": "reader", "text": "I tested this coding agent server on my Mac. The cache reduced repeated context loading, but memory limits still matter."}
        ]}}
        self.calls = []
        self.news = "<rss><channel></channel></rss>"

    def candidate(self):
        return ProductCandidate(name=self.name, url=self.launch, source="Product Hunt",
                                summary=f'<p>{self.summary}</p><a href="{self.outbound}">Link</a>')

    def fetch_page(self, url):
        self.calls.append(url)
        if url.startswith("https://news.google.com/rss/search"):
            return FetchedPage(url, self.news)
        if url not in self.pages:
            raise FetchError(f"HTTP Error 403: Forbidden: {url}")
        return self.pages[url]

    def fetch_text(self, url):
        return self.fetch_page(url).text

    def fetch_json(self, url):
        self.calls.append(url)
        if url.startswith("https://api.github.com/repos/"):
            raise FetchError("README not available in this fixture; use public page")
        if url.startswith("https://hn.algolia.com/api/v1/search?"):
            return {"hits": self.hits}
        if "/items/" in url:
            return self.details.get(url.rsplit("/", 1)[-1], {})
        raise AssertionError(url)


class ResearchIdentityTests(unittest.TestCase):
    def test_producthunt_is_not_official(self):
        self.assertEqual(classify_source_type("https://www.producthunt.com/products/omlx"), "feed")

    def test_blocked_listing_resolves_outbound_link(self):
        fetcher = IdentityFetcher()
        fetcher.pages[fetcher.outbound] = fetcher.pages[fetcher.official]
        result = collect_research_evidence(fetcher.candidate(), fetcher)
        self.assertTrue(has_required_evidence_mix(result.items))
        self.assertIn(fetcher.outbound, fetcher.calls)
        self.assertIn(fetcher.official, [str(e.url) for e in result.items if e.source_type == "official"])
        self.assertEqual(str(fetcher.candidate().url), fetcher.launch)

    def test_blocked_outbound_resolves_corroborated_hn_destination(self):
        fetcher = IdentityFetcher()
        result = collect_research_evidence(fetcher.candidate(), fetcher)
        self.assertTrue(has_required_evidence_mix(result.items))
        self.assertIn(fetcher.official, fetcher.calls)

    def test_maritime_does_not_match_starlink_maritime(self):
        fetcher = IdentityFetcher("Maritime", "Dedicated computers for AI agents starting at one dollar per month")
        fetcher.hits = [{"objectID": "1", "title": "Starlink Maritime", "url": "https://starlink.com/maritime", "num_comments": 508}]
        result = collect_research_evidence(fetcher.candidate(), fetcher)
        self.assertFalse(has_required_evidence_mix(result.items))
        self.assertNotIn("https://starlink.com/maritime", fetcher.calls)
        self.assertFalse(any(e.source_type == "community" for e in result.items))
        self.assertTrue(any("identity" in error for error in result.errors))

    def test_same_name_needs_purpose_corroboration(self):
        fetcher = IdentityFetcher("Superagent", "Desktop coding workspace with local files")
        fetcher.hits = [{"objectID": "2", "title": "Superagent: financial risk analytics", "url": "https://other.example/", "num_comments": 20}]
        result = collect_research_evidence(fetcher.candidate(), fetcher)
        self.assertFalse(has_required_evidence_mix(result.items))
        self.assertNotIn("https://other.example/", fetcher.calls)

    def test_outbound_landing_page_must_match_identity(self):
        fetcher = IdentityFetcher()
        fetcher.pages[fetcher.outbound] = FetchedPage("https://wrong.example/", "<title>Unrelated shop</title><p>Buy flowers and birthday gifts for your friends at our online shop.</p>")
        fetcher.hits = []
        result = collect_research_evidence(fetcher.candidate(), fetcher)
        self.assertFalse(has_required_evidence_mix(result.items))
        self.assertFalse(any(e.source_type == "official" for e in result.items))

    def test_zero_comments_and_author_pitch_are_not_independent(self):
        fetcher = IdentityFetcher()
        fetcher.hits[0]["story_text"] = "I built oMLX, a local Mac LLM coding agent server with a disk cache."
        fetcher.details["123"]["children"] = [{"author": "maker", "text": "I built this Mac LLM server for coding agents and would love some feedback."}]
        result = collect_research_evidence(fetcher.candidate(), fetcher)
        self.assertFalse(has_required_evidence_mix(result.items))
        self.assertFalse(any(e.source_type == "community" for e in result.items))

    def test_empty_first_discussion_does_not_hide_later_real_comments(self):
        fetcher = IdentityFetcher()
        fetcher.hits.insert(0, {**fetcher.hits[0], "objectID": "122", "num_comments": 0})
        result = collect_research_evidence(fetcher.candidate(), fetcher)
        self.assertTrue(has_required_evidence_mix(result.items))
        self.assertTrue(any("id=123" in str(e.url) for e in result.items))

    def test_news_headline_is_not_full_report_evidence(self):
        fetcher = IdentityFetcher()
        fetcher.details["123"]["children"] = []
        fetcher.news = '<rss><channel><item><title>oMLX Mac LLM coding server review</title><link>https://news.google.com/rss/articles/abc</link><description>oMLX review</description></item></channel></rss>'
        result = collect_research_evidence(fetcher.candidate(), fetcher)
        self.assertFalse(has_required_evidence_mix(result.items))
        self.assertFalse(any(e.source_type == "report" for e in result.items))

    def test_verified_site_rejects_namesake_even_with_same_keywords(self):
        fetcher = IdentityFetcher()
        hit = {"title": "oMLX local Mac LLM server", "url": "https://different.example/"}
        self.assertFalse(_hit_matches_candidate(fetcher.candidate(), hit, "https://omlx.ai/"))

    def test_news_requires_body_and_product_link(self):
        fetcher = IdentityFetcher()
        fetcher.details["123"]["children"] = []
        link = "https://news.google.com/rss/articles/abc"
        fetcher.news = f'<rss><channel><item><title>oMLX Mac LLM coding server review</title><link>{link}</link></item></channel></rss>'
        body = "oMLX is a Mac LLM coding agent server. This review compares cache reuse, memory limits and waiting time. " * 4
        fetcher.pages[link] = FetchedPage("https://publication.example/review", f'<title>oMLX review</title><p>{body}</p><a href="{fetcher.official}">Project</a>')
        result = collect_research_evidence(fetcher.candidate(), fetcher)
        self.assertTrue(has_required_evidence_mix(result.items))
        self.assertTrue(any(e.source_type == "report" for e in result.items))
        fetcher.pages[link] = FetchedPage("https://publication.example/review", f'<title>oMLX review</title><p>{body}</p>')
        result = collect_research_evidence(fetcher.candidate(), fetcher)
        self.assertFalse(has_required_evidence_mix(result.items))

    def test_research_retains_collection_diagnostics_when_model_runs(self):
        from ai_product_insight.agents import ResearchAgent
        from ai_product_insight.config import WorkflowConfig
        from ai_product_insight.llm import OfflineDemoLLM
        fetcher = IdentityFetcher()
        result = ResearchAgent(OfflineDemoLLM(), fetcher, WorkflowConfig(sources=[])).research(
            fetcher.candidate(), require_evidence_mix=True)
        self.assertEqual(result.quality, "usable")
        self.assertTrue(any("403" in diagnostic for diagnostic in result.collection_diagnostics))

    def test_different_github_repos_and_hosted_projects_are_not_same_site(self):
        self.assertFalse(_same_product_site("https://github.com/maker/omlx", "https://github.com/other/omlx"))
        self.assertFalse(_same_product_site("https://github.com/maker/omlx", "https://github.com/maker/other"))
        self.assertTrue(_same_product_site("https://github.com/maker/omlx", "https://github.com/maker/omlx/releases"))
        self.assertFalse(_same_product_site("https://maker.github.io/omlx", "https://maker.github.io/other"))
        self.assertFalse(_same_product_site("https://a.framer.website/", "https://b.framer.website/"))
        self.assertFalse(_same_product_site("https://a.github.io/", "https://github.io/"))


if __name__ == "__main__":
    unittest.main()
