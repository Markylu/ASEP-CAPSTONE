#!/usr/bin/env python3
"""R27 probe gate: a60's perceiver (g07 read plain and mirrored, image-right
fusion) against a49's g05 on fresh recorded frames. Gate and method:
eval/phase2/R27_mirrored_nr_perceiver/README.md, "Probe gate" (set before this ran).

The mirrored frame, the swap back and the fusion are the flight code
(server/decider/mirror.py, orchestrator.unmirrored, orchestrator.image_right).
Truth and sampling as probes C1/C2 (eval/probes/c1f1.py).

    python eval/r27_probe.py sample
    LITELLM_BASE_URL=http://127.0.0.1:8004 python eval/r27_probe.py run --shard 0 --of 2
    LITELLM_BASE_URL=http://127.0.0.1:8006 python eval/r27_probe.py run --shard 1 --of 2
    python eval/r27_probe.py score
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import statistics
import sys
from pathlib import Path

os.environ.setdefault("VLM_PROFILE", "remote")
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "eval" / "probes"))
import c1f1  # noqa: E402
from c1f1 import STRIPS, load_sample, truth_fields, write_jsonl  # noqa: E402

OUT = REPO_ROOT / "eval" / "phase2" / "R27_mirrored_nr_perceiver" / "probe"
READS = ("g05", "g07", "g07_mirror")
FLOOR_MAP = {"no_floor": "blocked_near", "bottom": "open_near", "lower": "open_far",
             "middle": "open_far"}  # a49's and a60's
GATE = {"missed_ratio_max": 0.5, "phantom_rise_max": 0.06, "goal_drop_max": 0.01,
        "door_drop_max": 0.02}


async def run_probe(shard: int, of: int) -> None:
    from server.decider import config, mirror, orchestrator, prompt as prompts, schema, views
    from server.decider import vlm

    async def call(read, f):
        version = "g05" if read == "g05" else "g07"
        p = prompts.get(version)
        b64 = base64.b64encode(Path(f["frame"]).read_bytes()).decode()
        if read == "g07_mirror":
            b64 = await asyncio.to_thread(mirror.flip_png_b64, b64)
        view = views.perceiver(p, f["manifest"], b64)
        sub = await vlm.call_structured(
            schema.PERCEIVER_SCHEMA_NAME, view.system, view.text, view.image_b64,
            schema.perceiver_schema(version),
            lambda parsed: orchestrator.perception_from(parsed, version, FLOOR_MAP),
            orchestrator.PERCEIVER_MAX_TOKENS)
        res = sub.result
        if read == "g07_mirror" and res:
            res = orchestrator.unmirrored(res)
        return {"id": f["id"], "key": f["key"], "read": read, "result": res, "raw": sub.raw,
                "rung": sub.rung, "latency_ms": sub.latency_ms,
                "instance": config.LITELLM_BASE_URL}

    todo = load_sample(OUT)[shard::of]
    path = OUT / "calls_{0}of{1}.jsonl".format(shard, of)
    done = set()
    if path.exists():
        done = {(c["id"], c["read"]) for c in map(json.loads, path.read_text().splitlines())}
    with path.open("a") as fh:
        for n, f in enumerate(todo):
            for read in READS:  # one at a time: concurrency 1
                if (f["id"], read) not in done:
                    fh.write(json.dumps(await call(read, f)) + "\n")
                    fh.flush()
            if n % 25 == 0:
                print("shard {0}/{1}: {2}/{3} frames".format(shard, of, n + 1, len(todo)),
                      flush=True)
    print("shard {0}/{1}: done on {2}".format(shard, of, config.LITELLM_BASE_URL))


def fields(res):
    out = {}
    for l in res["lanes"]:
        out[(l["strip"], "floor")] = l["floor"]
        out[(l["strip"], "door")] = l["doorway"] == "open"
    return out


def score() -> int:
    from server.decider import orchestrator
    sample = {f["id"]: f for f in load_sample(OUT)}
    calls = {}
    for fp in sorted(OUT.glob("calls_*of*.jsonl")):
        for c in map(json.loads, fp.read_text().splitlines()):
            calls.setdefault(c["id"], {})[c["read"]] = c
    full = [i for i in sample if all((calls.get(i, {}).get(r) or {}).get("result") for r in READS)]
    failed = sum(1 for i in calls for r in calls[i].values() if not r.get("result"))
    res = {i: {r: calls[i][r]["result"] for r in READS} for i in full}
    for i in full:
        res[i]["fused"] = orchestrator.image_right(res[i]["g07"], res[i]["g07_mirror"])
    T = {i: truth_fields(sample[i]["truth"]) for i in full}
    TG = {i: sample[i]["truth"]["goal"] for i in full}
    names = READS + ("fused",)

    def walls(read, strips=STRIPS):
        miss = blocked = phantom = open_ = 0
        for i in full:
            f = fields(res[i][read])
            for s in strips:
                if T[i][(s, "floor")] == "blocked_near":
                    blocked += 1
                    miss += f[(s, "floor")] != "blocked_near"
                else:
                    open_ += 1
                    phantom += f[(s, "floor")] == "blocked_near"
        return miss / max(1, blocked), phantom / max(1, open_), blocked, open_

    def door(read):
        return (sum(fields(res[i][read])[(s, "door")] == T[i][(s, "door")]
                    for i in full for s in STRIPS) / (5 * len(full)))

    def goal(read):
        return sum(res[i][read]["goal"] == TG[i] for i in full) / len(full)

    _, _, nb, no = walls("g05")
    lines = ["R27 probe: {0} frames sampled, {1} with all three reads; {2} failed calls".format(
        len(sample), len(full), failed),
        "  truth: {0} blocked strips (< 1 m), {1} open; {2} frames with the goal in view".format(
            nb, no, sum(TG[i] != "not_visible" for i in full)),
        "\n  {0:11s} {1:>12s} {2:>13s} {3:>9s} {4:>9s}   phantom wall image-left / right".format(
            "read", "missed wall", "phantom wall", "doorway", "goal")]
    for r in names:
        m, p, _, _ = walls(r)
        pl = walls(r, ("far_left", "left"))[1]
        pr = walls(r, ("right", "far_right"))[1]
        if r == "g07_mirror":  # its world-left strips sat on the image's right
            pl, pr = pr, pl
        lines.append("  {0:11s} {1:12.1%} {2:13.1%} {3:9.1%} {4:9.1%}   {5:.1%} / {6:.1%}".format(
            r, m, p, door(r), goal(r), pl, pr))
    lines.append("\n  median latency (ms): " + ", ".join(
        "{0} {1:.0f}".format(r, statistics.median(calls[i][r]["latency_ms"] for i in full))
        for r in READS))

    m05, p05 = walls("g05")[:2]
    mf, pf = walls("fused")[:2]
    checks = [
        ("missed walls <= half of g05's", mf <= GATE["missed_ratio_max"] * m05,
         "{0:.1%} vs {1:.1%}".format(mf, m05)),
        ("phantom walls <= g05 + 6 pts", pf - p05 <= GATE["phantom_rise_max"],
         "{0:+.1f} pts".format((pf - p05) * 100)),
        ("goal strip >= g05 - 1 pt", goal("fused") - goal("g05") >= -GATE["goal_drop_max"],
         "{0:+.1f} pts".format((goal("fused") - goal("g05")) * 100)),
        ("doorway >= g05 - 2 pts", door("fused") - door("g05") >= -GATE["door_drop_max"],
         "{0:+.1f} pts".format((door("fused") - door("g05")) * 100)),
    ]
    lines.append("\n## Gate (all four)")
    for name, ok, value in checks:
        lines.append("  {0:32s} {1:>14s}  {2}".format(name, value, "pass" if ok else "FAIL"))
    lines.append("  verdict: " + ("PASS" if all(ok for _, ok, _ in checks) else "FAIL"))
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
        seen = ({f["key"] for f in load_sample()}
                | {f["key"] for f in load_sample(c1f1.PROBES / "c2")})
        frames, cells = c1f1.sample(salt="r27:", exclude=seen)
        assert not seen & {f["key"] for f in frames}
        write_jsonl(OUT / "sample.jsonl", frames)
        print(len(frames), "fresh frames (none in C1's or C2's samples); cells before "
              "stratifying:", json.dumps(cells, indent=1))
        return 0
    if args.cmd == "run":
        asyncio.run(run_probe(args.shard, args.of))
        return 0
    return score()


if __name__ == "__main__":
    sys.exit(main())
