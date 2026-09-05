from __future__ import annotations

import json
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .models import CarouselSlide, ComparisonRow, SocialBundle


INK = "#1E3A8A"
MUTED = "#334155"
SECONDARY = "#64748B"
BLUE = "#2563EB"
PALE_BLUE = "#EBF3FF"
BACKGROUND = "#FFFFFF"
WHITE = "#FFFFFF"
PANEL = "#F8FAFC"
LINE = "#E2E8F0"
RING = "#BFDBFE"
NO_LINE_START = frozenset("，。！？；：、）》】〕〉”’…,.!?;:%）】》")


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


def _font(path: Path, size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    if bold:
        bold_candidates = [
            path.with_name("msyhbd.ttc"),
            path.with_name("NotoSansCJK-Bold.ttc"),
            path.with_name("DejaVuSans-Bold.ttf"),
        ]
        path = next((candidate for candidate in bold_candidates if candidate.is_file()), path)
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
                stripped = token.lstrip()
                if stripped and stripped[0] in NO_LINE_START:
                    current = candidate
                else:
                    lines.append(current.rstrip())
                    current = stripped
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
    text = text.translate(str.maketrans({"“": '"', "”": '"'}))
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


def _paste_top_cropped(canvas: Image.Image, source_path: Path, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    target_size = (right - left, bottom - top)
    with Image.open(source_path) as source:
        source = source.convert("RGB")
        fitted = ImageOps.fit(source, target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.0))
    canvas.paste(fitted, (left, top))


def _is_portrait(source_path: Path) -> bool:
    with Image.open(source_path) as source:
        return source.width / max(source.height, 1) <= 0.85


def _draw_card_base(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (34, 38, width - 30, height - 24),
        radius=44,
        fill=(30, 58, 138, 18),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((24, 24, width - 24, height - 24), radius=44, fill=WHITE, outline=LINE, width=2)
    return canvas, draw


def _draw_pill(draw: ImageDraw.ImageDraw, font_path: Path, x: int = 70, y: int = 72) -> None:
    draw.rounded_rectangle((x, y, x + 175, y + 58), radius=29, fill=PALE_BLUE)
    draw.text((x + 27, y + 12), "AI 洞察", font=_font(font_path, 25, bold=True), fill=BLUE)


def _draw_module(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: str = PANEL,
    radius: int = 28,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=LINE, width=2)


def _footer(draw: ImageDraw.ImageDraw, font_path: Path, index: str, width: int, height: int) -> None:
    draw.ellipse((width - 245, height - 235, width + 55, height + 65), outline=RING, width=5)
    draw.ellipse((width - 185, height - 175, width + 85, height + 95), outline=RING, width=5)
    draw.arc((width - 315, height - 165, width + 10, height + 90), 190, 325, fill=RING, width=5)
    draw.text((70, height - 86), "AI INSIGHTS", font=_font(font_path, 25), fill=BLUE)
    marker_width = draw.textlength(index, font=_font(font_path, 24))
    draw.text((width - 70 - marker_width, height - 86), index, font=_font(font_path, 24), fill=SECONDARY)


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
    draw.rounded_rectangle(box, radius=24, fill=WHITE, outline=LINE, width=2)
    draw.rounded_rectangle((left, top, right, top + header_h), radius=20, fill=PALE_BLUE)
    draw.rectangle((left, top + header_h - 20, right, top + header_h), fill=PALE_BLUE)
    for x in x_positions[1:-1]:
        draw.line((x, top, x, bottom), fill=LINE, width=2)
    for index, header in enumerate(headers):
        _draw_wrapped(draw, (x_positions[index] + 16, top + 19), header, _font(font_path, font_size, bold=True), INK, widths[index] - 30, spacing=7, max_lines=2)
    for row_index, row in enumerate(rows):
        y = top + header_h + row_index * row_h
        if row_index:
            draw.line((left, y, right, y), fill=LINE, width=2)
        values = (row.label, row.strength, row.gap)
        for col, value in enumerate(values):
            color = INK if col == 0 else MUTED
            size = font_size if col else font_size + 1
            _draw_wrapped(draw, (x_positions[col] + 16, y + 18), value, _font(font_path, size, bold=col == 0), color, widths[col] - 30, spacing=8, max_lines=4)


def _draw_x_comparison_cards(
    draw: ImageDraw.ImageDraw,
    rows: list[ComparisonRow],
    box: tuple[int, int, int, int],
    font_path: Path,
) -> None:
    left, top, right, bottom = box
    gap = 24
    card_height = (bottom - top - gap * (len(rows) - 1)) // max(len(rows), 1)
    for index, row in enumerate(rows):
        y = top + index * (card_height + gap)
        card_bottom = y + card_height
        draw.rounded_rectangle((left, y, right, card_bottom), radius=24, fill=PANEL, outline=LINE, width=2)
        draw.text((left + 32, y + 22), row.label, font=_font(font_path, 31, bold=True), fill=INK)
        block_left, block_right = left + 32, right - 32
        for block_top, label, value, fill in (
            (y + 72, "Most useful move:", row.strength, PALE_BLUE),
            (y + 142, "Still missing:", row.gap, "#F1F5F9"),
        ):
            draw.rounded_rectangle((block_left, block_top, block_right, block_top + 56), radius=14, fill=fill)
            dot_color = BLUE if fill == PALE_BLUE else MUTED
            draw.ellipse((block_left + 18, block_top + 22, block_left + 28, block_top + 32), fill=dot_color)
            draw.text((block_left + 40, block_top + 13), label, font=_font(font_path, 18, bold=True), fill=INK)
            _draw_wrapped(
                draw,
                (block_left + 232, block_top + 10),
                value,
                _font(font_path, 21),
                MUTED,
                block_right - block_left - 248,
                spacing=5,
                max_lines=2,
            )


def _draw_xhs_comparison_cards(
    draw: ImageDraw.ImageDraw,
    rows: list[ComparisonRow],
    box: tuple[int, int, int, int],
    font_path: Path,
) -> None:
    left, top, right, bottom = box
    gap = 16
    card_height = (bottom - top - gap * (len(rows) - 1)) // max(len(rows), 1)
    for index, row in enumerate(rows):
        y = top + index * (card_height + gap)
        card_bottom = y + card_height
        _draw_module(draw, (left, y, right, card_bottom), fill=PANEL, radius=24)
        draw.text((left + 28, y + 20), row.label, font=_font(font_path, 28, bold=True), fill=INK)
        block_left, block_right = left + 28, right - 28
        block_top = y + 66
        block_height = max((card_height - 82) // 2, 50)
        for label, value, fill, dot_color in (
            ("最有价值的动作", row.strength, PALE_BLUE, BLUE),
            ("仍然缺少什么", row.gap, "#F1F5F9", MUTED),
        ):
            draw.rounded_rectangle(
                (block_left, block_top, block_right, block_top + block_height),
                radius=14,
                fill=fill,
            )
            draw.ellipse((block_left + 16, block_top + 19, block_left + 26, block_top + 29), fill=dot_color)
            draw.text(
                (block_left + 38, block_top + 12),
                label,
                font=_font(font_path, 20, bold=True),
                fill=INK,
            )
            _draw_wrapped(
                draw,
                (block_left + 222, block_top + 10),
                value,
                _font(font_path, 22),
                MUTED,
                block_right - block_left - 238,
                spacing=7,
                max_lines=2,
            )
            block_top += block_height + 8


def render_x_card(bundle: SocialBundle, assets: dict[str, Path], output_path: Path, font_path: Path) -> None:
    canvas, draw = _draw_card_base(1600, 900)
    draw.rounded_rectangle((80, 72, 270, 132), radius=30, fill=PALE_BLUE)
    draw.text((109, 85), "AI INSIGHTS", font=_font(font_path, 24), fill=BLUE)
    _draw_wrapped(draw, (84, 180), bundle.x_post.headline, _font(font_path, 58, bold=True), INK, 510, spacing=14, max_lines=4)
    caption = bundle.x_post.visual_caption or bundle.key_takeaway
    _draw_module(draw, (80, 505, 610, 790), fill=PANEL, radius=26)
    _draw_wrapped(draw, (112, 542), caption, _font(font_path, 29), MUTED, 465, spacing=13, max_lines=5)

    screenshot = next((assets[item.screenshot_id] for item in bundle.screenshots if "x" in item.used_for and item.screenshot_id in assets), None)
    if bundle.x_post.comparison_rows:
        _draw_x_comparison_cards(
            draw,
            bundle.x_post.comparison_rows,
            (660, 86, 1515, 814),
            font_path,
        )
    elif screenshot:
        _draw_module(draw, (660, 86, 1515, 814), fill=PALE_BLUE, radius=30)
        if _is_portrait(screenshot):
            _paste_top_cropped(canvas, screenshot, (692, 118, 1483, 782))
        else:
            _paste_contained(canvas, screenshot, (692, 118, 1483, 782))
    else:
        _draw_module(draw, (660, 86, 1515, 814), fill=PALE_BLUE, radius=30)
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
    canvas, draw = _draw_card_base(1080, 1440)
    _draw_pill(draw, font_path)

    if slide.kind == "cover":
        y = _draw_wrapped(draw, (78, 176), slide.title, _font(font_path, 70, bold=True), INK, 900, spacing=20, max_lines=4)
        y = _draw_wrapped(
            draw,
            (80, y + 26),
            slide.body or bundle.key_takeaway,
            _font(font_path, 31),
            MUTED,
            890,
            spacing=15,
            max_lines=5,
        )
        cover_asset = next(
            (
                assets[item.screenshot_id]
                for item in bundle.screenshots
                if "xiaohongshu" in item.used_for and item.screenshot_id in assets
            ),
            None,
        )
        module_top = max(y + 38, 610)
        module_bottom = 1195
        _draw_module(draw, (72, module_top, 1008, module_bottom), fill=PALE_BLUE, radius=30)
        if cover_asset:
            if _is_portrait(cover_asset):
                _paste_top_cropped(canvas, cover_asset, (100, module_top + 28, 980, module_bottom - 28))
            else:
                _paste_contained(canvas, cover_asset, (100, module_top + 28, 980, module_bottom - 28))
        else:
            _draw_wrapped(
                draw,
                (116, module_top + 88),
                bundle.key_takeaway,
                _font(font_path, 38),
                INK,
                820,
                spacing=18,
                max_lines=7,
            )
    elif slide.kind == "screenshot" and slide.screenshot_id in assets:
        title_end = _draw_wrapped(draw, (80, 174), slide.title, _font(font_path, 56, bold=True), INK, 900, spacing=17, max_lines=3)
        image_top = max(title_end + 36, 340)
        image_bottom = min(image_top + 620, 980)
        _draw_module(draw, (72, image_top, 1008, image_bottom), fill=PALE_BLUE, radius=30)
        screenshot = assets[slide.screenshot_id]
        image_box = (98, image_top + 26, 982, image_bottom - 26)
        if _is_portrait(screenshot):
            _paste_top_cropped(canvas, screenshot, image_box)
        else:
            _paste_contained(canvas, screenshot, image_box)
        body_top = image_bottom + 28
        _draw_module(draw, (72, body_top, 1008, 1265), fill=PANEL, radius=26)
        _draw_wrapped(draw, (104, body_top + 30), slide.body, _font(font_path, 29), MUTED, 840, spacing=14, max_lines=6)
    elif slide.kind == "comparison" and slide.comparison_rows:
        title_end = _draw_wrapped(draw, (80, 176), slide.title, _font(font_path, 58, bold=True), INK, 900, spacing=18, max_lines=3)
        cards_top = max(title_end + 34, 330)
        _draw_xhs_comparison_cards(
            draw,
            slide.comparison_rows,
            (72, cards_top, 1008, 1125),
            font_path,
        )
        _draw_wrapped(draw, (88, 1162), slide.body, _font(font_path, 27), MUTED, 840, spacing=12, max_lines=3)
    else:
        title_end = _draw_wrapped(draw, (80, 184), slide.title, _font(font_path, 66, bold=True), INK, 900, spacing=20, max_lines=4)
        module_top = max(title_end + 58, 470)
        if slide.kind == "closing":
            draw.rounded_rectangle((72, module_top, 1008, 1185), radius=30, fill=INK)
            _draw_wrapped(
                draw,
                (112, module_top + 58),
                slide.body or bundle.key_takeaway,
                _font(font_path, 36),
                WHITE,
                820,
                spacing=19,
                max_lines=11,
            )
        else:
            body = slide.body or bundle.key_takeaway
            blocks = [item.strip() for item in body.splitlines() if item.strip()]
            if len(blocks) >= 2:
                available = 1185 - module_top
                gap = 18
                block_height = min(170, (available - gap * (len(blocks) - 1)) // len(blocks))
                y = module_top
                for block in blocks[:5]:
                    _draw_module(draw, (72, y, 1008, y + block_height), fill=PANEL, radius=24)
                    draw.rounded_rectangle((72, y, 80, y + block_height), radius=4, fill=BLUE)
                    _draw_wrapped(
                        draw,
                        (112, y + 30),
                        block,
                        _font(font_path, 31),
                        MUTED,
                        820,
                        spacing=14,
                        max_lines=3,
                    )
                    y += block_height + gap
            else:
                body_font = _font(font_path, 34)
                line_count = max(len(_wrap(draw, body, body_font, 820)), 1)
                module_bottom = min(module_top + 110 + line_count * 52, 1215)
                _draw_module(draw, (72, module_top, 1008, module_bottom), fill=PANEL, radius=30)
                _draw_wrapped(
                    draw,
                    (112, module_top + 52),
                    body,
                    body_font,
                    MUTED,
                    820,
                    spacing=18,
                    max_lines=12,
                )

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
