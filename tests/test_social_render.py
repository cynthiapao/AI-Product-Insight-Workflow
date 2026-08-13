import tempfile
import unittest
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover - dependency is installed by the project package.
    Image = None

from ai_product_insight.models import SocialBundle
from ai_product_insight.social_render import MissingAssetsError, render_social_assets, validate_assets
from tests.test_social_models import social_payload


@unittest.skipIf(Image is None, "Pillow is not installed")
class SocialRenderTests(unittest.TestCase):
    def test_missing_required_screenshot_is_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(MissingAssetsError, "01-website-home.png"):
                validate_assets(SocialBundle.model_validate(social_payload()), Path(temp))

    def test_renders_x_card_and_xiaohongshu_carousel(self):
        bundle = SocialBundle.model_validate(social_payload())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            assets = root / "assets"
            assets.mkdir()
            Image.new("RGB", (1200, 800), "#DCE9FF").save(assets / "01-website-home.png")
            bundle_path = root / "social.json"
            bundle_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
            outputs = render_social_assets(bundle_path, assets, root / "rendered")
            self.assertEqual(len(outputs), 5)
            self.assertTrue(all(path.is_file() for path in outputs))
            with Image.open(outputs[0]) as image:
                self.assertEqual(image.size, (1600, 900))
            with Image.open(outputs[3]) as image:
                self.assertEqual(image.size, (1080, 1440))


if __name__ == "__main__":
    unittest.main()
