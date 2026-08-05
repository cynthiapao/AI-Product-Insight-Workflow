from __future__ import annotations

import html
import json
from pathlib import Path

from .models import ArticleDraft


SOURCE_GROUP_ORDER = ("manual", "official", "memory", "community", "other")
SOURCE_GROUP_LABELS = {
    "manual": "个人体验与项目记录",
    "official": "官方介绍",
    "memory": "记忆功能说明",
    "community": "第三方资料",
    "other": "其他资料",
}


def _source_group(title: str, url: str, source_type: str) -> str:
    searchable = f"{title} {url}".casefold()
    if source_type == "manual":
        return "manual"
    if any(keyword in searchable for keyword in ("memory", "记忆")):
        return "memory"
    if source_type == "official":
        return "official"
    if source_type in {"community", "third_party"}:
        return "community"
    return "other"


def _source_lines(article: ArticleDraft) -> str:
    groups: dict[str, list[str]] = {name: [] for name in SOURCE_GROUP_ORDER}
    for item in article.sources:
        group = _source_group(item.title, str(item.url), item.source_type)
        groups[group].append(f"[{item.title}]({item.url})")
    return "\n".join(
        f"- {SOURCE_GROUP_LABELS[group]}：{'、'.join(groups[group])}"
        for group in SOURCE_GROUP_ORDER
        if groups[group]
    )


def render_markdown(article: ArticleDraft) -> str:
    methods = "\n\n".join(
        f"### {index}. {item.name}\n\n{item.principle}\n\n**适用场景：** {item.applies_when}"
        for index, item in enumerate(article.transferable_methods, 1)
    )
    tags = " / ".join(article.tags)
    product_takeaway = (
        f"\n\n## 产品启示\n\n{article.product_takeaway}"
        if article.product_takeaway
        else ""
    )
    return f"""---
title: "{article.title}"
slug: "{article.slug}"
summary: "{article.summary}"
read_minutes: {article.read_minutes}
tags: "{tags}"
review_status: "{article.review_status}"
generated_at: "{article.generated_at.isoformat()}"
---

# {article.title}

> {article.summary}

## 一句话看懂

{article.opening}

## 核心体验

{article.core_experience}

## 为什么有效

{article.why_it_works}

## 问题与边界

{article.boundaries}

## 我的判断

{article.personal_judgment}

## 可迁移的方法

{methods}{product_takeaway}

## 信息来源

{_source_lines(article)}

> 本文由自动化研究工作流生成初稿，发布前必须经过人工审核。
"""


def render_card(article: ArticleDraft, article_href: str | None = None) -> str:
    title = html.escape(article.title)
    summary = html.escape(article.summary)
    tags = html.escape(" / ".join(article.tags))
    body = f"""<article class="insight-item">
  <span class="read-time">{article.read_minutes} min read</span>
  <h3>{title}</h3>
  <p>{summary}</p>
  <div class="tag-line">{tags}</div>
</article>"""
    if article_href:
        return f'<a class="insight-link" href="{html.escape(article_href)}">\n{body}\n</a>'
    return body


def write_outputs(article: ArticleDraft, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{article.slug}.json"
    md_path = output_dir / f"{article.slug}.md"
    html_path = output_dir / f"{article.slug}.card.html"
    json_path.write_text(article.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(article), encoding="utf-8")
    html_path.write_text(render_card(article), encoding="utf-8")
    return [json_path, md_path, html_path]
