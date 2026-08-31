from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote_plus, urljoin, urlsplit

from .models import EvidenceItem, ProductCandidate, canonicalize_url
from .sources import FetchError, HttpFetcher, classify_source_type, is_safe_public_url


OFFICIAL_SOURCE_TYPES = {"official", "release"}
INDEPENDENT_SOURCE_TYPES = {"community", "report"}
RESEARCH_LINK_TERMS = {
    "changelog": 0,
    "release": 0,
    "what's new": 0,
    "docs": 1,
    "documentation": 1,
    "how it works": 1,
    "features": 2,
    "research": 2,
    "blog": 3,
    "about": 4,
}
STOP_WORDS = {"ai", "the", "a", "an", "for", "and", "with", "app", "tool"}


@dataclass
class EvidenceCollection:
    items: list[EvidenceItem]
    errors: list[str]


class _ResearchPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.in_title = False
        self.title = ""
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.current_href: str | None = None
        self.current_anchor: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg", "noscript"}:
            self.skip_depth += 1
        if tag == "title":
            self.in_title = True
        if tag == "a" and not self.skip_depth:
            attributes = dict(attrs)
            self.current_href = attributes.get("href")
            self.current_anchor = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title":
            self.in_title = False
        if tag == "a" and self.current_href:
            self.links.append((" ".join(self.current_anchor), self.current_href))
            self.current_href = None
            self.current_anchor = []

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        value = " ".join(data.split())
        if not value:
            return
        if self.in_title:
            self.title += value
        elif self.current_href:
            self.current_anchor.append(value)
        if len(value) >= 20:
            self.parts.append(value)


def _plain_text(value: str) -> str:
    parser = _ResearchPageParser()
    parser.feed(unescape(value or ""))
    text = " ".join(parser.parts)
    if text:
        return text
    return " ".join(re.sub(r"<[^>]+>", " ", unescape(value or "")).split())


def _parse_page(html_text: str) -> _ResearchPageParser:
    parser = _ResearchPageParser()
    parser.feed(html_text)
    return parser


def _same_product_site(candidate_url: str, related_url: str) -> bool:
    candidate_host = (urlsplit(candidate_url).hostname or "").lower().removeprefix("www.")
    related_host = (urlsplit(related_url).hostname or "").lower().removeprefix("www.")
    if not candidate_host or not related_host:
        return False
    return (
        candidate_host == related_host
        or related_host.endswith(f".{candidate_host}")
        or candidate_host.endswith(f".{related_host}")
    )


def _source_type_for_official_link(url: str) -> str:
    path = urlsplit(url).path.casefold()
    return "release" if any(term in path for term in ("release", "changelog", "updates", "whats-new")) else "official"


def _rank_official_links(parser: _ResearchPageParser, base_url: str) -> list[str]:
    ranked: list[tuple[int, str]] = []
    seen: set[str] = set()
    for anchor, href in parser.links:
        absolute = urljoin(base_url, href)
        if not is_safe_public_url(absolute) or not _same_product_site(base_url, absolute):
            continue
        try:
            canonical = canonicalize_url(absolute)
        except ValueError:
            continue
        if canonical in seen or canonical == canonicalize_url(base_url):
            continue
        haystack = f"{anchor} {urlsplit(canonical).path}".casefold()
        scores = [score for term, score in RESEARCH_LINK_TERMS.items() if term in haystack]
        if not scores:
            continue
        seen.add(canonical)
        ranked.append((min(scores), canonical))
    ranked.sort(key=lambda item: (item[0], len(item[1])))
    return [url for _, url in ranked]


def _evidence_from_html(name: str, url: str, html_text: str, source_type: str) -> EvidenceItem | None:
    parser = _parse_page(html_text)
    excerpt = "\n".join(parser.parts)[:5000]
    if len(excerpt) < 20:
        return None
    return EvidenceItem(
        title=parser.title[:240] or name,
        url=url,
        excerpt=excerpt,
        source_type=source_type,
    )


def _candidate_tokens(name: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", name.casefold())
        if len(token) >= 2 and token not in STOP_WORDS
    }


def _hit_matches_candidate(candidate: ProductCandidate, hit: dict[str, object]) -> bool:
    title = str(hit.get("title") or hit.get("story_title") or "")
    if candidate.name.casefold() in title.casefold():
        return True
    candidate_host = (urlsplit(str(candidate.url)).hostname or "").lower().removeprefix("www.")
    hit_host = (urlsplit(str(hit.get("url") or "")).hostname or "").lower().removeprefix("www.")
    if candidate_host and hit_host and candidate_host == hit_host:
        return True
    tokens = _candidate_tokens(candidate.name)
    title_tokens = set(re.findall(r"[a-z0-9]+", title.casefold()))
    required = 1 if len(tokens) == 1 else max(2, (len(tokens) + 1) // 2)
    return bool(tokens) and len(tokens & title_tokens) >= required


def _fetch_hackernews_evidence(candidate: ProductCandidate, fetcher: HttpFetcher) -> EvidenceItem | None:
    query = quote_plus(f'"{candidate.name}"')
    search_url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage=5"
    payload = fetcher.fetch_json(search_url)
    hits = payload.get("hits", []) if isinstance(payload, dict) else []
    for hit in hits:
        if not isinstance(hit, dict) or not _hit_matches_candidate(candidate, hit):
            continue
        object_id = str(hit.get("objectID") or "")
        if not object_id.isdigit():
            continue
        parts = [_plain_text(str(hit.get("story_text") or ""))]
        try:
            details = fetcher.fetch_json(f"https://hn.algolia.com/api/v1/items/{object_id}")
        except (FetchError, OSError, ValueError, json.JSONDecodeError):
            details = {}
        children = details.get("children", []) if isinstance(details, dict) else []
        for child in children[:5]:
            if isinstance(child, dict):
                parts.append(_plain_text(str(child.get("text") or "")))
        excerpt = "\n".join(part for part in parts if part)[:5000]
        if len(excerpt) < 20:
            excerpt = (
                f"Hacker News discussion with {hit.get('points', 0)} points and "
                f"{hit.get('num_comments', 0)} comments about {candidate.name}."
            )
        return EvidenceItem(
            title=str(hit.get("title") or f"Hacker News discussion: {candidate.name}")[:240],
            url=f"https://news.ycombinator.com/item?id={object_id}",
            excerpt=excerpt,
            source_type="community",
        )
    return None


def _fetch_news_evidence(candidate: ProductCandidate, fetcher: HttpFetcher) -> EvidenceItem | None:
    query = quote_plus(f'"{candidate.name}"')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    root = ET.fromstring(fetcher.fetch_text(url))
    for item in root.iter("item"):
        title = " ".join((item.findtext("title") or "").split())
        link = (item.findtext("link") or "").strip()
        description = _plain_text(item.findtext("description") or "")
        hit = {"title": title, "url": link}
        if not title or not link or not is_safe_public_url(link) or not _hit_matches_candidate(candidate, hit):
            continue
        excerpt = f"{title}. {description}".strip()[:5000]
        if len(excerpt) < 20:
            continue
        return EvidenceItem(title=title[:240], url=link, excerpt=excerpt, source_type="report")
    return None


def _deduplicate_evidence(items: list[EvidenceItem], max_items: int) -> list[EvidenceItem]:
    unique: list[EvidenceItem] = []
    seen: set[str] = set()
    for item in items:
        canonical = canonicalize_url(str(item.url))
        if canonical in seen:
            continue
        seen.add(canonical)
        unique.append(item)
        if len(unique) >= max_items:
            break
    return unique


def collect_research_evidence(
    candidate: ProductCandidate,
    fetcher: HttpFetcher,
    max_items: int = 5,
) -> EvidenceCollection:
    items: list[EvidenceItem] = []
    errors: list[str] = []
    candidate_url = str(candidate.url)
    primary_parser: _ResearchPageParser | None = None

    try:
        primary_html = fetcher.fetch_text(candidate_url)
        primary_parser = _parse_page(primary_html)
        primary = _evidence_from_html(
            candidate.name,
            candidate_url,
            primary_html,
            classify_source_type(candidate_url),
        )
        if primary:
            items.append(primary)
        else:
            errors.append("primary product page contained too little readable text")
    except (FetchError, OSError, ValueError, ET.ParseError, json.JSONDecodeError) as exc:
        errors.append(f"primary product page fetch failed: {exc}")

    independent: EvidenceItem | None = None
    try:
        independent = _fetch_hackernews_evidence(candidate, fetcher)
    except (FetchError, OSError, ValueError, ET.ParseError, json.JSONDecodeError) as exc:
        errors.append(f"Hacker News research failed: {exc}")
    if independent is None:
        try:
            independent = _fetch_news_evidence(candidate, fetcher)
        except (FetchError, OSError, ValueError, ET.ParseError, json.JSONDecodeError) as exc:
            errors.append(f"news research failed: {exc}")
    if independent is not None:
        items.append(independent)

    if primary_parser is not None:
        for related_url in _rank_official_links(primary_parser, candidate_url)[:2]:
            try:
                related_html = fetcher.fetch_text(related_url)
                evidence = _evidence_from_html(
                    candidate.name,
                    related_url,
                    related_html,
                    _source_type_for_official_link(related_url),
                )
                if evidence:
                    items.append(evidence)
            except (FetchError, OSError, ValueError, ET.ParseError, json.JSONDecodeError) as exc:
                errors.append(f"official related page fetch failed ({related_url}): {exc}")

    if candidate.summary:
        discovery_type = "manual" if candidate.manual else (
            "community" if candidate.source == "Hacker News Show" else "feed"
        )
        items.append(
            EvidenceItem(
                title=f"{candidate.name} - discovery note",
                url=candidate.url,
                excerpt=candidate.summary,
                source_type=discovery_type,
            )
        )

    return EvidenceCollection(items=_deduplicate_evidence(items, max_items=max_items), errors=errors)


def has_required_evidence_mix(items: list[EvidenceItem]) -> bool:
    source_types = {item.source_type for item in items}
    return bool(source_types & OFFICIAL_SOURCE_TYPES) and bool(source_types & INDEPENDENT_SOURCE_TYPES)


def missing_evidence_requirements(items: list[EvidenceItem]) -> list[str]:
    source_types = {item.source_type for item in items}
    missing: list[str] = []
    if not source_types & OFFICIAL_SOURCE_TYPES:
        missing.append("missing official or release evidence")
    if not source_types & INDEPENDENT_SOURCE_TYPES:
        missing.append("missing independent community or report evidence")
    return missing


