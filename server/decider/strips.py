"""The clean frame by strip, for R28's wall readers.

Standard library only, like mirror.py, whose PNG decoding it reuses:
- crops(): the five strips as five PNGs (w02);
- marked(): the frame with the four strip boundaries drawn in yellow (w03);
- bottom_features(): numbers that describe the bottom edge of each strip, for
  the code floor detector (w04, eval/probes/r28_walls.py).

Strips are equal fifths of the width, left to right (spatial.STRIPS).
"""
from __future__ import annotations

import struct
import zlib
from typing import Dict, List, Tuple

from .mirror import CHANNELS, SIGNATURE, _chunk, _chunks, _unfilter

STRIPS = ["far_left", "left", "centre", "right", "far_right"]
LINE = (255, 220, 0)  # w03's boundary colour
LINE_PX = 4
#: w04: the bottom band read, as fractions of the height from the bottom.
BAND = (0.0, 1 / 12)


def decode(data: bytes) -> Tuple[int, int, int, bytearray]:
    """(width, height, bytes per pixel, unfiltered pixels) of an 8-bit RGB or
    RGBA PNG, as mirror.flip_png reads it."""
    header, idat = None, b""
    for kind, body in _chunks(data):
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
    if header is None:
        raise ValueError("PNG without IHDR")
    width, height, depth, colour, _, _, interlace = header
    if depth != 8 or colour not in CHANNELS or interlace:
        raise ValueError("unsupported PNG: depth {0}, colour type {1}, interlace {2}".format(
            depth, colour, interlace))
    bpp = CHANNELS[colour]
    return width, height, bpp, _unfilter(zlib.decompress(idat), width, height, bpp)


def encode(width: int, height: int, bpp: int, pixels: bytes) -> bytes:
    colour = {v: k for k, v in CHANNELS.items()}[bpp]
    stride = width * bpp
    rows = b"".join(b"\x00" + bytes(pixels[y * stride:(y + 1) * stride]) for y in range(height))
    return (SIGNATURE + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, colour, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(rows, 6)) + _chunk(b"IEND", b""))


def bounds(width: int) -> List[Tuple[int, int]]:
    """Each strip's [x0, x1) columns."""
    edges = [round(i * width / len(STRIPS)) for i in range(len(STRIPS) + 1)]
    return list(zip(edges[:-1], edges[1:]))


def crops(data: bytes) -> List[bytes]:
    """w02: the five strips, far_left first, each a PNG of the strip's columns."""
    width, height, bpp, px = decode(data)
    stride = width * bpp
    out = []
    for x0, x1 in bounds(width):
        part = b"".join(bytes(px[y * stride + x0 * bpp:y * stride + x1 * bpp])
                        for y in range(height))
        out.append(encode(x1 - x0, height, bpp, part))
    return out


def marked(data: bytes) -> bytes:
    """w03: the frame with the four inner strip boundaries drawn, LINE_PX wide."""
    width, height, bpp, px = decode(data)
    stride = width * bpp
    colour = bytes(LINE) + (b"\xff" if bpp == 4 else b"")
    for x0, _ in bounds(width)[1:]:
        for y in range(height):
            for x in range(x0 - LINE_PX // 2, x0 + LINE_PX - LINE_PX // 2):
                i = y * stride + x * bpp
                px[i:i + bpp] = colour
    return encode(width, height, bpp, px)


def bottom_features(data: bytes) -> Dict[str, Dict[str, float]]:
    """w04: for each strip, the bottom band (BAND) described by brightness,
    its spread, edges, and edge direction. Floor shows grid lines running away
    from the camera (slanted in the image); a wall close in front is plain, or
    shows lines that are level or upright."""
    width, height, bpp, px = decode(data)
    stride = width * bpp
    y0 = height - max(2, round(BAND[1] * height))
    lum = [[0.0] * width for _ in range(height - y0)]
    orange = [[False] * width for _ in range(height - y0)]
    for j, y in enumerate(range(y0, height)):
        row = px[y * stride:(y + 1) * stride]
        for x in range(width):
            r, g, b = row[x * bpp], row[x * bpp + 1], row[x * bpp + 2]
            lum[j][x] = 0.299 * r + 0.587 * g + 0.114 * b
            orange[j][x] = r > g > b and r - b > 60
    out = {}
    for strip, (x0, x1) in zip(STRIPS, bounds(width)):
        vals, n_edge, n_slant, n_orange = [], 0, 0, 0
        for j in range(len(lum)):
            for x in range(x0, x1):
                vals.append(lum[j][x])
                n_orange += orange[j][x]
                if 0 < j < len(lum) - 1 and x0 < x < x1 - 1:
                    gx = lum[j][x + 1] - lum[j][x - 1]
                    gy = lum[j + 1][x] - lum[j - 1][x]
                    if abs(gx) + abs(gy) > 24:
                        n_edge += 1
                        # slanted: neither level nor upright (|gx| and |gy| comparable)
                        n_slant += min(abs(gx), abs(gy)) > 0.35 * max(abs(gx), abs(gy))
        n = len(vals)
        mean = sum(vals) / n
        sd = (sum((v - mean) ** 2 for v in vals) / n) ** 0.5
        out[strip] = {"mean": mean / 255, "sd": sd / 255, "edge": n_edge / n,
                      "slant": n_slant / max(1, n_edge), "orange": n_orange / n}
    return out
