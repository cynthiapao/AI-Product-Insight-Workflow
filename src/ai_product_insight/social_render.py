from __future__ import annotations

import json
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .models import CarouselSlide, ComparisonRow, SocialBundle


INK = "#071127"
MUTED = "#53657D"
BLUE = "#155EEF"
PALE_BLUE = "#EAF2FF"
BACKGROUND = "#F7FAFF"
WHITE = "#FFFFFF"
LINE = "#C9D8F1"


class MissingAssetsError(ValueError):
    pass


def load_bundle(path: Path) -> SocialBundle:
    return SocialBundle.model_validate(json.loads(path.read_text(encoding="utf-8")))


def validate_assets(bundle: SocialBundle, assets_dir: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    missing: list[str] = []
    for requirement in bundle.screenshots:
        path = assets_dir / requirement.filename
        if not path.is_file():
            if requirement.required:
                missing.append(requirement.filename)
            continue
        try:
            with Image.open(path) as image:
                image.verify()
        except (OSError, SyntaxError) as exc:
            raise MissingAssetsError(f"无法读取截图 {requirement.filename}: {exc}") from exc
        found[requirement.screenshot_id] = path
    if missing:
        raise MissingAssetsError("缺少必需截图：" + "、".join(missing))
    return found


def _font_candidates() -> list[Path]:
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    return [
        windows / "msyh.ttc",
        windows / "msyhbd.ttc",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]


def find_font_path(explicit: Path | None = None) -> Path:
    candidates = ([explicit] if explicit else []) + _font_candidates()
    for path in candidates:
        if path is not None and path.is_file():
            return path
    raise RuntimeError("找不到可用字体；GitHub Actions 请安装 fonts-noto-cjk，本地可通过 --font 指定字体。")


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:['’.-][A-Za-z0-9]+)*\s*|.", text)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for token in _tokens(paragraph):
            candidate = current + token
            if current and draw.textlength(candidate, font=font) > width:
                if re.fullmatch(r"[，。！？；：、,.!?;:）】》”’]+", token.strip()):
                    current += token
                else:
                    lines.append(current.rstrip())
                    current = token.lstrip()
            else:
                current = candidate
        if current:
            lines.append(current.rstrip())
    return lines


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
    width: int,
    spacing: int = 14,
    max_lines: int | None = None,
) -> int:
    lines = _wrap(draw, text, font, width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip("。.!?？！，,") + "…"
    line_height = font.size + spacing
    x, y = xy
    for index, line in enumerate(lines):
        draw.text((x, y + index * line_height), line, font=font, fill=fill)
    return y + len(lines) * line_height


def _paste_contained(canvas: Image.Image, source_path: Path, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    target_size = (right - left, bottom - top)
    with Image.open(source_path) as source:
        source = source.convert("RGB")
        fitted = ImageOps.contain(source, target_size, Image.Resampling.LANCZOS)
    x = left + (target_size[0] - fitted.width) // 2
    y = top + (target_size[1] - fitted.height) // 2
    canvas.paste(fitted, (x, y))


def _footer(draw: ImageDraw.ImageDraw, font_path: Path, index: str, width: int, height: int) -> None:
    draw.text((70, height - 80), "AI INSIGHTS", font=_font(font_path, 25), fill=BLUE)
    marker_width = draw.textlength(index, font=_font(font_path, 24))
    draw.text((width - 70 - marker_width, height - 80), index, font=_font(font_path, 24), fill=MUTED)


def _draw_comparison_table(
    draw: ImageDraw.ImageDraw,
    rows: list[ComparisonRow],
    box: tuple[int, int, int, int],
    font_path: Path,
    *,
    headers: tuple[str, str, str],
    font_size: int,
) -> None:
    left, top, right, bottom = box
    widths = [int((right - left) * 0.22), int((right - left) * 0.39)]
    widths.append((right - left) - sum(widths))
    header_h = 76
    row_h = (bottom - top - header_h) // max(len(rows), 1)
    x_positions = [left, left + widths[0], left + widths[0] + widths[1], right]
    draw.rounded_rectangle(box, radius=20, fill=WHITE, outline=LINE, width=2)
    draw.rounded_rectangle((left, top, right, top + header_h), radius=20, fill=PALE_BLUE)
    draw.rectangle((left, top + header_h - 20, right, top + header_h), fill=PALE_BLUE)
    for x in x_positions[1:-1]:
        draw.line((x, top, x, bottom), fill=LINE, width=2)
    for index, header in enumerate(headers):
        _draw_wrapped(draw, (x_positions[index] + 16, top + 19), header, _font(font_path, font_size), INK, widths[index] - 30, spacing=7, max_lines=2)
    for row_index, row in enumerate(rows):
        y = top + header_h + row_index * row_h
        if row_index:
            draw.line((left, y, right, y), fill=LINE, width=2)
        values = (row.label, row.strength, row.gap)
        for col, value in enumerate(values):
            color = INK if col == 0 else MUTED
            size = font_size if col else font_size + 1
            _draw_wrapped(draw, (x_positions[col] + 16, y + 18), value, _font(font_path, size), color, widths[col] - 30, spacing=8, max_lines=4)


def render_x_card(bundle: SocialBundle, assets: dict[str, Path], output_path: Path, font_path: Path) -> None:
    canvas = Image.new("RGB", (1600, 900), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((44, 44, 1556, 856), radius=36, fill=WHITE, outline=LINE, width=2)
    draw.text((92, 86), "AI INSIGHTS", font=_font(font_path, 28), fill=BLUE)
    _draw_wrapped(draw, (92, 160), bundle.x_post.headline, _font(font_path, 58), INK, 500, spacing=14, max_lines=4)
    caption = bundle.x_post.visual_caption or bundle.key_takeaway
    _draw_wrapped(draw, (92, 500), caption, _font(font_path, 29), MUTED, 500, spacing=13, max_lines=5)

    screenshot = next((assets[item.screenshot_id] for item in bundle.screenshots if "x" in item.used_for and item.screenshot_id in assets), None)
    draw.rounded_rectangle((660, 100, 1500, 800), radius=28, fill=PALE_BLUE, outline=LINE, width=2)
    if bundle.x_post.comparison_rows:
        _draw_comparison_table(
            draw,
            bundle.x_post.comparison_rows,
            (692, 150, 1468, 750),
            font_path,
            headers=("Product", "Most useful move", "Still missing"),
            font_size=21,
        )
    elif screenshot:
        _paste_contained(canvas, screenshot, (692, 132, 1468, 768))
    else:
        _draw_wrapped(draw, (730, 370), "Screenshot optional", _font(font_path, 38), MUTED, 700, max_lines=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", optimize=True)


def render_xhs_slide(
    bundle: SocialBundle,
    slide: CarouselSlide,
    assets: dict[str, Path],
    output_path: Path,
    font_path: Path,
    total: int,
) -> None:
    canvas = Image.new("RGB", (1080, 1440), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((42, 42, 1038, 1398), radius=42, fill=WHITE, outline=LINE, width=2)
    draw.rounded_rectangle((70, 72, 245, 128), radius=28, fill=PALE_BLUE)
    draw.text((98, 84), "AI 洞察", font=_font(font_path, 25), fill=BLUE)

    if slide.kind == "cover":
        draw.ellipse((760, 130, 960, 330), fill=PALE_BLUE)
        draw.ellipse((830, 220, 1000, 390), outline=BLUE, width=4)
        y = _draw_wrapped(draw, (90, 390), slide.title, _font(font_path, 76), INK, 820, spacing=22, max_lines=5)
        _draw_wrapped(draw, (90, y + 48), slide.body or bundle.key_takeaway, _font(font_path, 34), MUTED, 820, spacing=16, max_lines=6)
    elif slide.kind == "screenshot" and slide.screenshot_id in assets:
        _draw_wrapped(draw, (80, 170), slide.title, _font(font_path, 52), INK, 900, spacing=16, max_lines=3)
        draw.rounded_rectangle((72, 320, 1008, 1025), radius=28, fill=PALE_BLUE, outline=LINE, width=2)
        _paste_contained(canvas, assets[slide.screenshot_id], (98, 346, 982, 999))
        _draw_wrapped(draw, (85, 1070), slide.body, _font(font_path, 29), MUTED, 900, spacing=13, max_lines=6)
    elif slide.kind == "comparison" and slide.comparison_rows:
        draw.text((84, 190), f"0{slide.order}", font=_font(font_path, 42), fill=BLUE)
        _draw_wrapped(draw, (84, 290), slide.title, _font(font_path, 60), INK, 850, spacing=18, max_lines=3)
        _draw_comparison_table(
            draw,
            slide.comparison_rows,
            (74, 500, 1006, 1165),
            font_path,
            headers=("产品", "最有价值的动作", "仍然缺少什么"),
            font_size=25,
        )
        _draw_wrapped(draw, (84, 1205), slide.body, _font(font_path, 28), MUTED, 850, spacing=12, max_lines=3)
    else:
        accent = "结论" if slide.kind == "closing" else f"0{slide.order}"
        draw.text((84, 220), accent, font=_font(font_path, 42), fill=BLUE)
        y = _draw_wrapped(draw, (84, 360), slide.title, _font(font_path, 68), INK, 850, spacing=20, max_lines=5)
        _draw_wrapped(draw, (84, y + 54), slide.body or bundle.key_takeaway, _font(font_path, 34), MUTED, 850, spacing=16, max_lines=13)

    _footer(draw, font_path, f"{slide.order:02d}/{total:02d}", 1080, 1440)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", optimize=True)


def render_social_assets(
    bundle_path: Path,
    assets_dir: Path,
    output_dir: Path,
    font: Path | None = None,
) -> list[Path]:
    bundle = load_bundle(bundle_path)
    assets = validate_assets(bundle, assets_dir)
    font_path = find_font_path(font)
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = [output_dir / "x-card.png"]
    render_x_card(bundle, assets, outputs[0], font_path)
    slides = sorted(bundle.carousel, key=lambda item: item.order)
    for slide in slides:
        path = output_dir / f"xhs-{slide.order:02d}.png"
        render_xhs_slide(bundle, slide, assets, path, font_path, len(slides))
        outputs.append(path)
    return outputs
