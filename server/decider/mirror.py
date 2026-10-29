"""The clean frame mirrored left-right, for a60's second perceiver read.

Standard library only (the server has no image library): decode the PNG,
undo its row filters, reverse each row's pixels, and write it back unfiltered.
8-bit RGB or RGBA, not interlaced; anything else raises ValueError. About 0.7 s
for a 768 x 768 frame, run off the event loop (orchestrator.perceive). The
pixels match Pillow's FLIP_LEFT_RIGHT, which probe C2 used.
"""
from __future__ import annotations

import base64
import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHANNELS = {2: 3, 6: 4}  # PNG colour type -> bytes per pixel at 8 bits


def _chunks(data: bytes):
    if not data.startswith(SIGNATURE):
        raise ValueError("not a PNG")
    i = len(SIGNATURE)
    while i + 8 <= len(data):
        n, kind = struct.unpack(">I4s", data[i:i + 8])
        yield kind, data[i + 8:i + 8 + n]
        i += 12 + n


def _chunk(kind: bytes, body: bytes) -> bytes:
    return (struct.pack(">I", len(body)) + kind + body
            + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))


def _unfilter(raw: bytes, width: int, height: int, bpp: int) -> bytearray:
    stride = width * bpp
    out = bytearray(height * stride)
    prev = bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        kind = raw[start]
        line = bytearray(raw[start + 1:start + 1 + stride])
        if kind == 1:  # Sub
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif kind == 2:  # Up
            line = bytearray((a + b) & 255 for a, b in zip(line, prev))
        elif kind == 3:  # Average
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif kind == 4:  # Paeth
            for i in range(stride):
                if i >= bpp:
                    a, c = line[i - bpp], prev[i - bpp]
                else:
                    a = c = 0
                b = prev[i]
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif kind != 0:
            raise ValueError("unknown PNG filter {0}".format(kind))
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return out


def flip_png(data: bytes) -> bytes:
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
    stride = width * bpp
    pixels = _unfilter(zlib.decompress(idat), width, height, bpp)
    rows = []
    for y in range(height):
        rev = pixels[y * stride:(y + 1) * stride][::-1]  # pixels reversed, channels too
        row = bytearray(stride)
        for ch in range(bpp):
            row[ch::bpp] = rev[bpp - 1 - ch::bpp]
        rows.append(b"\x00" + bytes(row))
    return (SIGNATURE + _chunk(b"IHDR", struct.pack(">IIBBBBB", *header))
            + _chunk(b"IDAT", zlib.compress(b"".join(rows), 6)) + _chunk(b"IEND", b""))


def flip_png_b64(b64: str) -> str:
    return base64.b64encode(flip_png(base64.b64decode(b64))).decode("ascii")
