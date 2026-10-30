#!/usr/bin/env python3
"""R28 probe gate: the wall reader w01 against a49's g05 floor on three
recorded frame sets. Gate and method: eval/phase2/R28_wall_reader/README.md,
"Probe gate" (set before this ran).

Only w01 is called. g05's reads are the ones already recorded on the same
frames, at concurrency 1:
- F, R27's s02*/s03 flight frames: probe AG (eval/phase2/_probes/agree), read `g05`;
- P, R27's probe sample: eval/phase2/R27_mirrored_nr_perceiver/probe, read `g05`;
- C2's sample: eval/phase2/_probes/c2, read `orig` (g05).
Truth is each sample's own (c1f1.truth). The view, schema and validator are
the flight code (views.wall_reader, schema.wall_reader_schema,
orchestrator.walls_from).

    LITELLM_BASE_URL=http://127.0.0.1:8004 python eval/probes/w01.py run --shard 0 --of 2
    LITELLM_BASE_URL=http://127.0.0.1:8006 python eval/probes/w01.py run --shard 1 --of 2
    python eval/probes/w01.py score
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import r27_probe  # noqa: E402
from agree import calls_of, table  # noqa: E402
from c1f1 import load_sample  # noqa: E402
from common import PROBES  # noqa: E402

OUT = PROBES / "w01"
FLOOR_MAP = r27_probe.FLOOR_MAP  # a49's and a61's
#: name -> (sample folder, the recorded g05 read's name there)
SETS = {"F": (PROBES / "agree", "g05"),
        "P": (r27_probe.OUT, "g05"),
        "C2": (PROBES / "c2", "orig")}
GATED = ("F", "P")
GATE = {"missed_ratio_max": 0.5, "phantom_rise_max": 0.02, "s03_phantom_rise_max": 0.04}


def frames_of(name):
    folder, _ = SETS[name]
    return [dict(f, set=name, site=f.get("site") or f["key"].split("/")[1])
            for f in load_sample(folder)]


async def run_probe(shard: int, of: int) -> None:
    from server.decider import config, orchestrator, prompt as prompts, schema, views, vlm
    p = prompts.get("w01")

    async def call(f):
        b64 = base64.b64encode(Path(f["frame"]).read_bytes()).decode()
        view = views.wall_reader(p, f["manifest"], b64)
        sub = await vlm.call_structured(
            schema.WALL_READER_SCHEMA_NAME, view.system, view.text, view.image_b64,
            schema.wall_reader_schema(),
            lambda parsed: orchestrator.walls_from(parsed, FLOOR_MAP),
            orchestrator.PERCEIVER_MAX_TOKENS)
        return {"id": f["id"], "key": f["key"], "set": f["set"], "read": "w01",
                "result": sub.result, "raw": sub.raw, "rung": sub.rung,
                "latency_ms": sub.latency_ms, "instance": config.LITELLM_BASE_URL}

    todo = [f for name in SETS for f in frames_of(name)][shard::of]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "calls_{0}of{1}.jsonl".format(shard, of)
    done = set()
    if path.exists():
        done = {(c["set"], c["id"]) for c in map(json.loads, path.read_text().splitlines())}
    with path.open("a") as fh:
        for n, f in enumerate(todo):
            if (f["set"], f["id"]) not in done:  # one at a time: concurrency 1
                fh.write(json.dumps(await call(f)) + "\n")
                fh.flush()
            if n % 25 == 0:
                print("shard {0}/{1}: {2}/{3} frames".format(shard, of, n + 1, len(todo)),
                      flush=True)
    print("shard {0}/{1}: done on {2}".format(shard, of, config.LITELLM_BASE_URL))


def score() -> int:
    from server.decider import orchestrator
    mine = {}
    latency = []
    for fp in sorted(OUT.glob("calls_*of*.jsonl")):
        for c in map(json.loads, fp.read_text().splitlines()):
            mine.setdefault(c["set"], {})[c["id"]] = c["result"]
            latency.append(c["latency_ms"])
    lines = ["R28 probe: w01 against g05 (recorded reads), concurrency 1"]
    stats = {}
    for name, (folder, g05_read) in SETS.items():
        g05 = calls_of(folder)
        frames = frames_of(name)
        full = [f for f in frames
                if (g05.get(f["id"]) or {}).get(g05_read) and (mine.get(name) or {}).get(f["id"])]
        failed = sum(1 for v in (mine.get(name) or {}).values() if not v)
        res = {}
        for f in full:
            own = g05[f["id"]][g05_read]
            # w01 reads floors only; doorway and goal stay g05's, as in a61
            res[f["id"]] = {"g05": own, "w01": orchestrator.with_walls(own, mine[name][f["id"]])}
        out, stats[name] = table("Set {0}: {1} sampled, {2} failed w01 calls".format(
            name, len(frames), failed), full, res, ("g05", "w01"))
        lines += out
    if latency:
        lines.append("\n  w01 median latency {0:.0f} ms over {1} calls".format(
            statistics.median(latency), len(latency)))

    checks = []
    for name in GATED:
        w, g = stats[name]["w01"], stats[name]["g05"]
        checks += [
            ("{0} missed <= half of g05's".format(name),
             w["missed"] <= GATE["missed_ratio_max"] * g["missed"],
             "{0:.1%} vs {1:.1%}".format(w["missed"], g["missed"])),
            ("{0} phantom <= g05 + 2 pts".format(name),
             w["phantom"] - g["phantom"] <= GATE["phantom_rise_max"],
             "{0:+.1f} pts".format(100 * (w["phantom"] - g["phantom"]))),
        ]
    w, g = stats["F"]["w01"], stats["F"]["g05"]
    checks.append(("F s03 phantom <= g05 + 4 pts",
                   w["s03_phantom"] - g["s03_phantom"] <= GATE["s03_phantom_rise_max"],
                   "{0:+.1f} pts".format(100 * (w["s03_phantom"] - g["s03_phantom"]))))
    lines.append("\n## Gate (all five; C2 reported, not gated)")
    for name, ok, value in checks:
        lines.append("  {0:32s} {1:>20s}  {2}".format(name, value, "pass" if ok else "FAIL"))
    lines.append("  verdict: " + ("PASS" if all(ok for _, ok, _ in checks) else "FAIL"))
    text = "\n".join(lines) + "\n"
    (OUT / "score.txt").write_text(text)
    print(text, end="")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run", "score"))
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    args = ap.parse_args()
    if args.cmd == "run":
        asyncio.run(run_probe(args.shard, args.of))
        return 0
    return score()


if __name__ == "__main__":
    sys.exit(main())
