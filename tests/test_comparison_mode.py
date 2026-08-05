import json
import tempfile
import unittest
from pathlib import Path

from ai_product_insight.agents import AgentCrew, EditorAgent, InsightAgent, ResearchAgent, ScoutAgent
from ai_product_insight.cli import build_comparison_brief, build_parser
from ai_product_insight.config import WorkflowConfig
from ai_product_insight.discovery import DiscoveryAgent
from ai_product_insight.llm import OfflineDemoLLM
from ai_product_insight.models import ComparisonBrief, EvidenceItem, ProductCandidate, ResearchPack
from ai_product_insight.pipeline import InsightPipeline
from ai_product_insight.sources import HttpFetcher, classify_source_type


NOTES = (
    "在这次个人网站制作中，我把不同模型放进了同一个真实项目。Gemini 主要帮助形成初始设计，"
    "Codex 和 ChatGPT 接管后续执行，Claude 负责项目文案的精细调整，DeepSeek 则更擅长中文润色。"
    "这些判断只来自这次建站经历，不代表对模型能力的普遍排名。"
)


def candidate(name: str, suffix: str) -> ProductCandidate:
    return ProductCandidate(name=name, url=f"https://example.com/{suffix}", source="manual-comparison", manual=True)


def evidence(name: str, suffix: str) -> EvidenceItem:
    return EvidenceItem(
        title=f"{name} official page",
        url=f"https://example.com/{suffix}",
        excerpt=f"The official product page for {name} describes its supported AI workflows and primary interaction model.",
        source_type="official",
    )


class CapturingLLM:
    def __init__(self) -> None:
        self.delegate = OfflineDemoLLM()
        self.calls: list[tuple[str, str]] = []

    def generate_json(self, system: str, user: str):
        self.calls.append((system, user))
        return self.delegate.generate_json(system, user)


class ThreePatternComparisonLLM(OfflineDemoLLM):
    def generate_json(self, system: str, user: str):
        result = super().generate_json(system, user)
        if "[COMPARE_ANALYST]" in system:
            result["patterns"].append(
                {
                    "name": "保留人工校准节点",
                    "principle": "在模型之间切换或进入精细调整阶段时，明确设置人工确认点，防止风格与目标在自动交接中逐步偏移。",
                    "applies_when": "适用于设计和表达具有明显个人偏好的多模型项目。",
                }
            )
        return result


class ComparisonModeTests(unittest.TestCase):
    def test_wikipedia_is_not_labeled_as_official_evidence(self):
        self.assertEqual(classify_source_type("https://en.wikipedia.org/wiki/ChatGPT"), "community")

    def setUp(self):
        self.products = [candidate("Gemini", "gemini"), candidate("Claude", "claude")]
        self.brief = ComparisonBrief(title="在同一个网站项目里比较不同 AI 模型", products=self.products, notes=NOTES)
        self.research = [
            ResearchPack(
                candidate=item,
                evidence=[evidence(item.name, "gemini" if item.name == "Gemini" else "claude")],
                verified_facts=[f"{item.name} has an official product page describing its capabilities."],
                open_questions=["How stable is the observed behavior across unrelated projects?"],
                quality="usable",
            )
            for item in self.products
        ]

    def test_cli_accepts_repeated_product_pairs_and_loads_notes_file(self):
        with tempfile.TemporaryDirectory() as temp:
            notes_path = Path(temp) / "notes.md"
            notes_path.write_text(NOTES, encoding="utf-8")
            args = build_parser().parse_args(
                [
                    "compare",
                    "--name",
                    "在同一个网站项目里比较不同 AI 模型",
                    "--product",
                    "Gemini",
                    "https://example.com/gemini",
                    "--product",
                    "Claude",
                    "https://example.com/claude",
                    "--notes-file",
                    str(notes_path),
                ]
            )

            brief = build_comparison_brief(args)

        self.assertEqual([item.name for item in brief.products], ["Gemini", "Claude"])
        self.assertEqual(brief.notes, NOTES)

    def test_agents_use_comparison_prompts_and_create_one_article(self):
        llm = CapturingLLM()

        insight = InsightAgent(llm).compare(self.brief, self.research)
        article = EditorAgent(llm).draft_comparison(self.brief, self.research, insight)

        self.assertIn("[COMPARE_ANALYST]", llm.calls[0][0])
        self.assertIn("[COMPARE_EDITOR]", llm.calls[1][0])
        self.assertIn("Gemini", llm.calls[0][1])
        self.assertIn("Claude", llm.calls[0][1])
        self.assertIn(NOTES, llm.calls[0][1])
        self.assertEqual(article.review_status, "draft")
        self.assertEqual(len(article.sources), 2)

    def test_comparison_insight_accepts_three_transferable_patterns(self):
        insight = InsightAgent(ThreePatternComparisonLLM()).compare(self.brief, self.research)

        self.assertEqual(len(insight.patterns), 3)

    def test_pipeline_researches_all_products_and_writes_one_draft(self):
        config = WorkflowConfig(sources=[], min_score=3.0, min_evidence_items=2)
        fetcher = HttpFetcher(timeout=1, retries=0)
        llm = OfflineDemoLLM()
        crew = AgentCrew(
            scout=ScoutAgent(llm, config),
            researcher=ResearchAgent(llm, fetcher, config),
            analyst=InsightAgent(llm),
            editor=EditorAgent(llm),
        )
        fixture_evidence = {
            item.candidate_id: [evidence(item.name, "gemini" if item.name == "Gemini" else "claude")]
            for item in self.products
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pipeline = InsightPipeline(DiscoveryAgent(config, fetcher), crew, root / "drafts", root / "runs")

            report = pipeline.run_comparison(self.brief, fixture_evidence=fixture_evidence)

            self.assertEqual(report.status, "completed")
            self.assertEqual(report.candidate_count, 2)
            self.assertEqual(report.selected_count, 2)
            json_files = list((root / "drafts").glob("*.json"))
            self.assertEqual(len(json_files), 1)
            article = json.loads(json_files[0].read_text(encoding="utf-8"))
            self.assertEqual(article["review_status"], "draft")
            self.assertEqual(len(article["sources"]), 2)

    def test_pipeline_keeps_personal_experience_for_product_with_insufficient_public_evidence(self):
        third = candidate("Model C", "model-c")
        brief = ComparisonBrief(
            title="在同一个真实项目里比较三种 AI 工具",
            products=[*self.products, third],
            notes=NOTES + " Model C 也参与了这次项目，但其公开页面暂时无法由抓取器读取。",
        )

        class StubResearcher:
            def research(self, item, seed_evidence=None, min_evidence_items=None):
                if item.name == "Model C":
                    return ResearchPack(candidate=item, evidence=[], quality="insufficient")
                suffix = "gemini" if item.name == "Gemini" else "claude"
                return ResearchPack(
                    candidate=item,
                    evidence=[evidence(item.name, suffix)],
                    verified_facts=[f"{item.name} has a readable official page."],
                    quality="usable",
                )

        config = WorkflowConfig(sources=[], min_evidence_items=2)
        fetcher = HttpFetcher(timeout=1, retries=0)
        llm = OfflineDemoLLM()
        crew = AgentCrew(
            scout=ScoutAgent(llm, config),
            researcher=StubResearcher(),
            analyst=InsightAgent(llm),
            editor=EditorAgent(llm),
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pipeline = InsightPipeline(DiscoveryAgent(config, fetcher), crew, root / "drafts", root / "runs")

            report = pipeline.run_comparison(brief)

            self.assertEqual(report.status, "partial")
            self.assertEqual(report.selected_count, 2)
            self.assertEqual(len(report.outputs), 3)
            article = json.loads(next((root / "drafts").glob("*.json")).read_text(encoding="utf-8"))
            self.assertIn("Model C", article["summary"])


if __name__ == "__main__":
    unittest.main()
