"""R13 probe for a20 (explore, goal, verify) and a21 (a20 with the goal's true
position in the strategist's text), on synthetic steps and R12's recorded runs
(eval/phase2/R13_verify/README.md).

1. Transitions (`transitions`), synthetic, gated: explore -> goal -> verify ->
   goal with the sighting kept or overridden; a check look that fails; a check
   that needs a fresh look; an 8-step timeout; no path back; a standing detour
   that holds goal.
2. Smoke (`smoke`), gated: the real step (orchestrator.decide) over R12's
   recorded manifests with stub replies. a20 decides the same with and without
   the manifest's goal block; a21 decides the same as a20 except the
   strategist's text, which carries the goal's position, and no navigator text
   does; no step fails.
3. Open-loop count (`offline`), reported, not gated: a20's stage machine along
   R12's recorded paths (poses and g05 reports as recorded, the strategist the
   first item listed). Goal-to-verify episodes and how each ended, and the
   sightings scored against the manifest's line of sight. The recorded drone
   never turns back toward a vantage, so the check-look counts are a floor.

    python3 eval/r13_probe.py transitions
    python3 eval/r13_probe.py smoke eval/phase2/R12_staged_search/runs
    python3 eval/r13_probe.py offline

Evaluation only: the probe reads the manifest's goal ground truth to score.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))

from server.decider import planner, spatial  # noqa: E402
from spatial_replay import label, load, runs_under  # noqa: E402
from r12_probe import VOLATILE, in_view, los, memory_a17, smoke_run  # noqa: E402

PHASE2 = REPO_ROOT / "eval/phase2"

#: Record fields that name the agent, and so differ between a20 and a21.
IDENTITY = {"agent_version", "agent_sha", "subagent_prompts", "planner_a20_sha"}


# --- 1. transitions, synthetic ----------------------------------------------------

ACTIONS = [{"index": 0, "r": 0.0, "theta": math.pi, "theta_deg": 180.0, "turn_around": True}] + [
    {"index": i + 1, "r": 1.7, "theta": math.radians(t), "theta_deg": t, "turn_around": False}
    for i, t in enumerate((43.5, 21.75, 0.0, -21.75, -43.5))]


def perception(goal: Optional[str]) -> Dict[str, Any]:
    return {"goal": goal or "not_visible", "goal_range": "mid" if goal else None,
            "lanes": [{"strip": s, "floor": "open_far", "doorway": False}
                      for s in spatial.STRIPS]}


def manifest(step: int, x: float, y: float, heading: float) -> Dict[str, Any]:
    """A manifest at map point (x, y) facing `heading` (map degrees)."""
    return {"step": step, "actions": ACTIONS,
            "pose": {"position": [x, 1.75, -y], "yaw": math.radians(heading - 90.0)}}


def drive(seq: List[Tuple[float, float, float, Optional[str]]],
          detour_at: Optional[int] = None) -> List[planner.Staged]:
    """a20's stage machine over synthetic looks (x, y, heading, goal strip), the
    strategist answering with the first place listed. `detour_at`: from that
    step on, a standing detour 20 m away holds."""
    records: List[Dict[str, Any]] = []
    state = planner.VerifyState()
    target, mode, last_called = None, None, None
    out = []
    for step, (x, y, h, goal) in enumerate(seq):
        m = manifest(step, x, y, h)
        p = perception(goal)
        mem = spatial.rebuild(records, m, p, cfg=spatial.A17)
        if detour_at is not None and step >= detour_at and state.stage == "goal":
            target = spatial.Target("unexplored_1", "frontier", x + 20.0, y, "far", detour_at)
        r = planner.staged_verify(mem, m, p, state, target, mode, last_called)
        out.append(r)
        state, target, mode = r.state, r.target, r.mode
        if r.ask is not None:
            last_called = step
            target = r.menu[0] if r.menu else None
        records.append({"step": step, "manifest": m, "perceiver": {"result": p},
                        "stage": state.to_dict(),
                        "target": target.to_dict() if target else None, "mode": mode})
    return out


def cmd_transitions(_args: argparse.Namespace) -> int:
    E = "centre"
    cases = {
        # Seen twice (the sighting step is already goal), lost a step on, seen
        # again from where it was seen.
        "reacquired": ([(0, 0, 0, E), (0, 0, 0, E), (1.7, 0, 0, None), (0, 0, 0, E)],
                       None, ["goal", "goal", "verify", "goal"], "reacquired", None),
        # Seen again from the same place, 37 degrees off: the old rays go.
        "reacquired_moved": ([(0, 0, 0, E), (1.7, 0, 0, None), (0, 0, 0, "far_left")],
                             None, ["goal", "verify", "goal"], "reacquired_moved", None),
        # Back at the vantage, facing the seen way, nothing.
        "check_fails": ([(0, 0, 0, E), (1.7, 0, 0, None), (0.3, 0, 10, None)],
                        None, ["goal", "verify", "explore"], "verify_failed", "verify_failed"),
        # Lost at the vantage itself: that look is not the check; the next is.
        "fresh_look": ([(0, 0, 0, E), (0, 0, 0, None), (0, 0, 0, None)],
                       None, ["goal", "verify", "explore"], "verify_failed", "verify_failed"),
        # Away from the vantage for 9 steps after verify began: verify stands 8.
        "timeout": ([(0, 0, 0, E), (1.7, 0, 0, None)] + [(1.7 + 0.2 * k, 0, 0, None)
                                                         for k in range(1, 10)],
                    None, ["goal", "verify"] + ["verify"] * 8 + ["explore"],
                    "verify_timeout", "verify_timeout"),
        # A standing detour holds goal while the goal is out of view.
        "detour_holds": ([(0, 0, 0, E), (0, 0, 0, E), (0, 1.0, 90, None), (0, 2.0, 90, None)],
                         2, ["goal", "goal", "goal", "goal"], None, None),
    }
    ok = True
    for name, (seq, detour_at, want, event, ask) in cases.items():
        got = drive(seq, detour_at)
        stages = [r.state.stage for r in got][-len(want):]
        events = [e for r in got for e in r.events]
        asks = [r.ask for r in got if r.ask is not None]
        good = (stages == want and (event is None or event in events)
                and (event is not None or not any(e.startswith(("goal_lost", "verify"))
                                                  for e in events))
                and (ask is None or ask in asks))
        ok &= good
        print("   {0:<17} stages {1}; events {2}; asks {3} -> {4}".format(
            name, stages, events, asks, "pass" if good else "FAIL"))
    # No known path back: a vantage far off in ground the map has never seen.
    m = manifest(3, 0, 0, 0)
    p = perception(None)
    mem = spatial.rebuild([], m, p, cfg=spatial.A17)
    st = planner.VerifyState(stage="verify", rays_since=0, vantage=[60.0, 60.0, 0.0, 1],
                             verify_since=2)
    r = planner.staged_verify(mem, m, p, st, None, None, 0)
    good = r.state.stage == "explore" and "verify_unreachable" in r.events
    ok &= good
    print("   {0:<17} stage {1}; events {2}; ask {3} -> {4}".format(
        "unreachable", r.state.stage, r.events, r.ask, "pass" if good else "FAIL"))
    # The verify target: the vantage, then a point along the seen bearing.
    st = planner.VerifyState(stage="verify", vantage=[0.0, 0.0, 90.0, 4], verify_since=5)
    far, near = planner.verify_target(st, (5.0, 0.0, 0.0), 6), planner.verify_target(
        st, (0.5, 0.0, 0.0), 6)
    good = (far.id == "verify_vantage" and (far.x, far.y) == (0.0, 0.0)
            and near.id == "verify_look" and abs(near.y - 3.0) < 1e-6)
    ok &= good
    print("   verify target: far {0} ({1:.1f}, {2:.1f}); at vantage {3} ({4:.1f}, {5:.1f}) "
          "-> {6}".format(far.id, far.x, far.y, near.id, near.x, near.y,
                          "pass" if good else "FAIL"))
    print("1. transitions: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# --- 2. smoke ---------------------------------------------------------------------

def _strip(d: Dict[str, Any], drop_text: bool) -> str:
    out = {k: v for k, v in d.items() if k not in VOLATILE and k not in IDENTITY}
    if drop_text and out.get("strategist"):
        out["strategist"] = {k: v for k, v in out["strategist"].items() if k != "text"}
    return json.dumps(out, sort_keys=True)


def cmd_smoke(args: argparse.Namespace) -> int:
    known = spatial.WORDS_A14["goal_known"].split(":")[0]
    steps = errors = differ_a20 = differ_a21 = 0
    q_calls = q_known = nav_known = 0
    stages: Counter = Counter()
    events: Counter = Counter()
    example = None
    with tempfile.TemporaryDirectory() as tmp:
        for run in runs_under(Path(args.root).resolve()):
            os.environ["VLM_AGENT"] = args.agents[0]
            with_goal = smoke_run(run, Path(tmp) / "base", False)
            without = smoke_run(run, Path(tmp) / "base-none", True)
            os.environ["VLM_AGENT"] = args.agents[1]
            truth = smoke_run(run, Path(tmp) / "truth", False)
            errors += abs(len(with_goal) - len(without)) + abs(len(with_goal) - len(truth))
            for a, b, c in zip(with_goal, without, truth):
                steps += 1
                errors += bool(a.get("error")) + bool(b.get("error")) + bool(c.get("error"))
                differ_a20 += _strip(a, False) != _strip(b, False)
                differ_a21 += _strip(a, True) != _strip(c, True)
                stages[(a.get("stage") or {}).get("stage")] += 1
                events.update((a.get("evaluator") or {}).get("events") or [])
                if c.get("strategist"):
                    q_calls += 1
                    q_known += known in c["strategist"]["text"]
                    if known in c["strategist"]["text"] and example is None:
                        example = c["strategist"]["text"]
                nav_known += known in (c.get("navigator_text") or "")
    ok = (errors == 0 and differ_a20 == 0 and differ_a21 == 0 and nav_known == 0
          and q_known == q_calls)
    print("2. smoke ({0} and {1}) on {2}: decisions {3}; failed steps {4}".format(
        args.agents[0], args.agents[1], args.root, steps, errors))
    print("   no-truth agent with and without the goal block: differ {0}".format(differ_a20))
    print("   truth twin against it, strategist text aside: differ {0}".format(differ_a21))
    print("   truth twin strategist texts with the goal's position {0}/{1}; navigator texts {2}".format(
        q_known, q_calls, nav_known))
    print("   stages {0}; events {1}".format(dict(stages), dict(events)))
    print("smoke: " + ("PASS" if ok else "FAIL"))
    print("\nfirst a21 strategist text:\n" + (example or "(none)"))
    return 0 if ok else 1


# --- 3. open-loop count -----------------------------------------------------------

def verify_replay(run) -> Dict[str, Any]:
    """a20's stage machine open-loop along a recorded run."""
    rows = load(run)
    state = planner.VerifyState()
    target, mode, last_called = None, None, None
    stages: Counter = Counter()
    events: Counter = Counter()
    failed_in_sight = 0
    sightings = {"genuine": 0, "false": 0}
    for k, r in enumerate(rows):
        mem = memory_a17(rows, k)
        res = (r.get("perceiver") or {}).get("result") or {}
        m = {kk: v for kk, v in r["manifest"].items() if kk != "goal"}
        out = planner.staged_verify(mem, m, res, state, target, mode, last_called)
        if res.get("goal") in spatial.STRIPS:
            sightings["genuine" if in_view(r) else "false"] += 1
        events.update(out.events)
        if "verify_failed" in out.events and los(r):
            failed_in_sight += 1
        target, mode, state = out.target, out.mode, out.state
        if out.ask is not None:
            last_called = r["step"]
            target = out.menu[0] if out.menu else None
            mode = "explore" if state.stage == "explore" else "detour"
            state.target_dist_m = None
        stages[state.stage] += 1
    return {"stages": stages, "events": events, "failed_in_sight": failed_in_sight,
            "sightings": sightings, "steps": len(rows)}


def cmd_offline(_args: argparse.Namespace) -> int:
    stages: Counter = Counter()
    events: Counter = Counter()
    sightings: Counter = Counter()
    failed_in_sight = steps = 0
    print("3. a20 open-loop on R12's recorded paths (reported, not gated)")
    for run in runs_under(PHASE2 / "R12_staged_search/runs"):
        o = verify_replay(run)
        stages.update(o["stages"])
        events.update(o["events"])
        sightings.update(o["sightings"])
        failed_in_sight += o["failed_in_sight"]
        steps += o["steps"]
        e = o["events"]
        print("   {0:<22} lost {1:>2}; reacquired {2:>2} (moved {3:>2}); failed {4:>2}; "
              "timeout {5:>2}; unreachable {6}".format(
                  label(run), e["goal_lost"], e["reacquired"] + e["reacquired_moved"],
                  e["reacquired_moved"], e["verify_failed"], e["verify_timeout"],
                  e["verify_unreachable"]))
    print("   steps {0}: {1}".format(steps, ", ".join(
        "{0} {1} ({2:.0%})".format(k, v, v / max(1, steps)) for k, v in sorted(stages.items()))))
    print("   episodes: lost {goal_lost}; reacquired {reacquired}, moved {reacquired_moved}; "
          "failed {verify_failed}; timeout {verify_timeout}; unreachable "
          "{verify_unreachable}".format(**{k: events[k] for k in (
              "goal_lost", "reacquired", "reacquired_moved", "verify_failed",
              "verify_timeout", "verify_unreachable")}))
    print("   failed checks with the goal truly in line of sight: {0}".format(failed_in_sight))
    print("   sightings: genuine {genuine}, false {false}".format(**sightings))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("transitions", help="1. synthetic stage transitions")
    smoke = sub.add_parser("smoke", help="2. a20 and a21's real step on recorded manifests")
    smoke.add_argument("root")
    smoke.add_argument("--agents", nargs=2, default=["a20", "a21"],
                       help="the no-truth agent and its strategist-truth twin (a22 a23)")
    sub.add_parser("offline", help="3. open-loop count on R12's paths")
    args = ap.parse_args()
    return {"transitions": cmd_transitions, "smoke": cmd_smoke,
            "offline": cmd_offline}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
