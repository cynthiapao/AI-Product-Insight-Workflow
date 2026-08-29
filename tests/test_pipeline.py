import json
import tempfile
import unittest
from pathlib import Path

from ai_product_insight.agents import AgentCrew, EditorAgent, InsightAgent, ResearchAgent, ScoutAgent
from ai_product_insight.config import WorkflowConfig
from ai_product_insight.discovery import DiscoveryAgent
from ai_product_insight.llm import OfflineDemoLLM
from ai_product_insight.models import EvidenceItem, ProductCandidate
from ai_product_insight.pipeline import InsightPipeline
from ai_product_insight.sources import HttpFetcher


class PipelineTests(unittest.TestCase):
    def test_offline_pipeline_writes_review_draft(self):
        config = WorkflowConfig(sources=[], min_score=3.0, min_evidence_items=1)
        fetcher = HttpFetcher(timeout=1, retries=0)
        llm = OfflineDemoLLM()
        crew = AgentCrew(
            scout=ScoutAgent(llm, config),
            researcher=ResearchAgent(llm, fetcher, config),
            analyst=InsightAgent(llm),
            editor=EditorAgent(llm),
        )
        candidate = ProductCandidate(name="Demo AI", url="https://example.com/demo", source="fixture")
        evidence = EvidenceItem(
            title="Demo page",
            url="https://example.com/demo",
            excerpt="This product exposes task stages and lets a user intervene before final generation.",
            source_type="official",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pipeline = InsightPipeline(DiscoveryAgent(config, fetcher), crew, root / "drafts", root / "runs")
            report = pipeline.run(
                mode="offline-demo",
                fixture_candidates=[candidate],
                fixture_evidence={candidate.candidate_id: [evidence]},
            )
            self.assertEqual(report.status, "completed")
            json_files = list((root / "drafts").glob("*.json"))
            self.assertEqual(len(json_files), 1)
            article = json.loads(json_files[0].read_text(encoding="utf-8"))
            self.assertEqual(article["review_status"], "draft")
            self.assertEqual(article["read_minutes"], 5)

    def test_scheduled_pipeline_tries_fallback_after_insufficient_evidence(self):
        config = WorkflowConfig(sources=[], select_count=3, min_score=3.0, min_evidence_items=2)
        fetcher = HttpFetcher(timeout=1, retries=0)
        llm = OfflineDemoLLM()
        crew = AgentCrew(
            scout=ScoutAgent(llm, config),
            researcher=ResearchAgent(llm, fetcher, config),
            analyst=InsightAgent(llm),
            editor=EditorAgent(llm),
        )
        first = ProductCandidate(name="First AI", url="https://example.com/first", source="fixture")
        second = ProductCandidate(name="Second AI", url="https://example.com/second", source="fixture")
        first_evidence = EvidenceItem(
            title="First feed note",
            url="https://example.com/first",
            excerpt="Only one short evidence item is available for this candidate product.",
            source_type="feed",
        )
        second_evidence = [
            EvidenceItem(
                title="Second official page",
                url="https://example.com/second",
                excerpt="The official page explains the product workflow and its user controls.",
                source_type="official",
            ),
            EvidenceItem(
                title="Second community discussion",
                url="https://news.ycombinator.com/item?id=2",
                excerpt="Users discuss the staged workflow, review checkpoints, and remaining limitations.",
                source_type="community",
            ),
        ]

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pipeline = InsightPipeline(DiscoveryAgent(config, fetcher), crew, root / "drafts", root / "runs")
            report = pipeline.run(
                mode="scheduled",
                fixture_candidates=[first, second],
                fixture_evidence={
                    first.candidate_id: [first_evidence],
                    second.candidate_id: second_evidence,
                },
            )

            self.assertEqual(report.status, "partial")
            self.assertTrue(report.outputs)
            self.assertTrue(any(error.startswith("Insufficient evidence for First AI") for error in report.errors))
            articles = list((root / "drafts").glob("*.json"))
            self.assertEqual(len(articles), 1)
            article = json.loads(articles[0].read_text(encoding="utf-8"))
            self.assertIn("Second AI", article["title"])

    def test_scheduled_pipeline_researches_beyond_three_until_evidence_mix_is_usable(self):
        config = WorkflowConfig(
            sources=[],
            select_count=3,
            research_candidate_limit=5,
            min_score=3.0,
            min_evidence_items=2,
        )
        fetcher = HttpFetcher(timeout=1, retries=0)
        llm = OfflineDemoLLM()
        crew = AgentCrew(
            scout=ScoutAgent(llm, config),
            researcher=ResearchAgent(llm, fetcher, config),
            analyst=InsightAgent(llm),
            editor=EditorAgent(llm),
        )
        candidates = [
            ProductCandidate(name=f"Candidate {index}", url=f"https://example.com/{index}", source="fixture")
            for index in range(1, 6)
        ]
        fixture_evidence = {}
        for candidate in candidates[:4]:
            fixture_evidence[candidate.candidate_id] = [
                EvidenceItem(
                    title=f"{candidate.name} official page",
                    url=candidate.url,
                    excerpt="The official page contains a detailed but promotional description of the product.",
                    source_type="official",
                ),
                EvidenceItem(
                    title=f"{candidate.name} release note",
                    url=f"https://example.com/{candidate.candidate_id}/release",
                    excerpt="The release note lists product features without an independent point of view.",
                    source_type="release",
                ),
            ]
        final_candidate = candidates[-1]
        fixture_evidence[final_candidate.candidate_id] = [
            EvidenceItem(
                title="Candidate 5 official page",
                url=final_candidate.url,
                excerpt="The official page explains the product workflow and review controls.",
                source_type="official",
            ),
            EvidenceItem(
                title="Candidate 5 independent discussion",
                url="https://news.ycombinator.com/item?id=5",
                excerpt="Independent users discuss the workflow benefits and the controls that remain unclear.",
                source_type="community",
            ),
        ]

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pipeline = InsightPipeline(DiscoveryAgent(config, fetcher), crew, root / "drafts", root / "runs")
            report = pipeline.run(
                mode="scheduled",
                fixture_candidates=candidates,
                fixture_evidence=fixture_evidence,
            )

            self.assertEqual(report.selected_count, 5)
            self.assertTrue(report.outputs)
            self.assertEqual(sum("missing independent" in error for error in report.errors), 4)
            article = json.loads(next((root / "drafts").glob("*.json")).read_text(encoding="utf-8"))
            self.assertIn("Candidate 5", article["title"])


if __name__ == "__main__":
    unittest.main()
