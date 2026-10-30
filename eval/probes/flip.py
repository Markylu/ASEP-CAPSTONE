"""Mirror C1's sampled frames left-right (eval/phase2/_probes/c1f1/README.md).

Stdlib and Pillow only, so it runs outside the probe image, which has no Pillow:

    ~/miniforge3/envs/vllm-ai/bin/python eval/probes/flip.py [probe folder, default c1f1]
"""
import json
import sys
from pathlib import Path

from PIL import Image

PROBES = Path(__file__).resolve().parents[2] / "eval" / "phase2" / "_probes"
OUT = PROBES / (sys.argv[1] if len(sys.argv) > 1 else "c1f1")


def main() -> int:
    frames = OUT / "frames"
    frames.mkdir(exist_ok=True)
    n = 0
    for line in (OUT / "sample.jsonl").read_text().splitlines():
        f = json.loads(line)
        dst = frames / (f["id"] + "_m.png")
        if not dst.exists():
            with Image.open(f["frame"]) as im:
                im.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(dst)
            n += 1
    print("mirrored", n, "frames into", frames)
    return 0


if __name__ == "__main__":
    sys.exit(main())
