"""Probe DE (R38): can the model call a dead-end corridor from one frame?

a78's latch is only as good as its trigger. The trigger is the dead-end
confirmer (prompts e01, e02), asked on a step with a closed-door read in the
centre three strips, on that step's clean frame. This probe asks it on every
such step Round F, R32P and R35 flew (probe dead_end_trigger: 90 in the shut
s03 tine facing its door, 24 elsewhere in s03, 1126 in s02) and scores the
answers against where the drone stood. Gate and method:
eval/phase2/R38_dead_end_latch/README.md, "Probe gate" (set before this ran).

The frames are on the lane checkouts the rounds flew on (gitignored there), so
`sample` and `run` are run on that host:

    python eval/probes/dead_end.py sample ~/asep-final-l* ~/asep-r32*-l* ~/asep-r35-l*
    LITELLM_BASE_URL=http://127.0.0.1:8004 python eval/probes/dead_end.py run --prompt e01
    LITELLM_BASE_URL=http://127.0.0.1:8004 python eval/probes/dead_end.py run --prompt e02
    python eval/probes/dead_end.py score
    python eval/probes/dead_end.py breakdown

`breakdown` (no frames, no model; added after the gate was read, so it is a
description, not a test) splits the answers by where the drone stood, from the
repo's own copies of the runs. `run` takes --shard i --of n for more than one instance; concurrency is 1 per
instance, as every recorded read. `score` needs no frames and no model.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import collections
import hashlib
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

os.environ.setdefault("VLM_PROFILE", "remote")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dead_end_trigger as trigger  # noqa: E402
from common import PROBES, load, metrics, pct, spatial, switch_step, write_jsonl, xy  # noqa: E402

#: DEAD_END_OUT redirects the sample, the calls and the score (a dry run).
OUT = Path(os.environ.get("DEAD_END_OUT") or PROBES / "dead_end")
PROMPTS = ("e01", "e02")
FOLDERS = trigger.FOLDERS.split(",")
#: Set in the round README before any call. A confirmer that is never wrong
#: fires in 8 of the 11 s03 dynamic runs with 25 or more steps left (in the
#: other three the first closed-door read in the shut tine comes too late), so
#: the run count asks for 7.
GATE = {"shut_tine_yes_min": 0.80, "s02_yes_max": 0.05,
        "s03_dynamic_runs_min": 7, "steps_left_min": 25, "s02_runs_max": 5}


def sample(roots: List[str]) -> int:
    """One row per asked step whose clean frame is on disk under a lane root."""
    seen: Dict[Tuple[str, str, str, str], Path] = {}
    for root in roots:
        for folder in FOLDERS:
            for d in sorted(Path(root).expanduser().glob(
                    "eval/phase2/{0}/runs/*/*/seed*/decisions.jsonl".format(folder))):
                run = d.parent
                key = (folder.split("_", 1)[0], run.parts[-3], run.parts[-2], run.parts[-1])
                if run.parts[-2] != "initial" and (run / "frames").is_dir():
                    seen.setdefault(key, run)
    frames: List[Dict[str, Any]] = []
    missing = 0
    for (short, site, arm, seed), run in sorted(seen.items()):
        rows = [r for r in load(run) if r.get("manifest")]
        met = metrics(run)
        sw = switch_step(met)
        shut = trigger.shut_tine(arm, run, rows, sw) if site == "s03" else None
        crossed = next((r["step"] for r in rows
                        if xy(r) and xy(r)[0] < (-7.0 if site == "s03" else 0.0)), None)
        for r in rows:
            here = xy(r)
            lanes = ((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []
            strips = [l["strip"] for l in lanes
                      if l.get("doorway") == "closed" and l.get("strip") in spatial.CENTRAL_STRIPS]
            if here is None or not strips:
                continue
            frame = run / (r.get("clean_frame") or "")
            if not r.get("clean_frame") or not frame.exists():
                missing += 1
                continue
            key = "{0}/{1}/{2}/{3}/{4}".format(short, site, arm, seed, r["step"])
            frames.append({
                "id": hashlib.sha256(("dead_end:" + key).encode()).hexdigest()[:16],
                "folder": short, "site": site, "arm": arm, "seed": seed, "step": r["step"],
                "frame": str(frame), "strips": strips,
                "where": trigger.where(site, arm, shut, sw, here, r["step"]),
                "won": bool(met.get("goal_reached")), "crossed": crossed})
    write_jsonl(OUT / "sample.jsonl", frames)
    by = collections.Counter(f["where"] for f in frames)
    print("{0} asked steps with frames from {1} runs ({2}); {3} asked steps without a frame".format(
        len(frames), len(seen), dict(by), missing))
    return 0 if frames else 1


def load_sample() -> List[Dict[str, Any]]:
    path = OUT / "sample.jsonl"
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] \
        if path.exists() else []


async def run_probe(prompt: str, shard: int, of: int) -> None:
    from server.decider import config, orchestrator, prompt as prompts, schema, views, vlm
    p = prompts.get(prompt)

    async def call(f: Dict[str, Any]) -> Dict[str, Any]:
        b64 = base64.b64encode(Path(f["frame"]).read_bytes()).decode()
        view = views.dead_end_confirmer(p, f["strips"], b64)
        sub = await vlm.call_structured(
            schema.DEAD_END_CONFIRMER_SCHEMA_NAME, view.system, view.text, view.image_b64,
            schema.dead_end_confirmer_schema(), orchestrator._dead_end_checked,
            orchestrator.PERCEIVER_MAX_TOKENS)
        return {**{k: f[k] for k in ("id", "folder", "site", "arm", "seed", "step")},
                "prompt": prompt, "result": sub.result, "raw": sub.raw, "rung": sub.rung,
                "latency_ms": sub.latency_ms, "instance": config.LITELLM_BASE_URL}

    todo = load_sample()[shard::of]
    path = OUT / "calls_{0}_{1}of{2}.jsonl".format(prompt, shard, of)
    done = set()
    if path.exists():
        done = {c["id"] for c in map(json.loads, path.read_text().splitlines())}
    with path.open("a") as fh:
        for n, f in enumerate(todo):
            if f["id"] not in done:  # one at a time: concurrency 1
                fh.write(json.dumps(await call(f)) + "\n")
                fh.flush()
            if n % 50 == 0:
                print("{0} shard {1}/{2}: {3}/{4} frames".format(prompt, shard, of, n + 1,
                                                                 len(todo)), flush=True)
    print("{0} shard {1}/{2}: done on {3}".format(prompt, shard, of, config.LITELLM_BASE_URL))


def first_fire(reads: List[Tuple[int, str]], d: Dict[str, Any]) -> Optional[int]:
    """The first step the latch's own rule (planner.latch_reads_agree) calls a
    dead end on, given the confirmer's answers in step order."""
    from server.decider import planner
    for i, (step, _) in enumerate(reads):
        if planner.latch_reads_agree(reads[:i + 1], step, d):
            return step
    return None


def score() -> int:
    from server.decider import agent
    rule = agent.PATHFINDER_A78["dead_end_latch"]
    frames = {f["id"]: f for f in load_sample()}
    lines = ["Probe DE: the dead-end confirmer on {0} asked steps of {1}".format(
        len(frames), ", ".join(FOLDERS)),
        "Rule for a run: yes on a step and on {0} of the last {1} answers, none older than "
        "{2} steps (a78's).".format(rule["yes_reads"], rule["of_reads"], rule["recent_steps"])]
    passed: Dict[str, bool] = {}
    for prompt in PROMPTS:
        calls: Dict[str, Dict[str, Any]] = {}
        for fp in sorted(OUT.glob("calls_{0}_*.jsonl".format(prompt))):
            for c in map(json.loads, fp.read_text().splitlines()):
                if c["id"] in frames:
                    calls[c["id"]] = c
        if not calls:
            lines += ["", "## {0}: no calls recorded".format(prompt)]
            continue
        failed = sum(1 for c in calls.values() if not c.get("result"))
        yes = collections.Counter()
        n = collections.Counter()
        by_run: Dict[Tuple[str, str, str, str], List[Tuple[int, str]]] = collections.defaultdict(list)
        for fid, c in calls.items():
            f = frames[fid]
            if not c.get("result"):
                continue
            n[f["where"]] += 1
            yes[f["where"]] += c["result"]["dead_end"] == "yes"
            by_run[(f["folder"], f["site"], f["arm"], f["seed"])].append(
                (int(f["step"]), c["result"]["dead_end"]))
        lines += ["", "## {0}: {1} of {2} asked steps answered, {3} failed calls; median latency "
                  "{4:.0f} ms".format(prompt, sum(n.values()), len(frames), failed,
                                      statistics.median(c["latency_ms"] for c in calls.values()))]
        for where in ("shut_tine", "s03_other", "s02"):
            lines.append("  yes in {0:<10} {1}".format(where, pct(yes[where], n[where])
                                                        if n[where] else "0/0"))
        runs = {(f["folder"], f["site"], f["arm"], f["seed"]): f for f in frames.values()}
        s03d = [k for k in runs if k[1] == "s03" and k[2] == "dynamic"]
        s02 = [k for k in runs if k[1] != "s03"]
        fires = {k: first_fire(sorted(by_run.get(k, [])), rule) for k in runs}
        in_time = [k for k in s03d if fires[k] is not None
                   and 60 - fires[k] >= GATE["steps_left_min"]]
        early = [k for k in s02 if fires[k] is not None
                 and (runs[k]["crossed"] is None or fires[k] < runs[k]["crossed"])]
        early_won = [k for k in early if runs[k]["won"]]
        lines.append("  s03 dynamic runs fired in: {0} of {1}; with {2} or more steps left: {3}".format(
            sum(fires[k] is not None for k in s03d), len(s03d), GATE["steps_left_min"],
            len(in_time)))
        lines.append("  s02 runs fired in before the crossing: {0} of {1} ({2} of them won runs)".format(
            len(early), len(s02), len(early_won)))
        checks = [
            ("yes on >= 80% of shut-tine steps",
             n["shut_tine"] > 0 and yes["shut_tine"] / n["shut_tine"] >= GATE["shut_tine_yes_min"]),
            ("yes on <= 5% of s02 steps",
             n["s02"] > 0 and yes["s02"] / n["s02"] <= GATE["s02_yes_max"]),
            ("fires in >= 7 s03 dynamic runs with 25 or more steps left",
             len(in_time) >= GATE["s03_dynamic_runs_min"]),
            ("fires in <= 5 s02 runs", len(early) <= GATE["s02_runs_max"]),
            ("every asked step answered", sum(n.values()) == len(frames))]
        for name, ok in checks:
            lines.append("  {0}: {1}".format("PASS" if ok else "FAIL", name))
        passed[prompt] = all(ok for _, ok in checks)
        lines.append("  gate: {0}".format("PASS" if passed[prompt] else "FAIL"))
    lines += ["", "Probe gate: {0}".format(
        "PASS ({0})".format(", ".join(p for p, ok in passed.items() if ok))
        if any(passed.values()) else "FAIL" if passed else "not run")]
    (OUT / "score.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if any(passed.values()) else 1


def breakdown() -> int:
    """The answers by site, by range and angle to the s02 divider, by depth in
    the shut tine, and per run. Poses are the recorded ones (evaluation only)."""
    from common import REPO_ROOT
    frames = load_sample()
    answers: Dict[str, Dict[str, str]] = {}
    for prompt in PROMPTS:
        answers[prompt] = {}
        for fp in sorted(OUT.glob("calls_{0}_*.jsonl".format(prompt))):
            for c in map(json.loads, fp.read_text().splitlines()):
                if c.get("result"):
                    answers[prompt][c["id"]] = c["result"]["dead_end"]
    folders = {f.split("_", 1)[0]: f for f in FOLDERS}
    poses: Dict[Tuple[str, str, str, str], Dict[int, Any]] = {}

    def here(f: Dict[str, Any]):
        key = (f["folder"], f["site"], f["arm"], f["seed"])
        if key not in poses:
            run = (REPO_ROOT / "eval" / "phase2" / folders[f["folder"]] / "runs" / f["site"]
                   / f["arm"] / f["seed"])
            poses[key] = {r["step"]: xy(r) for r in load(run) if r.get("manifest")}
        return poses[key][f["step"]]

    def yes(rows: List[Dict[str, Any]], prompt: str) -> str:
        got = [answers[prompt][f["id"]] for f in rows if f["id"] in answers[prompt]]
        return pct(sum(a == "yes" for a in got), len(got)) if got else "0/0"

    def table(title: str, rows: List[Dict[str, Any]], key) -> List[str]:
        groups: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
        for f in rows:
            groups[key(f)].append(f)
        out = ["", title, "  {0:<22}{1:>18}{2:>18}".format("", *PROMPTS)]
        for name in sorted(groups):
            out.append("  {0:<22}{1:>18}{2:>18}".format(
                name.split(" ", 1)[1], *(yes(groups[name], p) for p in PROMPTS)))
        return out

    def bands(value: float, edges: List[float], unit: str) -> str:
        for i, edge in enumerate(edges):
            if value < edge:
                return "{0} under {1:g} {2}".format(i, edge, unit)
        return "{0} {1:g} {2} or more".format(len(edges), edges[-1], unit)

    s02 = [f for f in frames if f["where"] == "s02"]
    tine = [f for f in frames if f["where"] == "shut_tine"]
    lines = ["Probe DE breakdown: yes answers by where the drone stood ({0} asked steps)".format(
        len(frames))]
    lines += table("s02, by site", s02, lambda f: "0 " + f["site"])
    lines += table("s02, by metres from the divider (x; under 0 is the far side)", s02,
                   lambda f: bands(here(f)[0], [0.0, 2.0, 4.0, 8.0], "m"))
    lines += table("s02, by heading off square to the divider", s02,
                   lambda f: bands(abs(spatial.wrap(here(f)[2] - 180.0)), [30.0, 60.0], "deg"))
    lines += table("s02, by closed-door strips among the centre three", s02,
                   lambda f: "{0} {0} strip(s)".format(len(f["strips"])))
    lines += table("shut tine, by metres short of the door wall (x = -6)", tine,
                   lambda f: bands(here(f)[0] + 6.0, [2.0, 4.0, 6.0], "m"))
    lines += ["", "yes from both prompts on the same step"]
    for where in ("shut_tine", "s03_other", "s02"):
        rows = [f for f in frames if f["where"] == where]
        lines.append("  {0:<22}{1}".format(where, pct(sum(
            all(answers[p].get(f["id"]) == "yes" for p in PROMPTS) for f in rows), len(rows))))
    runs: Dict[Tuple[str, str, str, str], List[Dict[str, Any]]] = collections.defaultdict(list)
    for f in frames:
        runs[(f["folder"], f["site"], f["arm"], f["seed"])].append(f)
    lines += ["", "runs with at least one yes before the drone crossed"]
    for prompt in PROMPTS:
        hit = {k: sorted(f["step"] for f in v if answers[prompt].get(f["id"]) == "yes"
                         and (f["crossed"] is None or f["step"] < f["crossed"]))
               for k, v in runs.items()}
        s02_runs = [k for k in runs if k[1] != "s03"]
        s03d = sorted(k for k in runs if k[1] == "s03" and k[2] == "dynamic")
        lines.append("  {0}: s02 {1} of {2}; s03 dynamic {3} of {4}, first yes at step {5}".format(
            prompt, sum(bool(hit[k]) for k in s02_runs), len(s02_runs),
            sum(bool(hit[k]) for k in s03d), len(s03d),
            ", ".join(str(hit[k][0]) if hit[k] else "-" for k in s03d)))
    (OUT / "breakdown.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("roots", nargs="+")
    r = sub.add_parser("run")
    r.add_argument("--prompt", choices=PROMPTS, required=True)
    r.add_argument("--shard", type=int, default=0)
    r.add_argument("--of", type=int, default=1)
    sub.add_parser("score")
    sub.add_parser("breakdown")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.cmd == "sample":
        return sample(args.roots)
    if args.cmd == "run":
        asyncio.run(run_probe(args.prompt, args.shard, args.of))
        return 0
    if args.cmd == "breakdown":
        return breakdown()
    return score()


if __name__ == "__main__":
    raise SystemExit(main())
