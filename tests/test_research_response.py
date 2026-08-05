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


if __name__ == "__main__":
    unittest.main()
