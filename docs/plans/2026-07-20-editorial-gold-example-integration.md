# Editorial Gold Example Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the approved first article into reusable editorial rules and a few-shot example for the existing Insight and Editor agents.

**Architecture:** Add four versioned JSON resources for editorial profile, rubric, gold input, and gold output. A small loader validates and serializes these resources, and the CLI injects the resulting context into only the Insight and Editor system prompts. Scout, Research, article schemas, rendering, and human review remain unchanged.

**Tech Stack:** Python 3.11, Pydantic 2, JSON, unittest.

---

### Task 1: Add editorial resources

**Files:**
- Create: `config/editorial_profile.json`
- Create: `config/editorial_rubric.json`
- Create: `examples/gold/ai-website.input.json`
- Create: `examples/gold/ai-website.output.json`

**Steps:**
1. Encode the seven-section contract and the approved voice rules.
2. Separate personal experience, verified facts, open questions, and editorial inference in the gold input.
3. Encode the approved article in the existing `ArticleContent` output shape.
4. Validate every file with Python's JSON parser.

### Task 2: Load and serialize editorial context

**Files:**
- Create: `src/ai_product_insight/editorial.py`
- Test: `tests/test_editorial_context.py`

**Steps:**
1. Write a failing test for loading all four resources.
2. Implement `EditorialContext.load(project_root)` with clear missing/invalid-file errors.
3. Implement role-specific prompt context so Analyst receives editorial reasoning rules while Editor receives the full few-shot example and rubric.
4. Run the focused test and verify it passes.

### Task 3: Inject guidance into the two writing agents

**Files:**
- Modify: `src/ai_product_insight/agents.py`
- Modify: `src/ai_product_insight/cli.py`
- Test: `tests/test_editorial_context.py`

**Steps:**
1. Add optional `EditorialContext` dependencies to `InsightAgent` and `EditorAgent` so existing tests and offline substitutes remain compatible.
2. Append role-specific guidance to `ANALYST_SYSTEM` and `EDITOR_SYSTEM` without changing the JSON payload shape.
3. Load the context once in the CLI and share it between both agents.
4. Test that captured system prompts contain the seven-section contract, evidence rules, and gold example.

### Task 4: Verify regression safety

**Files:**
- Modify if required: `tests/test_pipeline.py`

**Steps:**
1. Run all unit tests with `python -m unittest discover -s tests -v`.
2. Run `python -m ai_product_insight offline-demo` with a temporary output directory.
3. Confirm the run completes and writes JSON, Markdown, and card HTML.
4. Sync only the tested files to the D-drive project.
5. Re-run the complete unit suite against the D-drive project.
