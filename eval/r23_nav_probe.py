"""R23 navigator probe: p18 with a17c's doorway tags on recorded s02 frames (live model).

Each case is a recorded s02 step (frame on disk). Its notes are worked out again
in memory a17c (an open doorway and a closed door tagged apart) from the records
up to it, the navigator text rendered with p18, and p18 asked on the recorded
annotated frame. The recorded pick (p17, a17 notes) is the baseline. Sets, from
the site model (R11's analysis/geo.py):
- `through`: some forward move's 3 m segment crosses the divider through a door
  open at that step. Want: such a move taken.
- `control`: no such move, but a strip the perceiver (after d01) calls an open
  doorway. Want: no more doorway moves than before, and no more moves truly
  blocked within 1.9 m.

    VLM_PROFILE=remote python eval/r23_nav_probe.py run RUNS... --out p18.jsonl
    python eval/r23_nav_probe.py score p18.jsonl RUNS...

Gate (R23 README): `through` taken at least 70%; `control` doorway-tag picks at
most the baseline + 5 points; truly blocked picks not above the baseline.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))
sys.path.insert(0, str(REPO_ROOT / "eval" / "phase2" / "R11_goal_default" / "analysis"))

from server.decider import config, prompt as prompts, schema, spatial, vlm  # noqa: E402
from server.decider.orchestrator import (_action, perceiver_line, plan_line,  # noqa: E402
                                         recent_moves)
from spatial_replay import label, load, runs_under  # noqa: E402
import geo  # noqa: E402

THROUGH_M = 3.0
BLOCKED_M = 1.9
CONTROL_CAP = 150


def through(site: str, arm: str, step: int, here: spatial.Pose, heading: float) -> bool:
    free = geo.world(site, arm, step)
    end = (here[0] + THROUGH_M * math.cos(math.radians(heading)),
           here[1] + THROUGH_M * math.sin(math.radians(heading)))
    return here[0] * end[0] < 0 and geo.segment_clear(free, here[:2], end)


def blocked(site: str, arm: str, step: int, here: spatial.Pose, heading: float) -> bool:
    free = geo.world(site, arm, step)
    return geo.ray(free, here[0], here[1], heading, max_d=BLOCKED_M) < BLOCKED_M


def cases(roots: List[str]):
    """(set, key, run, record, text, offered indices, through indices, doorway-tag indices)."""
    p = prompts.get("p18")
    found, control = [], []
    for root in roots:
        rnd = Path(root).resolve().parent.name
        for run in runs_under(Path(root).resolve()):
            site, arm = run.parts[-3], run.parts[-2]
            if not site.startswith("s02"):
                continue
            rows = load(run)
            for i, r in enumerate(rows):
                here = spatial.pose_xyh(r["manifest"].get("pose"))
                if here is None or not r.get("frame") or not (run / r["frame"]).is_file():
                    continue
                perception = (r.get("perceiver") or {}).get("result")
                mem = spatial.rebuild(rows[:i], r["manifest"], perception, spatial.A17C)
                target = spatial.Target.from_dict(r.get("target"))
                tags = spatial.project(mem, r["manifest"], perception, target)
                hidden = spatial.hide_turn_around(mem, r["manifest"], tags)
                offered = dict(r["manifest"], actions=[
                    a for a in r["manifest"].get("actions") or []
                    if int(a["index"]) not in hidden])
                acts = [a for a in offered["actions"] if not a.get("turn_around")]
                thru = [int(a["index"]) for a in acts
                        if through(site, arm, r["step"], here, spatial.action_heading(a, here[2]))]
                door = [int(a["index"]) for a in acts
                        if spatial.WORDS_A17C["doorway_open"] in tags.get(int(a["index"]), [])]
                text = p.render(p, offered, tags,
                                plan_line(target, r.get("mode"), here, True),
                                perceiver_line(perception), recent_moves(rows[:i], r["manifest"]))
                k = "{0}/{1}/{2}".format(rnd, label(run), r["step"])
                indices = sorted(int(a["index"]) for a in offered["actions"])
                case = (k, run, r, text, indices, thru, door)
                if thru:
                    found.append(("through",) + case)
                elif door:
                    control.append(("control",) + case)
    random.Random(23).shuffle(control)
    return found + control[:CONTROL_CAP]


def cmd_run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = set()
    if out.is_file():
        done = {json.loads(l)["key"] for l in out.read_text().splitlines() if l.strip()}
    todo = [c for c in cases(args.roots) if c[1] not in done]
    p = prompts.get("p18")
    print("{0} calls to make".format(len(todo)), flush=True)

    async def one(sem: asyncio.Semaphore, n: int, case) -> None:
        kind, k, run, r, text, indices, thru, door = case
        async with sem:
            b64 = base64.b64encode((run / r["frame"]).read_bytes()).decode()
            call = await vlm.call_structured(schema.SCHEMA_NAME, p.system, text, b64,
                                             schema.action_schema(indices), _action(indices),
                                             config.MAX_TOKENS)
        pick = call.result["index"] if call.result else None
        with out.open("a") as handle:
            handle.write(json.dumps({"key": k, "set": kind, "pick": pick,
                                     "recorded": r.get("index"), "through": thru, "door": door,
                                     "text": text, "error": call.error}) + "\n")
        print("{0}/{1} {2} {3}: through {4} pick {5} recorded {6}".format(
            n + 1, len(todo), kind, k, thru, pick, r.get("index")), flush=True)

    async def go() -> None:
        sem = asyncio.Semaphore(args.concurrency)
        try:
            await asyncio.gather(*(one(sem, n, c) for n, c in enumerate(todo)))
        finally:
            await vlm.aclose()

    asyncio.run(go())
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    t: Counter = Counter()
    rows = [json.loads(l) for l in Path(args.answers).read_text().splitlines() if l.strip()]
    meta: Dict[str, Tuple[str, str, int, Optional[spatial.Pose], Dict[int, Any]]] = {}
    for root in args.roots:
        rnd = Path(root).resolve().parent.name
        for run in runs_under(Path(root).resolve()):
            for r in load(run):
                k = "{0}/{1}/{2}".format(rnd, label(run), r["step"])
                meta[k] = (run.parts[-3], run.parts[-2], r["step"],
                           spatial.pose_xyh(r["manifest"].get("pose")),
                           {int(a["index"]): a for a in r["manifest"].get("actions") or []})
    for j in rows:
        if j["pick"] is None or j["key"] not in meta:
            continue
        site, arm, step, here, acts = meta[j["key"]]
        s = j["set"]
        t[(s, "n")] += 1
        for who in ("recorded", "pick"):
            i = j[who]
            t[(s, who, "through")] += i in j["through"]
            t[(s, who, "door")] += i in j["door"]
            a = acts.get(i)
            if a is not None and not a.get("turn_around") and here is not None:
                t[(s, who, "blocked")] += blocked(site, arm, step, here,
                                                  spatial.action_heading(a, here[2]))
    for s in ("through", "control"):
        n = t[(s, "n")]
        print("{0}: {1} steps".format(s, n))
        for who, name in (("recorded", "p17 (recorded)"), ("pick", "p18 + a17c")):
            print("  {0:15s} through-move {1}/{2}  doorway-tag move {3}/{2}  truly blocked "
                  "{4}/{2}".format(name, t[(s, who, "through")], n, t[(s, who, "door")],
                                   t[(s, who, "blocked")]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("roots", nargs="+")
    run.add_argument("--out", required=True)
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
