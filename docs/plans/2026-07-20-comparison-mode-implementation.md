# Multi-Product Comparison Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a comparison workflow that researches multiple user-selected products and produces one evidence-backed, personal comparison article.

**Architecture:** Introduce a strict `ComparisonBrief` model and comparison-specific methods on the existing Insight and Editor agents. Add a separate pipeline entry point that bypasses discovery and scoring, researches each product independently, then aggregates the results into the existing article output schema.

**Tech Stack:** Python 3.11+, argparse, Pydantic 2, unittest.

---

### Task 1: Define comparison behavior with failing tests

**Files:**
- Create: `tests/test_comparison_mode.py`

1. Test `ComparisonBrief` constraints and CLI parsing.
2. Test that comparison Agent prompts contain all products and the personal notes.
3. Test that the comparison pipeline writes exactly one review draft.
4. Run the focused test and confirm it fails before implementation.

### Task 2: Add comparison models, prompts, and Agent methods

**Files:**
- Modify: `src/ai_product_insight/models.py`
- Modify: `src/ai_product_insight/prompts.py`
- Modify: `src/ai_product_insight/agents.py`
- Modify: `src/ai_product_insight/llm.py`

1. Add `ComparisonBrief` and permit `compare` in `RunReport.mode`.
2. Add strict comparison analyst and editor prompts.
3. Add `InsightAgent.compare` and `EditorAgent.draft_comparison`.
4. Add deterministic offline responses for focused tests.
5. Run the Agent tests.

### Task 3: Add pipeline and CLI support

**Files:**
- Modify: `src/ai_product_insight/pipeline.py`
- Modify: `src/ai_product_insight/cli.py`

1. Add `InsightPipeline.run_comparison` with per-product checkpoints.
2. Aggregate unique evidence and require at least two usable research packs.
3. Add the `compare` parser with repeated two-value `--product` and required `--notes-file`.
4. Load UTF-8 notes, build candidates, and route to the comparison pipeline.
5. Run focused CLI and pipeline tests.

### Task 4: Verify and synchronize

**Files:**
- Create: `inputs/ai-model-comparison-notes.md`
- Modify: `README.md`

1. Add the user's initial comparison observations as an editable notes file.
2. Document the command and clarify the single-product/multi-product distinction.
3. Run the full unittest suite.
4. Run a deterministic local comparison demo using fixture evidence.
5. Synchronize changed files to the formal D-drive project and rerun all tests there.
