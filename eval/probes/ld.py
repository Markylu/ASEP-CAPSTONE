#!/usr/bin/env python3
"""Probe LD: lighting and depth perception (model calls).

Pre-rendered frames of walls at known distances under seven lighting
conditions, two single-task reads per frame (w01, g05's floor question alone;
ld01, metres per strip), three repeats, one call at a time per instance.
Method and gate: eval/phase2/_probes/ld/README.md (committed before any call).

    python eval/probes/ld.py poses            # manifest.jsonl, render0.jsonl (set B needs the lane frames)
    eval/godot-xvfb.sh --path first-project res://tools/ld_render.tscn --frame-size=768x768 \\
        -- --manifest=$PWD/eval/phase2/_probes/ld/render0.jsonl --out=$PWD/eval/phase2/_probes/ld/renders
    python eval/probes/ld.py render0          # floor-line rows -> eye height, nearest visible floor
    ... the same render command with manifest.jsonl ...
    python eval/probes/ld.py fidelity         # set B under L0 against the recorded frames
    python eval/probes/ld.py run --stub       # no model: structure and gate wiring
    LITELLM_BASE_URL=http://127.0.0.1:8004 python eval/probes/ld.py run --shard 0 --of 4
    LITELLM_BASE_URL=http://127.0.0.1:8006 python eval/probes/ld.py run --shard 1 --of 4
    python eval/probes/ld.py score
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import math
import os
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("VLM_PROFILE", "remote")
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import r27_probe  # noqa: E402
from agree import calls_of  # noqa: E402
from c1f1 import STRIPS, floor_class, load_sample  # noqa: E402
from common import PROBES, load, metrics, spatial, world_key, write_jsonl  # noqa: E402

OUT = PROBES / "ld"
RENDERS = OUT / "renders"
SET_F = PROBES / "agree"
FLOOR_MAP = r27_probe.FLOOR_MAP  # no_floor -> blocked_near, bottom -> open_near, else open_far
END_OF = {"blocked_near": "no_floor", "open_near": "bottom", "open_far": "middle"}

RIG_SCENE = "res://tools/ld_rig.tscn"
SITE_SCENES = {"s01": "res://sites/s01_occluder_dropin/site.tscn",
               "s02a": "res://sites/s02a_doors_open_a/site.tscn",
               "s02c": "res://sites/s02c_doors_open_c/site.tscn",
               "s02va": "res://sites/s02va_doors_visible_a/site.tscn",
               "s02vc": "res://sites/s02vc_doors_visible_c/site.tscn",
               "s03": "res://sites/s03_fork_deadend/site.tscn"}
EYE_Y = 1.75          # the spawn marker's y; the floor surface is at 0.25
HALF_FOV_TAN = math.tan(math.radians(87.0 / 2.0))
HALF_PX = 384         # half of the 768 frame

DISTANCES = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.3, 1.6, 2.0, 2.5, 3.0, 4.0, 6.0)
ANGLES = (0, 30, 60)
MATERIALS = ("dark", "light")
RENDER0_DISTANCES = (2.0, 3.0, 4.0, 6.0)
LIGHTINGS = ("L0", "L1", "L2", "L3", "L4", "L5", "L6")
READS = ("w01", "ld01")
REPS = 3
N_OPEN_CONTROLS = 43
RAY_M = 15.0          # as r12_probe.true_reach
DIST_BINS = ((0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 5.0),
             (5.0, math.inf))
FAR_READ_M = 8.0
GATE = {"a_move_min": 0.10, "b_move_min": 0.05, "phantom_rise_max": 0.02}


# --- poses ---------------------------------------------------------------------

def rig_truth(d: float, angle_deg: float):
    """One ray down each strip's centre from the camera at (d, 0) facing -x, to
    the wall plane through the origin with normal (cos a, sin a); capped as
    true_reach. Map frame: x, y = -z, headings anticlockwise from +x."""
    a = math.radians(angle_deg)
    n = (math.cos(a), math.sin(a))
    lanes = {}
    for s in STRIPS:
        b = math.radians(180.0 + spatial.strip_offset(s))
        u = (math.cos(b), math.sin(b))
        un = u[0] * n[0] + u[1] * n[1]
        reach = RAY_M
        if un < -1e-9:
            t = -(d * n[0]) / un
            if t > 0:
                reach = min(t, RAY_M)
        lanes[s] = {"reach": round(reach, 2), "floor": floor_class(reach), "door": False}
    return {"goal": "not_visible", "lanes": lanes}


def rig_row(set_name: str, d: float, angle: int, material: str):
    return {"id": "{0}_d{1:.1f}_a{2}_{3}".format(set_name, d, angle, material), "set": set_name,
            "scene": RIG_SCENE, "pos": [d, EYE_Y, 0.0], "yaw": math.pi / 2.0,
            "rig": {"d": d, "angle_deg": angle, "material": material}, "world": None,
            "truth": rig_truth(d, angle)}


def world_of(f):
    """The door state the frame's run was in at this step, for the renderer.
    Needs the run folder (the lane checkouts on sctsvr6); without it, the
    arm's default switch step, flagged."""
    site, arm, step = f["site"], f["arm"], int(f["key"].rsplit("/", 1)[1])
    run = Path(f["frame"]).parents[1]
    source = "run"
    if (run / "decisions.jsonl").exists():
        rows, met = load(run), metrics(run)
    else:
        rows, met, source = [], {}, "fallback"
    key = world_key(site, arm, step, rows, met)
    if site == "s03":
        return {"s03": key[1]}, source
    return {"s02": "final" if key[1] else "initial"}, source


def g05_missed(f, g05) -> bool:
    got = {l["strip"]: l["floor"] for l in g05["lanes"]}
    return any(l["floor"] == "blocked_near" and got.get(s) != "blocked_near"
               for s, l in f["truth"]["lanes"].items())


def poses() -> int:
    a_rows = [rig_row("A", d, a, m) for d in DISTANCES for a in ANGLES for m in MATERIALS]
    r0_rows = [rig_row("R0", d, 0, "light") for d in RENDER0_DISTANCES]

    frames = sorted(load_sample(SET_F), key=lambda f: f["id"])
    g05 = calls_of(SET_F)
    blocked = [f for f in frames if any(l["floor"] == "blocked_near"
                                        for l in f["truth"]["lanes"].values())]
    blocked_ids = {f["id"] for f in blocked}
    open_only = [f for f in frames if f["id"] not in blocked_ids]
    rng = random.Random("ld")
    by_site = {}
    for f in open_only:
        by_site.setdefault(f["site"], []).append(f)
    quota = {s: int(round(N_OPEN_CONTROLS * len(v) / len(open_only))) for s, v in by_site.items()}
    while sum(quota.values()) > N_OPEN_CONTROLS:
        quota[max(quota, key=lambda s: quota[s])] -= 1
    while sum(quota.values()) < N_OPEN_CONTROLS:
        quota[max(by_site, key=lambda s: len(by_site[s]))] += 1
    controls = []
    for site in sorted(by_site):
        controls += rng.sample(by_site[site], quota[site])
    b_rows, sources = [], Counter()
    for f in blocked + sorted(controls, key=lambda f: f["id"]):
        world, source = world_of(f)
        sources[source] += 1
        pose = f["manifest"]["pose"]
        read = (g05.get(f["id"]) or {}).get("g05")
        b_rows.append({"id": f["id"], "set": "B", "scene": SITE_SCENES[f["site"]],
                       "pos": [float(v) for v in pose["position"]], "yaw": float(pose["yaw"]),
                       "rig": None, "world": world, "key": f["key"], "site": f["site"],
                       "arm": f["arm"], "frame": f["frame"], "blocked": f["id"] in blocked_ids,
                       "g05_missed": bool(read and g05_missed(f, read)),
                       "truth": f["truth"]})

    manifest = [dict(r, lighting=L) for L in LIGHTINGS for r in a_rows + b_rows]
    write_jsonl(OUT / "manifest.jsonl", manifest)
    write_jsonl(OUT / "render0.jsonl", [dict(r, lighting="L0") for r in r0_rows])
    print("A: {0} poses; B: {1} poses ({2} with a blocked strip, {3} open controls, "
          "{4} g05 missed a wall); x {5} lightings = {6} renders; render 0: {7}".format(
              len(a_rows), len(b_rows), len(blocked), len(controls),
              sum(r["g05_missed"] for r in b_rows), len(LIGHTINGS), len(manifest),
              len(r0_rows)))
    print("B door state from:", dict(sources))
    if sources["fallback"]:
        print("  fallback = arm default, not the run's own switch: rerun poses on sctsvr6")
    return 0


def load_manifest(path: Path = OUT / "manifest.jsonl"):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def render_path(row) -> Path:
    return RENDERS / row["set"] / row["lighting"] / (row["id"] + ".png")


# --- pixels ----------------------------------------------------------------------

BAND_PX, SMOOTH_ROWS = 20, 6


def luminance_column(png: bytes, x: int):
    """Per-row mean luminance over a band of columns about x, smoothed over a
    few rows. One column alone can sit on a grid line of the wall texture
    (the world-triplanar grid has a line at z = 0, the image centre)."""
    from server.decider import strips
    w, h, bpp, px = strips.decode(png)
    xs = range(max(0, x - BAND_PX), min(w, x + BAND_PX), 2)
    raw = [sum(px[(y * w + xx) * bpp + c] for xx in xs for c in range(3)) / (3.0 * len(xs))
           for y in range(h)]
    return [statistics.mean(raw[y:y + SMOOTH_ROWS]) for y in range(h - SMOOTH_ROWS)], h - SMOOTH_ROWS


def render0() -> int:
    """Where the floor line sits for a wall at a known distance gives the eye
    height: h = (r / 384) * tan(43.5 deg) * d for the line r pixels below the
    image centre. 1.5 m means the nearest visible floor is 1.58 m away, 1.75 m
    means 1.84 m (the figure g05's geometry note assumes)."""
    lines = ["Render 0: floor line against a light wall, column 384"]
    heights = []
    for row in load_manifest(OUT / "render0.jsonl"):
        p = render_path(row)
        if not p.exists():
            lines.append("  {0}: not rendered".format(row["id"]))
            continue
        col, h = luminance_column(p.read_bytes(), HALF_PX)
        wall, floor = statistics.mean(col[HALF_PX - 60:HALF_PX - 10]), statistics.mean(col[-40:])
        cut = (wall + floor) / 2.0
        r = next((y - HALF_PX for y in range(HALF_PX, h) if col[y] < cut), None)
        d = row["rig"]["d"]
        if r is None:
            lines.append("  d={0:.1f}: no floor line found (wall {1:.0f}, floor {2:.0f})".format(
                d, wall, floor))
            continue
        eye = r / HALF_PX * HALF_FOV_TAN * d
        heights.append(eye)
        lines.append("  d={0:.1f}: line {1} px below centre -> eye {2:.2f} m".format(d, r, eye))
    if heights:
        eye = statistics.mean(heights)
        lines.append("  eye height {0:.2f} m (spread {1:.2f}); nearest visible floor {2:.2f} m "
                     "(1.84 assumed in prompt.py g05 note and agent.py)".format(
                         eye, max(heights) - min(heights), eye / HALF_FOV_TAN))
    text = "\n".join(lines) + "\n"
    (OUT / "render0.txt").write_text(text)
    print(text, end="")
    return 0


def fidelity() -> int:
    """Set B under L0 against the frames the model saw in flight: does the
    renderer reproduce the recorded pose and door state?"""
    from server.decider import strips
    shares = []
    lines = ["Fidelity: B/L0 renders against the recorded frames (|delta| < 2 per channel)"]
    for row in load_manifest():
        if row["set"] != "B" or row["lighting"] != "L0":
            continue
        p, orig = render_path(row), Path(row["frame"])
        if not (p.exists() and orig.exists()):
            continue
        a, b = strips.decode(p.read_bytes()), strips.decode(orig.read_bytes())
        if a[:3] != b[:3]:
            lines.append("  {0}: size differs {1} vs {2}".format(row["id"], a[:3], b[:3]))
            continue
        pa, pb = a[3], b[3]
        close = sum(1 for i in range(len(pa)) if abs(pa[i] - pb[i]) < 2)
        shares.append((close / len(pa), row["key"]))
    if shares:
        vals = sorted(s for s, _ in shares)
        lines.append("  {0} frames: median {1:.1%} close, min {2:.1%} ({3}); {4} of {0} at or "
                     "above 90%".format(len(vals), statistics.median(vals), vals[0],
                                        min(shares)[1], sum(v >= 0.9 for v in vals)))
    text = "\n".join(lines) + "\n"
    (OUT / "fidelity.txt").write_text(text)
    print(text, end="")
    return 0


# --- model calls ----------------------------------------------------------------

def distances_from(parsed):
    """ld01's reply, checked: a positive number of metres per strip."""
    from server.decider import vlm
    lanes = []
    for strip in STRIPS:
        v = (parsed.get(strip) or {}).get("metres")
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not (0.0 < v <= 100.0):
            raise vlm.VLMError("distance reader gave no valid metres for {0}".format(strip))
        lanes.append({"strip": strip, "metres": float(v)})
    return {"reason": str(parsed.get("reason", "")), "lanes": lanes}


def stub_result(read: str, row, rng: random.Random, flip: bool):
    """No model: w01 reads the truth back (under --stub-flip, 30% of blocked
    strips under L1 read open, to show the gate fires); ld01 reads 1.1x truth."""
    from server.decider import orchestrator
    if read == "w01":
        parsed: dict = {"reason": "stub"}
        for s in STRIPS:
            end = END_OF[row["truth"]["lanes"][s]["floor"]]
            if flip and row["lighting"] == "L1" and end == "no_floor" and rng.random() < 0.3:
                end = "bottom"
            parsed[s] = {"floor": end}
        return orchestrator.walls_from(parsed, FLOOR_MAP)
    return distances_from({"reason": "stub",
                           **{s: {"metres": row["truth"]["lanes"][s]["reach"] * 1.1}
                              for s in STRIPS}})


def tag(stub: bool, flip: bool) -> str:
    """File prefix: real calls, the plain stub, or the stub that flips L1."""
    return ("stubflip_" if flip else "stub_") if stub else ""


def todo_rows(manifest):
    """Repeat-major: every image once, then every image again, so a repeat is
    never its own prefix-cache neighbour."""
    rows = [r for r in manifest if r["set"] in ("A", "B")]
    return [(rep, read, r) for rep in range(REPS) for read in READS for r in rows]


async def run_probe(shard: int, of: int, limit, stub: bool, flip: bool) -> None:
    from server.decider import config, orchestrator, prompt as prompts, schema, views, vlm
    p_w01, p_ld01 = prompts.get("w01"), prompts.get("ld01")
    rng = random.Random("ld-stub-{0}".format(shard))

    async def call(read, row):
        b64 = base64.b64encode(render_path(row).read_bytes()).decode()
        if read == "w01":
            view = views.wall_reader(p_w01, {}, b64)
            name, sch = schema.WALL_READER_SCHEMA_NAME, schema.wall_reader_schema()

            def validate(parsed):
                return orchestrator.walls_from(parsed, FLOOR_MAP)
        else:
            view = views.wall_reader(p_ld01, {}, b64)
            name, sch = schema.DISTANCE_READER_SCHEMA_NAME, schema.distance_reader_schema()
            validate = distances_from
        sub = await vlm.call_structured(name, view.system, view.text, view.image_b64, sch,
                                        validate, orchestrator.PERCEIVER_MAX_TOKENS)
        return {"result": sub.result, "raw": sub.raw, "rung": sub.rung, "error": sub.error,
                "latency_ms": sub.latency_ms}

    todo = todo_rows(load_manifest())[shard::of]
    if limit:
        todo = todo[:limit]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "{0}calls_{1}of{2}.jsonl".format(tag(stub, flip), shard, of)
    done = set()
    if path.exists():
        done = {(c["set"], c["lighting"], c["id"], c["read"], c["rep"])
                for c in map(json.loads, path.read_text().splitlines())}
    with path.open("a") as fh:
        for n, (rep, read, row) in enumerate(todo):
            key = (row["set"], row["lighting"], row["id"], read, rep)
            if key not in done:  # one at a time: concurrency 1
                if stub:
                    got = {"result": stub_result(read, row, rng, flip), "raw": None,
                           "rung": "stub", "error": None, "latency_ms": 0}
                else:
                    got = await call(read, row)
                fh.write(json.dumps({"set": row["set"], "lighting": row["lighting"],
                                     "id": row["id"], "read": read, "rep": rep,
                                     "key": row.get("key"), "instance": config.LITELLM_BASE_URL,
                                     **got}) + "\n")
                fh.flush()
            if n % 100 == 0:
                print("shard {0}/{1}: {2}/{3} calls".format(shard, of, n + 1, len(todo)),
                      flush=True)
    print("shard {0}/{1}: done on {2}".format(shard, of, config.LITELLM_BASE_URL))


# --- scoring -----------------------------------------------------------------------

def dist_bin(reach: float) -> str:
    for lo, hi in DIST_BINS:
        if lo <= reach < hi:
            return "{0:g}-{1:g}".format(lo, hi) if hi != math.inf else ">{0:g}".format(lo)
    return "?"


def majority(ends):
    c = Counter(ends).most_common()
    top = [e for e, n in c if n == c[0][1]]
    return min(top, key=["no_floor", "bottom", "lower", "middle"].index)


def wall_stats(rows, calls):
    """calls: [(id, result)] for one set, lighting and read w01. Pooled rates,
    majority-of-REPS rates, agreement, and the distance-bin confusion."""
    truth = {r["id"]: r["truth"]["lanes"] for r in rows}
    n = Counter()
    ends = {}
    confusion = Counter()
    for id_, res in calls:
        if not res:
            n["failed"] += 1
            continue
        for l in res["lanes"]:
            t = truth[id_][l["strip"]]
            ends.setdefault((id_, l["strip"]), []).append(l["floor_end"])
            confusion[(dist_bin(t["reach"]), l["floor_end"])] += 1
            if t["floor"] == "blocked_near":
                n["blocked"] += 1
                n["miss"] += l["floor"] != "blocked_near"
            else:
                n["open"] += 1
                n["phantom"] += l["floor"] == "blocked_near"
    m = Counter()
    for (id_, s), es in ends.items():
        t = truth[id_][s]
        if len(es) == REPS:
            m["full"] += 1
            m["agree"] += len(set(es)) == 1
        cls = FLOOR_MAP[majority(es)]
        if t["floor"] == "blocked_near":
            m["blocked"] += 1
            m["miss"] += cls != "blocked_near"
        else:
            m["open"] += 1
            m["phantom"] += cls == "blocked_near"
    return {"calls": len(calls), "failed": n["failed"],
            "missed": n["miss"] / max(1, n["blocked"]), "phantom": n["phantom"] / max(1, n["open"]),
            "maj_missed": m["miss"] / max(1, m["blocked"]),
            "maj_phantom": m["phantom"] / max(1, m["open"]),
            "agree": m["agree"] / max(1, m["full"]), "confusion": confusion}


def distance_stats(rows, calls):
    truth = {r["id"]: r["truth"]["lanes"] for r in rows}
    logs, bias, within, far, per_strip, failed = [], [], 0, Counter(), {}, 0
    ests = {}
    for id_, res in calls:
        if not res:
            failed += 1
            continue
        for l in res["lanes"]:
            t = truth[id_][l["strip"]]["reach"]
            ests.setdefault((id_, l["strip"]), []).append(l["metres"])
            if t >= RAY_M:
                far["n"] += 1
                far["far_read"] += l["metres"] >= FAR_READ_M
                continue
            e = math.log(l["metres"] / t)
            logs.append(abs(e))
            bias.append(e)
            within += abs(e) <= math.log(1.5)
            per_strip.setdefault(l["strip"], []).append(abs(e))
    spread = [max(v) / min(v) <= 1.5 for v in ests.values() if len(v) == REPS]
    return {"calls": len(calls), "failed": failed, "n": len(logs),
            "med_abs_log": statistics.median(logs) if logs else math.nan,
            "within_1_5": within / max(1, len(logs)),
            "bias": statistics.median(bias) if bias else math.nan,
            "far_read": far["far_read"] / max(1, far["n"]),
            "per_strip": {s: statistics.median(v) for s, v in per_strip.items()},
            "agree": sum(spread) / max(1, len(spread))}


def score(stub: bool = False, flip: bool = False) -> int:
    manifest = load_manifest()
    rows = {}
    for r in manifest:
        rows.setdefault((r["set"], r["lighting"]), []).append(r)
    calls = {}
    latency = []
    prefix = tag(stub, flip)
    for fp in sorted(OUT.glob(prefix + "calls_*of*.jsonl")):
        for c in map(json.loads, fp.read_text().splitlines()):
            calls.setdefault((c["set"], c["lighting"], c["read"]), []).append(
                (c["id"], c["result"]))
            if c.get("latency_ms"):
                latency.append(c["latency_ms"])
    lines = ["Probe LD: lighting and depth perception, w01 and ld01 on pre-rendered frames, "
             "concurrency 1" + (" (STUB, no model{0})".format(", L1 flipped" if flip else "")
                                if stub else "")]
    W, D = {}, {}
    for set_name in ("A", "B"):
        lines.append("\n## Set {0}: {1} poses x {2} lightings".format(
            set_name, len(rows.get((set_name, "L0"), [])), len(LIGHTINGS)))
        lines.append("  w01    {0:>6s} {1:>8s} {2:>8s} {3:>10s} {4:>10s} {5:>7s} {6:>6s}".format(
            "calls", "missed", "phantom", "maj miss", "maj phant", "agree", "fail"))
        for L in LIGHTINGS:
            w = W[(set_name, L)] = wall_stats(rows.get((set_name, L), []),
                                              calls.get((set_name, L, "w01"), []))
            lines.append("  {0:6s} {1:6d} {2:8.1%} {3:8.1%} {4:10.1%} {5:10.1%} {6:7.1%} {7:6d}"
                         .format(L, w["calls"], w["missed"], w["phantom"], w["maj_missed"],
                                 w["maj_phantom"], w["agree"], w["failed"]))
        lines.append("  ld01   {0:>6s} {1:>9s} {2:>8s} {3:>7s} {4:>8s} {5:>7s} {6:>6s}".format(
            "calls", "med|log|", "in x1.5", "bias", "far>=8", "agree", "fail"))
        for L in LIGHTINGS:
            d = D[(set_name, L)] = distance_stats(rows.get((set_name, L), []),
                                                  calls.get((set_name, L, "ld01"), []))
            lines.append("  {0:6s} {1:6d} {2:9.3f} {3:8.1%} {4:+7.2f} {5:8.1%} {6:7.1%} {7:6d}"
                         .format(L, d["calls"], d["med_abs_log"], d["within_1_5"], d["bias"],
                                 d["far_read"], d["agree"], d["failed"]))
        lines.append("  ld01 median |log(est/true)| per strip, L0: " + ", ".join(
            "{0} {1:.2f}".format(s, D[(set_name, "L0")]["per_strip"].get(s, math.nan))
            for s in STRIPS))
        lines.append("  w01 confusion, L0 (truth distance bin -> floor end, pooled reads):")
        conf = W[(set_name, "L0")]["confusion"]
        bins = [dist_bin(lo + 0.01) for lo, _ in DIST_BINS]
        lines.append("  {0:>8s} {1}".format("bin", " ".join("{0:>9s}".format(e)
                                                            for e in FLOOR_MAP)))
        for b in bins:
            lines.append("  {0:>8s} {1}".format(b, " ".join("{0:9d}".format(conf[(b, e)])
                                                            for e in FLOOR_MAP)))
    missed_ids = {r["id"] for r in manifest if r["set"] == "B" and r.get("g05_missed")}
    if missed_ids:
        lines.append("\n## Set B, frames where g05 missed a wall in flight: w01 per lighting")
        for L in LIGHTINGS:
            sub = [r for r in rows.get(("B", L), []) if r["id"] in missed_ids]
            w = wall_stats(sub, [c for c in calls.get(("B", L, "w01"), []) if c[0] in missed_ids])
            lines.append("  {0:6s} missed {1:6.1%}  phantom {2:6.1%}  ({3} frames)".format(
                L, w["missed"], w["phantom"], len(sub)))
    if latency:
        lines.append("\n  median latency {0:.0f} ms over {1} calls".format(
            statistics.median(latency), len(latency)))

    lines.append("\n## Gate (set before any call; A: under-1 m missed rate moves >= 10 pts vs L0,"
                 " phantom <= L0 + 2 pts when improving; B: >= 5 pts the same way, same rule)")
    verdicts = {}
    for L in LIGHTINGS[1:]:
        a0, a, b0, b = W[("A", "L0")], W[("A", L)], W[("B", "L0")], W[("B", L)]
        a_move, b_move = a["missed"] - a0["missed"], b["missed"] - b0["missed"]
        a_ph, b_ph = a["phantom"] - a0["phantom"], b["phantom"] - b0["phantom"]
        a_ok = (abs(a_move) >= GATE["a_move_min"]
                and (a_move > 0 or a_ph <= GATE["phantom_rise_max"]))
        b_ok = (abs(b_move) >= GATE["b_move_min"] and (b_move > 0) == (a_move > 0)
                and (b_move > 0 or b_ph <= GATE["phantom_rise_max"]))
        verdicts[L] = "matters" if a_ok and b_ok else ("A only" if a_ok else "no")
        lines.append("  {0:4s} A missed {1:+6.1f} pts (phantom {2:+5.1f})  B missed {3:+6.1f} pts"
                     " (phantom {4:+5.1f})  {5}".format(L, 100 * a_move, 100 * a_ph,
                                                         100 * b_move, 100 * b_ph, verdicts[L]))
    if any(v == "matters" for v in verdicts.values()):
        verdict = "HOLDS: lighting matters ({0})".format(
            ", ".join(L for L, v in verdicts.items() if v == "matters"))
    elif any(v == "A only" for v in verdicts.values()):
        verdict = "NO CALL: moves on the rig only ({0})".format(
            ", ".join(L for L, v in verdicts.items() if v == "A only"))
    else:
        verdict = "REFUTED: no lighting moves the rig's missed walls by 10 pts"
    lines.append("  verdict: " + verdict)
    text = "\n".join(lines) + "\n"
    (OUT / (prefix + "score.txt")).write_text(text)
    print(text, end="")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("poses", "render0", "fidelity", "run", "score"))
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--stub", action="store_true", help="no model: the truth read back")
    ap.add_argument("--stub-flip", action="store_true",
                    help="with --stub: 30%% of blocked strips under L1 read open")
    args = ap.parse_args()
    if args.cmd == "poses":
        return poses()
    if args.cmd == "render0":
        return render0()
    if args.cmd == "fidelity":
        return fidelity()
    if args.cmd == "run":
        asyncio.run(run_probe(args.shard, args.of, args.limit, args.stub, args.stub_flip))
        return 0
    return score(stub=args.stub, flip=args.stub_flip)


if __name__ == "__main__":
    sys.exit(main())
