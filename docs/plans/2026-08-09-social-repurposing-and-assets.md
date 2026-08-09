# Social Repurposing and Human Screenshot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate X and Xiaohongshu drafts plus a screenshot brief with every article, then render reviewed screenshots into platform-ready images on the same Draft PR branch.

**Architecture:** Add a downstream social repurposing agent that consumes the finished article rather than repeating research. The first GitHub workflow writes the social bundle, screenshot manifest, asset placeholder, and PR checklist. A second path-triggered workflow validates human-uploaded screenshots, renders branded PNGs, commits them to the same branch, and comments on the existing Draft PR.

**Tech Stack:** Python 3.11+, Pydantic 2, Pillow, GitHub Actions, GitHub CLI.

---

### Task 1: Define the social output contract

**Files:**
- Modify: `src/ai_product_insight/models.py`
- Test: `tests/test_social_models.py`

Add strict models for one English X post, a personal Chinese Xiaohongshu draft, carousel slides, screenshot requirements, and the complete social bundle. Enforce the 280-character X limit, safe screenshot filenames, bounded list sizes, and valid screenshot references.

### Task 2: Generate and serialize social drafts

**Files:**
- Modify: `src/ai_product_insight/prompts.py`
- Modify: `src/ai_product_insight/agents.py`
- Modify: `src/ai_product_insight/llm.py`
- Modify: `src/ai_product_insight/pipeline.py`
- Create: `src/ai_product_insight/social.py`
- Test: `tests/test_social_generation.py`

Add `SocialRepurposeAgent`, normalize common model variations, and write `social.json`, `x-post.md`, `xiaohongshu.md`, `image-plan.yml`, `pr-body.md`, and `inputs/assets/<slug>/README.md` after each article draft.

### Task 3: Validate screenshots and render branded visuals

**Files:**
- Create: `src/ai_product_insight/social_render.py`
- Modify: `src/ai_product_insight/cli.py`
- Modify: `pyproject.toml`
- Test: `tests/test_social_render.py`

Add a `render-social` command. Validate required filenames and image integrity, locate an available Chinese font, and render one 1600x900 X card plus 1080x1440 Xiaohongshu carousel PNGs in the existing blue-and-white visual language.

### Task 4: Split GitHub automation at the human screenshot checkpoint

**Files:**
- Modify: `.github/workflows/generate-insight-draft.yml`
- Create: `.github/workflows/render-social-assets.yml`
- Modify: `tests/test_workflow_file.py`

Include social and asset-placeholder files in the generated Draft PR. Trigger the renderer only when a person pushes files under `inputs/assets/**`, then commit rendered outputs back to the current branch and comment on its Draft PR. Do not publish automatically.

### Task 5: Document and verify the operator experience

**Files:**
- Modify: `README.md`
- Modify: `docs/operations.md`
- Modify: `.gitignore`

Document the screenshot checklist, GitHub web upload steps, automatic continuation, missing-file behavior, local render command, and output paths. Run all unit tests and the offline end-to-end demo.
