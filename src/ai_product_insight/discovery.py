from __future__ import annotations

import re
from collections.abc import Iterable

from .config import WorkflowConfig
from .models import ProductCandidate, canonicalize_url
from .sources import FetchError, HttpFetcher, fetch_source


AI_TERMS = {
    "ai", "agent", "copilot", "llm", "model", "assistant", "automation",
    "生成式", "人工智能", "智能体", "工作流", "product", "tool", "app",
}


def heuristic_value(candidate: ProductCandidate) -> float:
    text = f"{candidate.name} {candidate.summary}".casefold()
    keyword_hits = sum(1 for term in AI_TERMS if term in text)
    source_bonus = 0.6 if candidate.source in {"Product Hunt", "Hacker News Show"} else 0.25
    manual_bonus = 2.0 if candidate.manual else 0.0
    return min(5.0, 1.2 + keyword_hits * 0.45 + source_bonus + manual_bonus)


def deduplicate(candidates: Iterable[ProductCandidate]) -> list[ProductCandidate]:
    by_url: dict[str, ProductCandidate] = {}
    by_title: set[str] = set()
    for candidate in candidates:
        url = canonicalize_url(str(candidate.url))
        title = re.sub(r"\W+", "", candidate.name.casefold())
        if url in by_url or title in by_title:
            continue
        by_url[url] = candidate
        by_title.add(title)
    return list(by_url.values())


class DiscoveryAgent:
    def __init__(self, config: WorkflowConfig, fetcher: HttpFetcher) -> None:
        self.config = config
        self.fetcher = fetcher

    def discover(self, manual: ProductCandidate | None = None) -> tuple[list[ProductCandidate], list[str]]:
        candidates: list[ProductCandidate] = [manual] if manual else []
        errors: list[str] = []
        for source in self.config.sources:
            if not source.enabled:
                continue
            try:
                candidates.extend(fetch_source(source, self.fetcher))
            except (FetchError, ValueError, OSError) as exc:
                errors.append(f"{source.name}: {exc}")
        unique = deduplicate(candidates)
        unique.sort(key=heuristic_value, reverse=True)
        return unique[: self.config.max_candidates], errors

