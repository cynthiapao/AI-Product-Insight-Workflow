import unittest

from ai_product_insight.agents import normalize_research_response
from ai_product_insight.models import EvidenceQuality, ResearchAnalysis


class ResearchResponseTests(unittest.TestCase):
    def test_normalizes_observed_evidence_quality_alias(self):
        raw = {
            "verified_facts": ["The product has an official release page."],
            "open_questions": ["Independent usage data is not available."],
            "evidence_quality": "usable",
        }

        analysis = ResearchAnalysis.model_validate(normalize_research_response(raw))

        self.assertEqual(analysis.quality, EvidenceQuality.usable)
        self.assertEqual(len(analysis.verified_facts), 1)

    def test_preserves_canonical_quality_and_removes_alias(self):
        raw = {
            "verified_facts": [],
            "open_questions": [],
            "quality": "strong",
            "evidence_quality": "usable",
        }

        normalized = normalize_research_response(raw)
        analysis = ResearchAnalysis.model_validate(normalized)

        self.assertEqual(analysis.quality, EvidenceQuality.strong)
        self.assertNotIn("evidence_quality", normalized)

    def test_trims_generated_lists_to_schema_limits(self):
        raw = {
            "verified_facts": [f"Verified fact {index}" for index in range(14)],
            "open_questions": [f"Open question {index}" for index in range(10)],
            "quality": "usable",
        }

        analysis = ResearchAnalysis.model_validate(normalize_research_response(raw))

        self.assertEqual(len(analysis.verified_facts), 12)
        self.assertEqual(analysis.verified_facts[-1], "Verified fact 11")
        self.assertEqual(len(analysis.open_questions), 8)
        self.assertEqual(analysis.open_questions[-1], "Open question 7")


if __name__ == "__main__":
    unittest.main()
