# Clarification and GitHub Pages Publishing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one bounded DeepSeek clarification round to comparison writing and a human-confirmed command that previews, approves, publishes, commits, and pushes an insight article to the existing static GitHub Pages portfolio.

**Architecture:** Extend the existing Insight Agent with a clarification-question method, while the CLI owns terminal input and the pipeline persists the resulting Q&A. Add a standalone static-site publisher that parses the workflow's known Markdown shape, renders a portfolio-aligned HTML article, updates a marker-delimited homepage card block, previews without mutating the site, and only writes/commits/pushes after explicit confirmation.

**Tech Stack:** Python 3.11 standard library, Pydantic 2, argparse, unittest, static HTML/CSS, Git subprocess.

---

### Task 1: One-round clarification contract

**Files:**
- Modify: `src/ai_product_insight/models.py`
- Modify: `src/ai_product_insight/prompts.py`
- Modify: `src/ai_product_insight/agents.py`
- Modify: `src/ai_product_insight/llm.py`
- Test: `tests/test_clarification.py`

1. Write a failing test for 1–3 clarification questions and saved answers.
2. Add strict clarification models and `[CLARIFIER]` prompt.
3. Add `InsightAgent.clarifying_questions` and pass Q&A into comparison analysis and editing.
4. Add deterministic offline output.
5. Run the focused tests.

### Task 2: Terminal interaction and checkpoint persistence

**Files:**
- Modify: `src/ai_product_insight/cli.py`
- Modify: `src/ai_product_insight/pipeline.py`
- Test: `tests/test_clarification.py`

1. Add `--no-clarify` to `compare`.
2. Add a CLI callback that prints at most three questions and accepts one answer per question.
3. Invoke clarification only for interactive terminals and only once.
4. Save `03-clarification.json`; shift later comparison checkpoints without changing article output.
5. Verify noninteractive and skipped flows never block.

### Task 3: Static Markdown publishing

**Files:**
- Create: `src/ai_product_insight/publishing.py`
- Modify: `src/ai_product_insight/cli.py`
- Test: `tests/test_publishing.py`

1. Write failing tests for frontmatter parsing, seven-section extraction, inline Markdown safety, and invalid drafts.
2. Render an editorial article page that reuses the portfolio's visual variables and navigation.
3. Generate `insights/<slug>.html`, `insights/insight.css`, and `insights/index.json`.
4. Update only the marker-delimited generated block inside the homepage insight list.
5. Classify Wikipedia evidence as `community`, never `official`.

### Task 4: Preview, approval, and scoped Git push

**Files:**
- Modify: `src/ai_product_insight/publishing.py`
- Modify: `src/ai_product_insight/cli.py`
- Test: `tests/test_publishing.py`

1. Render preview files under the insight project's output directory without touching the site.
2. Open the preview in the default browser unless `--no-open` is used.
3. Ask one explicit confirmation covering approval, site update, commit, and push.
4. On confirmation, update article status to `approved`, publish static files, stage only generated targets, commit, and push the current branch.
5. If Git is unavailable or push fails, keep local output and report the exact recovery action.

### Task 5: Documentation and verification

**Files:**
- Create: `docs/development-log.md`
- Modify: `README.md`
- Modify: `inputs/ai-model-comparison-notes.md`

1. Record features, failures, root causes, fixes, and remaining limitations through 2026-07-20.
2. Save the user's four new concrete model examples and screenshot-derived label comparison.
3. Document `compare` clarification and `publish` commands.
4. Run the full unit suite.
5. Run publishing end-to-end against a temporary copy of the portfolio.
6. Synchronize the verified files to the formal D-drive insight project and rerun tests there.
