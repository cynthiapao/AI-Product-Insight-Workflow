import unittest

from ai_product_insight.agents import ScoutAgent, normalize_scout_response
from ai_product_insight.config import WorkflowConfig
from ai_product_insight.models import CandidateSelection, ProductCandidate


class FixedScoutLLM:
    def generate_json(self, system: str, user: str):
        import json

        candidates = json.loads(user)["candidates"]
        assessments = []
        for candidate in candidates:
            assessments.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "score": {
                        "relevance": 4,
                        "novelty": 4,
                        "product_depth": 4,
                        "evidence": 4,
                        "total": 4.0,
                        "reason": "产品方向相关，且值得继续检查公开证据是否足够。",
                    },
                }
            )
        return {
            "assessments": assessments,
            "selected_ids": [item["candidate_id"] for item in candidates[:3]],
        }


class ScoutResponseTests(unittest.TestCase):
    def test_keeps_eligible_fallbacks_beyond_three_model_choices(self):
        config = WorkflowConfig(
            sources=[],
            select_count=3,
            research_candidate_limit=5,
            min_score=3.0,
        )
        candidates = [
            ProductCandidate(name=f"Product {index}", url=f"https://example.com/{index}", source="fixture")
            for index in range(1, 7)
        ]

        selected = ScoutAgent(FixedScoutLLM(), config).select(candidates)

        self.assertEqual(len(selected), 5)
        self.assertEqual([item.name for item in selected[:3]], ["Product 1", "Product 2", "Product 3"])

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
