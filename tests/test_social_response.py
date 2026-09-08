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


if __name__ == "__main__":
    unittest.main()
