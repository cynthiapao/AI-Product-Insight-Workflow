import json
import tempfile
import unittest
from pathlib import Path

from ai_product_insight.agents import AgentCrew, EditorAgent, InsightAgent, ResearchAgent, ScoutAgent
from ai_product_insight.config import WorkflowConfig
from ai_product_insight.discovery import DiscoveryAgent
from ai_product_insight.llm import OfflineDemoLLM
from ai_product_insight.models import ComparisonBrief, EvidenceItem, ProductCandidate
from ai_product_insight.pipeline import InsightPipeline
from ai_product_insight.sources import HttpFetcher


NOTES = "我在同一个个人网站项目中使用了多个 AI 工具。初版设计、代码执行、项目文案和中文润色分别由不同工具参与，这些观察只代表本次真实项目。" * 2


class CapturingLLM:
    def __init__(self):
        self.delegate = OfflineDemoLLM()
        self.calls: list[tuple[str, str]] = []

    def generate_json(self, system: str, user: str):
        self.calls.append((system, user))
        return self.delegate.generate_json(system, user)


class ClarificationTests(unittest.TestCase):
    def test_pipeline_asks_once_saves_answers_and_passes_them_to_writing(self):
        products = [
            ProductCandidate(name="Gemini", url="https://example.com/gemini", source="manual-comparison", manual=True),
            ProductCandidate(name="Claude", url="https://example.com/claude", source="manual-comparison", manual=True),
        ]
        brief = ComparisonBrief(title="在同一个网站项目中比较不同 AI 工具", products=products, notes=NOTES)
        evidence = {
            item.candidate_id: [
                EvidenceItem(
                    title=f"{item.name} page",
                    url=item.url,
                    excerpt=f"The public page for {item.name} describes the product and its supported workflows.",
                    source_type="official",
                )
            ]
            for item in products
        }
        config = WorkflowConfig(sources=[], min_evidence_items=2)
        fetcher = HttpFetcher(timeout=1, retries=0)
        llm = CapturingLLM()
        crew = AgentCrew(
            scout=ScoutAgent(llm, config),
            researcher=ResearchAgent(llm, fetcher, config),
            analyst=InsightAgent(llm),
            editor=EditorAgent(llm),
        )
        callback_calls: list[list[str]] = []

        def answer_once(questions: list[str]) -> list[str]:
            callback_calls.append(questions)
            return ["Gemini 能从非网页参考图理解视觉方向。", "当修改目标明确时，Codex 执行基本一次通过。"]

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pipeline = InsightPipeline(DiscoveryAgent(config, fetcher), crew, root / "drafts", root / "runs")
            report = pipeline.run_comparison(
                brief,
                fixture_evidence=evidence,
                clarification_callback=answer_once,
            )

            checkpoint = next((root / "runs").glob("*/03-clarification.json"))
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))

        self.assertEqual(report.status, "completed")
        self.assertEqual(len(callback_calls), 1)
        self.assertLessEqual(len(callback_calls[0]), 3)
        self.assertEqual(len(saved["items"]), 2)
        analyst_user = next(user for system, user in llm.calls if "[COMPARE_ANALYST]" in system)
        editor_user = next(user for system, user in llm.calls if "[COMPARE_EDITOR]" in system)
        self.assertIn("非网页参考图", analyst_user)
        self.assertIn("Codex 执行基本一次通过", editor_user)


if __name__ == "__main__":
    unittest.main()
