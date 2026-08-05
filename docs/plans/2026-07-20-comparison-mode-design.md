# Multi-Product Comparison Mode Design

## Goal

Add a dedicated `compare` mode that turns one real project experience involving two to six products into a single human-reviewed comparison article, without changing the existing `manual` single-product behavior.

## Chosen interface

```powershell
.\.venv\Scripts\python.exe -m ai_product_insight compare `
  --name "用四个 AI 模型制作个人网站" `
  --product "Gemini" "https://example.com/gemini" `
  --product "Codex & ChatGPT" "https://example.com/openai" `
  --product "Claude" "https://example.com/claude" `
  --product "DeepSeek" "https://example.com/deepseek" `
  --notes-file "inputs\ai-model-comparison-notes.md"
```

Each `--product` supplies one product name and one primary official URL. The notes file contains the author's full first-person record and is kept separate from public evidence.

## Data flow

1. Parse the topic, repeated product pairs, and UTF-8 notes file into a `ComparisonBrief`.
2. Skip discovery and candidate scoring because the author explicitly selected every comparison subject.
3. Run the existing Research Agent once per product so every product has its own evidence and open questions.
4. Run one comparison analysis call across all usable research packs plus the personal notes.
5. Run one comparison editing call to produce the existing seven-section `ArticleDraft` schema.
6. Aggregate and de-duplicate sources, render the usual JSON, Markdown, and card, and retain `review_status="draft"`.

## Guardrails

- Require 2–6 products and at least 80 characters of notes.
- Treat notes as first-person experience, not proof of general product facts.
- Frame conclusions as observations from this project rather than universal model rankings.
- Continue when at least two products have usable evidence; mark the report partial if others fail.
- Produce no article when fewer than two products are researchable.

## Testing

- Validate the comparison brief constraints.
- Verify the analyst and editor receive all products, notes, and comparison-specific instructions.
- Verify the pipeline researches every product and produces one draft with de-duplicated sources.
- Verify the CLI accepts repeated `--product` arguments and loads a UTF-8 notes file.
- Run the complete regression suite to protect `manual`, `scheduled`, and `offline-demo`.
