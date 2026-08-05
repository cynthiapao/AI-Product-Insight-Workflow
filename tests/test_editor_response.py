import unittest

from ai_product_insight.agents import normalize_editor_response
from ai_product_insight.models import ArticleContent


def valid_method(index: int) -> dict[str, str]:
    return {
        "name": f"Method {index}",
        "principle": "Design the returned information around the user's next decision instead of exposing every available detail.",
        "applies_when": "Use this when a product must turn complex source material into a focused action.",
    }


class EditorResponseTests(unittest.TestCase):
    def test_limits_tags_and_transferable_methods(self):
        raw = {
            "slug": "agent-ready-product-data",
            "title": "Designing Product Data for AI Agents",
            "summary": "A structured review of how an agent-facing product turns web information into focused inputs for model actions.",
            "read_minutes": 5,
            "tags": ["AI", "Agents", "Data", "Product", "Tools"],
            "opening": "The interesting part of this product is not simply that it collects web data, but that it prepares the result for an agent's next action.",
            "core_experience": "A user provides a source URL and receives a smaller structured response designed for downstream reasoning. This changes the experience from browsing and manual extraction into a compact handoff between a data service and an AI workflow.",
            "why_it_works": "The approach works because it reduces repeated parsing, removes irrelevant page elements, and makes the output easier for an agent to consume within a limited context window. The value is therefore located in the handoff format, not only in access to the source.",
            "boundaries": "The product still depends on source coverage, stable page structures, and reliable extraction. Public evidence also does not establish how consistently it performs across every supported site or complex page state.",
            "personal_judgment": "I think the agent-first framing is more meaningful than presenting another general scraping tool. Its long-term product value will depend on whether structured outputs remain dependable as coverage expands and whether integrations become difficult to replace.",
            "transferable_methods": [valid_method(1), valid_method(2), valid_method(3), valid_method(4), valid_method(5)],
        }

        content = ArticleContent.model_validate(normalize_editor_response(raw))

        self.assertEqual(content.tags, ["AI", "Agents", "Data", "Product"])
        self.assertEqual(len(content.transferable_methods), 4)

    def test_converts_single_tag_string_to_list(self):
        raw = {"tags": "AI Product"}

        normalized = normalize_editor_response(raw)

        self.assertEqual(normalized["tags"], ["AI Product"])

    def test_truncates_all_article_fields_to_schema_limits(self):
        raw = {
            "slug": "multi-model-website-workflow",
            "title": "多模型协作不是选出一个冠军，而是让不同模型在合适的阶段承担不同角色" * 3,
            "summary": "这是一次真实网站项目中的观察。" * 30,
            "read_minutes": 5,
            "tags": ["AI 产品", "多模型协作"],
            "opening": "不同模型在同一个项目里承担了不同角色。" * 40,
            "core_experience": "我沿着网站项目的真实推进过程观察模型，而不是用一道标准题比较它们。" * 50,
            "why_it_works": "设计探索、代码执行、内容精修和中文表达需要的能力并不相同。" * 50,
            "boundaries": "这些判断只来自这次个人网站项目，不能直接外推到所有模型和所有任务。" * 40,
            "personal_judgment": "我更愿意把模型选择理解成工作流设计，而不是寻找一个全能冠军。" * 50,
            "product_takeaway": "AI 产品经理需要拆解任务、设计工作流，并让不同模型承担合适角色。" * 30,
            "transferable_methods": [
                {
                    "name": "根据项目阶段分配不同模型角色" * 10,
                    "principle": "先识别任务处于探索、执行还是精修阶段，再选择合适的模型。" * 30,
                    "applies_when": "适用于设计、编程和写作混合发生的复杂个人项目。" * 30,
                }
            ],
        }

        normalized = normalize_editor_response(raw)
        content = ArticleContent.model_validate(normalized)

        self.assertLessEqual(len(content.title), 80)
        self.assertLessEqual(len(content.summary), 90)
        self.assertNotIn("\n", content.summary)
        self.assertLessEqual(len(content.opening), 500)
        self.assertLessEqual(len(content.core_experience), 1000)
        self.assertLessEqual(len(content.why_it_works), 1000)
        self.assertLessEqual(len(content.boundaries), 800)
        self.assertLessEqual(len(content.personal_judgment), 900)
        self.assertLessEqual(len(content.product_takeaway), 300)
        self.assertLessEqual(len(content.transferable_methods[0].name), 80)
        self.assertLessEqual(len(content.transferable_methods[0].principle), 500)
        self.assertLessEqual(len(content.transferable_methods[0].applies_when), 300)


if __name__ == "__main__":
    unittest.main()
