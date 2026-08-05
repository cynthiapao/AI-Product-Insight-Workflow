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


if __name__ == "__main__":
    unittest.main()

