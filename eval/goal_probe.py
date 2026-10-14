#!/usr/bin/env python3
"""Can the agent see the goal? A cheap check before a round flies.

A round costs about 40 minutes of flying, and R3 spent all of it on an agent
that had stopped seeing the goal (R3 summary: 0/30 early frames against R1's
30/30). This probe asks the same question offline. It sends frames that were
already recorded, with the goal's ground truth in their manifests, to the model
under an agent's prompt and schema, one call per frame, no Godot. Each frame
goes in as a step 0 with an empty log, which is exactly what the agent sees at
the start of a run. It scores the agent's `goal` report against the truth.

    python eval/goal_probe.py sample eval/phase2/R1_no_goal_hint eval/phase2/R3_memory_log \
        --out eval/phase2/R4_goal_after_reason/probe
    python eval/goal_probe.py run --agent a03 --out eval/phase2/R4_goal_after_reason/probe
    python eval/goal_probe.py run --agent a04 --out eval/phase2/R4_goal_after_reason/probe
    python eval/goal_probe.py report eval/phase2/R4_goal_after_reason/probe

Only an agent whose reply carries a `goal` field can be probed. `run` uses the
decider's profile settings (`--profile`, default remote, so the operator's
tunnel must be up) and resumes: frames already answered are skipped.

The set (`probe_set.jsonl`), one row per distinct frame (PNG sha256):
- visible frames, up to PER_BAND in each distance band (seed 0);
- NOT_VISIBLE frames where the goal is out of view, every one under 5 m first;
- forced in: the `early` frames (first round's steps 0-2, goal visible; R3
  summary's 30) and the `step0` frames (first round's step 0, with its pick).
Each row lists every recorded decision that showed that frame (`sources`), so
`early` is counted over decisions, as the R3 summary counted it.

Ground truth is `true_goal()` from agent_evidence.py. Deterministic apart from
the model.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import copy
import hashlib
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_evidence import run_dirs, true_goal  # noqa: E402
from phaselib import REPO_ROOT, read_jsonl  # noqa: E402

BANDS = [("<5 m", 0.0, 5.0), ("5-10 m", 5.0, 10.0), ("10-20 m", 10.0, 20.0),
         (">=20 m", 20.0, float("inf"))]
PER_BAND = 30
NOT_VISIBLE = 60
NEAR_M = 5.0
EARLY_STEPS = 3
SEED = 0

#: Pre-registered in eval/phase2/R4_goal_after_reason/README.md, "Probe gate".
GATE = {"calibration_early_max": 6, "early_min": 27, "seen_pooled_min": 0.50,
        "seen_near_min": 0.70, "false_positive_max": 0.10}


def band_of(distance: float) -> str:
    return next(name for name, lo, hi in BANDS if lo <= distance < hi)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# --- sample -------------------------------------------------------------------

def cmd_sample(args: argparse.Namespace) -> int:
    frames: Dict[str, Dict[str, Any]] = {}
    first = args.rounds[0].resolve()
    for unit in args.rounds:
        in_first = unit.resolve() == first
        for run in run_dirs(unit):
            run_id = "/".join(run.parts[-3:])
            for d in read_jsonl(run / "decisions.jsonl"):
                manifest = d.get("manifest") or {}
                truth = true_goal(manifest)
                if truth is None or not d.get("frame") or d.get("index") is None:
                    continue
                png = run / d["frame"]
                sha = hashlib.sha256(png.read_bytes()).hexdigest()[:16]
                row = frames.setdefault(sha, {
                    "sha": sha, "frame": rel(png), "manifest": manifest, "truth": truth,
                    "distance": round(float(manifest["goal"]["distance"]), 2),
                    "sources": []})
                step = int(d["step"])
                source = {"round": unit.name, "run": run_id, "step": step,
                          "index": d["index"], "goal": d.get("goal")}
                if in_first and step < EARLY_STEPS and truth != "not_visible":
                    source["early"] = True
                if in_first and step == 0:
                    source["step0"] = True
                row["sources"].append(source)

    rng = random.Random(SEED)
    chosen: Dict[str, Dict[str, Any]] = {}
    for row in frames.values():
        if any(s.get("early") or s.get("step0") for s in row["sources"]):
            chosen[row["sha"]] = row
    for name, _, _ in BANDS:
        pool = sorted((r for r in frames.values() if r["truth"] != "not_visible"
                       and band_of(r["distance"]) == name), key=lambda r: r["sha"])
        have = sum(1 for r in pool if r["sha"] in chosen)
        rest = [r for r in pool if r["sha"] not in chosen]
        for row in rng.sample(rest, max(0, min(len(rest), PER_BAND - have))):
            chosen[row["sha"]] = row
    hidden = sorted((r for r in frames.values() if r["truth"] == "not_visible"
                     and r["sha"] not in chosen), key=lambda r: r["sha"])
    near = [r for r in hidden if r["distance"] < NEAR_M]
    far = [r for r in hidden if r["distance"] >= NEAR_M]
    picked = near[:NOT_VISIBLE] + rng.sample(far, max(0, min(len(far), NOT_VISIBLE - len(near))))
    for row in picked:
        chosen[row["sha"]] = row

    out = args.out / "probe_set.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(chosen.values(), key=lambda r: r["sha"])
    out.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    counts: Dict[str, int] = defaultdict(int)
    for r in rows:
        counts["not visible" if r["truth"] == "not_visible" else band_of(r["distance"])] += 1
    early = sum(1 for r in rows for s in r["sources"] if s.get("early"))
    print("{0} distinct frames of {1} -> {2}".format(len(rows), len(frames), rel(out)))
    print("  " + ", ".join("{0}: {1}".format(k, counts[k])
                           for k in [b[0] for b in BANDS] + ["not visible"]))
    print("  early decisions: {0}".format(early))
    return 0


# --- run ----------------------------------------------------------------------

async def probe(rows: List[Dict[str, Any]], out: Path) -> None:
    from server.decider import agent, vlm  # after the env is set
    ident = agent.record()
    done = {r["sha"] for r in read_jsonl(out)} if out.is_file() else set()
    todo = [r for r in rows if r["sha"] not in done]
    print("{0}: {1} frames, {2} already done".format(ident["agent_version"], len(rows), len(done)))
    try:
        with out.open("a") as fh:
            for i, row in enumerate(todo, 1):
                manifest = copy.deepcopy(row["manifest"])
                manifest["step"] = 0
                # Frames are not in git; refuse one that is not the frame sampled.
                png = (REPO_ROOT / row["frame"]).read_bytes()
                if hashlib.sha256(png).hexdigest()[:16] != row["sha"]:
                    raise SystemExit("{0} no longer matches sha {1}".format(row["frame"], row["sha"]))
                b64 = base64.b64encode(png).decode()
                result: Dict[str, Any] = {"sha": row["sha"], **ident}
                try:
                    decision = await vlm.decide(manifest, b64, memory=[])
                    result.update(goal=decision.goal, index=decision.index,
                                  reason=decision.reason, rung=decision.rung,
                                  model=decision.model,
                                  latency_ms=round(decision.latency_ms, 1))
                except vlm.VLMError as exc:
                    result["error"] = str(exc)[:300]
                fh.write(json.dumps(result, sort_keys=True) + "\n")
                fh.flush()
                print("  {0}/{1} {2} truth={3} goal={4}".format(
                    i, len(todo), row["sha"], row["truth"], result.get("goal")))
    finally:
        await vlm.aclose()


def cmd_run(args: argparse.Namespace) -> int:
    # Both before the decider is imported: config reads the profile at import,
    # agent.current() reads VLM_AGENT on every call.
    os.environ["VLM_PROFILE"] = args.profile
    os.environ["VLM_AGENT"] = args.agent
    from server.decider import agent
    memory = agent.get(args.agent).features.get("memory") or {}
    if "goal" not in memory.get("fields", []):
        print("agent {0} makes no goal report; nothing to probe".format(args.agent))
        return 1
    rows = read_jsonl(args.out / "probe_set.jsonl")
    if args.limit:
        rows = rows[:args.limit]
    asyncio.run(probe(rows, args.out / "probe_{0}.jsonl".format(args.agent)))
    return 0


# --- report -------------------------------------------------------------------

def frac(k: int, n: int) -> str:
    return "–" if not n else "{0}/{1} ({2:.0%})".format(k, n, k / n)


def score(rows: Dict[str, Dict[str, Any]], answers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    s: Dict[str, Any] = defaultdict(int)
    s["bands"] = {name: [0, 0] for name, _, _ in BANDS}
    latencies: List[float] = []
    models = set()
    for sha, row in rows.items():
        ans = answers.get(sha)
        if ans is None:
            continue
        s["answered"] += 1
        if ans.get("error") or ans.get("goal") is None:
            s["no_report"] += 1
        models.add(ans.get("model"))
        if ans.get("latency_ms") is not None:
            latencies.append(ans["latency_ms"])
        seen = ans.get("goal") not in (None, "not_visible")
        if row["truth"] == "not_visible":
            s["hidden"] += 1
            s["false_pos"] += seen
            if row["distance"] < NEAR_M:
                s["hidden_near"] += 1
                s["false_pos_near"] += seen
        else:
            band = s["bands"][band_of(row["distance"])]
            band[0] += seen
            band[1] += 1
            s["visible"] += 1
            s["seen"] += seen
            if seen:
                s["seen_dir"] += 1
                s["dir_ok"] += ans["goal"] == row["truth"]
        for src in row["sources"]:
            if src.get("early"):
                s["early"] += 1
                s["early_seen"] += seen
            if src.get("step0"):
                s["step0"] += 1
                s["step0_same"] += ans.get("index") == src["index"]
    s["latency"] = latencies
    s["models"] = sorted(m for m in models if m)
    return s


def recorded_step0(rows: Dict[str, Dict[str, Any]], answers: Dict[str, Dict[str, Any]],
                   round_name: str) -> List[int]:
    """[matching, compared]: the probe's step-0 report against what a round
    recorded at step 0 on the same frame (the calibration's replay check)."""
    out = [0, 0]
    for sha, row in rows.items():
        ans = answers.get(sha)
        for src in row["sources"]:
            if ans and src["round"] == round_name and src["step"] == 0 and src.get("goal"):
                out[1] += 1
                out[0] += ans.get("goal") == src["goal"]
    return out


def cmd_report(args: argparse.Namespace) -> int:
    rows = {r["sha"]: r for r in read_jsonl(args.dir / "probe_set.jsonl")}
    agents = sorted(p.stem[len("probe_"):] for p in args.dir.glob("probe_a*.jsonl"))
    if not agents:
        print("no probe_aNN.jsonl in {0}".format(args.dir))
        return 1
    answers = {a: {r["sha"]: r for r in read_jsonl(args.dir / "probe_{0}.jsonl".format(a))}
               for a in agents}
    scores = {a: score(rows, answers[a]) for a in agents}

    def line(title: str, cell) -> str:
        return "| {0} | {1} |".format(title, " | ".join(cell(scores[a]) for a in agents))

    def pq(values: List[float], q: float) -> str:
        if not values:
            return "–"
        values = sorted(values)
        return "{0:.2f}".format(values[min(len(values) - 1, int(q * len(values)))] / 1000.0)

    out = ["# Goal-detection probe", "",
           "`python eval/goal_probe.py report {0}`. Each frame is sent as step 0 with an empty "
           "log; the reply's `goal` report is scored against the manifest's ground truth "
           "(`true_goal()`, eval/agent_evidence.py). Seen = any report other than "
           "`not_visible`. Early and step-0 rows count recorded decisions; every other row "
           "counts distinct frames.".format(rel(args.dir)), "",
           "| Measure | {0} |".format(" | ".join("`{0}`".format(a) for a in agents)),
           "|---|{0}".format("---|" * len(agents)),
           line("frames answered", lambda s: "{0} / {1}".format(s["answered"], len(rows))),
           line("model", lambda s: ", ".join(s["models"]) or "–"),
           line("no valid report", lambda s: str(s["no_report"])),
           line("**early** (first round, steps 0-2, goal visible)",
                lambda s: frac(s["early_seen"], s["early"])),
           line("**seen when visible**, pooled", lambda s: frac(s["seen"], s["visible"]))]
    for name, _, _ in BANDS:
        out.append(line("seen when visible, {0}".format(name),
                        lambda s, n=name: frac(*s["bands"][n])))
    out += [line("**false positive**, not visible", lambda s: frac(s["false_pos"], s["hidden"])),
            line("false positive, not visible under 5 m",
                 lambda s: frac(s["false_pos_near"], s["hidden_near"])),
            line("direction right, of seen", lambda s: frac(s["dir_ok"], s["seen_dir"])),
            line("step-0 pick = first round's pick", lambda s: frac(s["step0_same"], s["step0"])),
            line("latency p50 / p95 (s)",
                 lambda s: "{0} / {1}".format(pq(s["latency"], 0.5), pq(s["latency"], 0.95)))]

    if args.calibration in scores and args.candidate in scores:
        cal, cand = scores[args.calibration], scores[args.candidate]
        near = cand["bands"][BANDS[0][0]]
        checks = [
            ("Calibration: `{0}` early ≤ {1}".format(args.calibration,
                                                    GATE["calibration_early_max"]),
             cal["early"] > 0 and cal["early_seen"] <= GATE["calibration_early_max"],
             frac(cal["early_seen"], cal["early"])),
            ("`{0}` early ≥ {1}".format(args.candidate, GATE["early_min"]),
             cand["early_seen"] >= GATE["early_min"], frac(cand["early_seen"], cand["early"])),
            ("`{0}` seen when visible, pooled ≥ {1:.0%}".format(args.candidate,
                                                                GATE["seen_pooled_min"]),
             cand["visible"] > 0 and cand["seen"] / cand["visible"] >= GATE["seen_pooled_min"],
             frac(cand["seen"], cand["visible"])),
            ("`{0}` seen when visible, under 5 m ≥ {1:.0%}".format(args.candidate,
                                                                   GATE["seen_near_min"]),
             near[1] > 0 and near[0] / near[1] >= GATE["seen_near_min"], frac(*near)),
            ("`{0}` false positives ≤ {1:.0%}".format(args.candidate, GATE["false_positive_max"]),
             cand["hidden"] > 0
             and cand["false_pos"] / cand["hidden"] <= GATE["false_positive_max"],
             frac(cand["false_pos"], cand["hidden"])),
        ]
        passed = all(ok for _, ok, _ in checks)
        replay = recorded_step0(rows, answers[args.calibration], args.calibration_round)
        out += ["", "## Gate: **{0}**".format("PASS, fly" if passed else "FAIL, do not fly"), "",
                "| Check | Result | |", "|---|---|---|"]
        out += ["| {0} | {1} | {2} |".format(t, v, "pass" if ok else "**fail**")
                for t, ok, v in checks]
        out += ["", "Replay check (not gated): `{0}`'s step-0 report equals the one "
                "{1} recorded at step 0 on the same frame in {2}.".format(
                    args.calibration, args.calibration_round, frac(*replay))]
    text = "\n".join(out) + "\n"
    print(text, end="")
    (args.dir / "probe.md").write_text(text)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample", help="build probe_set.jsonl from recorded rounds")
    s.add_argument("rounds", nargs="+", type=Path,
                   help="round folders; the first supplies the early and step0 subsets")
    s.add_argument("--out", type=Path, required=True)
    r = sub.add_parser("run", help="ask one agent about every frame in the set")
    r.add_argument("--agent", required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--profile", choices=("remote", "local"), default="remote")
    r.add_argument("--limit", type=int, default=0, help="first N frames only (smoke test)")
    g = sub.add_parser("report", help="score every probe_aNN.jsonl and write probe.md")
    g.add_argument("dir", type=Path)
    g.add_argument("--calibration", default="a03")
    g.add_argument("--calibration-round", default="R3_memory_log")
    g.add_argument("--candidate", default="a04")
    args = parser.parse_args()
    return {"sample": cmd_sample, "run": cmd_run, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
