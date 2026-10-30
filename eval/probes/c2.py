"""Probe C2: image-right fusion of an original and a mirrored perceiver read (model calls)

Fresh frames, five reads each (orig, orig2, mirror, nr, nr_mirror), one call at
a time per instance. Fusion takes far_left/left from the mirrored read, the rest
from the original. Method and gate: eval/phase2/_probes/c2/README.md (committed
before the first call).

    python eval/probes/c2.py sample
    python eval/probes/flip.py c2                           # mirrored frames (needs Pillow)
    LITELLM_BASE_URL=http://127.0.0.1:8004 python eval/probes/c2.py run --shard 0 --of 2
    LITELLM_BASE_URL=http://127.0.0.1:8006 python eval/probes/c2.py run --shard 1 --of 2
    python eval/probes/c2.py score
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
from pathlib import Path

os.environ.setdefault("VLM_PROFILE", "remote")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1f1  # noqa: E402
from c1f1 import LEFT, RIGHT, STRIPS, load_sample, strip_fields, truth_fields  # noqa: E402
from common import PROBES, write_jsonl  # noqa: E402

READS = ("orig", "orig2", "mirror", "nr", "nr_mirror")
FUSED = {"fused": ("orig", "mirror"), "fused_nr": ("nr", "nr_mirror")}
OUT = PROBES / "c2"


def fuse(base, flipped):
    """Strip fields of `base`, with far_left/left taken from the mirrored read."""
    return {k: (flipped if k[0] in LEFT else base)[k] for k in base}


def score() -> int:
    sample = {f["id"]: f for f in load_sample(OUT)}
    calls = {}
    for fp in sorted(OUT.glob("calls_*of*.jsonl")):
        for c in map(json.loads, fp.read_text().splitlines()):
            calls.setdefault(c["id"], {})[c["read"]] = c
    full = [i for i in sample if all((calls.get(i, {}).get(r) or {}).get("result") for r in READS)]
    failed = sum(1 for i in calls for r in calls[i].values() if not r.get("result"))
    F = {i: {r: strip_fields(calls[i][r]["result"]) for r in READS} for i in full}
    for i in full:
        for name, (base, flipped) in FUSED.items():
            F[i][name] = fuse(F[i][base], F[i][flipped])
    T = {i: truth_fields(sample[i]["truth"]) for i in full}
    TG = {i: sample[i]["truth"]["goal"] for i in full}

    def acc(read, kind, strips=STRIPS):
        hit = n = 0
        for i in full:
            for k, v in F[i][read].items():
                if k[1] == kind and k[0] in strips:
                    n += 1
                    hit += v == T[i][k]
        return hit / n if n else float("nan")

    def goal_acc(read):
        return sum(calls[i][read]["result"]["goal"] == TG[i] for i in full) / len(full)

    lines = ["C2: {0} frames sampled, {1} with all five reads; {2} failed calls".format(
        len(sample), len(full), failed)]
    lines.append("\n## Accuracy (floor class, doorway open or not)")
    lines.append("  {0:9s} {1:>7s} {2:>7s} {3:>7s}   floor by strip far_left..far_right".format(
        "read", "floor", "door", "goal"))
    for r in READS + tuple(FUSED):
        goal = goal_acc(FUSED[r][0] if r in FUSED else r)
        by = " ".join("{0:3.0f}".format(acc(r, "floor", (s,)) * 100) for s in STRIPS)
        lines.append("  {0:9s} {1:7.1%} {2:7.1%} {3:7.1%}   {4}".format(
            r, acc(r, "floor"), acc(r, "door"), goal, by))
    lines.append("\n## Median latency per call (ms)")
    for r in READS:
        lines.append("  {0:9s} {1:.0f}".format(
            r, statistics.median(calls[i][r]["latency_ms"] for i in full)))

    def lean(read):
        return (1 - acc(read, "floor", LEFT)) - (1 - acc(read, "floor", RIGHT))

    gain = acc("fused", "floor") - acc("orig", "floor")
    band = abs(acc("orig", "floor") - acc("orig2", "floor"))
    door_d = acc("fused", "door") - acc("orig", "door")
    if gain < 0.02:
        verdict = "REFUTED"
    elif gain >= 0.05 and gain >= 2 * band and door_d >= -0.01:
        verdict = "HOLDS"
    else:
        verdict = "no call"
    mirror_gap = acc("fused", "floor") - acc("mirror", "floor")
    nr_floor = acc("fused_nr", "floor") - acc("fused", "floor")
    nr_door = acc("fused_nr", "door") - acc("fused", "door")
    lines += ["\n## Gate",
              "  fused - orig floor {0:+.1f} pts (>= 5, >= 2x band {1:.1f}); door {2:+.1f} pts "
              "(>= -1)".format(gain * 100, band * 100, door_d * 100),
              "  verdict: " + verdict,
              "\n## Decision rules",
              "  fused - mirror alone, floor: {0:+.1f} pts -> {1}".format(
                  mirror_gap * 100, "use one mirrored read" if mirror_gap < 0.02 else "fusion"),
              "  fused_nr - fused: floor {0:+.1f}, door {1:+.1f} pts -> {2}".format(
                  nr_floor * 100, nr_door * 100,
                  "fused_nr is enough" if nr_floor >= -0.02 and nr_door >= -0.01 else "keep g05"),
              "  lean on orig (floor error left - right): {0:+.1f} pts -> {1}; nr {2:+.1f}".format(
                  lean("orig") * 100, "replicates" if lean("orig") >= 0.05 else "did not replicate",
                  lean("nr") * 100)]
    text = "\n".join(lines) + "\n"
    (OUT / "score.txt").write_text(text)
    print(text, end="")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("sample", "run", "score"))
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    args = ap.parse_args()
    if args.cmd == "sample":
        seen = {f["key"] for f in load_sample()}
        frames, cells = c1f1.sample(salt="c2:", exclude=seen)
        assert not seen & {f["key"] for f in frames}
        write_jsonl(OUT / "sample.jsonl", frames)
        print(len(frames), "fresh frames (none in C1's sample); cells before stratifying:",
              json.dumps(cells, indent=1))
        return 0
    if args.cmd == "run":
        asyncio.run(c1f1.run_probe(args.shard, args.of, READS, OUT))
        return 0
    return score()


if __name__ == "__main__":
    sys.exit(main())
