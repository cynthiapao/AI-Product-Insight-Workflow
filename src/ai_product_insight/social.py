from __future__ import annotations

import json
from pathlib import Path

from .models import SocialBundle


def render_x_markdown(bundle: SocialBundle) -> str:
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
    return f"""自动化工作流已生成文章、X 和小红书草稿。请先核验事实、来源、个人判断和平台文案。

## 人工截图节点

请将截图上传到：

`inputs/assets/{bundle.article_slug}/`

{checklist}

截图提交到当前草稿分支后，第二段工作流会自动生成社交配图，并继续更新这个 Draft PR。合并 PR 不会自动发布内容。
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
        asset_dir / "README.md": render_asset_readme(bundle),
    }
    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
    return list(files)
