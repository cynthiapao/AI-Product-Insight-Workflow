# AI Product Insight Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a locally testable, GitHub Actions-ready workflow that discovers products, researches evidence, generates a structured Chinese insight draft with DeepSeek, and stops at human review.

**Architecture:** A deterministic Python pipeline coordinates four explicit agent roles. Each stage exchanges Pydantic models and persists JSON checkpoints; live services are behind small interfaces so offline tests use fixtures and a fake LLM.

**Tech Stack:** Python 3.11+, Pydantic 2, standard-library HTTP/RSS/HTML parsing, DeepSeek Chat Completions API, GitHub Actions, Markdown/HTML output.

---

### Task 1: Project skeleton and schemas

**Files:**
- Create: `pyproject.toml`
- Create: `src/ai_product_insight/models.py`
- Create: `src/ai_product_insight/config.py`
- Test: `tests/test_models.py`

**Steps:** Define strict candidate, evidence, insight, article and run-report schemas; load JSON configuration and environment variables; run schema tests; commit `feat: add insight workflow schemas`.

### Task 2: Product discovery

**Files:**
- Create: `src/ai_product_insight/sources.py`
- Create: `src/ai_product_insight/discovery.py`
- Create: `config/sources.json`
- Test: `tests/test_discovery.py`

**Steps:** Parse RSS/Atom and Hacker News responses; normalize URLs; de-duplicate by canonical URL and title; merge manual input; verify fixture-driven tests; commit `feat: add product discovery`.

### Task 3: DeepSeek client and agents

**Files:**
- Create: `src/ai_product_insight/llm.py`
- Create: `src/ai_product_insight/agents.py`
- Create: `src/ai_product_insight/prompts.py`
- Test: `tests/test_agents.py`

**Steps:** Implement JSON-mode API client with retry and validation; define sequential scout, researcher, analyst and editor agents; inject a fake LLM in tests; commit `feat: add structured multi-agent analysis`.

### Task 4: Pipeline, rendering and CLI

**Files:**
- Create: `src/ai_product_insight/pipeline.py`
- Create: `src/ai_product_insight/render.py`
- Create: `src/ai_product_insight/cli.py`
- Create: `fixtures/demo_candidates.json`
- Test: `tests/test_pipeline.py`

**Steps:** Persist checkpoints; enforce evidence threshold; render Markdown/JSON/HTML; implement scheduled/manual/offline commands; run an offline end-to-end test; commit `feat: add review-ready draft pipeline`.

### Task 5: GitHub automation and documentation

**Files:**
- Create: `.github/workflows/generate-insight-draft.yml`
- Create: `.env.example`
- Create: `README.md`
- Create: `docs/operations.md`

**Steps:** Add fortnightly and manual triggers; install project; run pipeline; upload outputs; create a draft PR when enabled; document secrets and repository settings; commit `ci: automate insight draft generation`.

### Task 6: Verification

**Files:**
- Modify only if tests reveal defects.

**Steps:** Run unit tests with `unittest`; run offline demo; inspect generated Markdown, JSON and HTML; validate workflow YAML structurally; confirm secret scanning patterns; record results in README; commit `test: verify offline insight workflow`.

