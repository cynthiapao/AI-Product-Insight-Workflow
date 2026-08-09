import unittest

from pydantic import ValidationError

from ai_product_insight.models import SocialBundle


def social_payload() -> dict[str, object]:
    return {
        "article_slug": "ai-design-intent",
        "key_takeaway": "AI 建站减少了执行成本，但准确理解没有说出口的设计偏好仍然困难。",
        "x_post": {
            "text": "AI can generate a website, but the harder problem is understanding what a user means by ‘more lively.’ Generation is fast; translating taste into design decisions still takes work.",
            "headline": "Generating is not understanding",
            "image_recommended": True,
            "image_brief": "Use the final website screenshot with one restrained annotation.",
            "alt_text": "A screenshot of the finished personal portfolio website.",
        },
        "xiaohongshu": {
            "title": "AI 建站最难的不是代码",
            "body": "我原本以为 AI 建站最难的是技术，真正开始做以后才发现，更费力的是把模糊的设计感受转换成可以执行的色彩、排版、间距和交互要求。生成很快，但判断仍然需要自己完成。",
            "hashtags": ["AI产品", "个人网站"],
        },
        "carousel": [
            {"order": 1, "kind": "cover", "title": "AI 建站最难的不是代码"},
            {"order": 2, "kind": "screenshot", "title": "最终网站", "body": "真实完成效果", "screenshot_id": "website-home"},
            {"order": 3, "kind": "insight", "title": "生成不等于理解", "body": "模糊偏好仍需翻译。"},
            {"order": 4, "kind": "closing", "title": "产品启示", "body": "降低表达成本比单纯提速更重要。"},
        ],
        "screenshots": [
            {
                "screenshot_id": "website-home",
                "filename": "01-website-home.png",
                "required": True,
                "source_kind": "personal",
                "purpose": "展示个人网站最终完成后的真实页面效果。",
                "capture": "截取首页首屏，保留标题、简介和项目入口。",
                "annotation": "AI 完成了生成，但设计仍需多轮对齐",
                "used_for": ["x", "xiaohongshu"],
            }
        ],
    }


class SocialModelTests(unittest.TestCase):
    def test_valid_social_bundle(self):
        bundle = SocialBundle.model_validate(social_payload())
        self.assertLessEqual(len(bundle.x_post.text), 280)
        self.assertEqual(bundle.screenshots[0].filename, "01-website-home.png")

    def test_rejects_x_post_over_280_characters(self):
        payload = social_payload()
        payload["x_post"]["text"] = "x" * 281  # type: ignore[index]
        with self.assertRaises(ValidationError):
            SocialBundle.model_validate(payload)

    def test_rejects_unknown_screenshot_reference(self):
        payload = social_payload()
        payload["carousel"][1]["screenshot_id"] = "missing"  # type: ignore[index]
        with self.assertRaises(ValidationError):
            SocialBundle.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
