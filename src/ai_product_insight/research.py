from __future__ import annotations

import base64
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import escape, unescape
from html.parser import HTMLParser
from urllib.parse import quote_plus, urljoin, urlsplit

from .models import EvidenceItem, ProductCandidate, canonicalize_url
from .sources import FetchError, FetchedPage, HttpFetcher, classify_source_type, is_safe_public_url


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
CONTEXT_STOP_WORDS = STOP_WORDS | {
    "from", "into", "that", "this", "your", "our", "its", "you", "of", "to", "in", "on",
    "is", "it", "by", "as", "at", "be", "are", "was", "can", "not", "only", "new", "more",
    "than", "all", "how", "what", "get", "use", "using", "built", "build", "product", "link",
    "discussion", "http", "https", "www", "com", "show", "hn", "first", "best", "now",
}
FETCH_ERRORS = (FetchError, OSError, ValueError, ET.ParseError)
MIN_COMMENT_CHARS = 60
MIN_REPORT_CHARS = 300


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
    if not is_safe_public_url(candidate_url) or not is_safe_public_url(related_url):
        return False
    candidate_host = (urlsplit(candidate_url).hostname or "").lower().removeprefix("www.")
    related_host = (urlsplit(related_url).hostname or "").lower().removeprefix("www.")
    if not candidate_host or not related_host:
        return False
    # Shared hosts are not a single product. Scope GitHub/HF by owner + repo,
    # GitHub Pages by project, and other hosted sites by exact hostname.
    if candidate_host in {"github.com", "huggingface.co"} or related_host in {"github.com", "huggingface.co"}:
        left = urlsplit(candidate_url).path.strip("/").split("/")[:2]
        right = urlsplit(related_url).path.strip("/").split("/")[:2]
        return candidate_host == related_host and len(left) == 2 and left == right
    shared_hosts = ("github.io", "framer.website", "vercel.app", "netlify.app", "pages.dev")
    if any(candidate_host == host or related_host == host or candidate_host.endswith(f".{host}")
           or related_host.endswith(f".{host}") for host in shared_hosts):
        if candidate_host != related_host:
            return False
        if candidate_host.endswith(".github.io"):
            return urlsplit(candidate_url).path.strip("/").split("/")[0] == urlsplit(related_url).path.strip("/").split("/")[0]
        return True
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


def _name_mentioned(name: str, text: str) -> bool:
    name = re.sub(r"^show hn:\s*", "", name, flags=re.I)
    return bool(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I))


def _context_tokens(text: str) -> set[str]:
    # Strip links, not just HTML tags: RSS URLs must not become identity signals.
    text = re.sub(r"<a\b[^>]*>.*?</a>", " ", text, flags=re.I | re.S)
    text = re.sub(r"https?://\S+", " ", _plain_text(text))
    tokens = set(re.findall(r"[a-z][a-z0-9-]{2,}|[\u4e00-\u9fff]{2,}", text.casefold()))
    return {token.rstrip("s") if token.endswith("s") and len(token) > 4 else token
            for token in tokens if token not in CONTEXT_STOP_WORDS}


def _purpose_matches(candidate: ProductCandidate, text: str) -> bool:
    context = _context_tokens(candidate.summary) - _context_tokens(candidate.name)
    return bool(context) and len(context & _context_tokens(text)) >= min(2, len(context))


def _hit_matches_candidate(candidate: ProductCandidate, hit: dict[str, object], official_url: str | None = None) -> bool:
    target = str(hit.get("url") or "")
    if official_url:
        # Once an identity is verified, do not switch brands on name similarity.
        return bool(target) and _same_product_site(official_url, target)
    text = f"{hit.get('title') or hit.get('story_title') or ''} {_plain_text(str(hit.get('story_text') or ''))}"
    # A matching token alone (Maritime / Starlink Maritime) is insufficient.
    return _name_mentioned(candidate.name, text) and _purpose_matches(candidate, text)


def _fetch_page(fetcher: HttpFetcher, url: str) -> FetchedPage:
    return fetcher.fetch_page(url)


def _product_page(fetcher: HttpFetcher, url: str) -> FetchedPage:
    parts = urlsplit(url)
    path = parts.path.strip("/").split("/")
    if parts.hostname == "github.com" and len(path) == 2:
        # The repository README is more useful than GitHub's navigation chrome.
        try:
            readme = fetcher.fetch_json(f"https://api.github.com/repos/{path[0]}/{path[1]}/readme")
            if isinstance(readme, dict) and readme.get("encoding") == "base64":
                text = base64.b64decode(readme.get("content", "")).decode("utf-8", errors="replace")
                if text.strip():
                    return FetchedPage(url, f"<title>{escape(path[1])}</title><p>{escape(text)}</p>")
        except FETCH_ERRORS:
            pass
    return _fetch_page(fetcher, url)


def _search_hackernews(candidate: ProductCandidate, fetcher: HttpFetcher) -> list[dict[str, object]]:
    query = quote_plus(f'"{candidate.name}"')
    search_url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage=5"
    payload = fetcher.fetch_json(search_url)
    hits = payload.get("hits", []) if isinstance(payload, dict) else []
    return [hit for hit in hits[:5] if isinstance(hit, dict)] if isinstance(hits, list) else []


def _is_listing(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return host == "producthunt.com" or host.endswith(".producthunt.com")


def _official_destination(url: str) -> bool:
    if not is_safe_public_url(url):
        return False
    host = (urlsplit(url).hostname or "").lower()
    if classify_source_type(url) != "official":
        return False
    # A news article / search result / discussion is not a product-owned page.
    if host in {"news.google.com", "hn.algolia.com"}:
        return False
    path = urlsplit(url).path.casefold()
    return not any(term in path for term in ("/newsroom/", "/news/", "/articles/", "/blog/"))


def _page_links_to(page: FetchedPage, target: str) -> bool:
    links = [urljoin(page.url, href) for _, href in _parse_page(page.text).links]
    # README bodies preserve Markdown as text, including their official links.
    links.extend(re.findall(r"https?://[^\s<>\"')\]]+", unescape(page.text)))
    return any(is_safe_public_url(link) and _same_product_site(target, link) for link in links)


def _verified_linked_pages(candidate: ProductCandidate, page: FetchedPage, hits: list[dict[str, object]],
                           fetcher: HttpFetcher, errors: list[str]) -> list[FetchedPage]:
    """Accept website/repository aliases only with reciprocal links and identity checks."""
    verified: list[FetchedPage] = []
    attempted: set[str] = set()
    for hit in hits:
        target = str(hit.get("url") or "")
        if (not _official_destination(target) or target in attempted
                or _same_product_site(page.url, target) or not _page_links_to(page, target)):
            continue
        attempted.add(target)
        if len(attempted) > 2:
            break
        try:
            linked = _product_page(fetcher, target)
            content = _plain_text(linked.text)
            if (_official_destination(linked.url) and _name_mentioned(candidate.name, content)
                    and _purpose_matches(candidate, content) and _page_links_to(linked, page.url)):
                verified.append(linked)
            else:
                errors.append(f"unverified website/repository alias ignored: {target}")
        except FETCH_ERRORS as exc:
            errors.append(f"linked official page fetch failed: {exc}")
    return verified


def _resolve_product_page(candidate: ProductCandidate, fetcher: HttpFetcher,
                          hits: list[dict[str, object]], errors: list[str]) -> FetchedPage | None:
    original = str(candidate.url)
    if not _is_listing(original):
        try:
            return _product_page(fetcher, original)
        except FETCH_ERRORS as exc:
            errors.append(f"primary product page fetch failed: {exc}")
            return None

    options: list[str] = []
    # The RSS description contains an explicit Link, even when the listing is 403.
    for anchor, href in _parse_page(candidate.summary).links:
        url = urljoin(original, href)
        if anchor.strip().casefold() in {"link", "visit", "website", "visit website"} and is_safe_public_url(url):
            options.append(url)
    # Prefer a product website over a code repository for user-facing workflow evidence.
    ordered_hits = sorted(hits, key=lambda hit: str(hit.get("url") or "").startswith("https://github.com/"))
    for hit in ordered_hits:
        if not _hit_matches_candidate(candidate, hit):
            errors.append(f"identity mismatch: ignored HN result {hit.get('objectID', '')}")
            continue
        url = str(hit.get("url") or "")
        if _official_destination(url):
            options.append(url)

    seen: set[str] = set()
    for url in list(dict.fromkeys(options))[:4]:
        if url in seen:
            continue
        seen.add(url)
        try:
            page = _product_page(fetcher, url)
            if page.url != url and urlsplit(page.url).hostname == "github.com":
                page = _product_page(fetcher, page.url)
            content = _plain_text(page.text)
            if not _official_destination(page.url):
                errors.append("outbound link did not resolve to a product-owned page")
                continue
            if not _name_mentioned(candidate.name, content) or not _purpose_matches(candidate, content):
                errors.append(f"identity not corroborated on destination: {page.url}")
                continue
            # Keep evidence URL as the verified destination, not the blocked listing.
            return page
        except FETCH_ERRORS as exc:
            errors.append(f"official destination fetch failed ({url}): {exc}")
    errors.append("official URL unresolved: discovery listing is not official evidence")
    return None


def _fetch_hackernews_evidence(candidate: ProductCandidate, fetcher: HttpFetcher,
                              hits: list[dict[str, object]], official_url: str | None,
                              errors: list[str], aliases: list[str] | None = None) -> EvidenceItem | None:
    for hit in hits:
        if not any(_hit_matches_candidate(candidate, hit, url) for url in [official_url, *(aliases or [])]):
            continue
        object_id = str(hit.get("objectID") or "")
        if not object_id.isdigit():
            continue
        try:
            details = fetcher.fetch_json(f"https://hn.algolia.com/api/v1/items/{object_id}")
        except FETCH_ERRORS as exc:
            errors.append(f"HN discussion {object_id} fetch failed: {exc}")
            continue
        if not isinstance(details, dict):
            continue
        author = details.get("author") or hit.get("author")
        queue = list(details.get("children") or [])
        comments: list[str] = []
        examined = 0
        while queue and examined < 30 and len(comments) < 5:
            child = queue.pop(0)
            examined += 1
            if not isinstance(child, dict):
                continue
            queue.extend(child.get("children") or [])
            text = _plain_text(str(child.get("text") or ""))
            if (author and child.get("author") and child["author"] != author
                    and not child.get("dead") and not child.get("deleted") and len(text) >= MIN_COMMENT_CHARS):
                comments.append(text)
        if not comments:
            errors.append(f"HN discussion {object_id}: no substantive non-author comments; metadata is not evidence")
            continue
        excerpt = "\n".join(comments)[:5000]
        return EvidenceItem(
            title=str(hit.get("title") or f"Hacker News discussion: {candidate.name}")[:240],
            url=f"https://news.ycombinator.com/item?id={object_id}",
            excerpt=excerpt,
            source_type="community",
        )
    return None


def _fetch_news_evidence(candidate: ProductCandidate, fetcher: HttpFetcher,
                         official_url: str | None, errors: list[str]) -> EvidenceItem | None:
    query = quote_plus(f'"{candidate.name}"')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    root = ET.fromstring(fetcher.fetch_text(url))
    for item in list(root.iter("item"))[:3]:
        title = " ".join((item.findtext("title") or "").split())
        link = (item.findtext("link") or "").strip()
        description = _plain_text(item.findtext("description") or "")
        hit = {"title": title, "url": link, "story_text": description}
        if not title or not link or not is_safe_public_url(link) or not _hit_matches_candidate(candidate, hit):
            continue
        try:
            page = _fetch_page(fetcher, link)
        except FETCH_ERRORS as exc:
            errors.append(f"news article fetch failed: {exc}")
            continue
        body = _plain_text(page.text)
        host = urlsplit(page.url).hostname
        links = _parse_page(page.text).links
        links_to_product = bool(official_url) and any(
            _same_product_site(official_url, urljoin(page.url, href)) for _, href in links
        )
        if (host == "news.google.com" or len(body) < MIN_REPORT_CHARS
                or (official_url and _same_product_site(official_url, page.url))
                or not links_to_product
                or not _name_mentioned(candidate.name, body) or not _purpose_matches(candidate, body)):
            errors.append("news headline/redirect or uncorroborated text is not independent article evidence")
            continue
        return EvidenceItem(title=title[:240], url=page.url, excerpt=body[:5000], source_type="report")
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
    hits: list[dict[str, object]] = []
    try:
        hits = _search_hackernews(candidate, fetcher)
    except FETCH_ERRORS as exc:
        errors.append(f"Hacker News research failed: {exc}")

    page = _resolve_product_page(candidate, fetcher, hits, errors)
    official_url: str | None = None
    if page:
        primary_parser = _parse_page(page.text)
        official_url = page.url if classify_source_type(page.url) in OFFICIAL_SOURCE_TYPES else None
        primary = _evidence_from_html(
            candidate.name,
            page.url,
            page.text,
            classify_source_type(page.url),
        )
        if primary:
            items.append(primary)
        else:
            errors.append("primary product page contained too little readable text")
    independent: EvidenceItem | None = None
    linked_pages = _verified_linked_pages(candidate, page, hits, fetcher, errors) if page and official_url else []
    try:
        independent = _fetch_hackernews_evidence(candidate, fetcher, hits, official_url, errors,
                                                [linked.url for linked in linked_pages])
    except FETCH_ERRORS as exc:
        errors.append(f"Hacker News research failed: {exc}")
    if independent is None:
        try:
            independent = _fetch_news_evidence(candidate, fetcher, official_url, errors)
        except FETCH_ERRORS as exc:
            errors.append(f"news research failed: {exc}")
    if independent is not None:
        items.append(independent)

    for linked in linked_pages:
        linked_evidence = _evidence_from_html(candidate.name, linked.url, linked.text, "official")
        if linked_evidence:
            items.append(linked_evidence)

    if primary_parser is not None and official_url:
        for related_url in _rank_official_links(primary_parser, official_url)[:2]:
            try:
                related_page = _fetch_page(fetcher, related_url)
                if not _same_product_site(official_url, related_page.url):
                    errors.append(f"related page redirected outside product site: {related_url}")
                    continue
                evidence = _evidence_from_html(
                    candidate.name,
                    related_page.url,
                    related_page.text,
                    _source_type_for_official_link(related_url),
                )
                if evidence:
                    items.append(evidence)
            except FETCH_ERRORS as exc:
                errors.append(f"official related page fetch failed ({related_url}): {exc}")

    if candidate.summary:
        discovery_type = "manual" if candidate.manual else "feed"
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


