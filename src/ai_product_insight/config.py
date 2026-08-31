from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl


class SourceConfig(BaseModel):
    name: str
    kind: str
    url: HttpUrl
    enabled: bool = True
    limit: int = Field(default=10, ge=1, le=50)


class WorkflowConfig(BaseModel):
    sources: list[SourceConfig]
    max_candidates: int = Field(default=20, ge=1, le=100)
    select_count: int = Field(default=1, ge=1, le=3)
    research_candidate_limit: int = Field(default=8, ge=1, le=20)
    min_score: float = Field(default=3.1, ge=0, le=5)
    min_evidence_items: int = Field(default=1, ge=1, le=5)
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_fast_model: str = "deepseek-v4-flash"
    deepseek_quality_model: str = "deepseek-v4-pro"
    request_timeout_seconds: int = Field(default=25, ge=5, le=120)

    @classmethod
    def load(cls, path: Path) -> "WorkflowConfig":
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))

    @property
    def api_key(self) -> str | None:
        return os.getenv("DEEPSEEK_API_KEY")
