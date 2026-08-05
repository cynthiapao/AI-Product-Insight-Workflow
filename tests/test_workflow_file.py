import unittest
from pathlib import Path


class WorkflowFileTests(unittest.TestCase):
    def test_workflow_has_human_review_and_secret_reference(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / ".github" / "workflows" / "generate-insight-draft.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("schedule:", text)
        self.assertIn('cron: "20 9 * * 1"', text)
        self.assertIn('timezone: "Asia/Shanghai"', text)
        self.assertIn("${{ secrets.DEEPSEEK_API_KEY }}", text)
        self.assertIn("gh pr create", text)
        self.assertIn("--draft", text)
        self.assertNotIn("continue-on-error: true", text)
        self.assertNotRegex(text, r"sk-[A-Za-z0-9]{12,}")


if __name__ == "__main__":
    unittest.main()
