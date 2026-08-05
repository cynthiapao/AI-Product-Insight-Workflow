from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonicalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("URL must use http or https")
    blocked = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref"}
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in blocked])
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CandidateScore(StrictModel):
    relevance: int = Field(ge=0, le=5)
    novelty: int = Field(ge=0, le=5)
    product_depth: int = Field(ge=0, le=5)
    evidence: int = Field(ge=0, le=5)
    total: float = Field(ge=0, le=5)
    reason: str = Field(min_length=10, max_length=300)

    @model_validator(mode="after")
    def total_matches_dimensions(self) -> "CandidateScore":
        expected = round(
            self.relevance * 0.35
            + self.novelty * 0.25
            + self.product_depth * 0.25
            + self.evidence * 0.15,
            2,
        )
        if abs(self.total - expected) > 0.02:
            self.total = expected
        return self


class ProductCandidate(StrictModel):
    candidate_id: str = ""
    name: str = Field(min_length=1, max_length=160)
    url: HttpUrl
    source: str = Field(min_length=1, max_length=80)
    summary: str = Field(default="", max_length=1200)
    published_at: datetime | None = None
    discovered_at: datetime = Field(default_factory=utc_now)
    manual: bool = False
    score: CandidateScore | None = None

    @field_validator("url", mode="before")
    @classmethod
    def normalize_url(cls, value: object) -> object:
        return canonicalize_url(str(value))

    @model_validator(mode="after")
    def populate_id(self) -> "ProductCandidate":
        if not self.candidate_id:
            raw = f"{self.name.casefold()}|{canonicalize_url(str(self.url))}"
            self.candidate_id = sha256(raw.encode("utf-8")).hexdigest()[:16]
        return self


class CandidateAssessment(StrictModel):
    candidate_id: str
    score: CandidateScore


class CandidateSelection(StrictModel):
    assessments: list[CandidateAssessment]
    selected_ids: list[str] = Field(min_length=1, max_length=3)


class EvidenceItem(StrictModel):
    title: str = Field(min_length=1, max_length=240)
    url: HttpUrl
    excerpt: str = Field(min_length=20, max_length=5000)
    source_type: Literal["official", "release", "report", "community", "feed", "manual"]
    retrieved_at: datetime = Field(default_factory=utc_now)


class EvidenceQuality(str, Enum):
    insufficient = "insufficient"
    usable = "usable"
    strong = "strong"


class ResearchPack(StrictModel):
    candidate: ProductCandidate
    evidence: list[EvidenceItem]
    verified_facts: list[str] = Field(default_factory=list, max_length=12)
    open_questions: list[str] = Field(default_factory=list, max_length=8)
    quality: EvidenceQuality


class ResearchAnalysis(StrictModel):
    verified_facts: list[str] = Field(default_factory=list, max_length=12)
    open_questions: list[str] = Field(default_factory=list, max_length=8)
    quality: EvidenceQuality


class DesignPattern(StrictModel):
    name: str = Field(min_length=2, max_length=80)
    principle: str = Field(min_length=20, max_length=500)
    applies_when: str = Field(min_length=10, max_length=300)


class ProductInsight(StrictModel):
    one_line: str = Field(min_length=20, max_length=180)
    core_mechanism: str = Field(min_length=40, max_length=800)
    why_it_works: str = Field(min_length=40, max_length=800)
    limitations: list[str] = Field(min_length=1, max_length=4)
    personal_judgment: str = Field(min_length=40, max_length=700)
    patterns: list[DesignPattern] = Field(min_length=1, max_length=4)


class ArticleDraft(StrictModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=8, max_length=80)
    summary: str = Field(
        min_length=20,
        max_length=90,
        description="用于首页产品洞察模块、产品洞察列表页及文章页导语的一行说明",
    )
    read_minutes: int = Field(default=5, ge=3, le=6)
    tags: list[str] = Field(min_length=1, max_length=4)
    opening: str = Field(min_length=40, max_length=500)
    core_experience: str = Field(min_length=80, max_length=1000)
    why_it_works: str = Field(min_length=80, max_length=1000)
    boundaries: str = Field(min_length=60, max_length=800)
    personal_judgment: str = Field(min_length=80, max_length=900)
    transferable_methods: list[DesignPattern] = Field(min_length=1, max_length=4)
    product_takeaway: str = Field(
        default="",
        max_length=300,
        description="面向 AI 产品经理的一段简洁产品启示",
    )
    sources: list[EvidenceItem] = Field(min_length=1)
    review_status: Literal["draft", "approved"] = "draft"
    generated_at: datetime = Field(default_factory=utc_now)


class ArticleContent(StrictModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=8, max_length=80)
    summary: str = Field(
        min_length=20,
        max_length=90,
        description="用于首页产品洞察模块、产品洞察列表页及文章页导语的一行说明",
    )
    read_minutes: int = Field(default=5, ge=3, le=6)
    tags: list[str] = Field(min_length=1, max_length=4)
    opening: str = Field(min_length=40, max_length=500)
    core_experience: str = Field(min_length=80, max_length=1000)
    why_it_works: str = Field(min_length=80, max_length=1000)
    boundaries: str = Field(min_length=60, max_length=800)
    personal_judgment: str = Field(min_length=80, max_length=900)
    transferable_methods: list[DesignPattern] = Field(min_length=1, max_length=4)
    product_takeaway: str = Field(
        default="",
        max_length=300,
        description="面向 AI 产品经理的一段简洁产品启示",
    )


class ClarificationPlan(StrictModel):
    questions: list[str] = Field(min_length=1, max_length=3)

    @field_validator("questions")
    @classmethod
    def clean_questions(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for question in value:
            question = question.strip()[:300]
            if question and question not in cleaned:
                cleaned.append(question)
        if not cleaned:
            raise ValueError("At least one clarification question is required")
        return cleaned[:3]


class ClarificationItem(StrictModel):
    question: str = Field(min_length=5, max_length=300)
    answer: str = Field(min_length=1, max_length=2000)


class ClarificationRound(StrictModel):
    items: list[ClarificationItem] = Field(default_factory=list, max_length=3)


class ComparisonBrief(StrictModel):
    title: str = Field(min_length=8, max_length=160)
    products: list[ProductCandidate] = Field(min_length=2, max_length=6)
    notes: str = Field(min_length=80, max_length=8000)

    @model_validator(mode="after")
    def product_names_are_unique(self) -> "ComparisonBrief":
        names = [item.name.casefold().strip() for item in self.products]
        if len(names) != len(set(names)):
            raise ValueError("Comparison product names must be unique")
        return self


class RunReport(StrictModel):
    run_id: str
    mode: Literal["scheduled", "manual", "compare", "offline-demo"]
    status: Literal["completed", "partial", "failed"]
    candidate_count: int = 0
    selected_count: int = 0
    outputs: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
