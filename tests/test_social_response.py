import unittest

from ai_product_insight.agents import normalize_social_response


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


if __name__ == "__main__":
    unittest.main()
