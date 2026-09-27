"""Draw a saved frame in the terminal, with no new dependency.

Two vertical pixels share one character cell: the upper half-block glyph takes
the top pixel as its foreground and the bottom pixel as its background, so a
cell carries two colours and the picture gets twice the vertical resolution
plain ASCII art would give. That is enough to recognise the annotation fan and
the goal beacon, which is what the frame is being looked at for.

Full-fidelity inline images (kitty, sixel) are not usable here: Textual owns the
screen buffer and raw graphics escapes corrupt it. `open_externally` is the
escape hatch when the actual pixels matter.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional, Tuple

from PIL import Image
from rich.color import Color
from rich.console import Console, ConsoleOptions, RenderResult
from rich.segment import Segment
from rich.style import Style
from rich.text import Text

UPPER_HALF = "▀"


def _fit(size: Tuple[int, int], max_cells: Tuple[int, int]) -> Tuple[int, int]:
    """Cells are about twice as tall as wide; a cell holds two pixel rows."""
    width, height = size
    max_w, max_h = max_cells
    max_w = max(1, max_w)
    max_h = max(1, max_h)
    target_w = max_w
    target_h = int(round(height / float(width) * target_w / 2.0))
    if target_h > max_h:
        target_h = max_h
        target_w = int(round(width / float(height) * target_h * 2.0))
    return max(1, target_w), max(1, target_h)


class HalfBlockImage:
    """A Rich renderable. Reloads on render so a changed file shows changed."""

    def __init__(self, path: Path, max_height: int = 24) -> None:
        self.path = Path(path)
        self.max_height = max_height

    def __rich_console__(self, console: Console,
                         options: ConsoleOptions) -> RenderResult:
        max_cells = (options.max_width, min(self.max_height,
                                            options.height or self.max_height))
        try:
            with Image.open(self.path) as source:
                image = source.convert("RGB")
                cols, rows = _fit(image.size, max_cells)
                image = image.resize((cols, rows * 2), Image.LANCZOS)
                pixels = image.load()
        except (OSError, ValueError) as exc:
            yield Text("cannot render {0}: {1}".format(self.path.name, exc),
                       style="red")
            return

        for row in range(rows):
            for col in range(cols):
                top = pixels[col, row * 2]
                bottom = pixels[col, row * 2 + 1]
                yield Segment(UPPER_HALF, Style(
                    color=Color.from_rgb(*top),
                    bgcolor=Color.from_rgb(*bottom)))
            yield Segment.line()


def open_externally(path: Path) -> Optional[str]:
    """None on success, else why not. macOS `open`, with Linux fallback."""
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    try:
        subprocess.Popen([opener, str(path)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return None
    except OSError as exc:
        return "could not launch {0}: {1}".format(opener, exc)
