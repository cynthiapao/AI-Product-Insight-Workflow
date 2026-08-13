from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


REQUIRED_SECTION_NAMES = (
    "一句话看懂",
    "核心体验",
    "为什么有效",
    "问题与边界",
    "我的判断",
    "可迁移的方法",
    "信息来源",
)
DISPLAY_SECTION_NAMES = (
    "一句话看懂",
    "核心体验",
    "为什么有效",
    "问题与边界",
    "我的判断",
    "可迁移的方法",
    "产品启示",
    "信息来源",
)
SECTION_EYEBROWS = {
    "一句话看懂": "In One Line",
    "核心体验": "Experience",
    "为什么有效": "Mechanism",
    "问题与边界": "Boundaries",
    "我的判断": "My Take",
    "可迁移的方法": "Patterns",
    "产品启示": "Product Insight",
    "信息来源": "Sources",
}
AUTO_START = "<!-- AUTO-GENERATED-INSIGHTS:START -->"
AUTO_END = "<!-- AUTO-GENERATED-INSIGHTS:END -->"


@dataclass(frozen=True)
class MarkdownArticle:
    source_path: Path
    title: str
    slug: str
    summary: str
    read_minutes: int
    tags: list[str]
    review_status: str
    generated_at: str
    sections: dict[str, str]


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_article_markdown(path: Path) -> MarkdownArticle:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("Article must start with YAML-style frontmatter")
    try:
        frontmatter_text, body = text[4:].split("\n---\n", 1)
    except ValueError as exc:
        raise ValueError("Article frontmatter is not closed") from exc

    metadata: dict[str, str] = {}
    for line in frontmatter_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = _unquote(value)

    required_metadata = {"title", "slug", "summary", "read_minutes", "tags", "review_status"}
    missing = sorted(required_metadata - metadata.keys())
    if missing:
        raise ValueError(f"Missing article metadata: {', '.join(missing)}")

    sections: dict[str, str] = {}
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", body))
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[name] = body[match.end() : end].strip()
    missing_sections = [name for name in REQUIRED_SECTION_NAMES if name not in sections]
    if missing_sections:
        raise ValueError(f"Missing article sections: {', '.join(missing_sections)}")

    slug = metadata["slug"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("Article slug must contain lowercase English letters, numbers, and hyphens")
    tags = [item.strip() for item in metadata["tags"].split("/") if item.strip()]
    return MarkdownArticle(
        source_path=path,
        title=metadata["title"],
        slug=slug,
        summary=metadata["summary"],
        read_minutes=int(metadata["read_minutes"]),
        tags=tags,
        review_status=metadata["review_status"],
        generated_at=metadata.get("generated_at", ""),
        sections=sections,
    )


def _inline_markdown(value: str) -> str:
    escaped = html.escape(value, quote=True)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        lambda match: f'<a href="{match.group(2)}" target="_blank" rel="noreferrer">{match.group(1)}</a>',
        escaped,
    )
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def _render_markdown_fragment(value: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{_inline_markdown(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{_inline_markdown(item)}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    lines = value.splitlines()
    index = 0
    while index < len(lines):
        raw_line = lines[index]
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            flush_list()
        elif (
            line.startswith("|")
            and index + 1 < len(lines)
            and _is_markdown_table_separator(lines[index + 1])
        ):
            flush_paragraph()
            flush_list()
            headers = _markdown_table_cells(line)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(_markdown_table_cells(lines[index]))
                index += 1
            blocks.append(_render_markdown_table(headers, rows))
            continue
        elif line.startswith("### "):
            flush_paragraph()
            flush_list()
            blocks.append(f"<h3>{_inline_markdown(line[4:])}</h3>")
        elif line.startswith("- "):
            flush_paragraph()
            list_items.append(line[2:])
        elif line.startswith("> "):
            flush_paragraph()
            flush_list()
            blocks.append(f"<blockquote>{_inline_markdown(line[2:])}</blockquote>")
        else:
            flush_list()
            paragraph.append(line)
        index += 1
    flush_paragraph()
    flush_list()
    return "\n".join(blocks)


def _markdown_table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_markdown_table_separator(line: str) -> bool:
    cells = _markdown_table_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f'<th scope="col">{_inline_markdown(cell)}</th>' for cell in headers)
    body_rows: list[str] = []
    for row in rows:
        padded = (row + [""] * len(headers))[: len(headers)]
        first, *rest = padded
        cells = f'<th scope="row">{_inline_markdown(first)}</th>'
        cells += "".join(f"<td>{_inline_markdown(cell)}</td>" for cell in rest)
        body_rows.append(f"<tr>{cells}</tr>")
    body = "".join(body_rows)
    return (
        '<div class="insight-table-wrap" role="region" aria-label="文章内容对比表" tabindex="0">'
        f'<table class="insight-compare-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
        "</div>"
    )


INSIGHT_CSS = """
.insight-article-page .detail-hero { grid-template-columns: minmax(0, 1fr) 280px; }
.insight-article-page .main-title { white-space: normal; font-size: clamp(38px, 4.8vw, 64px); }
.insight-article-page .insight-meta { display: grid; gap: 14px; }
.insight-article-page .insight-meta div { padding-bottom: 12px; border-bottom: 1px solid var(--line); }
.insight-article-page .insight-meta div:last-child { padding-bottom: 0; border-bottom: 0; }
.insight-article-page .insight-meta dt { color: var(--text-muted); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; }
.insight-article-page .insight-meta dd { margin: 3px 0 0; color: var(--accent-deep); font-weight: 700; }
.insight-article-page .insight-prose { max-width: 780px; }
.insight-article-page .insight-section { padding: 58px 0; border-top: 1px solid var(--line); }
.insight-article-page .insight-section:first-child { border-top: 0; }
.insight-article-page .insight-section h2 { margin: 6px 0 24px; color: var(--accent-deep); font-family: "Noto Serif SC", "SimSun", Georgia, serif; font-size: clamp(28px, 3vw, 40px); line-height: 1.25; }
.insight-article-page .insight-section h3 { margin: 30px 0 10px; color: var(--accent-deep); font-size: 20px; }
.insight-article-page .insight-section p, .insight-article-page .insight-section li { color: #334155; font-size: 17px; line-height: 1.95; }
.insight-article-page .insight-section p { margin: 0 0 18px; }
.insight-article-page .insight-section ul { margin: 12px 0 20px; padding-left: 22px; }
.insight-article-page .insight-section a { color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }
.insight-article-page .insight-table-wrap { margin: 22px 0 26px; overflow-x: auto; border: 1px solid var(--line); border-radius: 16px; }
.insight-article-page .insight-compare-table { width: 100%; min-width: 680px; border-collapse: collapse; background: #fff; font-size: 14px; line-height: 1.65; }
.insight-article-page .insight-compare-table th, .insight-article-page .insight-compare-table td { padding: 14px 16px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
.insight-article-page .insight-compare-table thead th { color: var(--accent-deep); background: var(--accent-soft); font-weight: 850; }
.insight-article-page .insight-compare-table tbody th { color: var(--accent-deep); background: #f8fbff; font-weight: 800; }
.insight-article-page .insight-compare-table tr:last-child th, .insight-article-page .insight-compare-table tr:last-child td { border-bottom: 0; }
.insight-article-page blockquote { margin: 22px 0; padding: 18px 22px; color: var(--accent-deep); background: var(--accent-soft); border-left: 3px solid var(--accent); border-radius: 0 var(--radius) var(--radius) 0; font-weight: 700; }
.insight-article-page .insight-back { display: inline-flex; margin-top: 26px; color: var(--accent); font-weight: 800; }
@media (max-width: 760px) { .insight-article-page .detail-hero { grid-template-columns: 1fr; } .insight-article-page .insight-section { padding: 42px 0; } }
""".strip()


def _article_html(article: MarkdownArticle, preview_site_css: str | None = None) -> str:
    if preview_site_css:
        styles = f'<link rel="stylesheet" href="{html.escape(preview_site_css)}" />\n<style>{INSIGHT_CSS}</style>'
        home_href = ""
    else:
        styles = '<link rel="stylesheet" href="../style.css" />\n<link rel="stylesheet" href="insight.css" />'
        home_href = "../index.html"
    tags = " / ".join(article.tags)
    sections = "\n".join(
        f'''<section class="insight-section" id="section-{index}">
  <p class="eyebrow">{SECTION_EYEBROWS[name]}</p>
  <h2>{html.escape(name)}</h2>
  <div class="insight-section-body">{_render_markdown_fragment(article.sections[name])}</div>
</section>'''
        for index, name in enumerate(
            (name for name in DISPLAY_SECTION_NAMES if name in article.sections),
            1,
        )
    )
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="{html.escape(article.summary, quote=True)}" />
  <title>{html.escape(article.title)} | 鲍康昕</title>
  {styles}
</head>
<body class="detail-page insight-article-page">
  <header class="site-header">
    <a class="brand" href="{home_href}#hero" aria-label="返回首页"><span class="brand-mark">BX</span><span><strong>鲍康昕</strong><small>AI 产品经理</small></span></a>
    <div class="status-container"><span class="status-dot"></span><span class="status-text">持续更新ing...</span></div>
    <nav class="nav-links" aria-label="文章页导航"><a href="{home_href}#portfolio">项目经验</a><a href="{home_href}#insights">产品洞察</a><a class="resume-button" href="{home_href}">返回首页</a></nav>
  </header>
  <main>
    <section class="detail-hero section">
      <div class="detail-hero-copy"><div class="header-section"><span class="top-tag">AI INSIGHT</span><h1 class="main-title detail-title-compact">{html.escape(article.title)}</h1><div class="decorative-line"></div></div><p class="detail-lead">{html.escape(article.summary)}</p></div>
      <aside class="detail-summary-card"><dl class="insight-meta"><div><dt>阅读时间</dt><dd>{article.read_minutes} 分钟</dd></div><div><dt>主题</dt><dd>{html.escape(tags)}</dd></div><div><dt>内容状态</dt><dd>人工审核后发布</dd></div></dl></aside>
    </section>
    <div class="section insight-prose">{sections}<a class="insight-back" href="{home_href}#insights">← 返回产品洞察</a></div>
  </main>
</body>
</html>'''


def render_preview(article: MarkdownArticle, site_dir: Path, preview_dir: Path) -> Path:
    site_css = site_dir / "style.css"
    current_css = site_dir / "detail.css"
    if not site_css.is_file() and not current_css.is_file():
        raise FileNotFoundError(f"Portfolio stylesheet not found: {site_css} or {current_css}")
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_path = preview_dir / f"{article.slug}.preview.html"
    if current_css.is_file():
        content = _portfolio_article_html(article).replace("../detail.css", current_css.resolve().as_uri())
    else:
        content = _article_html(article, site_css.resolve().as_uri())
    preview_path.write_text(content, encoding="utf-8")
    return preview_path


def approve_markdown(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^review_status:\s*["\']?draft["\']?\s*$',
        'review_status: "approved"',
        text,
        count=1,
    )
    if count == 0 and not re.search(r'(?m)^review_status:\s*["\']?approved["\']?\s*$', text):
        raise ValueError("Article frontmatter does not contain review_status")
    path.write_text(updated, encoding="utf-8")
    json_path = path.with_suffix(".json")
    if json_path.is_file():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        data["review_status"] = "approved"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def approve_and_archive(path: Path, reviewed_dir: Path) -> list[Path]:
    """Mark a human-reviewed article approved and move its source files out of drafts."""
    approve_markdown(path)
    reviewed_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for source in (path, path.with_suffix(".json")):
        if not source.is_file():
            continue
        target = reviewed_dir / source.name
        if source.resolve() != target.resolve():
            shutil.move(str(source), str(target))
        outputs.append(target)
    return outputs


def _manifest_entry(article: MarkdownArticle) -> dict[str, object]:
    return {
        "slug": article.slug,
        "title": article.title,
        "summary": article.summary,
        "read_minutes": article.read_minutes,
        "tags": article.tags,
        "generated_at": article.generated_at,
    }


def _render_cards(entries: list[dict[str, object]]) -> str:
    cards = []
    for entry in entries:
        tags = " / ".join(str(tag) for tag in entry.get("tags", []))
        cards.append(
            f'''          <a class="insight-item" href="insights/{html.escape(str(entry["slug"]))}.html">
            <span class="read-time">{int(entry["read_minutes"])} min read</span>
            <h3>《{html.escape(str(entry["title"]))}》</h3>
            <p>{html.escape(str(entry["summary"]))}</p>
            <div class="tag-line">{html.escape(tags)}</div>
          </a>'''
        )
    return f"{AUTO_START}\n" + "\n\n".join(cards) + f"\n          {AUTO_END}"


def _update_homepage(index_path: Path, entries: list[dict[str, object]]) -> None:
    text = index_path.read_text(encoding="utf-8")
    block = _render_cards(entries)
    if AUTO_START in text and AUTO_END in text:
        pattern = re.compile(re.escape(AUTO_START) + r".*?" + re.escape(AUTO_END), re.DOTALL)
        text = pattern.sub(block, text, count=1)
    else:
        marker = '<div class="insight-list">'
        if marker not in text:
            raise ValueError("Could not find the homepage insight list")
        text = text.replace(marker, marker + "\n          " + block, 1)
    index_path.write_text(text, encoding="utf-8")


def _portfolio_date(article: MarkdownArticle) -> str:
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", article.generated_at)
    return ".".join(match.groups()) if match else "2026.08.13"


def _portfolio_header(prefix: str) -> str:
    return f'''<header class="site-header">
  <a class="brand" href="{prefix}index.html#hero" aria-label="返回首页"><span class="brand-mark">BX</span><span><strong>Kangxin Bao</strong><small>AI 产品经理</small></span></a>
  <div class="status-container" aria-label="当前动态"><span class="status-dot"></span><span class="status-text">持续更新ing...</span></div>
  <nav class="nav-links" aria-label="洞察页导航"><a href="{prefix}index.html#about">关于我</a><a href="{prefix}index.html#projects">项目经验</a><a href="{prefix}index.html#insights">产品洞察</a><a class="resume-button" href="{prefix}index.html#hero">返回首页</a></nav>
</header>'''


def _portfolio_article_html(article: MarkdownArticle) -> str:
    tags = "\n".join(f"<span>{html.escape(tag)}</span>" for tag in article.tags)
    body = "\n".join(
        f"<h2>{html.escape(name)}</h2>\n{_render_markdown_fragment(article.sections[name])}"
        for name in DISPLAY_SECTION_NAMES
        if name in article.sections
    )
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><meta name="description" content="{html.escape(article.summary, quote=True)}" /><title>{html.escape(article.title)} | Kangxin Bao</title><link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin /><link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" /><link rel="stylesheet" href="../detail.css" /><script src="https://unpkg.com/lucide@latest"></script></head>
<body class="detail-page insight-article-page">
{_portfolio_header('../')}
<main>
  <section class="section insight-article-hero"><a class="secondary-cta" href="../insights.html">← 返回产品洞察</a><p class="top-tag">AI INSIGHT</p><h1>{html.escape(article.title)}</h1><p class="detail-lead">{html.escape(article.summary)}</p><p class="article-meta-line">{_portfolio_date(article)} <span aria-hidden="true">·</span> {article.read_minutes} min read</p><div class="pill-row detail-pills article-tags">{tags}</div><p class="article-note">本文基于具体使用体验做产品观察，经人工审核后发布</p></section>
  <article class="section insight-article-body">{body}</article>
  <section class="section detail-section detail-next"><a class="secondary-cta" href="../index.html#insights">← 返回首页洞察</a><a class="primary-cta" href="../insights.html">查看全部产品洞察 <span aria-hidden="true">→</span></a></section>
</main>
<footer class="detail-copyright">© 2026 Kangxin Bao. All rights reserved.</footer><script src="../main.js"></script><script>if (window.lucide) {{ lucide.createIcons(); }}</script>
</body></html>'''


def _portfolio_home_card(article: MarkdownArticle) -> str:
    tag = html.escape(article.tags[0] if article.tags else "AI洞察")
    return f'''        <a class="insight-item" href="insights/{article.slug}.html">
          <div class="insight-main"><h3>{html.escape(article.title)}</h3><p>{html.escape(article.summary)}</p></div>
          <div class="insight-side"><span class="keyword-tag">{tag}</span><span class="read-time">{article.read_minutes} min read</span></div>
        </a>'''


def _portfolio_archive_card(article: MarkdownArticle) -> str:
    tag = html.escape(article.tags[0] if article.tags else "AI洞察")
    return f'''        <a class="insight-archive-card" href="insights/{article.slug}.html">
          <div><span class="keyword-tag">{tag}</span><h3>{html.escape(article.title)}</h3><p>{html.escape(article.summary)}</p></div>
          <span class="publish-date">{_portfolio_date(article)}</span>
        </a>'''


def _insert_after_marker(path: Path, marker: str, card: str, slug: str) -> None:
    text = path.read_text(encoding="utf-8")
    if f'{slug}.html' in text:
        return
    if marker not in text:
        raise ValueError(f"Could not find portfolio marker in {path.name}")
    path.write_text(text.replace(marker, marker + "\n" + card, 1), encoding="utf-8")


def _publish_to_portfolio(article: MarkdownArticle, site_dir: Path) -> list[Path]:
    article_path = site_dir / "insights" / f"{article.slug}.html"
    article_path.parent.mkdir(parents=True, exist_ok=True)
    article_path.write_text(_portfolio_article_html(article), encoding="utf-8")
    index_path = site_dir / "index.html"
    archive_path = site_dir / "insights.html"
    _insert_after_marker(index_path, "<!-- INSIGHTS_AUTO_START -->", _portfolio_home_card(article), article.slug)
    archive_text = archive_path.read_text(encoding="utf-8")
    archive_marker = '<section class="section insight-archive-list" aria-label="产品洞察文章列表">'
    if f'{article.slug}.html' not in archive_text:
        if archive_marker not in archive_text:
            raise ValueError("Could not find portfolio insight archive list")
        archive_path.write_text(archive_text.replace(archive_marker, archive_marker + "\n" + _portfolio_archive_card(article), 1), encoding="utf-8")
    return [article_path, index_path, archive_path]


def publish_to_site(article: MarkdownArticle, site_dir: Path) -> list[Path]:
    if article.review_status != "approved":
        raise ValueError("Article must be approved before publishing")
    index_path = site_dir / "index.html"
    if not index_path.is_file():
        raise FileNotFoundError(f"Portfolio index not found: {index_path}")
    if (site_dir / "detail.css").is_file() and (site_dir / "insights.html").is_file():
        return _publish_to_portfolio(article, site_dir)
    insights_dir = site_dir / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)
    article_path = insights_dir / f"{article.slug}.html"
    css_path = insights_dir / "insight.css"
    manifest_path = insights_dir / "index.json"

    entries: list[dict[str, object]] = []
    if manifest_path.is_file():
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(value, list):
            entries = [item for item in value if isinstance(item, dict)]
    entry = _manifest_entry(article)
    entries = [entry] + [item for item in entries if item.get("slug") != article.slug]

    article_path.write_text(_article_html(article), encoding="utf-8")
    css_path.write_text(INSIGHT_CSS + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    _update_homepage(index_path, entries)
    return [article_path, css_path, manifest_path, index_path]


def find_git_executable() -> Path | None:
    found = shutil.which("git")
    if found:
        return Path(found)
    candidates = [
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git" / "cmd" / "git.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Git" / "cmd" / "git.exe",
    ]
    desktop = Path(os.environ.get("LOCALAPPDATA", "")) / "GitHubDesktop"
    if desktop.is_dir():
        candidates.extend(sorted(desktop.glob("app-*/resources/app/git/cmd/git.exe"), reverse=True))
    return next((path for path in candidates if path.is_file()), None)


def git_commit_and_push(site_dir: Path, changed_paths: Sequence[Path], message: str) -> str:
    git = find_git_executable()
    if git is None:
        raise RuntimeError("Git executable was not found. Install Git or GitHub Desktop before automatic publishing.")
    relative = [str(path.resolve().relative_to(site_dir.resolve())) for path in changed_paths]

    def run(args: list[str]) -> str:
        result = subprocess.run(
            [str(git), "-C", str(site_dir), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout).strip())
        return result.stdout.strip()

    branch = run(["rev-parse", "--abbrev-ref", "HEAD"])
    run(["add", "--", *relative])
    status = run(["status", "--porcelain", "--", *relative])
    if not status:
        return "No site changes to commit"
    run(["commit", "--only", "-m", message, "--", *relative])
    return run(["push", "origin", branch]) or f"Pushed {branch}"
