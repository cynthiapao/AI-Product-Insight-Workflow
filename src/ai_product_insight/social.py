from __future__ import annotations

from html import escape
import json
from pathlib import Path

from .models import ComparisonRow, SocialBundle, x_preflight_length


SOCIAL_CARDS_CSS = """:root {
  --blue: #1e3a8a;
  --accent: #2563eb;
  --text: #334155;
  --muted: #64748b;
  --pale: #ebf3ff;
  --panel: #f8fafc;
  --line: #e2e8f0;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; padding: 40px; color: var(--text); background: #f1f5f9; }
.gallery { display: grid; gap: 32px; justify-content: center; }
.social-card { position: relative; overflow: hidden; background: #fff; border: 1px solid var(--line); border-radius: 32px; box-shadow: 0 18px 50px rgba(30, 58, 138, .08); }
.x-summary-card { width: min(1600px, 96vw); aspect-ratio: 16 / 9; padding: 6%; display: grid; grid-template-columns: 36% 1fr; gap: 5%; }
.xhs-card { width: min(1080px, 92vw); aspect-ratio: 3 / 4; padding: 7%; }
.tag { display: inline-flex; padding: 12px 24px; border-radius: 999px; color: var(--accent); background: var(--pale); font-weight: 700; }
h1, h2, h3 { color: var(--blue); margin: 0; line-height: 1.12; }
h1 { margin-top: 8%; font-size: clamp(38px, 5vw, 82px); }
h2 { margin: 5% 0 4%; font-size: clamp(34px, 4.4vw, 64px); }
h3 { font-size: clamp(20px, 2.2vw, 32px); }
p { line-height: 1.7; }
.caption, .body-panel, .visual-panel, .comparison-card { background: var(--panel); border: 1px solid var(--line); border-radius: 22px; }
.caption { align-self: end; padding: 28px; font-size: clamp(18px, 2vw, 30px); }
.visual-panel { padding: 24px; display: grid; gap: 16px; align-content: center; }
.comparison-list { display: grid; gap: 16px; }
.comparison-card { padding: 22px; }
.comparison-block { margin-top: 12px; padding: 13px 16px; border-radius: 14px; background: var(--pale); }
.comparison-block.missing { background: #f1f5f9; }
.comparison-block strong { color: var(--blue); }
.body-panel { padding: 28px; font-size: clamp(18px, 2vw, 30px); }
.body-panel p { margin: 0 0 16px; }
.body-panel p:last-child { margin-bottom: 0; }
.screenshot { width: 100%; max-height: 54%; object-fit: contain; border-radius: 20px; background: var(--pale); }
.closing { background: #0f172a; }
.closing h2, .closing .tag { color: #bfdbfe; }
.closing .tag { background: rgba(37, 99, 235, .2); }
.closing .body-panel { color: #fff; background: rgba(255,255,255,.08); border-color: rgba(255,255,255,.16); }
.footer { position: absolute; left: 7%; right: 7%; bottom: 4%; display: flex; justify-content: space-between; color: var(--accent); }
.rings { position: absolute; width: 240px; height: 240px; right: -70px; bottom: -85px; border: 4px solid #bfdbfe; border-radius: 50%; opacity: .8; }
.rings::after { content: ""; position: absolute; width: 180px; height: 180px; left: -60px; top: 45px; border: 4px solid #bfdbfe; border-radius: 50%; }
@media (max-width: 800px) { body { padding: 16px; } .x-summary-card { grid-template-columns: 1fr; aspect-ratio: auto; min-height: 90vw; } }
"""


def _paragraphs(text: str) -> str:
    cleaned = text.replace("**", "").strip()
    return "".join(f"<p>{escape(part.strip())}</p>" for part in cleaned.split("\n\n") if part.strip())


def _comparison_cards(rows: list[ComparisonRow]) -> str:
    return "".join(
        "<article class=\"comparison-card\">"
        f"<h3>{escape(row.label)}</h3>"
        f"<div class=\"comparison-block\"><strong>最有价值的动作：</strong>{escape(row.strength)}</div>"
        f"<div class=\"comparison-block missing\"><strong>仍然缺少什么：</strong>{escape(row.gap)}</div>"
        "</article>"
        for row in rows
    )


def render_social_cards_html(bundle: SocialBundle) -> str:
    screenshots = {item.screenshot_id: item for item in bundle.screenshots}
    x_rows = _comparison_cards(bundle.x_post.comparison_rows)
    x_visual = f'<div class="comparison-list">{x_rows}</div>' if x_rows else f'<div class="body-panel">{_paragraphs(bundle.key_takeaway)}</div>'
    cards = [
        '<section class="social-card x-summary-card">'
        '<div><span class="tag">AI INSIGHTS</span>'
        f'<h1>{escape(bundle.x_post.headline)}</h1>'
        f'<div class="caption">{escape(bundle.x_post.visual_caption or bundle.key_takeaway)}</div></div>'
        f'<div class="visual-panel">{x_visual}</div>'
        '</section>'
    ]
    slides = sorted(bundle.carousel, key=lambda item: item.order)
    for slide in slides:
        classes = "social-card xhs-card" + (" closing" if slide.kind == "closing" else "")
        content = [f'<section class="{classes}">', '<span class="tag">AI 洞察</span>', f'<h2>{escape(slide.title)}</h2>']
        if slide.kind == "comparison" and slide.comparison_rows:
            content.append(f'<div class="comparison-list">{_comparison_cards(slide.comparison_rows)}</div>')
        elif slide.kind == "screenshot" and slide.screenshot_id in screenshots:
            shot = screenshots[slide.screenshot_id]
            src = f"../../../inputs/assets/{bundle.article_slug}/{shot.filename}"
            content.append(f'<img class="screenshot" src="{escape(src)}" alt="{escape(shot.purpose)}">')
            content.append(f'<div class="body-panel">{_paragraphs(slide.body)}</div>')
        else:
            content.append(f'<div class="body-panel">{_paragraphs(slide.body or bundle.key_takeaway)}</div>')
        content.append('<div class="rings"></div>')
        content.append(f'<footer class="footer"><span>AI INSIGHTS</span><span>{slide.order:02d}/{len(slides):02d}</span></footer>')
        content.append('</section>')
        cards.append("".join(content))
    return "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Social card review</title><link rel=\"stylesheet\" href=\"social-cards.css\"></head><body><main class=\"gallery\">" + "".join(cards) + "</main></body></html>\n"


def render_x_markdown(bundle: SocialBundle) -> str:
    relationship_lines: list[str] = []
    if bundle.x_post.official_mentions:
        relationship_lines.append("## 官方账号核验")
        for mention in bundle.x_post.official_mentions:
            status = "文章来源已支持" if mention.verification_status == "verified_from_evidence" else "发布前人工核验"
            relationship_lines.append(
                f"- [ ] {mention.product_name}：[{mention.handle}]({mention.profile_url})（{status}）"
            )
    if bundle.x_post.unresolved_product_mentions:
        relationship_lines.append("## 待补充官方账号")
        relationship_lines.extend(f"- [ ] {name}" for name in bundle.x_post.unresolved_product_mentions)

    if bundle.x_post.thread:
        screenshots = {item.screenshot_id: item for item in bundle.screenshots}
        parts = ["# X thread draft", "按顺序连续回复上一条；只复制代码框内的文字。配图和 Alt text 分别上传/填写。字符数为保守预检，发布前以 X 编辑器为准。"]
        total = len(bundle.x_post.thread)
        for index, post in enumerate(bundle.x_post.thread, 1):
            text = f"{index}/{total}\n{post.text}"
            parts.append(f"## {index}/{total}\n\n```text\n{text}\n```\n\n预检长度：{x_preflight_length(text)}/280")
            if post.image_kind == "cover":
                parts.append("配图：[16:9 总览卡片](rendered/x-card.png)")
            elif post.image_kind == "screenshot":
                shot = screenshots[post.screenshot_id]
                parts.append(f"配图：[{shot.filename}](../../../inputs/assets/{bundle.article_slug}/{shot.filename})")
            else:
                parts.append("配图：无需配图")
            if post.image_kind != "none":
                parts.append(f"Alt text: {post.alt_text}")
        return "\n\n".join([*parts, *relationship_lines]) + "\n"
    if bundle.social_standard == "v5" and bundle.x_post.format == "single":
        parts = [
            "# X single-post draft",
            "冷启动单推形态；复制代码框内文字，并上传 16:9 总结卡片。发布前以 X 编辑器字符数为准。",
            f"```text\n{bundle.x_post.text}\n```",
            f"预检长度：{x_preflight_length(bundle.x_post.text)}/280",
            "配图：[16:9 总览卡片](rendered/x-card.png)",
            f"Alt text: {bundle.x_post.alt_text}",
            *relationship_lines,
        ]
        return "\n\n".join(parts) + "\n"
    image_note = "建议配图" if bundle.x_post.image_recommended else "无需配图"
    return f"""# X draft

{bundle.x_post.text}

## Visual

- {image_note}
- Headline: {bundle.x_post.headline}
- Brief: {bundle.x_post.image_brief}
- Alt text: {bundle.x_post.alt_text}
"""


def render_xiaohongshu_markdown(bundle: SocialBundle) -> str:
    hashtags = " ".join(f"#{tag}" for tag in bundle.xiaohongshu.hashtags)
    slides = "\n".join(
        f"{slide.order}. [{slide.kind}] {slide.title}"
        + (f" — {slide.body}" if slide.body else "")
        + (f"（截图：{slide.screenshot_id}）" if slide.screenshot_id else "")
        for slide in sorted(bundle.carousel, key=lambda item: item.order)
    )
    return f"""# {bundle.xiaohongshu.title}

{bundle.xiaohongshu.body}

{hashtags}

## 轮播结构

{slides}
"""


def render_image_plan(bundle: SocialBundle) -> str:
    lines = [
        f'article_slug: {json.dumps(bundle.article_slug, ensure_ascii=False)}',
        "screenshots:",
    ]
    for item in bundle.screenshots:
        lines.extend(
            [
                f"  - screenshot_id: {json.dumps(item.screenshot_id, ensure_ascii=False)}",
                f"    filename: {json.dumps(item.filename, ensure_ascii=False)}",
                f"    required: {'true' if item.required else 'false'}",
                f"    source_kind: {json.dumps(item.source_kind, ensure_ascii=False)}",
                f"    purpose: {json.dumps(item.purpose, ensure_ascii=False)}",
                f"    capture: {json.dumps(item.capture, ensure_ascii=False)}",
                f"    annotation: {json.dumps(item.annotation, ensure_ascii=False)}",
                "    used_for:",
                *(f"      - {platform}" for platform in item.used_for),
            ]
        )
    return "\n".join(lines) + "\n"


def render_asset_readme(bundle: SocialBundle) -> str:
    checklist = "\n".join(
        f"- [{' ' if item.required else 'x'}] `{item.filename}`"
        f"{'（必需）' if item.required else '（可选）'}：{item.capture}"
        for item in bundle.screenshots
    )
    return f"""# 截图上传区：{bundle.article_slug}

请按下面的固定文件名上传真实截图。不要改名；上传前请隐藏账号、密钥、私人消息等敏感信息。

{checklist}

提交截图后，GitHub Actions 会自动校验文件，并把 X 配图和小红书轮播图写回当前 Draft PR。
"""


def render_pr_body(bundle: SocialBundle) -> str:
    checklist = "\n".join(
        f"- [ ] `{item.filename}`{'（可选）' if not item.required else ''}：{item.purpose}"
        for item in bundle.screenshots
    )
    mention_checklist = "\n".join(
        f"- [ ] 核验 {item.product_name} 官方账号：[{item.handle}]({item.profile_url})"
        for item in bundle.x_post.official_mentions
    )
    unresolved = "\n".join(f"- [ ] 补充 {name} 的官方 X Handle" for name in bundle.x_post.unresolved_product_mentions)
    relationship_review = "\n".join(item for item in (mention_checklist, unresolved) if item) or "- [x] 本文不涉及具体产品账号"
    return f"""自动化工作流已生成文章、X 和小红书草稿。请先核验事实、来源、个人判断和平台文案。

## X 关系链核验

{relationship_review}

## 人工截图节点

请将截图上传到：

`inputs/assets/{bundle.article_slug}/`

{checklist}

截图提交到当前草稿分支后，第二段工作流会自动生成社交配图，并继续更新这个 Draft PR。`social-cards.html` 和 `social-cards.css` 可直接在浏览器中预览和修改。合并 PR 不会自动发布内容。
"""


def write_social_outputs(bundle: SocialBundle, social_root: Path, assets_root: Path) -> list[Path]:
    output_dir = social_root / bundle.article_slug
    asset_dir = assets_root / bundle.article_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    asset_dir.mkdir(parents=True, exist_ok=True)

    files = {
        output_dir / "social.json": bundle.model_dump_json(indent=2),
        output_dir / "x-post.md": render_x_markdown(bundle),
        output_dir / "xiaohongshu.md": render_xiaohongshu_markdown(bundle),
        output_dir / "image-plan.yml": render_image_plan(bundle),
        output_dir / "pr-body.md": render_pr_body(bundle),
        output_dir / "social-cards.html": render_social_cards_html(bundle),
        output_dir / "social-cards.css": SOCIAL_CARDS_CSS,
        asset_dir / "README.md": render_asset_readme(bundle),
    }
    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
    return list(files)
