import unittest
from pathlib import Path

from ai_product_insight.agents import EditorAgent, InsightAgent
from ai_product_insight.editorial import EditorialContext
from ai_product_insight.llm import OfflineDemoLLM
from ai_product_insight.models import (
    ArticleContent,
    CandidateScore,
    EvidenceItem,
    EvidenceQuality,
    ProductCandidate,
    ResearchPack,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CapturingLLM:
    def __init__(self):
        self.delegate = OfflineDemoLLM()
        self.system_prompts: list[str] = []

    def generate_json(self, system: str, user: str):
        self.system_prompts.append(system)
        return self.delegate.generate_json(system, user)


def research_pack() -> ResearchPack:
    candidate = ProductCandidate(
        name="Demo AI",
        url="https://example.com/demo",
        source="fixture",
        score=CandidateScore(
            relevance=5,
            novelty=4,
            product_depth=4,
            evidence=4,
            total=4.4,
            reason="产品机制和公开信息足以支撑进一步研究与文章写作。",
        ),
    )
    evidence = EvidenceItem(
        title="Demo page",
        url="https://example.com/demo",
        excerpt="This product exposes task stages and lets a user intervene before final generation.",
        source_type="official",
    )
    return ResearchPack(
        candidate=candidate,
        evidence=[evidence],
        verified_facts=["The product exposes task stages."],
        open_questions=["Long-term reliability is unknown."],
        quality=EvidenceQuality.usable,
    )


class EditorialContextTests(unittest.TestCase):
    def test_loads_resources_and_gold_output_matches_schema(self):
        context = EditorialContext.load(PROJECT_ROOT)

        self.assertEqual(context.profile["version"], 1)
        self.assertEqual(context.gold_input["example_id"], "ai-website-design-alignment-v1")
        self.assertEqual(len(context.gold_examples), 2)
        self.assertEqual(context.social_gold["example_id"], "approved-social-style-v4-x-thread")
        self.assertIn("thread", context.social_gold["rules"]["x"][0])
        self.assertEqual(
            context.gold_examples[1].input["example_id"],
            "ai-model-workflow-role-division-v1",
        )
        for example in context.gold_examples:
            ArticleContent.model_validate(example.output)

        social_prompt = context.social_prompt_suffix()
        self.assertIn("2-4 个短段落", social_prompt)
        self.assertIn("300-500 个中文字符", social_prompt)
        self.assertIn("内容放不下时优先调整排版", social_prompt)

    def test_injects_role_specific_guidance_into_writing_agents(self):
        context = EditorialContext.load(PROJECT_ROOT)
        llm = CapturingLLM()
        research = research_pack()

        insight = InsightAgent(llm, context).analyze(research)
        EditorAgent(llm, context).draft(research, insight)

        analyst_prompt, editor_prompt = llm.system_prompts
        self.assertIn("一句话看懂", analyst_prompt)
        self.assertIn("ai-website-design-alignment-v1", analyst_prompt)
        self.assertIn("一句话看懂", editor_prompt)
        self.assertIn("AI 建站真正难的", editor_prompt)
        self.assertIn("四个 AI 如何协作", editor_prompt)
        self.assertIn("首页“产品洞察”模块", editor_prompt)
        self.assertIn("通常只加粗 1-2 个", editor_prompt)
        self.assertIn("避免一两句话就换段", editor_prompt)
        self.assertIn("紧凑 Markdown 表格", editor_prompt)
        self.assertIn("产品启示", editor_prompt)
        self.assertIn("工作流角色", editor_prompt)
        self.assertIn("ai-model-workflow-role-division-v1", analyst_prompt)
        self.assertIn("虚构第一人称体验", editor_prompt)


if __name__ == "__main__":
    unittest.main()
