import unittest

from ai_product_insight.agents import normalize_scout_response
from ai_product_insight.models import CandidateSelection


class ScoutResponseTests(unittest.TestCase):
    def test_normalizes_flat_deepseek_score_layout(self):
        raw = {
            "assessments": [
                {
                    "candidate_id": "candidate-1",
                    "relevance": 5,
                    "novelty": 4,
                    "product_depth": 4,
                    "evidence": 3,
                    "total": 4.2,
                }
            ],
            "selected_ids": ["candidate-1"],
        }

        selection = CandidateSelection.model_validate(normalize_scout_response(raw))

        self.assertEqual(selection.assessments[0].score.relevance, 5)
        self.assertEqual(selection.assessments[0].score.total, 4.2)
        self.assertIn("结构兼容", selection.assessments[0].score.reason)

    def test_preserves_nested_score_layout(self):
        raw = {
            "assessments": [
                {
                    "candidate_id": "candidate-1",
                    "score": {
                        "relevance": 5,
                        "novelty": 4,
                        "product_depth": 4,
                        "evidence": 3,
                        "total": 4.2,
                        "reason": "产品机制清晰，公开资料也足以支持继续研究。",
                    },
                }
            ],
            "selected_ids": ["candidate-1"],
        }

        selection = CandidateSelection.model_validate(normalize_scout_response(raw))

        self.assertEqual(selection.assessments[0].score.reason, "产品机制清晰，公开资料也足以支持继续研究。")


if __name__ == "__main__":
    unittest.main()
