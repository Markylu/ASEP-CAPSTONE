"""R21 along-the-wall probe (no model): a39's two items at every recorded detour call.

At each recorded call where the planner asked for a detour (walled, blocked or
stall), the memory is rebuilt from the records up to that step and
planner.along_wall builds the items. Each is scored against the site model
(R11's analysis/geo.py): is its end on free floor with a clear straight line
from the drone, and, at the s02 divider (drone within 3 m of it), does it lead
toward a door open at that step and is its axis along the divider.

`run` asks q08 (live, text only) at every recorded strategist call with the
items added to the recorded menu and the situation worded again; `score` counts
how often it takes an along-the-wall item and, at the divider, whether the side
it takes leads toward the open door.

    python3 eval/r21_along_probe.py items eval/phase2/R15_known_goal_reach/runs ...
    VLM_PROFILE=remote python eval/r21_along_probe.py run RUNS... --out q08.jsonl
    python3 eval/r21_along_probe.py score q08.jsonl RUNS...
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))
sys.path.insert(0, str(REPO_ROOT / "eval" / "phase2" / "R11_goal_default" / "analysis"))

from server.decider import agent, planner, prompt as prompts, schema, spatial, vlm  # noqa: E402
from server.decider.orchestrator import STRATEGIST_MAX_TOKENS, _strategy, goal_at  # noqa: E402
from spatial_replay import label, load, runs_under  # noqa: E402
import geo  # noqa: E402


A39 = agent.get("a39")
CFG = A39.spatial_config
P = A39.features["orchestrator"]["along_wall"]


def toward_open_door(site: str, arm: str, step: int, here: spatial.Pose,
                     end: Tuple[float, float]) -> Optional[bool]:
    """At the s02 divider: does going to `end` bring the drone nearer an open door
    along it? None away from the divider."""
    if not (site.startswith("s02") and abs(here[0]) < 3.0):
        return None
    doors = geo.open_doors(site, arm, step)
    dy = min(abs(here[1] - geo.S02_DOORS[d]) for d in doors)
    return min(abs(end[1] - geo.S02_DOORS[d]) for d in doors) < dy - 0.5


def cases(roots: List[str]):
    """(key, site, arm, step, here, menu, text) at every recorded strategist call,
    the menu with the along-the-wall items first and the situation worded again."""
    for root in roots:
        rnd = Path(root).resolve().parent.name
        for run in runs_under(Path(root).resolve()):
            site, arm = run.parts[-3], run.parts[-2]
            rows = load(run)
            for i, r in enumerate(rows):
                s = r.get("strategist") or {}
                ask = (r.get("planner") or {}).get("ask")
                here = spatial.pose_xyh(r["manifest"].get("pose"))
                goal = goal_at(r["manifest"])
                if s.get("menu") is None or not s.get("text"):
                    continue
                if ask is None or here is None or goal is None:
                    continue
                perception = (r.get("perceiver") or {}).get("result")
                mem = spatial.rebuild(rows[:i], r["manifest"], perception, CFG)
                items = planner.along_wall(mem, here, r["step"], goal, rows[:i], P)
                menu = items + [spatial.Target.from_dict(m) for m in s["menu"]]
                text = planner.detour_situation(mem, r["manifest"], menu, ask, goal)
                yield ("{0}/{1}/{2}".format(rnd, label(run), r["step"]), site, arm, r["step"],
                       here, menu, text)


def cmd_run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = set()
    if out.is_file():
        done = {json.loads(l)["key"] for l in out.read_text().splitlines() if l.strip()}
    todo = [c for c in cases(args.roots) if c[0] not in done]
    p = prompts.get(args.prompt)
    print("{0} calls to ask".format(len(todo)), flush=True)

    async def one(sem: asyncio.Semaphore, n: int, case) -> None:
        key, _, _, _, _, menu, text = case
        ids = [t.id for t in menu] + ["explore"]
        async with sem:
            call = await vlm.call_structured(schema.STRATEGIST_SCHEMA_NAME, p.system, text, None,
                                             schema.strategist_schema(ids), _strategy(ids),
                                             STRATEGIST_MAX_TOKENS)
        with out.open("a") as handle:
            handle.write(json.dumps({"key": key, "prompt": p.version, "text": text,
                                     "result": call.result, "error": call.error}) + "\n")
        print("{0}/{1} {2}: {3}".format(n + 1, len(todo), key,
                                        (call.result or {}).get("target", call.error)),
              flush=True)

    async def go() -> None:
        sem = asyncio.Semaphore(args.concurrency)
        try:
            await asyncio.gather(*(one(sem, n, c) for n, c in enumerate(todo)))
        finally:
            await vlm.aclose()

    asyncio.run(go())
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    answers: Dict[str, Any] = {}
    for line in Path(args.answers).read_text().splitlines():
        j = json.loads(line) if line.strip() else {}
        if j.get("result"):
            answers[j["key"]] = j["result"]["target"]
    t: Counter = Counter()
    for key, site, arm, step, here, menu, _ in cases(args.roots):
        pick = answers.get(key)
        if pick is None:
            continue
        t["calls"] += 1
        has = [m for m in menu if m.kind == "along"]
        if has:
            t["along_listed"] += 1
        chosen = next((m for m in menu if m.id == pick), None)
        t["kind_" + (chosen.kind if chosen else "explore")] += 1
        if chosen is not None and chosen.kind == "along":
            tw = toward_open_door(site, arm, step, here, (chosen.x, chosen.y))
            if tw is not None:
                t["divider_along_picks"] += 1
                t["divider_toward_open"] += tw
    for k in sorted(t):
        print("  {0}: {1}".format(k, t[k]))
    if t["along_listed"]:
        print("  along picked when listed {0}/{1}".format(t["kind_along"], t["along_listed"]))
    return 0


def cmd_items(args: argparse.Namespace) -> int:
    cfg, p = CFG, P
    for root in args.roots:
        t: Counter = Counter()
        for run in runs_under(Path(root).resolve()):
            site, arm = run.parts[-3], run.parts[-2]
            rows = load(run)
            for i, r in enumerate(rows):
                ask = (r.get("planner") or {}).get("ask")
                here = spatial.pose_xyh(r["manifest"].get("pose"))
                goal = goal_at(r["manifest"])
                if ask is None or here is None or goal is None:
                    continue
                perception = ((r.get("perceiver") or {}).get("result"))
                mem = spatial.rebuild(rows[:i], r["manifest"], perception, cfg)
                items = planner.along_wall(mem, here, r["step"], goal, rows[:i], p)
                t["calls"] += 1
                t["items_{0}".format(len(items))] += 1
                free = geo.world(site, arm, r["step"])
                divider = site.startswith("s02") and abs(here[0]) < 3.0
                doors = geo.open_doors(site, arm, r["step"]) if divider else set()
                if divider:
                    t["divider_calls"] += 1
                for it in items:
                    t["items"] += 1
                    end = (it.x, it.y)
                    ok = free(*end) and geo.segment_clear(free, here[:2], end)
                    t["clear"] += ok
                    if divider:
                        t["divider_items"] += 1
                        heading = spatial.bearing(here[:2], end)
                        along = abs(math.sin(math.radians(heading))) > math.cos(math.radians(30))
                        t["divider_along_axis"] += along
                        dy = min(abs(here[1] - geo.S02_DOORS[d]) for d in doors)
                        dy_end = min(abs(it.y - geo.S02_DOORS[d]) for d in doors)
                        t["divider_toward_open_door"] += dy_end < dy - 0.5
        print(root)
        for k in sorted(t):
            print("  {0}: {1}".format(k, t[k]))
        if t["items"]:
            print("  clear share {0:.0%}".format(t["clear"] / t["items"]))
        if t["divider_items"]:
            print("  divider: along axis {0:.0%}, toward an open door {1:.0%}".format(
                t["divider_along_axis"] / t["divider_items"],
                t["divider_toward_open_door"] / t["divider_items"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    items = sub.add_parser("items")
    items.add_argument("roots", nargs="+")
    items.set_defaults(fn=cmd_items)
    run = sub.add_parser("run")
    run.add_argument("roots", nargs="+")
    run.add_argument("--out", required=True)
    run.add_argument("--prompt", default="q08")
    run.add_argument("--concurrency", type=int, default=4)
    run.set_defaults(fn=cmd_run)
    score = sub.add_parser("score")
    score.add_argument("answers")
    score.add_argument("roots", nargs="+")
    score.set_defaults(fn=cmd_score)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
