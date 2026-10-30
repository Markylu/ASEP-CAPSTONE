"""Probe N1: is the step-0 lottery caused by batching? (model calls)

Same perceiver call on the same frame, alone vs. alongside 7 other requests, on
a vLLM instance nothing else uses. Method and gate:
eval/phase2/_probes/n1/README.md (committed before the first call).

    LITELLM_BASE_URL=http://127.0.0.1:8006 python eval/probes/n1.py run
    python eval/probes/n1.py score
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import random
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

os.environ.setdefault("VLM_PROFILE", "remote")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROBES, load, runs, write_jsonl  # noqa: E402

AGENT = "a49"
FRAMES = (("R25D", "s02a", "final"), ("R25D", "s03", "final"))
TRIALS = 20
FILLERS = 7
OUT = PROBES / "n1"


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def reading(result):
    """The perceiver result without its reason, as a hashable tuple."""
    if not result:
        return None
    lanes = tuple((l.get("strip"), l.get("floor"), l.get("doorway"))
                  for l in result.get("lanes") or [])
    return (result.get("goal"), result.get("goal_range"), lanes)


def fields(rd):
    """Strip-level fields of a reading, for agreement rates."""
    goal, rng, lanes = rd
    out = {"goal": goal, "goal_range": rng}
    for strip, floor, door in lanes:
        out[strip + ".floor"] = floor
        out[strip + ".doorway"] = door
    return out


def agree(a, b) -> float:
    fa, fb = fields(a), fields(b)
    keys = set(fa) | set(fb)
    return sum(fa.get(k) == fb.get(k) for k in keys) / len(keys)


def targets():
    """The two step-0 frames, plus every recorded :8004 step-0 reading of the same bytes."""
    idx = {(r["round"], r["site"], r["arm"]): r for r in runs(22, 26)}
    out = []
    for rnd, site, arm in FRAMES:
        run = idx[(rnd, site, arm)]
        row = load(run["path"])[0]
        frame = run["path"] / row["clean_frame"]
        h = md5(frame)
        history = []
        for r in idx.values():
            if r["site"] != site:
                continue
            r0 = load(r["path"])[0]
            f0 = r["path"] / r0["clean_frame"]
            rd = reading((r0.get("perceiver") or {}).get("result"))
            if rd and f0.exists() and md5(f0) == h:
                history.append({"run": "{0}/{1}/{2}".format(r["round"], r["site"], r["arm"]),
                                "reading": rd})
        out.append({"name": "{0}/{1}/{2}".format(rnd, site, arm), "frame": str(frame),
                    "manifest": row["manifest"], "md5": h, "history": history})
    return out


def fillers():
    pool = []
    for run in runs(25, 25):
        if run["round"] != "R25D":
            continue
        for row in load(run["path"]):
            if 5 <= row["step"] <= 40 and row.get("clean_frame"):
                f = run["path"] / row["clean_frame"]
                if f.exists():
                    pool.append((str(f), row["manifest"]))
    random.Random(0).shuffle(pool)
    return pool


async def run_probe() -> None:
    from server.decider import agent as agents, config, orchestrator, prompt as prompts
    from server.decider import schema, views, vlm
    feats = agents.get(AGENT).features["orchestrator"]
    p = prompts.get(feats["perceiver"])

    async def call(frame, manifest):
        b64 = base64.b64encode(Path(frame).read_bytes()).decode()
        view = views.perceiver(p, manifest, b64)
        return await vlm.call_structured(
            schema.PERCEIVER_SCHEMA_NAME, view.system, view.text, view.image_b64,
            schema.perceiver_schema(p.version),
            lambda parsed: orchestrator.perception_from(parsed, p.version, feats.get("floor_map")),
            orchestrator.PERCEIVER_MAX_TOKENS)

    tg, pool = targets(), fillers()
    rows = []
    for t in tg:
        for i in range(TRIALS):
            sub = await call(t["frame"], t["manifest"])
            rows.append({"frame": t["name"], "arm": "alone", "trial": i, "raw": sub.raw,
                         "result": sub.result, "rung": sub.rung, "latency_ms": sub.latency_ms})
        for i in range(TRIALS):
            extra = pool[i * FILLERS:(i + 1) * FILLERS]
            subs = await asyncio.gather(call(t["frame"], t["manifest"]),
                                        *(call(f, m) for f, m in extra))
            sub = subs[0]
            rows.append({"frame": t["name"], "arm": "loaded", "trial": i, "raw": sub.raw,
                         "result": sub.result, "rung": sub.rung, "latency_ms": sub.latency_ms})
        print("{0}: done".format(t["name"]), flush=True)
    meta = [{"name": t["name"], "frame": t["frame"], "md5": t["md5"], "history": t["history"]}
            for t in tg]
    write_jsonl(OUT / "calls.jsonl", rows)
    (OUT / "meta.json").write_text(json.dumps({"url": config.LITELLM_BASE_URL, "frames": meta},
                                              indent=1))


def _tuple(rd):
    return (rd[0], rd[1], tuple(tuple(x) for x in rd[2]))


def score() -> int:
    rows = [json.loads(l) for l in (OUT / "calls.jsonl").read_text().splitlines()]
    meta = json.loads((OUT / "meta.json").read_text())
    lines = ["N1 on {0}: {1} calls".format(meta["url"], len(rows))]
    distinct, loaded_dis, stand_in = {}, [], []
    for fm in meta["frames"]:
        name = fm["name"]
        lines.append("\n## {0} (md5 {1}; same bytes in {2} recorded :8004 runs)".format(
            name, fm["md5"][:8], len(fm["history"])))
        modes = {}
        for arm in ("alone", "loaded"):
            rs = [r for r in rows if r["frame"] == name and r["arm"] == arm]
            ok = [x for x in (reading(r["result"]) for r in rs) if x]
            mode = Counter(ok).most_common(1)[0][0] if ok else None
            modes[arm] = mode
            dis = (sum(1 - agree(x, mode) for x in ok) / len(ok)) if ok else 0.0
            if arm == "loaded":
                loaded_dis.append(dis)
            distinct[(name, arm)] = len(set(ok))
            lines.append("  {0:6s}: {1} calls, distinct raw {2}, distinct readings {3}, failed {4}, "
                         "strip-field disagreement with mode {5:.1%}".format(
                             arm, len(rs), len({r["raw"] for r in rs}), len(set(ok)),
                             len(rs) - len(ok), dis))
        hist = [_tuple(h["reading"]) for h in fm["history"]]
        if len(hist) >= 2 and modes["alone"]:
            pair = [agree(a, b) for a, b in combinations(hist, 2)]
            self_agree = sum(pair) / len(pair)
            copy_agree = sum(agree(modes["alone"], h) for h in hist) / len(hist)
            stand_in.append(copy_agree >= self_agree - 0.05)
            lines.append("  recorded :8004 readings: {0} distinct of {1}; pairwise agreement "
                         "{2:.1%}; copy's alone mode vs recorded {3:.1%}".format(
                             len(set(hist)), len(hist), self_agree, copy_agree))
    names = [fm["name"] for fm in meta["frames"]]
    holds = (all(distinct[(n, "alone")] <= 2 for n in names)
             and any(distinct[(n, "loaded")] >= 5 for n in names))
    refuted = all(distinct[(n, "alone")] >= distinct[(n, "loaded")] for n in names)
    lines += ["\n## Gate",
              "  verdict: " + ("HOLDS" if holds else "REFUTED" if refuted else "no call"),
              "  stand-in: " + ("yes" if stand_in and all(stand_in) else "no"),
              "  noise floor for C1/F1 (loaded strip-field disagreement, mean): {0:.1%}".format(
                  sum(loaded_dis) / len(loaded_dis) if loaded_dis else 0.0)]
    text = "\n".join(lines) + "\n"
    (OUT / "score.txt").write_text(text)
    print(text, end="")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run", "score"))
    args = ap.parse_args()
    if args.cmd == "run":
        asyncio.run(run_probe())
        return 0
    return score()


if __name__ == "__main__":
    sys.exit(main())
