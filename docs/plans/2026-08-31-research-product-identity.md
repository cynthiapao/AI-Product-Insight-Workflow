# Research Product Identity Implementation Plan

**Goal:** Resolve real product sources from discovery links, reject namesakes and empty independent evidence, and verify the scheduled workflow with the August 31 failure cases.

**Architecture:** Keep the discovery URL and stable candidate ID. Resolve Product Hunt feed outbound links first; if blocked, use bounded HN search results as possible destinations, requiring both product-name and purpose overlap before fetching. A possible destination is not official evidence until its readable page corroborates the identity. Use the verified destination to match community discussions; never count author pitches, comment counts or RSS headlines as independent research.

**Tech Stack:** Python standard library, Pydantic, unittest, GitHub Actions. No new search keys or paid services.

## Scope and tradeoffs

- Approved by the user's request to continue the diagnosed fix. Implement in an isolated worktree; retain manual review and evidence thresholds.
- Prefer feed link resolution and existing HN endpoints over a new search provider. Leaving an ambiguous product unresearched is preferable to accepting a namesake.
- Do not bypass Product Hunt access restrictions. A 403 causes fallback to other public sources.
- This is a bounded heuristic identity check, not proof of site ownership. Unclear results remain insufficient.

## Task 1 — Regression cases first

Files: `tests/test_research_identity.py`, `tests/test_scout_response.py`, `tests/test_sources.py`.

1. Add fixtures for blocked Product Hunt pages with outbound links; an oMLX-like HN repository fallback; Maritime vs Starlink Maritime; a same-name different-purpose tool; author-only / zero-comment discussions; news headline-only results; cross-repository links on github.com.
2. Add tests that candidates after the first ten receive assessment, redirects to private URLs are rejected, and partial research diagnostics survive.
3. Run `python -m unittest discover -s tests` to demonstrate failing behavior before implementation.

## Task 2 — Source identity and evidence

Files: `src/ai_product_insight/research.py`, `sources.py`, `agents.py`.

1. Add a bounded page-fetch API returning final URL and validate redirect targets.
2. Resolve Product Hunt's RSS Link destination; verify product name and purpose on destination content. Fall back to matching HN outbound links when redirects are unavailable.
3. Separate discovery / publisher content from official content. Use verified URLs for related docs and HN identity matching, with repository / hosted-site scope preserved.
4. Require substantive non-author comments for community evidence. Fetch real independent article text for news; headlines are discovery clues only.
5. Assess the bounded configured candidate pool, not only the first ten. Retain the research-attempt cap and score threshold.
6. Preserve collection diagnostics without overwriting model-quality decisions.

## Task 3 — Verification and handoff

Files: `.github/workflows/generate-insight-draft.yml`, `.github/workflows/render-social-assets.yml`, `docs/development-log.md`, `docs/operations.md`.

1. Upgrade upload-artifact to the verified Node 24 version; keep zipped artifacts and review behavior.
2. Run the whole unittest suite and compileall with `PYTHONPATH=src`.
3. Replay real Aug 31 candidates through live research collection (no model calls); report identity and evidence failures honestly.
4. Commit scoped files and open a fix PR. Validate on the branch with the existing GitHub workflow if permitted, leaving merge and article approval to the user.
5. Do not claim cloud end-to-end success on unit-test results alone.
