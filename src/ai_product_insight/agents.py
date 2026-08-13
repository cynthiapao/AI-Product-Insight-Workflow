from __future__ import annotations

import json
from dataclasses import dataclass

from .config import WorkflowConfig
from .editorial import EditorialContext
from .llm import JsonLLM
from .models import (
    ArticleContent,
    ArticleDraft,
    CandidateSelection,
    ClarificationPlan,
    ClarificationRound,
    ComparisonBrief,
    EvidenceItem,
    EvidenceQuality,
    ProductCandidate,
    ProductInsight,
    ResearchAnalysis,
    ResearchPack,
    SocialBundle,
)
from .prompts import (
    ANALYST_SYSTEM,
    CLARIFIER_SYSTEM,
    COMPARE_ANALYST_SYSTEM,
    COMPARE_EDITOR_SYSTEM,
    EDITOR_SYSTEM,
    RESEARCH_SYSTEM,
    SCOUT_SYSTEM,
    SOCIAL_SYSTEM,
)
from .sources import FetchError, HttpFetcher, fetch_evidence


SCORE_FIELDS = ("relevance", "novelty", "product_depth", "evidence", "total", "reason")
ARTICLE_TEXT_LIMITS = {
    "title": 80,
    "summary": 90,
    "opening": 500,
    "core_experience": 1000,
    "why_it_works": 1000,
    "boundaries": 800,
    "personal_judgment": 900,
    "product_takeaway": 300,
}


def _json(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False)


def _truncate_text(value: str, max_length: int) -> str:
    value = value.strip()
    if len(value) <= max_length:
        return value
    clipped = value[:max_length].rstrip()
    sentence_end = max(clipped.rfind(mark) for mark in ("。", "！", "？", ".", "!", "?")) + 1
    if sentence_end >= int(max_length * 0.6):
        return clipped[:sentence_end].rstrip()
    return clipped


def normalize_scout_response(raw: dict[str, object]) -> dict[str, object]:
    """Accept the two common score layouts while keeping strict downstream models.

    DeepSeek JSON mode guarantees valid JSON, but it does not guarantee that the
    generated object follows our nested Pydantic schema. In live runs it may put
    score fields beside ``candidate_id`` instead of inside ``score``.
    """
    normalized = dict(raw)
    normalized_assessments: list[dict[str, object]] = []
    assessments = raw.get("assessments", [])
    if not isinstance(assessments, list):
        return normalized

    for assessment in assessments:
        if not isinstance(assessment, dict):
            normalized_assessments.append(assessment)
            continue
        item = dict(assessment)
        score = item.get("score")
        if not isinstance(score, dict):
            score = {field: item.pop(field) for field in SCORE_FIELDS if field in item}
        else:
            score = dict(score)
        score.setdefault("reason", "模型未返回评分说明，已按各维度分数完成结构兼容。")
        item["score"] = score
        normalized_assessments.append(item)

    normalized["assessments"] = normalized_assessments
    return normalized


def normalize_research_response(raw: dict[str, object]) -> dict[str, object]:
    """Accept DeepSeek's observed alias for the evidence-quality field.

    The strict model intentionally keeps ``quality`` as the single downstream
    field name. Live model output has also used ``evidence_quality``; normalize
    that boundary variation before Pydantic validation.
    """
    normalized = dict(raw)
    evidence_quality = normalized.pop("evidence_quality", None)
    if "quality" not in normalized and evidence_quality is not None:
        normalized["quality"] = evidence_quality
    return normalized


def normalize_insight_response(raw: dict[str, object], max_patterns: int = 2) -> dict[str, object]:
    """Normalize the alternate insight layout observed in live DeepSeek output."""
    normalized = dict(raw)

    explanation = normalized.pop("explanation", None)
    judgment = normalized.pop("judgment", None)
    takeaways = normalized.pop("actionable_takeaways", None)

    if "one_line" not in normalized:
        summary_source = normalized.get("core_mechanism") or explanation
        if isinstance(summary_source, str):
            normalized["one_line"] = summary_source.strip()[:180].rstrip()
    if "why_it_works" not in normalized and isinstance(explanation, str):
        normalized["why_it_works"] = explanation
    if "personal_judgment" not in normalized and isinstance(judgment, str):
        normalized["personal_judgment"] = judgment

    limitations = normalized.get("limitations")
    if isinstance(limitations, str):
        normalized["limitations"] = [limitations]

    if "patterns" not in normalized and isinstance(takeaways, list):
        patterns: list[dict[str, str]] = []
        for index, takeaway in enumerate(takeaways[:max_patterns], start=1):
            if isinstance(takeaway, str):
                patterns.append(
                    {
                        "name": f"方法 {index}",
                        "principle": takeaway,
                        "applies_when": "适用于需要将这条方法迁移到相似产品设计中的场景。",
                    }
                )
            elif isinstance(takeaway, dict):
                patterns.append(dict(takeaway))
        normalized["patterns"] = patterns

    patterns = normalized.get("patterns")
    if isinstance(patterns, list):
        normalized["patterns"] = patterns[:max_patterns]

    return normalized


def normalize_editor_response(raw: dict[str, object]) -> dict[str, object]:
    """Keep variable-length editor lists within the published article schema."""
    normalized = dict(raw)

    for field, max_length in ARTICLE_TEXT_LIMITS.items():
        value = normalized.get(field)
        if isinstance(value, str):
            if field == "summary":
                value = " ".join(value.split())
            normalized[field] = _truncate_text(value, max_length)

    tags = normalized.get("tags")
    if isinstance(tags, str):
        normalized["tags"] = [tags]
    elif isinstance(tags, list):
        unique_tags: list[object] = []
        for tag in tags:
            if tag not in unique_tags:
                unique_tags.append(tag)
        normalized["tags"] = unique_tags[:4]

    methods = normalized.get("transferable_methods")
    if isinstance(methods, list):
        normalized_methods: list[object] = []
        for method in methods[:4]:
            if not isinstance(method, dict):
                normalized_methods.append(method)
                continue
            item = dict(method)
            for field, max_length in (("name", 80), ("principle", 500), ("applies_when", 300)):
                value = item.get(field)
                if isinstance(value, str):
                    item[field] = _truncate_text(value, max_length)
            normalized_methods.append(item)
        normalized["transferable_methods"] = normalized_methods

    return normalized


def normalize_clarification_response(raw: dict[str, object]) -> dict[str, object]:
    normalized = dict(raw)
    questions = normalized.get("questions")
    if isinstance(questions, str):
        normalized["questions"] = [questions]
    elif isinstance(questions, list):
        cleaned: list[str] = []
        for item in questions:
            if isinstance(item, str):
                question = item
            elif isinstance(item, dict):
                question = str(item.get("question", ""))
            else:
                continue
            question = question.strip()
            if question and question not in cleaned:
                cleaned.append(question)
        normalized["questions"] = cleaned[:3]
    return normalized


def normalize_social_response(raw: dict[str, object], article_slug: str) -> dict[str, object]:
    """Keep common model variation inside the strict social publishing contract."""
    normalized = dict(raw)
    normalized["article_slug"] = article_slug

    x_post = normalized.get("x_post")
    if isinstance(x_post, str):
        x_post = {
            "text": x_post,
            "headline": "One product insight",
            "image_recommended": True,
            "image_brief": "Use the primary real screenshot as evidence for the post.",
            "alt_text": "A real product screenshot related to the product insight.",
        }
    if isinstance(x_post, dict):
        x_item = dict(x_post)
        text = x_item.get("text")
        if isinstance(text, str) and len(text.strip()) > 280:
            clipped = text.strip()[:280]
            last_space = clipped.rfind(" ")
            x_item["text"] = clipped[:last_space].rstrip(" ,;:-") if last_space >= 220 else clipped.rstrip()
        normalized["x_post"] = x_item

    xiaohongshu = normalized.get("xiaohongshu")
    if isinstance(xiaohongshu, dict):
        xhs_item = dict(xiaohongshu)
        hashtags = xhs_item.get("hashtags")
        if isinstance(hashtags, str):
            xhs_item["hashtags"] = [item for item in hashtags.replace("#", " ").split() if item][:8]
        elif isinstance(hashtags, list):
            xhs_item["hashtags"] = hashtags[:8]
        normalized["xiaohongshu"] = xhs_item

    carousel = normalized.get("carousel")
    if isinstance(carousel, list):
        normalized["carousel"] = carousel[:8]
    screenshots = normalized.get("screenshots")
    if isinstance(screenshots, list):
        normalized_screenshots: list[object] = []
        for screenshot in screenshots[:6]:
            if not isinstance(screenshot, dict):
                normalized_screenshots.append(screenshot)
                continue
            item = dict(screenshot)
            used_for = item.get("used_for")
            if isinstance(used_for, str):
                used_for = [used_for]
            if isinstance(used_for, list):
                platforms: list[str] = []
                for platform in used_for:
                    # DeepSeek sometimes describes a Xiaohongshu carousel by
                    # its format rather than by the strict platform name.
                    normalized_platform = "xiaohongshu" if platform == "carousel" else platform
                    if normalized_platform in {"x", "xiaohongshu"} and normalized_platform not in platforms:
                        platforms.append(normalized_platform)
                item["used_for"] = platforms
            normalized_screenshots.append(item)
        normalized["screenshots"] = normalized_screenshots
    return normalized


class ScoutAgent:
    def __init__(self, llm: JsonLLM, config: WorkflowConfig) -> None:
        self.llm = llm
        self.config = config

    def select(self, candidates: list[ProductCandidate]) -> list[ProductCandidate]:
        if not candidates:
            return []
        payload = {
            "candidates": [item.model_dump(mode="json") for item in candidates[:10]],
            "max_selected": self.config.select_count,
        }
        raw_selection = self.llm.generate_json(SCOUT_SYSTEM, _json(payload))
        selection = CandidateSelection.model_validate(normalize_scout_response(raw_selection))
        scores = {item.candidate_id: item.score for item in selection.assessments}
        for candidate in candidates:
            if candidate.candidate_id in scores:
                candidate.score = scores[candidate.candidate_id]
        eligible = [
            item
            for item in candidates
            if item.score and item.score.total >= self.config.min_score
        ]
        eligible.sort(key=lambda item: item.score.total if item.score else 0, reverse=True)

        selected_order = {candidate_id: index for index, candidate_id in enumerate(selection.selected_ids)}
        primary = [item for item in eligible if item.candidate_id in selected_order]
        primary.sort(key=lambda item: selected_order[item.candidate_id])
        fallbacks = [item for item in eligible if item.candidate_id not in selected_order]
        return (primary + fallbacks)[: self.config.select_count]


class ResearchAgent:
    def __init__(self, llm: JsonLLM, fetcher: HttpFetcher, config: WorkflowConfig) -> None:
        self.llm = llm
        self.fetcher = fetcher
        self.config = config

    def research(
        self,
        candidate: ProductCandidate,
        seed_evidence: list[EvidenceItem] | None = None,
        min_evidence_items: int | None = None,
    ) -> ResearchPack:
        evidence = list(seed_evidence or [])
        if not evidence:
            if candidate.summary:
                evidence.append(
                    EvidenceItem(
                        title=f"{candidate.name} - discovery note",
                        url=candidate.url,
                        excerpt=candidate.summary,
                        source_type="manual" if candidate.manual else "feed",
                    )
                )
            try:
                evidence.append(fetch_evidence(candidate, self.fetcher))
            except FetchError:
                pass
        required_evidence = self.config.min_evidence_items if min_evidence_items is None else min_evidence_items
        if len(evidence) < required_evidence:
            return ResearchPack(candidate=candidate, evidence=evidence, quality=EvidenceQuality.insufficient)
        payload = {
            "candidate": candidate.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in evidence],
        }
        raw_analysis = self.llm.generate_json(RESEARCH_SYSTEM, _json(payload))
        analysis = ResearchAnalysis.model_validate(normalize_research_response(raw_analysis))
        return ResearchPack(candidate=candidate, evidence=evidence, **analysis.model_dump())


class InsightAgent:
    def __init__(self, llm: JsonLLM, editorial_context: EditorialContext | None = None) -> None:
        self.llm = llm
        self.editorial_context = editorial_context

    def analyze(self, research: ResearchPack) -> ProductInsight:
        system_prompt = ANALYST_SYSTEM
        if self.editorial_context:
            system_prompt += self.editorial_context.analyst_prompt_suffix()
        raw_insight = self.llm.generate_json(system_prompt, _json(research.model_dump(mode="json")))
        return ProductInsight.model_validate(normalize_insight_response(raw_insight, max_patterns=2))

    def clarifying_questions(self, brief: ComparisonBrief, research: list[ResearchPack]) -> ClarificationPlan:
        payload = {
            "topic": brief.title,
            "personal_notes": brief.notes,
            "products": [item.model_dump(mode="json") for item in research],
        }
        raw_plan = self.llm.generate_json(CLARIFIER_SYSTEM, _json(payload))
        return ClarificationPlan.model_validate(normalize_clarification_response(raw_plan))

    def compare(
        self,
        brief: ComparisonBrief,
        research: list[ResearchPack],
        clarification: ClarificationRound | None = None,
    ) -> ProductInsight:
        payload = {
            "topic": brief.title,
            "personal_notes": brief.notes,
            "comparison_subjects": [item.model_dump(mode="json") for item in brief.products],
            "products": [item.model_dump(mode="json") for item in research],
            "clarification": (clarification or ClarificationRound()).model_dump(mode="json"),
        }
        system_prompt = COMPARE_ANALYST_SYSTEM
        if self.editorial_context:
            system_prompt += self.editorial_context.analyst_prompt_suffix()
        raw_insight = self.llm.generate_json(system_prompt, _json(payload))
        return ProductInsight.model_validate(normalize_insight_response(raw_insight, max_patterns=4))


class EditorAgent:
    def __init__(self, llm: JsonLLM, editorial_context: EditorialContext | None = None) -> None:
        self.llm = llm
        self.editorial_context = editorial_context

    def draft(self, research: ResearchPack, insight: ProductInsight) -> ArticleDraft:
        payload = {
            "candidate": research.candidate.model_dump(mode="json"),
            "verified_facts": research.verified_facts,
            "open_questions": research.open_questions,
            "insight": insight.model_dump(mode="json"),
        }
        system_prompt = EDITOR_SYSTEM
        if self.editorial_context:
            system_prompt += self.editorial_context.editor_prompt_suffix()
        raw_content = self.llm.generate_json(system_prompt, _json(payload))
        content = ArticleContent.model_validate(normalize_editor_response(raw_content))
        return ArticleDraft(**content.model_dump(), sources=research.evidence, review_status="draft")

    def draft_comparison(
        self,
        brief: ComparisonBrief,
        research: list[ResearchPack],
        insight: ProductInsight,
        clarification: ClarificationRound | None = None,
    ) -> ArticleDraft:
        payload = {
            "topic": brief.title,
            "personal_notes": brief.notes,
            "comparison_subjects": [item.model_dump(mode="json") for item in brief.products],
            "products": [item.model_dump(mode="json") for item in research],
            "insight": insight.model_dump(mode="json"),
            "clarification": (clarification or ClarificationRound()).model_dump(mode="json"),
        }
        system_prompt = COMPARE_EDITOR_SYSTEM
        if self.editorial_context:
            system_prompt += self.editorial_context.editor_prompt_suffix()
        raw_content = self.llm.generate_json(system_prompt, _json(payload))
        content = ArticleContent.model_validate(normalize_editor_response(raw_content))
        sources: list[EvidenceItem] = []
        seen_urls: set[str] = set()
        for item in research:
            for source in item.evidence:
                url = str(source.url)
                if url not in seen_urls:
                    seen_urls.add(url)
                    sources.append(source)
        return ArticleDraft(**content.model_dump(), sources=sources, review_status="draft")


class SocialRepurposeAgent:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def draft(self, article: ArticleDraft) -> SocialBundle:
        payload = {
            "article": article.model_dump(mode="json"),
            "platform_requirements": {
                "x_language": "English",
                "x_max_characters": 280,
                "xiaohongshu_language": "Chinese",
                "visual_source": "real screenshots supplied by the author",
            },
        }
        raw_social = self.llm.generate_json(SOCIAL_SYSTEM, _json(payload))
        return SocialBundle.model_validate(normalize_social_response(raw_social, article.slug))


@dataclass
class AgentCrew:
    scout: ScoutAgent
    researcher: ResearchAgent
    analyst: InsightAgent
    editor: EditorAgent
    social: SocialRepurposeAgent | None = None
