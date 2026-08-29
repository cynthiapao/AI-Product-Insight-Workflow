from __future__ import annotations

import json
import ipaddress
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

from .config import SourceConfig
from .models import EvidenceItem, ProductCandidate


USER_AGENT = "AIProductInsightBot/0.1 (+human-reviewed portfolio research)"
DEFAULT_MAX_RESPONSE_BYTES = 2_000_000


class FetchError(RuntimeError):
    pass


def is_safe_public_url(url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return False
    hostname = parts.hostname.casefold().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


class HttpFetcher:
    def __init__(
        self,
        timeout: int = 25,
        retries: int = 2,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.max_response_bytes = max_response_bytes

    def fetch_bytes(self, url: str) -> bytes:
        if not is_safe_public_url(url):
            raise FetchError(f"Refusing non-public URL: {url}")
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
                with urlopen(request, timeout=self.timeout) as response:
                    body = response.read(self.max_response_bytes + 1)
                    if len(body) > self.max_response_bytes:
                        raise FetchError(f"Response exceeded {self.max_response_bytes} bytes: {url}")
                    return body
            except (HTTPError, URLError, TimeoutError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.4 * (attempt + 1))
        raise FetchError(f"Unable to fetch {url}: {last_error}")

    def fetch_text(self, url: str) -> str:
        return self.fetch_bytes(url).decode("utf-8", errors="replace")

    def fetch_json(self, url: str) -> Any:
        return json.loads(self.fetch_text(url))


def _text(node: ET.Element | None, names: tuple[str, ...]) -> str:
    if node is None:
        return ""
    for child in list(node):
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local in names and child.text:
            return " ".join(child.text.split())
    return ""


def _published(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None


def parse_feed(xml_text: str, source: SourceConfig) -> list[ProductCandidate]:
    root = ET.fromstring(xml_text)
    nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1].lower() in {"item", "entry"}]
    candidates: list[ProductCandidate] = []
    for node in nodes[: source.limit]:
        title = _text(node, ("title",))
        summary = unescape(_text(node, ("description", "summary", "content")))
        published = _text(node, ("pubdate", "published", "updated"))
        link = _text(node, ("link",))
        if not link:
            for child in list(node):
                if child.tag.rsplit("}", 1)[-1].lower() == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    break
        if title and link:
            candidates.append(
                ProductCandidate(
                    name=title,
                    url=link,
                    source=source.name,
                    summary=" ".join(summary.split())[:1200],
                    published_at=_published(published),
                )
            )
    return candidates


def fetch_hackernews(source: SourceConfig, fetcher: HttpFetcher) -> list[ProductCandidate]:
    ids = fetcher.fetch_json(str(source.url))[: source.limit]
    candidates: list[ProductCandidate] = []
    for item_id in ids:
        item = fetcher.fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
        if not item or not item.get("title") or not item.get("url"):
            continue
        candidates.append(
            ProductCandidate(
                name=item["title"],
                url=item["url"],
                source=source.name,
                summary=f"Hacker News discussion score: {item.get('score', 0)}",
                published_at=datetime.fromtimestamp(item["time"]) if item.get("time") else None,
            )
        )
    return candidates


def fetch_source(source: SourceConfig, fetcher: HttpFetcher) -> list[ProductCandidate]:
    if source.kind == "rss":
        return parse_feed(fetcher.fetch_text(str(source.url)), source)
    if source.kind == "hackernews":
        return fetch_hackernews(source, fetcher)
    raise ValueError(f"Unsupported source kind: {source.kind}")


class _ReadableHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.title = ""
        self.in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg", "noscript"}:
            self.skip_depth += 1
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        value = " ".join(data.split())
        if not value:
            return
        if self.in_title:
            self.title += value
        elif len(value) >= 20:
            self.parts.append(value)


def fetch_evidence(candidate: ProductCandidate, fetcher: HttpFetcher) -> EvidenceItem:
    parser = _ReadableHTML()
    parser.feed(fetcher.fetch_text(str(candidate.url)))
    excerpt = "\n".join(parser.parts)[:5000]
    if len(excerpt) < 20:
        excerpt = candidate.summary or f"Public page for {candidate.name}"
    return EvidenceItem(
        title=parser.title[:240] or candidate.name,
        url=candidate.url,
        excerpt=excerpt,
        source_type=classify_source_type(str(candidate.url)),
    )


def classify_source_type(url: str) -> str:
    hostname = (urlsplit(url).hostname or "").lower()
    community_hosts = ("wikipedia.org", "reddit.com", "news.ycombinator.com")
    if any(hostname == host or hostname.endswith(f".{host}") for host in community_hosts):
        return "community"
    return "official"
