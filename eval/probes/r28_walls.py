#!/usr/bin/env python3
"""R28 probe gate, second attempt: four wall readers against a49's g05 on the
recorded frame sets w01 used. Gate and method: eval/phase2/R28_wall_reader/README.md,
"Probe gate, second attempt" (set before this ran).

Candidates, each merged with the recorded g05 read the way an agent would:
- k01: a second look (wall or floor) at the strips g05 read open;
- w02: the floor question on the five strip crops, in one call;
- w03: the floor question on the frame with the strip boundaries drawn;
- w04: no model; a logistic rule on strips.bottom_features, fitted on C1's
  frames only, that adds a wall to a strip g05 read open.
A failed call leaves g05's reading. Frames: F, P (gated) and C2 (reported)
as eval/probes/w01.py; C1 (eval/phase2/_probes/c1f1) for w04's fit only.

    LITELLM_BASE_URL=http://127.0.0.1:8004 python eval/probes/r28_walls.py run --shard 0 --of 4
    ... :8006 --shard 1, :8007 --shard 2, :8008 --shard 3
    python eval/probes/r28_walls.py fit
    python eval/probes/r28_walls.py score
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import math
import os
import statistics
import sys
from pathlib import Path

os.environ.setdefault("VLM_PROFILE", "remote")
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import w01  # noqa: E402
from agree import calls_of, table  # noqa: E402
from c1f1 import STRIPS, load_sample, truth_fields  # noqa: E402
from common import PROBES  # noqa: E402

OUT = PROBES / "r28_walls"
FLOOR_MAP = w01.FLOOR_MAP
SETS = dict(w01.SETS, C1=(PROBES / "c1f1", "orig"))
SCORED = ("F", "P", "C2")
MODEL_READS = ("k01", "w02", "w03")
CANDIDATES = MODEL_READS + ("w04",)
GATE = w01.GATE
FEATURES = ("mean", "sd", "edge", "slant", "orange")
#: w04's threshold: added phantom walls on C1 at most this share of open strips.
W04_C1_PHANTOM_ADD = 0.015


def frames_of(name):
    folder, _ = SETS[name]
    return [dict(f, set=name, site=f.get("site") or f["key"].split("/")[1])
            for f in load_sample(folder)]


def recorded_g05(name):
    folder, read = SETS[name]
    return {i: r.get(read) for i, r in calls_of(folder).items()}


def open_strips(own):
    from server.decider import orchestrator
    return [l["strip"] for l in own["lanes"] if l.get("floor_end") in orchestrator.OPEN_ENDS]


async def run_probe(shard: int, of: int) -> None:
    from server.decider import config, orchestrator, prompt as prompts, schema, strips, views, vlm

    async def model(read, f, png, own):
        if read == "k01":
            asked = open_strips(own)
            if not asked:
                return {"result": {"reason": ""}, "asked": [], "latency_ms": 0.0}
            view = views.wall_confirmer(prompts.get("k01"), asked, base64.b64encode(png).decode())
            sub = await vlm.call_structured(
                schema.WALL_CONFIRMER_SCHEMA_NAME, view.system, view.text, view.image_b64,
                schema.wall_confirmer_schema(asked), orchestrator.walls_checked(asked),
                orchestrator.PERCEIVER_MAX_TOKENS)
        else:
            if read == "w02":
                image = [base64.b64encode(c).decode() for c in strips.crops(png)]
            else:
                image = base64.b64encode(strips.marked(png)).decode()
            view = views.wall_reader(prompts.get(read), f["manifest"], image)
            sub = await vlm.call_structured(
                schema.WALL_READER_SCHEMA_NAME, view.system, view.text, view.image_b64,
                schema.wall_reader_schema(),
                lambda parsed: orchestrator.walls_from(parsed, FLOOR_MAP),
                orchestrator.PERCEIVER_MAX_TOKENS)
            asked = None
        return {"result": sub.result, "asked": asked, "raw": sub.raw, "rung": sub.rung,
                "error": sub.error, "latency_ms": sub.latency_ms}

    g05 = {name: recorded_g05(name) for name in SETS}
    todo = [f for name in SETS for f in frames_of(name) if g05[name].get(f["id"])][shard::of]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "calls_{0}of{1}.jsonl".format(shard, of)
    done = set()
    if path.exists():
        done = {(c["set"], c["id"], c["read"])
                for c in map(json.loads, path.read_text().splitlines())}
    with path.open("a") as fh:
        for n, f in enumerate(todo):
            png = Path(f["frame"]).read_bytes()
            own = g05[f["set"]][f["id"]]
            reads = ("w04f",) + (MODEL_READS if f["set"] in SCORED else ())
            for read in reads:  # one call at a time: concurrency 1
                if (f["set"], f["id"], read) in done:
                    continue
                if read == "w04f":
                    rec = {"result": strips.bottom_features(png), "latency_ms": 0.0}
                else:
                    rec = await model(read, f, png, own)
                rec.update({"id": f["id"], "key": f["key"], "set": f["set"], "read": read,
                            "instance": config.LITELLM_BASE_URL})
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
            if n % 25 == 0:
                print("shard {0}/{1}: {2}/{3} frames".format(shard, of, n + 1, len(todo)),
                      flush=True)
    print("shard {0}/{1}: done on {2}".format(shard, of, config.LITELLM_BASE_URL))


def load_calls():
    calls = {}
    for fp in sorted(OUT.glob("calls_*of*.jsonl")):
        for c in map(json.loads, fp.read_text().splitlines()):
            calls.setdefault(c["set"], {}).setdefault(c["id"], {})[c["read"]] = c
    return calls


def vector(feats, end):
    return [feats[k] for k in FEATURES] + [float(end == e) for e in ("bottom", "lower")]


def prob(fit, x):
    z = fit["b"] + sum(w * (v - m) / s for w, v, m, s in zip(fit["w"], x, fit["mu"], fit["sd"]))
    return 1 / (1 + math.exp(-max(-30.0, min(30.0, z))))


def fit_w04() -> int:
    """Logistic regression on C1 only: strips g05 read open, label truly
    blocked. The threshold keeps the walls it adds on truly open C1 strips at
    most W04_C1_PHANTOM_ADD of all open C1 strips."""
    calls = load_calls().get("C1", {})
    g05 = recorded_g05("C1")
    X, y, n_open = [], [], 0
    for f in frames_of("C1"):
        own, c = g05.get(f["id"]), calls.get(f["id"], {}).get("w04f")
        if not own or not c:
            continue
        T = truth_fields(f["truth"])
        ends = {l["strip"]: l["floor_end"] for l in own["lanes"]}
        for s in STRIPS:
            n_open += T[(s, "floor")] != "blocked_near"
            if ends[s] in ("bottom", "lower", "middle"):
                X.append(vector(c["result"][s], ends[s]))
                y.append(float(T[(s, "floor")] == "blocked_near"))
    k = len(X[0])
    mu = [sum(x[j] for x in X) / len(X) for j in range(k)]
    sd = [max(1e-6, (sum((x[j] - mu[j]) ** 2 for x in X) / len(X)) ** 0.5) for j in range(k)]
    fit = {"mu": mu, "sd": sd, "w": [0.0] * k, "b": 0.0}
    for _ in range(3000):  # plain gradient descent, L2 0.01
        gw, gb = [0.0] * k, 0.0
        for x, t in zip(X, y):
            e = prob(fit, x) - t
            gb += e
            for j in range(k):
                gw[j] += e * (x[j] - mu[j]) / sd[j]
        fit["b"] -= 0.5 * gb / len(X)
        fit["w"] = [w - 0.5 * (g / len(X) + 0.01 * w) for w, g in zip(fit["w"], gw)]
    scored = sorted(((prob(fit, x), t) for x, t in zip(X, y)), reverse=True)
    best, fp = float("inf"), 0
    for p, t in scored:
        fp += t == 0
        if fp > W04_C1_PHANTOM_ADD * n_open:
            break
        best = p
    fit.update({"threshold": best, "features": list(FEATURES) + ["end_bottom", "end_lower"],
                "c1": {"open_ends": len(X), "blocked_among_them": int(sum(y)),
                       "open_strips": n_open}})
    (OUT / "w04_fit.json").write_text(json.dumps(fit, indent=1) + "\n")
    print(json.dumps(fit, indent=1))
    return 0


def merged(read, own, c, fit):
    from server.decider import orchestrator
    res = (c or {}).get("result")
    if not res:
        return own
    if read == "w04":
        add = [l["strip"] for l in own["lanes"] if l.get("floor_end") in orchestrator.OPEN_ENDS
               and prob(fit, vector(res[l["strip"]], l["floor_end"])) >= fit["threshold"]]
        return orchestrator.with_walls_added(own, add, FLOOR_MAP)
    if read == "k01":
        return orchestrator.with_walls_added(
            own, [s for s in STRIPS if res.get(s) == "wall"], FLOOR_MAP)
    return orchestrator.with_walls(own, res)


def score() -> int:
    calls = load_calls()
    fit = json.loads((OUT / "w04_fit.json").read_text())
    lines = ["R28 probe, second attempt: k01, w02, w03, w04 against g05 (recorded reads), "
             "concurrency 1", "  w04 fitted on C1 only: threshold {0:.3f} ({1})".format(
                 fit["threshold"], json.dumps(fit["c1"]))]
    stats = {}
    for name in SCORED:
        g05 = recorded_g05(name)
        frames = [f for f in frames_of(name) if g05.get(f["id"])]
        mine = calls.get(name, {})
        res = {}
        for f in frames:
            own = g05[f["id"]]
            res[f["id"]] = dict({"g05": own}, **{
                r: merged(r, own, mine.get(f["id"], {}).get("w04f" if r == "w04" else r), fit)
                for r in CANDIDATES})
        failed = {r: sum(1 for f in frames
                         if not (mine.get(f["id"], {}).get(r) or {}).get("result"))
                  for r in MODEL_READS}
        out, stats[name] = table("Set {0}: {1} frames; failed calls {2}".format(
            name, len(frames), failed), frames, res, ("g05",) + CANDIDATES)
        lines += out
    lat = {r: [c[r]["latency_ms"] for s in SCORED for c in calls.get(s, {}).values()
               if r in c and c[r].get("result") and c[r]["latency_ms"]] for r in MODEL_READS}
    lines.append("\n  median latency (ms): " + ", ".join(
        "{0} {1:.0f}".format(r, statistics.median(v)) for r, v in lat.items() if v))

    passed = []
    for cand in CANDIDATES:
        checks = []
        for name in ("F", "P"):
            w, g = stats[name][cand], stats[name]["g05"]
            checks += [
                ("{0} missed <= half of g05's".format(name),
                 w["missed"] <= GATE["missed_ratio_max"] * g["missed"],
                 "{0:.1%} vs {1:.1%}".format(w["missed"], g["missed"])),
                ("{0} phantom <= g05 + 2 pts".format(name),
                 w["phantom"] - g["phantom"] <= GATE["phantom_rise_max"],
                 "{0:+.1f} pts".format(100 * (w["phantom"] - g["phantom"])))]
        w, g = stats["F"][cand], stats["F"]["g05"]
        checks.append(("F s03 phantom <= g05 + 4 pts",
                       w["s03_phantom"] - g["s03_phantom"] <= GATE["s03_phantom_rise_max"],
                       "{0:+.1f} pts".format(100 * (w["s03_phantom"] - g["s03_phantom"]))))
        ok = all(c[1] for c in checks)
        lines.append("\n## Gate {0} (all five)".format(cand))
        for label, good, value in checks:
            lines.append("  {0:32s} {1:>20s}  {2}".format(label, value,
                                                            "pass" if good else "FAIL"))
        lines.append("  verdict: " + ("PASS" if ok else "FAIL"))
        if ok:
            passed.append((stats["F"][cand]["missed"] + stats["P"][cand]["missed"], cand))
    lines.append("\nWinner (lowest F + P missed among those that pass): "
                 + (min(passed)[1] if passed else "none"))
    text = "\n".join(lines) + "\n"
    (OUT / "score.txt").write_text(text)
    print(text, end="")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run", "fit", "score"))
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    args = ap.parse_args()
    if args.cmd == "run":
        asyncio.run(run_probe(args.shard, args.of))
        return 0
    if args.cmd == "fit":
        return fit_w04()
    return score()


if __name__ == "__main__":
    sys.exit(main())
