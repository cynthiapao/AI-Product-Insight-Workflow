import unittest

from ai_product_insight.models import CandidateScore, ProductCandidate, canonicalize_url


class ModelTests(unittest.TestCase):
    def test_canonicalize_url_removes_tracking(self):
        result = canonicalize_url("HTTPS://Example.COM/product/?utm_source=test&x=1#top")
        self.assertEqual(result, "https://example.com/product?x=1")

    def test_candidate_id_is_stable(self):
        first = ProductCandidate(name="Demo", url="https://example.com/demo", source="test")
        second = ProductCandidate(name="Demo", url="https://example.com/demo/", source="other")
        self.assertEqual(first.candidate_id, second.candidate_id)

    def test_score_total_is_recalculated(self):
        score = CandidateScore(relevance=5, novelty=4, product_depth=3, evidence=2, total=0, reason="Enough detail for validation")
        self.assertEqual(score.total, 3.8)


if __name__ == "__main__":
    unittest.main()

