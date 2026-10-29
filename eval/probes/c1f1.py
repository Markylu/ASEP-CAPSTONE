"""Probes C1 and F1: mirrored second read, and g05 without reason-first (model calls)

One frame sample, four perceiver calls per frame (orig, orig2, mirror, nr), one
at a time per instance. Method and gates: eval/phase2/_probes/c1f1/README.md
(committed before the first call).

    python eval/probes/c1f1.py sample                       # frames + ground truth
    python eval/probes/flip.py                              # mirrored frames (needs Pillow)
    LITELLM_BASE_URL=http://127.0.0.1:8004 python eval/probes/c1f1.py run --shard 0 --of 2
    LITELLM_BASE_URL=http://127.0.0.1:8006 python eval/probes/c1f1.py run --shard 1 --of 2
    python eval/probes/c1f1.py score
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import copy
import hashlib
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("VLM_PROFILE", "remote")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROBES, geo, load, metrics, runs, spatial, world, write_jsonl, xy  # noqa: E402
from r12_probe import in_view, true_reach  # noqa: E402

AGENT = "a49"
N_FRAMES = 300
PER_SITE_ARM = 200
FIRST, LAST = 22, 26
READS = ("orig", "orig2", "mirror", "nr")
STRIPS = spatial.STRIPS
LEFT, RIGHT = ("far_left", "left"), ("right", "far_right")
SWAP = {"far_left": "far_right", "left": "right", "centre": "centre",
        "right": "left", "far_right": "far_left"}
BLOCKED_M, NEAR_M = 1.0, 3.0
RAY_M, HALF_STRIP_DEG = 12.0, 9.0  # as r20_door_probe.genuine
DESCRIBE_FIRST = ("First say, for each strip from left to right, what fills the bottom of the\n"
                  "strip and where its floor ends. Then describe walls, openings, doors and\n"
                  "anything that could be the goal. Then give the report.")
OUT = PROBES / "c1f1"
FRAMES = OUT / "frames"


def h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def floor_class(d: float) -> str:
    return "blocked_near" if d < BLOCKED_M else ("open_near" if d < NEAR_M else "open_far")


def door_open(free, site: str, here, strip: str) -> bool:
    """r20_door_probe.genuine, in the run's own world: a ray across the strip
    crosses the door plane."""
    plane = 0.0 if site.startswith("s02") else -6.5
    centre = here[2] + spatial.strip_offset(strip)
    for k in range(-2, 3):
        hd = centre + k * HALF_STRIP_DEG / 2.0
        d = geo.ray(free, here[0], here[1], hd, max_d=RAY_M)
        end_x = here[0] + d * math.cos(math.radians(hd))
        if (here[0] - plane) * (end_x - plane) < 0:
            return True
    return False


def truth(site, arm, r, rows, met):
    here = xy(r)
    assert here is not None
    free = world(site, arm, r["step"], rows, met)
    lanes = {}
    for s in STRIPS:
        d = true_reach(free, here[:2], (here[2] + spatial.strip_offset(s)) % 360.0)
        lanes[s] = {"reach": round(d, 2), "floor": floor_class(d),
                    "door": door_open(free, site, here, s)}
    goal = "not_visible"
    if in_view(r):
        goal = spatial.strip_for(float(r["manifest"]["goal"]["bearing_deg"]))
    return {"goal": goal, "lanes": lanes}


def sample():
    pool = {}
    for run in runs(FIRST, LAST):
        site, arm = run["site"], run["arm"]
        if not (site.startswith("s02") or site == "s03"):
            continue
        rows = load(run["path"])
        met = metrics(run["path"])
        for r in rows:
            if not r.get("clean_frame") or xy(r) is None:
                continue
            f = run["path"] / r["clean_frame"]
            if not f.exists():
                continue
            key = "{0}/{1}/{2}/{3}".format(run["round"], site, arm, r["step"])
            pool.setdefault((site, arm), []).append((h(key), key, str(f), r, rows, met))
    cells = {}
    for (site, arm), items in sorted(pool.items()):
        for hk, key, f, r, rows, met in sorted(items, key=lambda x: x[0])[:PER_SITE_ARM]:
            t = truth(site, arm, r, rows, met)
            door = any(l["door"] for l in t["lanes"].values())
            cells.setdefault((site, arm, door), []).append(
                {"id": hk[:16], "key": key, "site": site, "arm": arm, "door_in_view": door,
                 "frame": f, "manifest": r["manifest"], "truth": t})
    out, queues = [], [cells[c] for c in sorted(cells)]
    while len(out) < N_FRAMES and any(queues):
        for q in queues:
            if q and len(out) < N_FRAMES:
                out.append(q.pop(0))
    return out, {"{0}/{1}/{2}".format(*c): len(v) for c, v in sorted(cells.items())}


def unmirror(result):
    out = copy.deepcopy(result)
    out["goal"] = SWAP.get(out["goal"], out["goal"])
    lanes = {SWAP[l["strip"]]: dict(l, strip=SWAP[l["strip"]]) for l in out["lanes"]}
    out["lanes"] = [lanes[s] for s in STRIPS]
    return out


def mirrored(f) -> Path:
    return FRAMES / (f["id"] + "_m.png")


async def run_probe(shard: int, of: int) -> None:
    from server.decider import agent as agents, config, orchestrator, prompt as prompts
    from server.decider import schema, views, vlm
    feats = agents.get(AGENT).features["orchestrator"]
    p = prompts.get(feats["perceiver"])
    assert p.version == "g05" and DESCRIBE_FIRST in p.system, "g05 text moved"
    nr_system = p.system.replace(DESCRIBE_FIRST, "Give the report.")
    sch = schema.perceiver_schema("g05")
    nr_sch = copy.deepcopy(sch)
    del nr_sch["properties"]["reason"]
    nr_sch["required"] = [k for k in nr_sch["required"] if k != "reason"]

    async def call(name, f):
        frame = mirrored(f) if name == "mirror" else Path(f["frame"])
        view = views.perceiver(p, f["manifest"], base64.b64encode(frame.read_bytes()).decode())
        system, js = (nr_system, nr_sch) if name == "nr" else (view.system, sch)
        sub = await vlm.call_structured(
            schema.PERCEIVER_SCHEMA_NAME, system, view.text, view.image_b64, js,
            lambda parsed: orchestrator.perception_from(parsed, "g05", feats.get("floor_map")),
            orchestrator.PERCEIVER_MAX_TOKENS)
        res = sub.result
        if name == "mirror" and res:
            res = unmirror(res)
        return {"id": f["id"], "key": f["key"], "read": name, "result": res, "raw": sub.raw,
                "rung": sub.rung, "latency_ms": sub.latency_ms,
                "instance": config.LITELLM_BASE_URL}

    todo = load_sample()[shard::of]
    path = OUT / "calls_{0}of{1}.jsonl".format(shard, of)
    done = set()
    if path.exists():
        done = {(c["id"], c["read"]) for c in map(json.loads, path.read_text().splitlines())}
    with path.open("a") as fh:
        for n, f in enumerate(todo):
            for name in READS:  # one at a time: concurrency 1
                if (f["id"], name) not in done:
                    fh.write(json.dumps(await call(name, f)) + "\n")
                    fh.flush()
            if n % 25 == 0:
                print("shard {0}/{1}: {2}/{3} frames".format(shard, of, n + 1, len(todo)),
                      flush=True)
    print("shard {0}/{1}: done on {2}".format(shard, of, config.LITELLM_BASE_URL))


def load_sample():
    return [json.loads(l) for l in (OUT / "sample.jsonl").read_text().splitlines()]


# --- scoring -----------------------------------------------------------------

def strip_fields(res):
    """{(strip, 'floor'|'door'): answer} for one read."""
    out = {}
    for l in res["lanes"]:
        out[(l["strip"], "floor")] = l["floor"]
        out[(l["strip"], "door")] = l["doorway"] == "open"
    return out


def truth_fields(t):
    out = {}
    for s, l in t["lanes"].items():
        out[(s, "floor")] = l["floor"]
        out[(s, "door")] = l["door"]
    return out


def score() -> int:
    sample = {f["id"]: f for f in load_sample()}
    calls = {}
    for fp in sorted(OUT.glob("calls_*of*.jsonl")):
        for c in map(json.loads, fp.read_text().splitlines()):
            calls.setdefault(c["id"], {})[c["read"]] = c
    full = [i for i in sample if all((calls.get(i, {}).get(r) or {}).get("result") for r in READS)]
    failed = sum(1 for i in calls for r in calls[i].values() if not r.get("result"))
    F = {i: {r: strip_fields(calls[i][r]["result"]) for r in READS} for i in full}
    T = {i: truth_fields(sample[i]["truth"]) for i in full}
    G = {i: {r: calls[i][r]["result"]["goal"] for r in READS} for i in full}
    TG = {i: sample[i]["truth"]["goal"] for i in full}

    def acc(read, kind=None, strips=STRIPS, ids=None, mask=None):
        hit = n = 0
        for i in ids or full:
            for k, v in F[i][read].items():
                if (kind and k[1] != kind) or k[0] not in strips:
                    continue
                if mask and not mask(i, k):
                    continue
                n += 1
                hit += v == T[i][k]
        return (hit / n if n else float("nan")), n

    def agree(a, b, kind=None):
        same = n = 0
        for i in full:
            for k in F[i][a]:
                if kind and k[1] != kind:
                    continue
                n += 1
                same += F[i][a][k] == F[i][b][k]
        return same / n if n else float("nan")

    def goal_acc(read, ids=None):
        ids = ids or full
        return sum(G[i][read] == TG[i] for i in ids) / len(ids)

    def lean(read, kind=None, mask=None):
        l = acc(read, kind, LEFT, mask=mask)[0]
        r = acc(read, kind, RIGHT, mask=mask)[0]
        return (1 - l) - (1 - r)

    def agreed_with(b):
        return lambda i, k: F[i]["orig"][k] == F[i][b][k]

    door_keys = [(i, k) for i in full for k in T[i] if k[1] == "door"]
    n_open = sum(T[i][k] for i, k in door_keys)
    lines = ["C1/F1: {0} frames sampled, {1} with all four reads; {2} failed calls".format(
        len(sample), len(full), failed),
        "  truth: {0} strips with an open door, {1} frames with the goal in view".format(
            n_open, sum(TG[i] != "not_visible" for i in full))]

    lines.append("\n## Accuracy per read (strip fields: floor class, doorway open or not)")
    lines.append("  {0:6s} {1:>7s} {2:>7s} {3:>7s} {4:>7s} {5:>12s} {6:>12s}".format(
        "read", "floor", "door", "both", "goal", "door recall", "false open"))
    for r in READS:
        recall = sum(F[i][r][k] for i, k in door_keys if T[i][k]) / max(1, n_open)
        false_open = (sum(F[i][r][k] for i, k in door_keys if not T[i][k])
                      / max(1, len(door_keys) - n_open))
        lines.append("  {0:6s} {1:7.1%} {2:7.1%} {3:7.1%} {4:7.1%} {5:12.1%} {6:12.1%}".format(
            r, acc(r, "floor")[0], acc(r, "door")[0], acc(r)[0], goal_acc(r), recall, false_open))

    lines.append("\n## Agreement with orig (strip fields)")
    for b in ("orig2", "mirror", "nr"):
        lines.append("  orig vs {0:6s}: all {1:.1%}, floor {2:.1%}, door {3:.1%}".format(
            b, agree("orig", b), agree("orig", b, "floor"), agree("orig", b, "door")))

    single = acc("orig")[0]
    agreed_m, n_m = acc("orig", mask=agreed_with("mirror"))
    agreed_n, n_n = acc("orig", mask=agreed_with("orig2"))
    lines += ["\n## C1",
              "  orig alone: {0:.1%}".format(single),
              "  fields where orig = mirror: {0:.1%} accurate ({1} fields)".format(agreed_m, n_m),
              "  fields where orig = orig2 (control): {0:.1%} accurate ({1} fields)".format(
                  agreed_n, n_n)]
    for kind in ("floor", "door"):
        lines.append("  {0}: orig {1:.1%}, agreed with mirror {2:.1%}, agreed with orig2 "
                     "{3:.1%}".format(kind, acc("orig", kind)[0],
                                      acc("orig", kind, mask=agreed_with("mirror"))[0],
                                      acc("orig", kind, mask=agreed_with("orig2"))[0]))
    lines.append("  lean (error left - error right):")
    for kind in (None, "floor", "door"):
        lines.append("    {0:5s}: orig {1:+.1%}, orig2 {2:+.1%}, mirror {3:+.1%}, "
                     "agreed {4:+.1%}".format(kind or "all", lean("orig", kind),
                                              lean("orig2", kind), lean("mirror", kind),
                                              lean("orig", kind, agreed_with("mirror"))))

    lines.append("\n## By cell (site/arm/door in view): frames, orig acc, orig=mirror agreement")
    for cell in sorted({(sample[i]["site"], sample[i]["arm"], sample[i]["door_in_view"])
                        for i in full}):
        ids = [i for i in full if (sample[i]["site"], sample[i]["arm"],
                                   sample[i]["door_in_view"]) == cell]
        same = sum(F[i]["orig"][k] == F[i]["mirror"][k] for i in ids for k in F[i]["orig"])
        lines.append("  {0}/{1}/{2}: {3}, {4:.1%}, {5:.1%}".format(
            *cell, len(ids), acc("orig", ids=ids)[0], same / (10 * len(ids))))

    lines.append("\n## By instance: frames, orig vs orig2 agreement")
    for inst in sorted({calls[i]["orig"]["instance"] for i in full}):
        ids = [i for i in full if calls[i]["orig"]["instance"] == inst]
        same = sum(F[i]["orig"][k] == F[i]["orig2"][k] for i in ids for k in F[i]["orig"])
        lines.append("  {0}: {1}, {2:.1%}".format(inst, len(ids), same / (10 * len(ids))))

    dis_m, dis_n = 1 - agree("orig", "mirror"), 1 - agree("orig", "orig2")
    gain = agreed_m - single
    lean_o, lean_a = lean("orig"), lean("orig", None, agreed_with("mirror"))
    c_holds = ((gain >= 0.05 and 1 - dis_m >= 0.80)
               or (abs(lean_o) >= 0.10 and abs(lean_a) <= 0.03))
    c_verdict = "REFUTED" if dis_m <= dis_n else ("HOLDS" if c_holds else "no call")
    lines += ["\n## Gate C1",
              "  gain of agreed fields {0:+.1f} pts (>= 5) with agreement {1:.1%} (>= 80%)".format(
                  gain * 100, 1 - dis_m),
              "  lean orig {0:+.1f} pts (|.| >= 10), agreed {1:+.1f} pts (|.| <= 3)".format(
                  lean_o * 100, lean_a * 100),
              "  disagreement orig-mirror {0:.1%} vs orig-orig2 {1:.1%}".format(dis_m, dis_n),
              "  verdict: " + c_verdict]

    lines.append("\n## Gate F1 (nr - orig; counts at >= 3 pts and >= 2x |orig - orig2|)")
    better = worse = False
    for kind in ("floor", "door"):
        d = acc("nr", kind)[0] - acc("orig", kind)[0]
        band = abs(acc("orig2", kind)[0] - acc("orig", kind)[0])
        counts = abs(d) >= 0.03 and abs(d) >= 2 * band
        better |= counts and d > 0
        worse |= counts and d < 0
        lines.append("  {0}: {1:+.1f} pts, band {2:.1f} pts, counts: {3}".format(
            kind, d * 100, band * 100, "yes" if counts else "no"))
    goal_d = goal_acc("nr") - goal_acc("orig")
    lines.append("  goal: {0:+.1f} pts (>= -1)".format(goal_d * 100))
    if worse:
        f_verdict = "no call (mixed)" if better else "REFUTED"
    else:
        f_verdict = "HOLDS" if better and goal_d >= -0.01 else "no call"
    lines.append("  verdict: " + f_verdict)
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
        frames, cells = sample()
        write_jsonl(OUT / "sample.jsonl", frames)
        print(len(frames), "frames; cells before stratifying:", json.dumps(cells, indent=1))
        return 0
    if args.cmd == "run":
        asyncio.run(run_probe(args.shard, args.of))
        return 0
    return score()


if __name__ == "__main__":
    sys.exit(main())
