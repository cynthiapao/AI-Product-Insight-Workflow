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
                title="Second release note",
                url="https://example.com/second/releases",
                excerpt="The release note documents the staged workflow and review checkpoints.",
                source_type="release",
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
            self.assertIn("Insufficient evidence for First AI", report.errors)
            articles = list((root / "drafts").glob("*.json"))
            self.assertEqual(len(articles), 1)
            article = json.loads(articles[0].read_text(encoding="utf-8"))
            self.assertIn("Second AI", article["title"])


if __name__ == "__main__":
    unittest.main()
