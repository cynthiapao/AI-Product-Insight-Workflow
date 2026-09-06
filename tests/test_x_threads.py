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
    data["social_standard"] = "v5"
    data["content_track"] = "deep_insight"
    data["x_post"]["format"] = "thread"
    data["x_post"]["mentions_applicable"] = True
    data["x_post"]["official_mentions"] = [
        {
            "product_name": "OpenAI",
            "handle": "@OpenAI",
            "profile_url": "https://x.com/OpenAI",
            "verification_status": "needs_review",
        }
    ]
    data["x_post"]["thread"] = [
        {"text": "I tried an @OpenAI design workflow.\n\nThe main challenge was explaining intent.", "image_kind": "cover", "alt_text": "The overview of the design workflow."},
        {"text": "The screenshot gives us a concrete result to discuss and improve.", "image_kind": "screenshot", "screenshot_id": "website-home", "alt_text": "The finished personal website."},
        {"text": "Design tools should help define the task.\n\nWhat part do you find hardest?", "image_kind": "none"},
    ]
    data["xiaohongshu"]["title"] = "AI建站难在理解意图"
    data["xiaohongshu"]["body"] += "\n\n你觉得更难的是表达设计意图，还是判断生成结果是否合适？"
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

    def test_offline_agent_can_explicitly_use_cold_start_single(self):
        bundle = SocialRepurposeAgent(OfflineDemoLLM(), x_format="single").draft(article())
        self.assertEqual(bundle.x_post.format, "single")
        self.assertEqual(bundle.x_post.thread, [])
        self.assertIn("single-post draft", render_x_markdown(bundle))

    def test_agent_rejects_silent_single_post_fallback(self):
        class SinglePostLLM:
            def generate_json(self, system, user):
                return social_payload()
        with self.assertRaisesRegex(ValueError, "3-8 posts"):
            SocialRepurposeAgent(SinglePostLLM()).draft(article())

    def test_v5_thread_first_post_requires_cover(self):
        data = payload()
        data["x_post"]["thread"][0]["image_kind"] = "none"
        data["x_post"]["thread"][0]["alt_text"] = ""
        with self.assertRaisesRegex(ValidationError, "first post must use the 16:9 cover"):
            SocialBundle.model_validate(data)

    def test_v5_single_post_is_allowed_when_explicit(self):
        data = payload()
        data["x_post"]["format"] = "single"
        data["x_post"]["thread"] = []
        data["x_post"]["text"] = "A cold-start post about @OpenAI with one summary card and a clear product insight."
        bundle = SocialBundle.model_validate(data)
        self.assertEqual(bundle.x_post.format, "single")

    def test_official_handle_must_appear_and_match_profile(self):
        data = payload()
        data["x_post"]["official_mentions"][0]["profile_url"] = "https://x.com/not-openai"
        with self.assertRaisesRegex(ValidationError, "profile path"):
            SocialBundle.model_validate(data)
        data = payload()
        data["x_post"]["thread"][0]["text"] = data["x_post"]["thread"][0]["text"].replace("@OpenAI ", "")
        with self.assertRaisesRegex(ValidationError, "must appear"):
            SocialBundle.model_validate(data)

    def test_unresolved_product_mentions_are_explicit(self):
        data = payload()
        data["x_post"]["official_mentions"] = []
        data["x_post"]["unresolved_product_mentions"] = ["Example Product"]
        bundle = SocialBundle.model_validate(data)
        rendered = render_x_markdown(bundle)
        self.assertIn("待补充官方账号", rendered)
        self.assertIn("Example Product", rendered)

    def test_official_mentions_are_listed_for_manual_verification(self):
        rendered = render_x_markdown(SocialBundle.model_validate(payload()))
        self.assertIn("官方账号核验", rendered)
        self.assertIn("[@OpenAI](https://x.com/OpenAI)", rendered)

    def test_v5_xiaohongshu_title_and_question_are_enforced(self):
        data = payload()
        data["xiaohongshu"]["title"] = "这是一个明显超过二十个字符限制的小红书深度洞察标题"
        with self.assertRaisesRegex(ValidationError, "20 characters"):
            SocialBundle.model_validate(data)
        data = payload()
        data["xiaohongshu"]["body"] = data["xiaohongshu"]["body"].rstrip("？") + "。"
        with self.assertRaisesRegex(ValidationError, "end with a discussion question"):
            SocialBundle.model_validate(data)


if __name__ == "__main__":
    unittest.main()
