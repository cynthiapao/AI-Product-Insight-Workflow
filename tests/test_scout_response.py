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
                    "application_fit": True,
                    "application_category": "productivity",
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
    def test_assesses_candidates_after_the_first_ten(self):
        candidates = [ProductCandidate(name=f"Product {i}", url=f"https://example.com/{i}", source="fixture")
                      for i in range(25)]
        config = WorkflowConfig(sources=[], max_candidates=25, research_candidate_limit=8)
        ScoutAgent(FixedScoutLLM(), config).select(candidates)
        self.assertTrue(all(candidate.score is not None for candidate in candidates))

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

    def test_excludes_clear_technical_artifact_before_model_selection(self):
        class RecordingScoutLLM(FixedScoutLLM):
            seen_names: list[str]

            def generate_json(self, system: str, user: str):
                import json

                self.seen_names = [item["name"] for item in json.loads(user)["candidates"]]
                return super().generate_json(system, user)

        llm = RecordingScoutLLM()
        candidates = [
            ProductCandidate(
                name="TERMy",
                url="https://github.com/example/termy",
                source="fixture",
                summary="A fast terminal assistant and command-line tool for developers.",
            ),
            ProductCandidate(
                name="Care Coach AI",
                url="https://example.com/care-coach",
                source="fixture",
                summary="A patient-facing health coaching app with a guided mobile workflow.",
            ),
        ]

        selected = ScoutAgent(llm, WorkflowConfig(sources=[])).select(candidates)

        self.assertEqual(llm.seen_names, ["Care Coach AI"])
        self.assertEqual([item.name for item in selected], ["Care Coach AI"])

    def test_rejects_high_scoring_candidate_when_model_marks_non_application(self):
        class NonApplicationLLM(FixedScoutLLM):
            def generate_json(self, system: str, user: str):
                result = super().generate_json(system, user)
                result["assessments"][0]["application_fit"] = False
                result["assessments"][0]["application_category"] = "non_application"
                return result

        candidate = ProductCandidate(
            name="Ambiguous AI Project",
            url="https://example.com/project",
            source="fixture",
            summary="A newly released AI project with public documentation.",
        )

        selected = ScoutAgent(NonApplicationLLM(), WorkflowConfig(sources=[])).select([candidate])

        self.assertEqual(selected, [])

    def test_manual_candidate_bypasses_deterministic_scope_guard(self):
        candidate = ProductCandidate(
            name="Explicit terminal review",
            url="https://example.com/terminal",
            source="manual",
            summary="A terminal assistant selected directly by the editor.",
            manual=True,
        )

        selected = ScoutAgent(FixedScoutLLM(), WorkflowConfig(sources=[])).select([candidate])

        self.assertEqual([item.name for item in selected], ["Explicit terminal review"])

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
