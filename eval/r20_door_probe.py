"""R20 doorway-confirmer probe: d01 on every recorded open-doorway report (live model).

Every recorded step where the perceiver reported an open doorway in one or more
strips is asked again with d01 on its clean frame. Each reported strip is
scored against the site model (R11's analysis/geo.py): genuine when a ray inside
that strip, from the drone's pose, passes through a door that is open at that
step (s02: across the divider; s03: across the exit wall) before any wall.
s01 has no doors: every report there is false. The gate (R20 README) wants most
false reports refused and almost no genuine one.

    VLM_PROFILE=remote python eval/r20_door_probe.py run RUNS... --out d01.jsonl
    python eval/r20_door_probe.py score d01.jsonl RUNS...

The frames must be on disk (the flight host keeps them). Evaluation reads the
pose and the site; the confirmer never sees them.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))
sys.path.insert(0, str(REPO_ROOT / "eval" / "phase2" / "R11_goal_default" / "analysis"))

from server.decider import prompt as prompts, schema, spatial, vlm  # noqa: E402
from server.decider.orchestrator import PERCEIVER_MAX_TOKENS, _doors_checked  # noqa: E402
from spatial_replay import label, load, runs_under  # noqa: E402
import geo  # noqa: E402

RAY_M = 12.0
HALF_STRIP_DEG = 9.0


def reported(r: Dict[str, Any]) -> List[str]:
    lanes = ((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []
    return [l["strip"] for l in lanes
            if l.get("doorway") == "open" or l.get("doorway_reported") == "open"]


def reports(roots: List[str]) -> List[Tuple[str, Path, Dict[str, Any]]]:
    out = []
    for root in roots:
        for run in runs_under(Path(root).resolve()):
            for r in load(run):
                if reported(r) and r.get("clean_frame"):
                    out.append((Path(root).resolve().parent.name, run, r))
    return out


def key(rnd: str, run: Path, r: Dict[str, Any]) -> str:
    return "{0}/{1}/{2}".format(rnd, label(run), r["step"])


def genuine(run: Path, r: Dict[str, Any], strip: str) -> bool:
    site, arm = run.parts[-3], run.parts[-2]
    if site == "s01":
        return False
    here = spatial.pose_xyh(r["manifest"].get("pose"))
    if here is None:
        return False
    free = geo.world(site, arm, r["step"])
    plane = 0.0 if site.startswith("s02") else -6.5
    centre = here[2] + spatial.strip_offset(strip)
    for k in range(-2, 3):
        h = centre + k * HALF_STRIP_DEG / 2.0
        d = geo.ray(free, here[0], here[1], h, max_d=RAY_M)
        end_x = here[0] + d * math.cos(math.radians(h))
        if (here[0] - plane) * (end_x - plane) < 0:
            return True
    return False


def cmd_run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    done = set()
    if out.is_file():
        done = {json.loads(line)["key"] for line in out.read_text().splitlines() if line.strip()}
    todo = [c for c in reports(args.roots) if key(*c) not in done
            and (c[1] / c[2]["clean_frame"]).is_file()]
    p = prompts.get(args.prompt)
    print("{0} reports to ask".format(len(todo)), flush=True)

    async def one(sem: asyncio.Semaphore, n: int, case) -> None:
        rnd, run, r = case
        strips = reported(r)
        async with sem:
            b64 = base64.b64encode((run / r["clean_frame"]).read_bytes()).decode()
            call = await vlm.call_structured(schema.DOOR_CONFIRMER_SCHEMA_NAME, p.system,
                                             p.render(p, strips), b64,
                                             schema.door_confirmer_schema(strips),
                                             _doors_checked(strips), PERCEIVER_MAX_TOKENS)
        with out.open("a") as handle:
            handle.write(json.dumps({"key": key(rnd, run, r), "prompt": p.version,
                                     "strips": strips, "result": call.result,
                                     "error": call.error}) + "\n")
        print("{0}/{1} {2}: {3}".format(n + 1, len(todo), key(rnd, run, r),
                                        {s: (call.result or {}).get(s) for s in strips}
                                        if call.result else call.error), flush=True)

    async def go() -> None:
        sem = asyncio.Semaphore(args.concurrency)
        try:
            await asyncio.gather(*(one(sem, n, c) for n, c in enumerate(todo)))
        finally:
            await vlm.aclose()

    asyncio.run(go())
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    answers = {}
    for line in Path(args.answers).read_text().splitlines():
        j = json.loads(line) if line.strip() else {}
        if j.get("result"):
            answers[j["key"]] = j["result"]
    tally: Counter = Counter()
    by_site: Counter = Counter()
    for rnd, run, r in reports(args.roots):
        a = answers.get(key(rnd, run, r))
        if a is None:
            continue
        for strip in reported(r):
            truth = "genuine" if genuine(run, r, strip) else "false"
            kept = a.get(strip) == "open"
            tally[(truth, kept)] += 1
            by_site[(run.parts[-3][:3], truth, kept)] += 1
    g = tally[("genuine", True)] + tally[("genuine", False)]
    f = tally[("false", True)] + tally[("false", False)]
    print("open-doorway reports asked: {0} genuine, {1} false".format(g, f))
    print("  genuine kept   {0}/{1} = {2:.1%}".format(tally[("genuine", True)], g,
                                                     tally[("genuine", True)] / max(1, g)))
    print("  false refused  {0}/{1} = {2:.1%}".format(tally[("false", False)], f,
                                                     tally[("false", False)] / max(1, f)))
    for site in ("s01", "s02", "s03"):
        print("  {0}: genuine kept {1}/{2}, false refused {3}/{4}".format(
            site, by_site[(site, "genuine", True)],
            by_site[(site, "genuine", True)] + by_site[(site, "genuine", False)],
            by_site[(site, "false", False)],
            by_site[(site, "false", False)] + by_site[(site, "false", True)]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("roots", nargs="+")
    run.add_argument("--out", required=True)
    run.add_argument("--prompt", default="d01")
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
