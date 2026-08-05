import unittest
from types import SimpleNamespace

from ai_product_insight.models import EvidenceItem
from ai_product_insight.render import _source_lines


class SourceRenderingTests(unittest.TestCase):
    def test_groups_sources_by_purpose_instead_of_one_line_per_link(self):
        article = SimpleNamespace(
            sources=[
                EvidenceItem(
                    title="个人建站过程记录",
                    url="https://example.com/notes",
                    excerpt="Personal project notes.",
                    source_type="manual",
                ),
                EvidenceItem(
                    title="Gemini 官方介绍",
                    url="https://example.com/gemini",
                    excerpt="Official product page.",
                    source_type="official",
                ),
                EvidenceItem(
                    title="Claude 官方介绍",
                    url="https://example.com/claude",
                    excerpt="Official product page.",
                    source_type="official",
                ),
                EvidenceItem(
                    title="ChatGPT Memory 说明",
                    url="https://example.com/memory",
                    excerpt="Official memory documentation.",
                    source_type="official",
                ),
            ]
        )

        rendered = _source_lines(article)

        self.assertEqual(len(rendered.splitlines()), 3)
        self.assertIn("- 个人体验与项目记录：", rendered)
        self.assertIn("- 官方介绍：", rendered)
        self.assertIn("Gemini 官方介绍", rendered)
        self.assertIn("Claude 官方介绍", rendered)
        self.assertIn("- 记忆功能说明：", rendered)
        self.assertNotIn("**", rendered)


if __name__ == "__main__":
    unittest.main()
