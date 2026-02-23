"""
Kage Scan — Typesetting Service
Renders translated text onto cleaned manga images using Pillow.
Handles word-wrap, font sizing, and centering within bounding boxes.
"""

import asyncio
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from loguru import logger


# ── Font Resolution ───────────────────────────────────────────────────

def _find_font(font_family: str, font_size: int) -> ImageFont.FreeTypeFont:
    """
    Try to load a TrueType font, with multiple fallback layers.
    Order: requested font → common system fonts → Pillow default.
    """
    # Candidates: user-requested + common system fonts (Windows, Mac, Linux)
    candidates = [
        font_family,
        # Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/msgothic.ttc",  # Japanese support
        "C:/Windows/Fonts/YuGothR.ttc",
        "C:/Windows/Fonts/segoeui.ttf",
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",
    ]

    for path in candidates:
        try:
            return ImageFont.truetype(path, size=font_size)
        except (OSError, IOError):
            continue

    # Ultimate fallback: Pillow's built-in bitmap font
    logger.warning(f"No TrueType font found. Using Pillow default bitmap font.")
    return ImageFont.load_default()


def _wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    draw: ImageDraw.ImageDraw,
) -> list[str]:
    """
    Word-wrap text to fit within max_width pixels.
    Uses binary search on character count for efficiency.
    """
    if not text:
        return []

    # Estimate chars per line based on average character width
    avg_char_w = max(1, draw.textlength("あいうえ", font=font) / 4)
    chars_per_line = max(1, int(max_width / avg_char_w))

    # Try progressively shorter wraps until text fits
    for attempt_width in range(chars_per_line, 0, -1):
        lines = textwrap.wrap(text, width=attempt_width)
        if not lines:
            break
        # Check if the widest line actually fits
        widest = max(draw.textlength(line, font=font) for line in lines)
        if widest <= max_width:
            return lines

    # If nothing fits, force one-char-per-line (extreme case)
    return textwrap.wrap(text, width=1) or [text]


def _auto_font_size(
    text: str,
    box_width: int,
    box_height: int,
    font_family: str,
    draw: ImageDraw.ImageDraw,
    min_size: int = 10,
    max_size: int = 48,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """
    Find the largest font size where the wrapped text fits inside the bbox.
    Returns the font object and the wrapped lines.
    """
    best_font = _find_font(font_family, min_size)
    best_lines = [text]

    for size in range(max_size, min_size - 1, -1):
        font = _find_font(font_family, size)
        lines = _wrap_text(text, font, box_width - 8, draw)  # 4px horizontal padding

        if not lines:
            continue

        # Calculate total text height
        line_height = font.size + 4  # font size + line spacing
        total_height = line_height * len(lines)

        if total_height <= (box_height - 8):  # 4px vertical padding
            return font, lines

        best_font = font
        best_lines = lines

    return best_font, best_lines


class Typesetter:
    """
    Renders translated text onto cleaned manga images.
    Handles font selection, word-wrapping, and centering within bounding boxes.
    """

    _instance: "Typesetter | None" = None

    def __new__(cls) -> "Typesetter":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _render_sync(
        self,
        image_path: str,
        text_blocks: list[dict],
        output_path: str,
    ) -> str:
        """Synchronous text rendering onto image."""
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        for block in text_blocks:
            text = block.get("text_translated", "")
            if not text or not text.strip():
                continue

            # Extract bbox coordinates
            bx = int(block.get("box_x", 0))
            by = int(block.get("box_y", 0))
            bw = int(block.get("box_width", 100))
            bh = int(block.get("box_height", 50))

            # Typesetting properties
            font_family = block.get("font_family", "Arial")
            font_size = block.get("font_size", 18)
            text_color = block.get("text_color", "#000000")
            alignment = block.get("text_alignment", "center")

            # ── Auto-size if text doesn't fit ─────────────────────
            font = _find_font(font_family, font_size)
            lines = _wrap_text(text, font, bw - 8, draw)

            line_height = font.size + 4
            total_height = line_height * len(lines)

            # If text overflows vertically, auto-shrink
            if total_height > (bh - 8):
                font, lines = _auto_font_size(text, bw, bh, font_family, draw)
                line_height = font.size + 4
                total_height = line_height * len(lines)

            # ── Draw white background behind text ─────────────────
            # Ensures readability over any inpainted surface
            bg_padding = 2
            draw.rectangle(
                [bx + bg_padding, by + bg_padding, bx + bw - bg_padding, by + bh - bg_padding],
                fill="#FFFFFF",
            )

            # ── Draw each line centered in the bbox ───────────────
            y_start = by + max(0, (bh - total_height) // 2)

            for i, line in enumerate(lines):
                line_w = draw.textlength(line, font=font)

                if alignment == "center":
                    x_pos = bx + (bw - line_w) / 2
                elif alignment == "right":
                    x_pos = bx + bw - line_w - 4
                else:  # left
                    x_pos = bx + 4

                y_pos = y_start + (i * line_height)

                draw.text(
                    (x_pos, y_pos),
                    line,
                    fill=text_color,
                    font=font,
                )

            logger.debug(
                f"Rendered '{text[:20]}...' at ({bx},{by}) "
                f"font={font.size}px, {len(lines)} lines"
            )

        # Save final image
        img.save(output_path, quality=95)
        logger.info(f"Typeset image saved: {Path(output_path).name}")

        return output_path

    async def render_text(
        self,
        image_path: str,
        text_blocks: list[dict],
        output_path: str,
    ) -> str:
        """
        Async wrapper — renders translated text onto a cleaned image.

        Args:
            image_path: Path to the inpainted (cleaned) image.
            text_blocks: List of dicts with keys:
                text_translated, box_x, box_y, box_width, box_height,
                font_size, font_family, text_color, text_alignment.
            output_path: Where to save the final rendered image.

        Returns:
            Path to the saved output image.
        """
        return await asyncio.to_thread(
            self._render_sync, image_path, text_blocks, output_path,
        )
