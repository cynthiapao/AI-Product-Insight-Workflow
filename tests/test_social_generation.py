import json
import tempfile
import unittest
from pathlib import Path

from ai_product_insight.agents import SocialRepurposeAgent
from ai_product_insight.llm import OfflineDemoLLM
from ai_product_insight.models import ArticleDraft, DesignPattern, EvidenceItem
from ai_product_insight.social import write_social_outputs


def article() -> ArticleDraft:
    return ArticleDraft(
        slug="ai-design-intent",
        title="AI 建站真正难的，不是生成，而是理解设计意图",
        summary="真实建站体验说明，生成速度无法替代对模糊设计偏好的理解。",
        tags=["AI设计", "意图理解"],
        opening="AI 建站降低了从想法到方案的距离，但生成并不等于理解用户脑中的感觉。真正费时间的是把模糊偏好转换成明确的设计要求。",
        core_experience="我在真实项目中使用 AI 完成网页设计和代码执行，也经历了模糊要求需要多轮调整的过程。当修改方向足够明确时，代码执行通常很稳定；当我只能说出页面应该更活泼时，模型给出的结果就需要反复校准。",
        why_it_works="明确的设计变量可以直接进入执行，而模糊的感受需要先被拆成色彩、排版、间距和交互。生成工具能够缩短制作时间，却不能自动知道每个人心中的审美标准，这也是探索和精确执行需要不同交互方式的原因。",
        boundaries="生成速度很快，但意图翻译仍然需要时间、判断和持续校准。即使第一版已经达到可用程度，细节中的线条、间距和动效也可能需要多轮对话，因此不能把可生成直接等同于完全理解。",
        personal_judgment="未来产品的差异不只是谁生成更快，还在于谁能降低用户表达偏好和纠正结果的成本。真正优秀的 AI 设计工具应该参与任务定义，帮助用户把感觉变成选择，同时在方向确定后把精确控制权交还给人。",
        transferable_methods=[DesignPattern(name="双轨交互", principle="探索阶段帮助定义方向，执行阶段保留精确控制。", applies_when="适用于生成式设计工具。")],
        sources=[EvidenceItem(title="Personal project record", url="https://example.com", excerpt="A sufficiently detailed personal project record for the article source.", source_type="manual")],
    )


class SocialGenerationTests(unittest.TestCase):
    def test_agent_and_writer_create_review_files(self):
        bundle = SocialRepurposeAgent(OfflineDemoLLM()).draft(article())
        self.assertLessEqual(len(bundle.x_post.text), 280)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = write_social_outputs(bundle, root / "social", root / "assets")
            self.assertEqual(len(paths), 6)
            saved = json.loads((root / "social" / bundle.article_slug / "social.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["article_slug"], bundle.article_slug)
            readme = (root / "assets" / bundle.article_slug / "README.md").read_text(encoding="utf-8")
            self.assertIn("01-primary-result.png", readme)


if __name__ == "__main__":
    unittest.main()
