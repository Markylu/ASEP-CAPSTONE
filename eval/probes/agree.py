#!/usr/bin/env python3
"""Probe AG: a60's two g07 reads, with a wall only where both reads see one.
Gate and method: eval/phase2/_probes/agree/README.md (set before any call).

Set F is every s02*/s03 step R27 flew (frames in the lane checkouts on
sctsvr6); set P is R27's probe sample, scored from its recorded calls.

    python eval/probes/agree.py sample ~/asep-r27-l1/eval/phase2/R27_mirrored_nr_perceiver/runs ...
    LITELLM_BASE_URL=http://127.0.0.1:8004 python eval/probes/agree.py run --shard 0 --of 2
    LITELLM_BASE_URL=http://127.0.0.1:8006 python eval/probes/agree.py run --shard 1 --of 2
    python eval/probes/agree.py score
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import r27_probe  # noqa: E402
from c1f1 import STRIPS, h, load_sample, truth, truth_fields, write_jsonl  # noqa: E402
from common import PROBES, load, metrics, xy  # noqa: E402

OUT = PROBES / "agree"
READS = r27_probe.READS  # g05, g07, g07_mirror
GATE = {"missed_ratio_max": 0.5, "phantom_rise_max": 0.02, "s03_phantom_rise_max": 0.04,
        "door_drop_max": 0.02, "goal_drop_max": 0.01}


def agree(own, flipped):
    """a60's image-right fusion, but a strip stays blocked_near only if the other
    read says so too; otherwise its floor comes from the other read."""
    from server.decider import orchestrator
    fused = orchestrator.image_right(own, flipped)
    other = orchestrator.image_right(flipped, own)  # per strip, the read fused did not use
    lanes = []
    for f, o in zip(fused["lanes"], other["lanes"]):
        if f["floor"] == "blocked_near" and o["floor"] != "blocked_near":
            f = dict(f, **{k: o[k] for k in ("floor", "floor_end") if k in o})
        lanes.append(f)
    return dict(fused, lanes=lanes)


def fuse(res) -> None:
    from server.decider import orchestrator
    for r in res.values():
        r["a60"] = orchestrator.image_right(r["g07"], r["g07_mirror"])
        r["agree"] = agree(r["g07"], r["g07_mirror"])


def sample(roots) -> None:
    frames = []
    for root in map(Path, roots):
        for run in sorted(root.glob("*/*/seed*")):
            site, arm = run.parts[-3], run.parts[-2]
            if not (site.startswith("s02") or site == "s03"):
                continue
            rows, met = load(run), metrics(run)
            for r in rows:
                if not r.get("clean_frame") or xy(r) is None:
                    continue
                f = run / r["clean_frame"]
                if not f.exists():
                    continue
                key = "R27/{0}/{1}/{2}".format(site, arm, r["step"])
                p, m = r.get("perceiver") or {}, r.get("perceiver_mirror") or {}
                frames.append({"id": h("agree:" + key)[:16], "key": key, "site": site,
                               "arm": arm, "frame": str(f), "manifest": r["manifest"],
                               "truth": truth(site, arm, r, rows, met),
                               "flight": {"g07": p.get("result_own"),
                                          "g07_mirror": m.get("result_unmirrored")}})
    write_jsonl(OUT / "sample.jsonl", frames)
    print(len(frames), "frames from", len(roots), "roots")


def calls_of(folder: Path):
    calls = {}
    for fp in sorted(folder.glob("calls_*of*.jsonl")):
        for c in map(json.loads, fp.read_text().splitlines()):
            calls.setdefault(c["id"], {})[c["read"]] = c["result"]
    return calls


def table(name, frames, res, reads):
    """res[id][read] is a perception; returns (lines, stats[read])."""
    T = {f["id"]: truth_fields(f["truth"]) for f in frames}
    stats = {}
    for read in reads:
        n = dict.fromkeys(("miss", "blocked", "phantom", "open", "s03_ph", "s03_open", "door",
                           "goal"), 0)
        for f in frames:
            got = r27_probe.fields(res[f["id"]][read])
            for s in STRIPS:
                if T[f["id"]][(s, "floor")] == "blocked_near":
                    n["blocked"] += 1
                    n["miss"] += got[(s, "floor")] != "blocked_near"
                else:
                    ph = got[(s, "floor")] == "blocked_near"
                    n["open"] += 1
                    n["phantom"] += ph
                    if f["site"] == "s03":
                        n["s03_open"] += 1
                        n["s03_ph"] += ph
                n["door"] += got[(s, "door")] == T[f["id"]][(s, "door")]
            n["goal"] += res[f["id"]][read]["goal"] == f["truth"]["goal"]
        k = max(1, len(frames))
        stats[read] = {"missed": n["miss"] / max(1, n["blocked"]),
                       "phantom": n["phantom"] / max(1, n["open"]),
                       "s03_phantom": n["s03_ph"] / max(1, n["s03_open"]),
                       "door": n["door"] / (5 * k), "goal": n["goal"] / k}
    lines = ["\n## {0}: {1} frames".format(name, len(frames)),
             "  {0:11s} {1:>12s} {2:>13s} {3:>12s} {4:>9s} {5:>9s}".format(
                 "read", "missed wall", "phantom wall", "s03 phantom", "doorway", "goal")]
    for read, s in stats.items():
        lines.append("  {0:11s} {1:12.1%} {2:13.1%} {3:12.1%} {4:9.1%} {5:9.1%}".format(
            read, s["missed"], s["phantom"], s["s03_phantom"], s["door"], s["goal"]))
    return lines, stats


def score() -> int:
    names = READS + ("a60", "agree")
    frames = load_sample(OUT)
    calls = calls_of(OUT)
    full = [f for f in frames if all((calls.get(f["id"]) or {}).get(r) for r in READS)]
    failed = sum(1 for i in calls for v in calls[i].values() if not v)
    res = {f["id"]: dict(calls[f["id"]]) for f in full}
    fuse(res)
    lines = ["Probe AG: set F {0} frames, {1} with all three reads, {2} failed calls".format(
        len(frames), len(full), failed)]
    out, F = table("Set F (R27 flight frames, fresh reads)", full, res, names)
    lines += out

    pcalls = calls_of(r27_probe.OUT)
    pfull = [dict(f, site=f["key"].split("/")[1]) for f in load_sample(r27_probe.OUT)
             if all((pcalls.get(f["id"]) or {}).get(r) for r in READS)]
    pres = {f["id"]: dict(pcalls[f["id"]]) for f in pfull}
    fuse(pres)
    out, P = table("Set P (R27 probe sample, recorded calls)", pfull, pres, names)
    lines += out

    flown = [f for f in frames if f["flight"]["g07"] and f["flight"]["g07_mirror"]]
    fres = {f["id"]: dict(f["flight"]) for f in flown}
    fuse(fres)
    out, _ = table("Not gated: set F, the reads recorded in flight", flown, fres,
                   ("g07", "g07_mirror", "a60", "agree"))
    lines += out

    a, g, pa, pg = F["agree"], F["g05"], P["agree"], P["g05"]
    checks = [
        ("F missed <= half of g05's", a["missed"] <= GATE["missed_ratio_max"] * g["missed"],
         "{0:.1%} vs {1:.1%}".format(a["missed"], g["missed"])),
        ("F phantom <= g05 + 2 pts", a["phantom"] - g["phantom"] <= GATE["phantom_rise_max"],
         "{0:+.1f} pts".format(100 * (a["phantom"] - g["phantom"]))),
        ("F s03 phantom <= g05 + 4 pts",
         a["s03_phantom"] - g["s03_phantom"] <= GATE["s03_phantom_rise_max"],
         "{0:+.1f} pts".format(100 * (a["s03_phantom"] - g["s03_phantom"]))),
        ("F doorway >= g05 - 2, goal >= g05 - 1",
         a["door"] - g["door"] >= -GATE["door_drop_max"]
         and a["goal"] - g["goal"] >= -GATE["goal_drop_max"],
         "{0:+.1f} / {1:+.1f} pts".format(100 * (a["door"] - g["door"]),
                                         100 * (a["goal"] - g["goal"]))),
        ("P missed <= half, phantom <= g05 + 2",
         pa["missed"] <= GATE["missed_ratio_max"] * pg["missed"]
         and pa["phantom"] - pg["phantom"] <= GATE["phantom_rise_max"],
         "{0:.1%} vs {1:.1%}, {2:+.1f} pts".format(pa["missed"], pg["missed"],
                                                   100 * (pa["phantom"] - pg["phantom"]))),
    ]
    lines.append("\n## Gate (all five)")
    for name, ok, value in checks:
        lines.append("  {0:38s} {1:>24s}  {2}".format(name, value, "pass" if ok else "FAIL"))
    lines.append("  verdict: " + ("PASS" if all(ok for _, ok, _ in checks) else "FAIL"))
    text = "\n".join(lines) + "\n"
    (OUT / "score.txt").write_text(text)
    print(text, end="")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("sample", "run", "score"))
    ap.add_argument("roots", nargs="*")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    args = ap.parse_args()
    if args.cmd == "sample":
        sample(args.roots)
        return 0
    if args.cmd == "run":
        r27_probe.OUT = OUT  # r27_probe's three reads, written to this probe's folder
        asyncio.run(r27_probe.run_probe(args.shard, args.of))
        return 0
    return score()


if __name__ == "__main__":
    sys.exit(main())
