import unittest
from pydantic import ValidationError
from ai_product_insight.models import SocialBundle, x_preflight_length
from ai_product_insight.social import render_x_markdown
from ai_product_insight.agents import SocialRepurposeAgent
from ai_product_insight.llm import OfflineDemoLLM
from test_social_models import social_payload
from test_social_generation import article


def payload():
    data = social_payload()
    data["x_post"]["thread"] = [
        {"text": "I tried a design workflow.\n\nThe main challenge was explaining intent.", "image_kind": "cover", "alt_text": "The overview of the design workflow."},
        {"text": "The screenshot gives us a concrete result to discuss and improve.", "image_kind": "screenshot", "screenshot_id": "website-home", "alt_text": "The finished personal website."},
        {"text": "Design tools should help define the task.\n\nWhat part do you find hardest?", "image_kind": "none"},
    ]
    return data


class XThreadTests(unittest.TestCase):
    def test_legacy_single_post_is_readable(self):
        self.assertIn("# X draft", render_x_markdown(SocialBundle.model_validate(social_payload())))

    def test_thread_markdown_and_assets(self):
        result = render_x_markdown(SocialBundle.model_validate(payload()))
        self.assertIn("# X thread draft", result)
        self.assertIn("1/3\nI tried", result)
        self.assertIn("rendered/x-card.png", result)
        self.assertIn("../../../inputs/assets/ai-design-intent/01-website-home.png", result)
        self.assertIn("配图：无需配图", result)

    def test_length_includes_numbering(self):
        data = payload()
        data["x_post"]["thread"][0]["text"] = "a" * 277
        with self.assertRaises(ValidationError):
            SocialBundle.model_validate(data)

    def test_conservative_unicode_and_short_url_budget(self):
        self.assertEqual(x_preflight_length("a\n😀"), 4)
        self.assertEqual(x_preflight_length("https://x.co"), 23)

    def test_unknown_thread_screenshot_rejected(self):
        data = payload()
        data["x_post"]["thread"][1]["screenshot_id"] = "unknown"
        with self.assertRaises(ValidationError):
            SocialBundle.model_validate(data)

    def test_image_alt_text_required(self):
        data = payload()
        data["x_post"]["thread"][0]["alt_text"] = ""
        with self.assertRaises(ValidationError):
            SocialBundle.model_validate(data)

    def test_offline_agent_defaults_to_thread(self):
        bundle = SocialRepurposeAgent(OfflineDemoLLM()).draft(article())
        self.assertEqual(len(bundle.x_post.thread), 3)

    def test_agent_rejects_silent_single_post_fallback(self):
        class SinglePostLLM:
            def generate_json(self, system, user):
                return social_payload()
        with self.assertRaisesRegex(ValueError, "must contain"):
            SocialRepurposeAgent(SinglePostLLM()).draft(article())


if __name__ == "__main__":
    unittest.main()
