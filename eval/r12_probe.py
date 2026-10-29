"""R12 probe for a17 (staged search with a coverage map), on recorded runs
(eval/phase2/R12_staged_search/README.md).

Code-only lines, no model (`offline`), scored against the 2D site model of
R11's failure analysis (eval/phase2/R11_goal_default/analysis/geo.py; s03's
exit doors are taken as open, the model not knowing which one closed):
3. Coverage: runs where ground within 1 m of the goal is marked searched before
   the goal was first reported (a false "empty", which would block the goal
   off), gated; and, reported as g03's baseline, the share of searched cells
   truly in line of sight from the look's pose (gated live on g04, line 7).
4. Reachability: at R11's 38 q03 calls, a17's top search target is inside a
   wall or not truly reachable from the drone (R11's goal-side frontier: 37/38).

The perceiver is g03 as recorded, so open_far runs its old 6 m; g04's classes
are checked live (line 7):
7. g04 asked on every recorded step's clean frame (`run-g04`, the model the VLM
   profile names), then scored (`score-g04`): the share of searched cells truly
   in line of sight with a17's memory rebuilt on g04's reports, and the share
   of strips whose true clear distance is under 1 m that g04 reads as anything
   but blocked_near.

    python eval/r12_probe.py offline
    VLM_PROFILE=remote python eval/r12_probe.py run-g04 RUNS --out g04.jsonl
    python eval/r12_probe.py score-g04 g04.jsonl RUNS

Evaluation only: the probe reads the manifest's goal ground truth to score.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))
sys.path.insert(0, str(REPO_ROOT / "eval/phase2/R11_goal_default/analysis"))

from server.decider import spatial  # noqa: E402
from spatial_replay import label, load, runs_under, true_goal  # noqa: E402
import geo  # noqa: E402

PHASE2 = REPO_ROOT / "eval/phase2"
COVERAGE_ROUNDS = ["R10_goal_planner", "R11C_a14_control", "R11_goal_default"]

#: The gate (README, "Probe gate").
GATE = {"coverage_los_min": 0.90, "goal_searched_runs_max": 2, "unreachable_max": 5,
        "false_caught_min": 0.80, "true_lost_max": 0.05, "blocked_read_open_max": 0.15}

#: Line 7: a strip is truly blocked near when its centre ray meets a wall under this.
BLOCKED_TRUE_M = 1.0
#: Line 7: true clear-distance bins for g04's confusion table.
REACH_BINS = [(0.0, 1.0), (1.0, 3.0), (3.0, 5.0), (5.0, 8.0), (8.0, 99.0)]


def site_arm(run: Path) -> Tuple[str, str]:
    return run.parts[-3], run.parts[-2]


def memory_a17(rows: List[Dict[str, Any]], k: int) -> spatial.SpatialMemory:
    r = rows[k]
    return spatial.rebuild(rows[:k], r["manifest"], (r.get("perceiver") or {}).get("result"),
                           cfg=spatial.A17)


def centre(c: Tuple[int, int]) -> spatial.Point:
    return ((c[0] + 0.5) * spatial.CELL_M, (c[1] + 0.5) * spatial.CELL_M)


def coverage(run: Path, rows: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    rows = rows if rows is not None else load(run)
    site, arm = site_arm(run)
    mem = memory_a17(rows, len(rows) - 1)
    pose = {s: (x, y) for s, x, y, _ in mem.trail}
    total = clear = 0
    for look in mem.looks:
        here = pose.get(look.step)
        if here is None:
            continue
        free = geo.world(site, arm, look.step)
        for c in look.cells:
            total += 1
            clear += geo.segment_clear(free, here, centre(c))
    # A false "empty": ground within 1 m of the goal searched before the
    # perceiver first reported the goal (after that the goal stage steers).
    goal = true_goal(rows)
    first = min((r["step"] for r in rows
                 if ((r.get("perceiver") or {}).get("result") or {}).get("goal") in spatial.STRIPS),
                default=None)
    goal_searched = goal is not None and any(
        spatial.dist(centre(c), goal) < 1.0 and (first is None or s < first)
        for c, s in mem.seen.items())
    return {"cells": total, "in_sight": clear, "goal_searched": goal_searched}


def flood(free: Callable[[float, float], bool], start: spatial.Point,
          res: float = 0.25) -> set:
    def key(p: spatial.Point) -> Tuple[int, int]:
        return (int(math.floor(p[0] / res)), int(math.floor(p[1] / res)))
    s = key(start)
    out, todo = {s}, [s]
    while todo:
        c = todo.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + dx, c[1] + dy)
            if n not in out and free((n[0] + 0.5) * res, (n[1] + 0.5) * res):
                out.add(n)
                todo.append(n)
    return out


def reachability() -> Dict[str, Any]:
    calls = unreachable = inside = none = 0
    for run in runs_under(PHASE2 / "R11_goal_default/runs"):
        rows = load(run)
        site, arm = site_arm(run)
        for k, r in enumerate(rows):
            if not r.get("strategist"):
                continue
            here = spatial.pose_xyh(r["manifest"].get("pose"))
            if here is None:
                continue
            calls += 1
            mem = memory_a17(rows, k)
            top = mem.search_frontiers(here[:2])
            if not top:
                none += 1
                continue
            p = top[0][0]
            free = geo.world(site, arm, r["step"])
            if not free(*p):
                inside += 1
                unreachable += 1
                continue
            res = 0.25
            if (int(math.floor(p[0] / res)), int(math.floor(p[1] / res))) not in flood(free, here[:2]):
                unreachable += 1
    return {"calls": calls, "unreachable": unreachable, "inside_wall": inside, "no_target": none}


def in_view(r: Dict[str, Any], half_fov: float = 60.0) -> bool:
    """Genuine sighting: line of sight, and the goal within the frame or just
    past its edge (the sphere's glow reaches past 43.5 degrees)."""
    g = r["manifest"].get("goal") or {}
    return bool(g.get("line_of_sight")) and abs(g.get("bearing_deg", 180.0)) <= half_fov


def los(r: Dict[str, Any]) -> bool:
    return bool((r["manifest"].get("goal") or {}).get("line_of_sight"))


def stage_replay(run: Path) -> Dict[str, Any]:
    """a17's stage machine driven open-loop along a recorded run: the recorded
    poses and perceiver reports, q04 stubbed to the first item on its menu.
    Scores each sighting: genuine (goal truly in view) or not, and whether the
    belief resting on it was disproved within `HORIZON` steps."""
    from server.decider import planner
    rows = load(run)
    state = planner.StageState()
    target, mode, last_called = None, None, None
    sightings: List[Dict[str, Any]] = []
    disproved: Dict[int, bool] = {}  # step -> goal truly in line of sight then
    stages = {"explore": 0, "goal": 0}
    asks = 0
    for k, r in enumerate(rows):
        mem = memory_a17(rows, k)
        res = (r.get("perceiver") or {}).get("result") or {}
        manifest = {kk: v for kk, v in r["manifest"].items() if kk != "goal"}
        here = spatial.pose_xyh(manifest.get("pose"))
        for s in sightings:
            # Did a later look within the horizon face the believed point?
            if (s["belief"] is not None and here is not None
                    and s["step"] < r["step"] <= s["step"] + HORIZON
                    and abs(spatial.wrap(spatial.bearing(here[:2], s["belief"]) - here[2]))
                    <= spatial.FOV_DEG / 2.0 - 4.0):
                s["faced"] = True
        out = planner.staged(mem, manifest, res, state, target, mode, last_called)
        if res.get("goal") in spatial.STRIPS:
            b = mem.goal_belief(since=out.state.rays_since)
            sightings.append({"step": r["step"], "genuine": in_view(r), "faced": False,
                              "belief": b[:2] if b else None})
        if "lost" in out.events:
            disproved[r["step"]] = los(r)
        target, mode, state = out.target, out.mode, out.state
        if out.ask is not None:
            asks += 1
            last_called = r["step"]
            target = out.menu[0] if out.menu else None
            mode = "explore" if out.state.stage == "explore" else "detour"
            state.target_dist_m = None
        stages[state.stage] += 1
    return {"sightings": sightings, "disproved": disproved, "stages": stages, "asks": asks,
            "steps": len(rows)}


HORIZON = 3


def hallucination_line() -> Dict[str, Any]:
    """False sightings (no line of sight, or more than 60 degrees off): of those
    a later look faced within the horizon, the share disproved (gated; the
    open-loop drone does not turn toward a17's belief, so unfaced ones say
    nothing), and of all, the share. Genuine sightings: the share whose belief
    was disproved while the goal was still truly in line of sight (gated);
    those dropped after it went out of sight (a door closing in `dynamic`) are
    counted apart."""
    c = {"false": 0, "false_faced": 0, "false_faced_caught": 0, "false_caught": 0,
         "true": 0, "true_lost_los": 0, "true_lost_occluded": 0}
    stages = {"explore": 0, "goal": 0}
    asks = steps = 0
    for rnd in ["R11_goal_default", "R11C_a14_control"]:
        for run in runs_under(PHASE2 / rnd / "runs"):
            out = stage_replay(run)
            for k in stages:
                stages[k] += out["stages"][k]
            asks += out["asks"]
            steps += out["steps"]
            for s in out["sightings"]:
                hit = [d for d in out["disproved"] if s["step"] < d <= s["step"] + HORIZON + 1]
                if s["genuine"]:
                    c["true"] += 1
                    if hit:
                        c["true_lost_los" if out["disproved"][hit[0]] else "true_lost_occluded"] += 1
                else:
                    c["false"] += 1
                    c["false_caught"] += bool(hit)
                    if s["faced"]:
                        c["false_faced"] += 1
                        c["false_faced_caught"] += bool(hit)
    return dict(c, stages=stages, asks=asks, steps=steps)


def smoke_run(run: Path, work: Path, strip_goal: bool) -> List[Dict[str, Any]]:
    """a17's real step (orchestrator.decide) over a run's recorded manifests,
    with stub replies: the perceiver as recorded, q04 the first item listed,
    the navigator the recorded pick where offered. With `strip_goal` the
    manifests reach decide() with no goal block at all."""
    import asyncio
    import types
    from server.decider import orchestrator, recorder, schema, vlm
    rows = load(run)
    cur: Dict[str, Any] = {}

    async def stub(name, system, text, image_b64, json_schema, validate, max_tokens,
                   follow_up=None):
        rec = cur["rec"]
        if name == schema.PERCEIVER_SCHEMA_NAME:
            return vlm.SubCall(name, (rec.get("perceiver") or {}).get("result"), "stub")
        if name == schema.STRATEGIST_SCHEMA_NAME:
            ids = json_schema["properties"]["target"]["enum"]
            return vlm.SubCall(name, validate({"reason": "stub", "mode": "explore",
                                               "target": ids[0]}), "stub")
        if name == schema.CONFIRMER_SCHEMA_NAME:
            # Refuse every other report, so both branches run.
            cur["confirms"] = cur.get("confirms", 0) + 1
            return vlm.SubCall(name, validate({"reason": "stub", "present":
                                               "no" if cur["confirms"] % 2 else "yes"}), "stub")
        if name == schema.DOOR_CONFIRMER_SCHEMA_NAME:
            # Alternate open, closed, none over the reported strips.
            strips = [k for k in json_schema["properties"] if k != "reason"]
            cur["doors"] = cur.get("doors", 0) + 1
            answers = ["open", "closed", "none"]
            return vlm.SubCall(name, validate(dict(
                {"reason": "stub"},
                **{s: answers[(cur["doors"] + i) % 3] for i, s in enumerate(strips)})), "stub")
        enum = json_schema["properties"]["action"]["enum"]
        pick = rec["index"] if rec.get("index") in enum else enum[0]
        return vlm.SubCall(name, validate({"action": pick, "reason": "stub"}), "stub")

    real = vlm.call_structured
    vlm.call_structured = stub
    try:
        r = recorder.Run("smoke-" + "-".join(run.parts[-3:]), work / label(run))
        r.ensure()
        for rec in rows:
            cur["rec"] = rec
            manifest = rec["manifest"]
            if strip_goal:
                manifest = {k: v for k, v in manifest.items() if k != "goal"}
            request = types.SimpleNamespace(
                manifest=manifest, step=rec["step"], frame_size=rec.get("frame_size"),
                frame_png_b64="AA==", clean_frame_png_b64="AA==")
            asyncio.run(orchestrator.decide(request, r, rec.get("frame")))
        return recorder._read_jsonl(r.decisions)
    finally:
        vlm.call_structured = real


#: Fields that differ between two smoke runs for reasons other than the agent.
VOLATILE = {"manifest", "t", "clean_frame", "latency_ms", "step_latency_ms", "timing"}


def cmd_smoke(args: argparse.Namespace) -> int:
    """Line 6: a17 decides the same with and without the manifest's goal block,
    on every step of the runs under `root`; plus counts of what it did."""
    import json
    import os
    import tempfile
    from collections import Counter
    os.environ["VLM_AGENT"] = args.agent
    differ = errors = steps = asks = 0
    stages: Counter = Counter()
    events: Counter = Counter()
    toward_bad = 0
    example = None
    with tempfile.TemporaryDirectory() as tmp:
        for run in runs_under(Path(args.root).resolve()):
            with_goal = smoke_run(run, Path(tmp) / "with", False)
            without = smoke_run(run, Path(tmp) / "without", True)
            for a, b in zip(with_goal, without):
                steps += 1
                errors += bool(a.get("error")) + bool(b.get("error"))
                strip = lambda d: json.dumps({k: v for k, v in d.items() if k not in VOLATILE},
                                             sort_keys=True)
                if strip(a) != strip(b):
                    differ += 1
                stages[(a.get("stage") or {}).get("stage")] += 1
                events.update((a.get("evaluator") or {}).get("events") or [])
                if a.get("strategist"):
                    asks += 1
                    example = example or a["strategist"]["text"]
                toward_bad += sum(1 for notes in (a.get("tags") or {}).values()
                                  if spatial.WORDS["toward_target"] in notes
                                  and any(n.startswith(("blocked", "stopped short", "wall close"))
                                          for n in notes))
            errors += abs(len(with_goal) - len(without))
    ok = differ == 0 and errors == 0
    print("6. no goal truth: decisions {0}; differ with and without the goal block {1}; "
          "failed steps {2} -> {3}".format(steps, differ, errors, "pass" if ok else "FAIL"))
    print("   stages {0}; q04 calls {1} ({2:.0%}); events {3}; 'toward' on a not-open "
          "action {4}".format(dict(stages), asks, asks / max(1, steps), dict(events), toward_bad))
    print("\nfirst q04 text:\n" + (example or "(none)"))
    return 0 if ok else 1


def cmd_offline(_args: argparse.Namespace) -> int:
    ok = True
    print("3. coverage against geometry (a17 memory, g03 as recorded)")
    for rnd in COVERAGE_ROUNDS:
        total = clear = searched = 0
        bad = []
        for run in runs_under(PHASE2 / rnd / "runs"):
            c = coverage(run)
            total += c["cells"]
            clear += c["in_sight"]
            if c["goal_searched"]:
                searched += 1
                bad.append(label(run))
        # The in-sight share is g03's baseline only: its open_far misreads walls
        # within 1 m a third of the time, which g04 is built to fix, so the
        # share is gated live on g04's reads (line 7).
        share = clear / max(1, total)
        line_ok = searched <= GATE["goal_searched_runs_max"]
        ok &= line_ok
        print("   {0}: searched cells in sight {1}/{2} ({3:.1%}); goal ground searched in {4} "
              "runs {5} -> {6}".format(rnd, clear, total, share, searched, bad,
                                      "pass" if line_ok else "FAIL"))
    print("4. reachability at R11's q03 calls")
    r = reachability()
    line_ok = r["unreachable"] <= GATE["unreachable_max"]
    ok &= line_ok
    print("   calls {calls}; top target unreachable {unreachable} (inside a wall {inside_wall}); "
          "no target {no_target} -> ".format(**r) + ("pass" if line_ok else "FAIL"))
    print("5. sightings disproved within {0} steps (stage machine open-loop on R11, R11C)".format(
        HORIZON))
    h = hallucination_line()
    false_share = h["false_faced_caught"] / max(1, h["false_faced"])
    true_share = h["true_lost_los"] / max(1, h["true"])
    line_ok = false_share >= GATE["false_caught_min"] and true_share <= GATE["true_lost_max"]
    ok &= line_ok
    print("   false sightings: faced later {false_faced_caught}/{false_faced} disproved "
          "(all: {false_caught}/{false})".format(**h))
    print("   genuine sightings: disproved with the goal in sight {true_lost_los}/{true}; "
          "after it went out of sight {true_lost_occluded}".format(**h)
          + " -> " + ("pass" if line_ok else "FAIL"))
    print("   steps {0}: explore {1}, goal {2}; q04 asked {3} ({4:.0%})".format(
        h["steps"], h["stages"]["explore"], h["stages"]["goal"], h["asks"],
        h["asks"] / max(1, h["steps"])))
    print("offline gate: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# --- line 7, live: g04 on recorded clean frames ------------------------------------

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    import json
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def cmd_run_g04(args: argparse.Namespace) -> int:
    """Ask --agent's perceiver (a17: g04, a18: g05) on each recorded step's
    clean frame, the manifest without its goal block as decide() would send it.
    Appends to --out and skips steps done."""
    import asyncio
    import base64
    import json
    from server.decider import agent, orchestrator, prompt as prompts, schema, views, vlm
    features = agent.get(args.agent).features["orchestrator"]
    p = prompts.get(features["perceiver"])
    floor_map = features.get("floor_map")
    out = Path(args.out)
    done = {(j["run"], j["step"]) for j in _read_jsonl(out) if j.get("result")}
    items = [(run, r) for run in runs_under(Path(args.root).resolve()) for r in load(run)
             if r.get("clean_frame") and (label(run), r["step"]) not in done]
    print("{0} steps to ask, {1} done".format(len(items), len(done)), flush=True)

    async def one(sem: asyncio.Semaphore, n: int, run: Path, r: Dict[str, Any]) -> None:
        async with sem:
            b64 = base64.b64encode((run / r["clean_frame"]).read_bytes()).decode()
            view = views.perceiver(p, orchestrator.without_goal(r["manifest"]), b64)
            call = await vlm.call_structured(
                schema.PERCEIVER_SCHEMA_NAME, view.system, view.text, view.image_b64,
                schema.perceiver_schema(p.version),
                lambda parsed: orchestrator.perception_from(parsed, p.version, floor_map),
                orchestrator.PERCEIVER_MAX_TOKENS)
            with out.open("a") as handle:
                handle.write(json.dumps({"run": label(run), "step": r["step"],
                                         "prompt": p.version, "result": call.result,
                                         "error": call.error,
                                         "latency_ms": round(call.latency_ms, 1)}) + "\n")
            print("{0}/{1} {2} step {3}: {4}".format(n + 1, len(items), label(run), r["step"],
                                                      "ok" if call.result else call.error),
                  flush=True)

    async def go() -> None:
        sem = asyncio.Semaphore(args.concurrency)
        try:
            await asyncio.gather(*(one(sem, n, run, r) for n, (run, r) in enumerate(items)))
        finally:
            await vlm.aclose()

    asyncio.run(go())
    return 0


def true_reach(free: Callable[[float, float], bool], here: spatial.Point, heading: float,
               cap: float = 15.0, res: float = 0.1) -> float:
    """Evaluation only: how far a ray from `here` runs before the site model's wall."""
    d = res
    while d <= cap:
        p = spatial.ahead(here, heading, d)
        if not free(p[0], p[1]):
            return d
        d += res
    return cap


def cmd_score_g04(args: argparse.Namespace) -> int:
    """Line 7, scored on g04's answers against R11's site model."""
    from collections import Counter
    answers = {(j["run"], j["step"]): j.get("result") for j in _read_jsonl(Path(args.answers))}
    total = clear = steps = missing = blocked = read_open = 0
    confusion: Counter = Counter()
    ends: Counter = Counter()
    for run in runs_under(Path(args.root).resolve()):
        site, arm = site_arm(run)
        rows = []
        for r in load(run):
            g04 = answers.get((label(run), r["step"]))
            steps += 1
            missing += g04 is None
            rows.append(dict(r, perceiver={"result": g04}))
            here = spatial.pose_xyh(r["manifest"].get("pose"))
            if g04 is None or here is None:
                continue
            free = geo.world(site, arm, r["step"])
            for lane in g04.get("lanes") or []:
                if lane.get("strip") not in spatial.STRIPS:
                    continue
                d = true_reach(free, here[:2], (here[2] + spatial.strip_offset(lane["strip"]))
                               % 360.0)
                bin_ = next(b for b in REACH_BINS if b[0] <= d < b[1])
                confusion[(bin_, lane.get("floor"))] += 1
                if lane.get("floor_end"):
                    ends[(bin_, lane["floor_end"])] += 1
                if d < BLOCKED_TRUE_M:
                    blocked += 1
                    read_open += lane.get("floor") != "blocked_near"
        cov = coverage(run, rows)
        total += cov["cells"]
        clear += cov["in_sight"]
    share = clear / max(1, total)
    open_share = read_open / max(1, blocked)
    ok = (share >= GATE["coverage_los_min"] and open_share < GATE["blocked_read_open_max"]
          and missing == 0)
    print("7. g04 reads: steps {0}, no answer {1}".format(steps, missing))
    print("   searched cells in line of sight {0}/{1} = {2:.1%} (gate >= {3:.0%})".format(
        clear, total, share, GATE["coverage_los_min"]))
    print("   strips truly blocked under {0} m read as not blocked_near {1}/{2} = {3:.1%} "
          "(gate < {4:.0%})".format(BLOCKED_TRUE_M, read_open, blocked, open_share,
                                    GATE["blocked_read_open_max"]))
    classes = list(spatial.PARAMS_A17["floor_range_m"])
    print("\n   true clear distance (m) x g04 floor class, strips")
    print("   {0:>9} ".format("") + " ".join("{0:>13}".format(c) for c in classes))
    for b in REACH_BINS:
        print("   {0:>9} ".format("{0:g}-{1:g}".format(*b)) +
              " ".join("{0:>13}".format(confusion[(b, c)]) for c in classes))
    if ends:
        from server.decider import schema
        print("\n   true clear distance (m) x g05 floor end, strips")
        print("   {0:>9} ".format("") + " ".join("{0:>13}".format(c)
                                                  for c in schema.FLOOR_ENDS_G05))
        for b in REACH_BINS:
            print("   {0:>9} ".format("{0:g}-{1:g}".format(*b)) +
                  " ".join("{0:>13}".format(ends[(b, c)]) for c in schema.FLOOR_ENDS_G05))
    print("line 7: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("offline").set_defaults(fn=cmd_offline)
    smoke = sub.add_parser("smoke")
    smoke.add_argument("root", nargs="?", default=str(PHASE2 / "R11_goal_default/runs"))
    smoke.add_argument("--agent", default="a17")
    smoke.set_defaults(fn=cmd_smoke)
    run = sub.add_parser("run-g04", help="line 7: ask g04 on recorded clean frames (live)")
    run.add_argument("root")
    run.add_argument("--out", required=True)
    run.add_argument("--concurrency", type=int, default=4)
    run.add_argument("--agent", default="a17", help="whose perceiver and floor map (a17, a18)")
    run.set_defaults(fn=cmd_run_g04)
    score = sub.add_parser("score-g04", help="line 7: score g04's answers against geometry")
    score.add_argument("answers")
    score.add_argument("root", nargs="?", default=str(PHASE2 / "R11_goal_default/runs"))
    score.set_defaults(fn=cmd_score_g04)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
