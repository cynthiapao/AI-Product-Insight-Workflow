import unittest

from ai_product_insight.agents import normalize_social_response
from ai_product_insight.models import x_preflight_length


class SocialResponseTests(unittest.TestCase):
    def test_normalizes_carousel_to_xiaohongshu_platform(self):
        raw = {
            "screenshots": [
                {"screenshot_id": "learning-flow", "used_for": ["carousel", "x", "carousel"]}
            ]
        }

        normalized = normalize_social_response(raw, "ai-tutor-learning-process")

        self.assertEqual(
            normalized["screenshots"][0]["used_for"],
            ["xiaohongshu", "x"],
        )

    def test_shortens_every_thread_post_with_numbering_budget(self):
        raw = {
            "x_post": {
                "format": "thread",
                "text": "Lead text that will be replaced by the normalized first post.",
                "thread": [
                    {"text": "First sentence explains the product clearly. " * 10},
                    {"text": "Second sentence describes a concrete workflow limitation. " * 10},
                    {"text": "Third sentence closes with a useful product question. " * 10},
                ],
            }
        }

        normalized = normalize_social_response(raw, "application-product")
        thread = normalized["x_post"]["thread"]

        self.assertEqual(normalized["x_post"]["text"], thread[0]["text"])
        for index, post in enumerate(thread, 1):
            self.assertLessEqual(x_preflight_length(f"{index}/3\n{post['text']}"), 280)
            self.assertGreaterEqual(len(post["text"]), 20)

    def test_keeps_xhs_title_complete_and_expands_short_carousel(self):
        raw = {
            "key_takeaway": "AI 把旅行搜索与交易放进一个入口，但排序透明度决定用户是否愿意信任它。",
            "xiaohongshu": {
                "title": "谷歌AI Mode把旅行装进搜索，但信任仍是问题",
                "body": "第一段用于交代产品发生了什么变化，以及它为什么值得关注。\n\n第二段具体说明用户减少了哪些切换和比较成本，也保留真实边界。\n\n第三段说明推荐排序不透明为什么会影响用户判断和信任。\n\n你会把旅行预订交给这样的 AI 吗？",
            },
            "carousel": [
                {"order": 1, "kind": "cover", "title": "封面", "body": "核心判断"},
                {"order": 2, "kind": "screenshot", "title": "界面", "body": "截图说明"},
                {"order": 3, "kind": "comparison", "title": "对比", "body": "比较结果"},
                {"order": 4, "kind": "closing", "title": "结论", "body": "最终判断"},
            ],
        }

        normalized = normalize_social_response(raw, "travel-ai")

        self.assertEqual(normalized["xiaohongshu"]["title"], "谷歌AI Mode把旅行装进搜索")
        self.assertEqual(len(normalized["carousel"]), 6)
        self.assertEqual(normalized["carousel"][-1]["kind"], "closing")
        self.assertEqual([item["order"] for item in normalized["carousel"]], list(range(1, 7)))


if __name__ == "__main__":
    unittest.main()
