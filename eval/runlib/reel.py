"""Compose the decision reel: what the model saw, beside what it said.

The flight video shows the trajectory but not the decision, which is the part
worth defending in a write-up. Captions are burned in with Pillow rather than
ffmpeg's drawtext because the reasons contain quotes, commas and newlines that
drawtext's escaping mangles, and because wrapping has to be measured against
the actual font to stay legible.
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from .model import Run

# First that exists wins; the last is Pillow's built-in bitmap, always present.
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
MONO_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]

BACKGROUND = (16, 18, 22)
HEADING = (235, 238, 242)
BODY = (200, 206, 214)
ACCENT = (120, 190, 255)
WARNING = (255, 170, 90)


def _font(candidates: List[str], size: int) -> ImageFont.ImageFont:
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, ValueError):
            continue
    return ImageFont.load_default()


def _wrap(text: str, font, draw: ImageDraw.ImageDraw, max_width: int) -> List[str]:
    """Measured wrapping — a character count guess overflows at this font size."""
    lines = []  # type: List[str]
    for paragraph in text.splitlines() or [""]:
        if not paragraph.strip():
            lines.append("")
            continue
        current = ""
        for word in paragraph.split():
            candidate = (current + " " + word).strip()
            if draw.textlength(candidate, font=font) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def compose_card(run: Run, decision, width: int = 1280,
                 height: int = 720) -> Image.Image:
    """Frame on the left, step heading and wrapped reason on the right."""
    card = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(card)

    image_box = int(width * 0.52)
    frame_path = run.frame_for(decision)
    if frame_path is not None:
        with Image.open(frame_path) as source:
            frame = source.convert("RGB")
            scale = min((image_box - 40) / float(frame.width),
                        (height - 80) / float(frame.height))
            frame = frame.resize((max(1, int(frame.width * scale)),
                                  max(1, int(frame.height * scale))), Image.LANCZOS)
        card.paste(frame, (20, (height - frame.height) // 2))
    else:
        draw.text((40, height // 2), "frame not on disk",
                  font=_font(FONT_CANDIDATES, 28), fill=WARNING)

    x = image_box + 20
    text_width = width - x - 40
    heading_font = _font(MONO_CANDIDATES, 30)
    meta_font = _font(MONO_CANDIDATES, 20)
    body_font = _font(FONT_CANDIDATES, 23)

    y = 46
    chosen = "action {0}".format(decision.index) if decision.index is not None else "FAILED"
    draw.text((x, y), "step {0} — {1}".format(decision.step, chosen),
              font=heading_font, fill=ACCENT)
    y += 44
    draw.text((x, y), "rung {0}   {1:.1f}s   {2} tok".format(
        decision.rung or "?", decision.latency_ms / 1000.0,
        decision.completion_tokens), font=meta_font, fill=(140, 148, 160))
    y += 30
    goal = decision.goal
    if goal:
        # What the model was shown, so the reason can be checked against it.
        draw.text((x, y), "saw goal {0:.1f} m at {1:+.0f}°".format(
            float(goal.get("distance", 0.0)), float(goal.get("bearing_deg", 0.0))),
            font=meta_font, fill=(140, 148, 160))
    y += 34

    if decision.attempts:
        draw.text((x, y), "{0} failed attempt(s) before this".format(
            len(decision.attempts)), font=meta_font, fill=WARNING)
        y += 34

    # Reasons run to several hundred characters and vary a lot in length, so the
    # body font shrinks until the whole thing fits rather than being cut off —
    # a truncated reason is the one thing this reel exists to avoid.
    body = decision.reason or decision.error or "(no reason recorded)"
    body_font, lines, line_height = _fit_body(body, draw, text_width, height - y - 24)
    for line in lines:
        draw.text((x, y), line, font=body_font, fill=BODY)
        y += line_height

    return card


def _fit_body(text: str, draw: ImageDraw.ImageDraw, max_width: int,
              max_height: int) -> Tuple[ImageFont.ImageFont, List[str], int]:
    """Largest size whose wrapped text fits the box; smallest size if none do."""
    for size in (24, 22, 20, 18, 16, 14, 12):
        font = _font(FONT_CANDIDATES, size)
        line_height = int(size * 1.38)
        lines = _wrap(text, font, draw, max_width)
        if len(lines) * line_height <= max_height:
            return font, lines, line_height
    font = _font(FONT_CANDIDATES, 12)
    line_height = 17
    lines = _wrap(text, font, draw, max_width)
    keep = max(1, max_height // line_height)
    if len(lines) > keep:
        lines = lines[:keep - 1] + [lines[keep - 1][:60] + " …"]
    return font, lines, line_height


def build_reel(run: Run, work_dir: Path, seconds_per_frame: float = 3.0,
               width: int = 1280, height: int = 720) -> Tuple[Path, int]:
    """Write the captioned cards and the concat file ffmpeg will read.

    Raises ValueError when there is nothing to show, so the caller can say why
    rather than handing ffmpeg an empty list.
    """
    if not run.decisions:
        raise ValueError("no decisions.jsonl — there are no reasons to show")
    if not run.frames:
        raise ValueError("frames/ is absent (it is gitignored); re-fly the run "
                         "to regenerate the images")

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    entries = []  # type: List[str]
    written = 0

    for decision in sorted(run.decisions, key=lambda d: d.step):
        card = compose_card(run, decision, width=width, height=height)
        card_path = work_dir / "card_{0:04d}.png".format(decision.step)
        card.save(card_path)
        # The concat demuxer needs the final image repeated, or it drops the
        # last entry's duration entirely.
        entries.append("file '{0}'".format(card_path))
        entries.append("duration {0}".format(seconds_per_frame))
        written += 1
    if entries:
        entries.append("file '{0}'".format(work_dir / "card_{0:04d}.png".format(
            sorted(run.decisions, key=lambda d: d.step)[-1].step)))

    concat_file = work_dir / "reel.txt"
    concat_file.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return concat_file, written
