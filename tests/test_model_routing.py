import unittest

from ai_product_insight.cli import build_agent_crew
from ai_product_insight.config import WorkflowConfig


class DummyFetcher:
    pass


class DummyEditorialContext:
    pass


class DummyLLM:
    def generate_json(self, system: str, user: str) -> dict:
        return {}


class ModelRoutingTests(unittest.TestCase):
    def test_routes_flash_to_research_and_pro_to_writing(self):
        fast_llm = DummyLLM()
        quality_llm = DummyLLM()
        crew = build_agent_crew(
            config=WorkflowConfig(sources=[]),
            fetcher=DummyFetcher(),
            editorial_context=DummyEditorialContext(),
            fast_llm=fast_llm,
            quality_llm=quality_llm,
        )

        self.assertIs(crew.scout.llm, fast_llm)
        self.assertIs(crew.researcher.llm, fast_llm)
        self.assertIs(crew.analyst.llm, quality_llm)
        self.assertIs(crew.editor.llm, quality_llm)

    def test_defaults_to_one_model_for_offline_runs(self):
        llm = DummyLLM()
        crew = build_agent_crew(
            config=WorkflowConfig(sources=[]),
            fetcher=DummyFetcher(),
            editorial_context=DummyEditorialContext(),
            fast_llm=llm,
        )

        self.assertIs(crew.analyst.llm, llm)
        self.assertIs(crew.editor.llm, llm)


if __name__ == "__main__":
    unittest.main()
