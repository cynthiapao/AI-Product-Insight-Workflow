import unittest

from ai_product_insight.agents import normalize_insight_response
from ai_product_insight.models import ProductInsight


class InsightResponseTests(unittest.TestCase):
    def test_merges_excess_limitations_without_losing_caveats(self):
        caveats = [f"Limitation {i}: evidence remains limited for this product scenario." for i in range(5)]
        detail = "This is a sufficiently detailed explanation of the product mechanism and its observed boundaries."
        raw = {"one_line": detail, "core_mechanism": detail, "why_it_works": detail,
               "personal_judgment": detail, "limitations": caveats,
               "patterns": [{"name": "Review evidence", "principle": detail, "applies_when": detail}]}
        result = ProductInsight.model_validate(normalize_insight_response(raw))
        self.assertEqual(len(result.limitations), 4)
        for caveat in caveats:
            self.assertIn(caveat, " ".join(result.limitations))

    def test_normalizes_observed_alternate_layout(self):
        raw = {
            "core_mechanism": "The product turns arbitrary web pages into structured data designed for downstream AI agents and tool calls.",
            "explanation": "This works because it removes repeated parsing work and returns smaller, task-oriented payloads to the model.",
            "limitations": "It depends on recognizable page structure and currently supports a limited set of sites.",
            "judgment": "The agent-first positioning is useful, although long-term defensibility depends on coverage and integration depth.",
            "actionable_takeaways": [
                "For agent-facing data products, optimize the returned structure for the next model action rather than reproducing the full page.",
                "Start with constrained high-value sources before expanding coverage, so output reliability can be evaluated clearly.",
            ],
        }

        insight = ProductInsight.model_validate(normalize_insight_response(raw))

        self.assertTrue(insight.one_line.startswith("The product turns"))
        self.assertEqual(len(insight.limitations), 1)
        self.assertEqual(len(insight.patterns), 2)
        self.assertIn("agent-facing", insight.patterns[0].principle)

    def test_preserves_canonical_fields_and_removes_aliases(self):
        raw = {
            "one_line": "This is a sufficiently long canonical one-line product judgment for validation.",
            "core_mechanism": "A sufficiently detailed canonical core mechanism that remains unchanged during response normalization.",
            "why_it_works": "A sufficiently detailed explanation of why the product mechanism works for its intended users.",
            "limitations": ["The available evidence does not yet establish performance across every supported source."],
            "personal_judgment": "A sufficiently detailed personal judgment that remains unchanged after normalization is applied.",
            "patterns": [
                {
                    "name": "Canonical pattern",
                    "principle": "Keep the canonical structured method instead of replacing it with an alternate field.",
                    "applies_when": "Use it when the canonical response is already present.",
                }
            ],
            "judgment": "This alias must not override the canonical field.",
        }

        normalized = normalize_insight_response(raw)
        insight = ProductInsight.model_validate(normalized)

        self.assertTrue(insight.personal_judgment.startswith("A sufficiently detailed"))
        self.assertNotIn("judgment", normalized)


if __name__ == "__main__":
    unittest.main()
