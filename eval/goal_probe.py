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

An agent with a goal identifier (a05 on) is probed through the identifier:
the frame goes to it alone, as in flight, and its report is scored; the
navigator is then asked for the step-0 pick with that report.

    python eval/goal_probe.py run --agent a05 --out eval/phase2/R5_goal_identifier/probe

The replay probe (R5 on) puts a log in place. It takes recorded decisions
where an earlier sighting is 5-20 steps old and the goal is now out of view,
rebuilds the log the agent had, and asks whether the navigator's reason still
places the goal around it now (agent_evidence.claims_goal). The R4 summary:
a probe that only tests step 0 cannot see a failure that builds up in the log.

    python eval/goal_probe.py sample-replay eval/phase2/R4_goal_after_reason \
        --out eval/phase2/R5_goal_identifier/probe
    python eval/goal_probe.py run-replay --agent a04 --out eval/phase2/R5_goal_identifier/probe
    python eval/goal_probe.py run-replay --agent a05 --out eval/phase2/R5_goal_identifier/probe
    python eval/goal_probe.py report eval/phase2/R5_goal_identifier/probe --gate R5 \
        --calibration a04 --candidate a05

`a04` replays its own recorded log. An agent with an identifier gets a log
whose goal reports are ground truth (what a perfect identifier would have
written) and its identifier is asked about the current frame live.

Only an agent whose reply carries a `goal` field, or that has a goal
identifier, can be probed. `run` uses the
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
from agent_evidence import claims_goal, run_dirs, true_goal  # noqa: E402
from phaselib import REPO_ROOT, read_jsonl  # noqa: E402

BANDS = [("<5 m", 0.0, 5.0), ("5-10 m", 5.0, 10.0), ("10-20 m", 10.0, 20.0),
         (">=20 m", 20.0, float("inf"))]
PER_BAND = 30
NOT_VISIBLE = 60
NEAR_M = 5.0
EARLY_STEPS = 3
SEED = 0

#: Pre-registered per round, in its README's "Probe gate"; `report --gate`.
GATES = {
    "R4": {"calibration_early_max": 6, "early_min": 27, "seen_pooled_min": 0.50,
           "seen_near_min": 0.70, "false_positive_max": 0.10},
    "R5": {"early_min": 27, "seen_pooled_min": 0.90, "seen_near_min": 0.90,
           "false_positive_max": 0.05, "calibration_claim_min": 0.25,
           "claim_max": 0.10},
}
GATE = GATES["R4"]

#: Replay set: an earlier true sighting this many steps back, the goal now
#: out of view, split by how far the drone has turned since.
REPLAY_AGE = (5, 20)
REPLAY_PER_GROUP = 20
REPLAY_TURN_SPLIT = 90.0
REPLAY_GROUPS = ("stale, turned < 90°", "stale, turned ≥ 90°", "visible")


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
                    if agent.current().features.get("goal_identifier"):
                        # As in flight: the identifier sees the frame alone,
                        # and its report is what is scored.
                        sighting = await vlm.identify_goal(manifest, b64)
                        decision = await vlm.decide(manifest, b64, [], sighting.goal)
                        result.update(goal=sighting.goal, identifier_reason=sighting.reason,
                                      identifier_rung=sighting.rung,
                                      nav_latency_ms=round(decision.latency_ms, 1),
                                      latency_ms=round(sighting.latency_ms, 1))
                        if sighting.error:
                            result["identifier_error"] = sighting.error[:300]
                    else:
                        decision = await vlm.decide(manifest, b64, memory=[])
                        result.update(goal=decision.goal,
                                      latency_ms=round(decision.latency_ms, 1))
                    result.update(index=decision.index, reason=decision.reason,
                                  rung=decision.rung, model=decision.model)
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
    if not reports_goal(args.agent):
        print("agent {0} makes no goal report; nothing to probe".format(args.agent))
        return 1
    rows = read_jsonl(args.out / "probe_set.jsonl")
    if args.limit:
        rows = rows[:args.limit]
    asyncio.run(probe(rows, args.out / "probe_{0}.jsonl".format(args.agent)))
    return 0


def reports_goal(version: str) -> bool:
    """A `goal` field in the reply (a03, a04) or a goal identifier (a05 on)."""
    from server.decider import agent
    features = agent.get(version).features
    memory = features.get("memory") or {}
    return bool(features.get("goal_identifier")) or "goal" in memory.get("fields", [])


def wrap(degrees: float) -> float:
    """Into [-180, 180)."""
    return (degrees + 180.0) % 360.0 - 180.0


# --- replay -------------------------------------------------------------------

def cmd_sample_replay(args: argparse.Namespace) -> int:
    from server.decider.prompt import _turn
    from server.decider.recorder import Run
    pools: Dict[str, Dict[str, Dict[str, Any]]] = {g: {} for g in REPLAY_GROUPS}
    for unit in args.rounds:
        for run in run_dirs(unit):
            run_id = "/".join(run.parts[-3:])
            decisions = [d for d in read_jsonl(run / "decisions.jsonl")
                         if not d.get("error") and d.get("index") is not None]
            truths = {int(d["step"]): true_goal(d.get("manifest") or {}) for d in decisions}
            for d in decisions:
                step, truth = int(d["step"]), truths[int(d["step"])]
                if truth is None or not d.get("frame"):
                    continue
                seen = [n for n, t in truths.items() if n < step and t in ("ahead", "left", "right")]
                if not seen:
                    continue
                last = max(seen)
                age = step - last
                # The log as the agent had it at this step: Run.memory(), as in flight.
                memory = Run("replay:{0}:{1}".format(unit.name, run_id), run).memory(step)
                turned = wrap(sum(_turn(e) for e in memory if e["step"] >= last))
                if truth == "not_visible":
                    if not REPLAY_AGE[0] <= age <= REPLAY_AGE[1]:
                        continue
                    group = REPLAY_GROUPS[0] if abs(turned) < REPLAY_TURN_SPLIT else REPLAY_GROUPS[1]
                else:
                    group = REPLAY_GROUPS[2]
                png = run / d["frame"]
                sha = hashlib.sha256(png.read_bytes()).hexdigest()[:16]
                pools[group].setdefault(sha, {
                    "sha": sha, "frame": rel(png), "manifest": d["manifest"], "truth": truth,
                    "group": group, "age": age, "turned": round(turned, 1),
                    "distance": round(float(d["manifest"]["goal"]["distance"]), 2),
                    "source": {"round": unit.name, "run": run_id, "step": step,
                               "index": d["index"], "goal": d.get("goal"),
                               "claim": claims_goal(d.get("reason", ""))},
                    "memory": memory,
                    "truth_log": {str(e["step"]): truths.get(int(e["step"])) for e in memory}})

    rng = random.Random(SEED)
    rows: List[Dict[str, Any]] = []
    for group in REPLAY_GROUPS:
        pool = sorted(pools[group].values(), key=lambda r: r["sha"])
        rows += rng.sample(pool, min(len(pool), REPLAY_PER_GROUP))
    out = args.out / "replay_set.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    print("{0} replay frames -> {1}".format(len(rows), rel(out)))
    for group in REPLAY_GROUPS:
        pool = list(pools[group].values())
        chosen = [r for r in rows if r["group"] == group]
        print("  {0}: {1} of {2}; in flight the reason placed the goal around the drone "
              "in {3} of the pool, {4} of the chosen".format(
                  group, len(chosen), len(pool),
                  frac(sum(r["source"]["claim"] for r in pool), len(pool)),
                  frac(sum(r["source"]["claim"] for r in chosen), len(chosen))))
    return 0


async def replay(rows: List[Dict[str, Any]], out: Path) -> None:
    from server.decider import agent, vlm  # after the env is set
    ident = agent.record()
    identifier = bool(agent.current().features.get("goal_identifier"))
    done = {r["sha"] for r in read_jsonl(out)} if out.is_file() else set()
    todo = [r for r in rows if r["sha"] not in done]
    print("{0}: {1} replay frames, {2} already done".format(
        ident["agent_version"], len(rows), len(done)))
    try:
        with out.open("a") as fh:
            for i, row in enumerate(todo, 1):
                manifest = copy.deepcopy(row["manifest"])
                memory = copy.deepcopy(row["memory"])
                png = (REPO_ROOT / row["frame"]).read_bytes()
                if hashlib.sha256(png).hexdigest()[:16] != row["sha"]:
                    raise SystemExit("{0} no longer matches sha {1}".format(row["frame"], row["sha"]))
                b64 = base64.b64encode(png).decode()
                result: Dict[str, Any] = {"sha": row["sha"], **ident}
                try:
                    if identifier:
                        # The log a perfect identifier would have written.
                        for entry in memory:
                            entry["goal"] = row["truth_log"].get(str(entry["step"]))
                        sighting = await vlm.identify_goal(manifest, b64)
                        decision = await vlm.decide(manifest, b64, memory, sighting.goal)
                        result.update(goal=sighting.goal, identifier_reason=sighting.reason)
                    else:
                        decision = await vlm.decide(manifest, b64, memory)
                        result["goal"] = decision.goal
                    result.update(index=decision.index, reason=decision.reason,
                                  claim=claims_goal(decision.reason), rung=decision.rung,
                                  model=decision.model, latency_ms=round(decision.latency_ms, 1))
                except vlm.VLMError as exc:
                    result["error"] = str(exc)[:300]
                fh.write(json.dumps(result, sort_keys=True) + "\n")
                fh.flush()
                print("  {0}/{1} {2} {3} goal={4} claim={5}".format(
                    i, len(todo), row["sha"], row["group"], result.get("goal"),
                    result.get("claim")))
    finally:
        await vlm.aclose()


def cmd_run_replay(args: argparse.Namespace) -> int:
    os.environ["VLM_PROFILE"] = args.profile
    os.environ["VLM_AGENT"] = args.agent
    from server.decider import agent
    if not agent.get(args.agent).features.get("memory"):
        print("agent {0} keeps no log; nothing to replay".format(args.agent))
        return 1
    rows = read_jsonl(args.out / "replay_set.jsonl")
    if args.limit:
        rows = rows[:args.limit]
    asyncio.run(replay(rows, args.out / "replay_{0}.jsonl".format(args.agent)))
    return 0


def score_replay(rows: Dict[str, Dict[str, Any]],
                 answers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Per group: [answered, reason places the goal now, goal reported seen]."""
    s: Dict[str, Any] = {g: [0, 0, 0] for g in REPLAY_GROUPS}
    s["errors"] = 0
    for sha, row in rows.items():
        ans = answers.get(sha)
        if ans is None:
            continue
        if ans.get("error"):
            s["errors"] += 1
            continue
        cell = s[row["group"]]
        cell[0] += 1
        cell[1] += bool(ans.get("claim"))
        cell[2] += ans.get("goal") not in (None, "not_visible")
    stale = [s[g] for g in REPLAY_GROUPS[:2]]
    s["stale"] = [sum(c[i] for c in stale) for i in range(3)]
    return s


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

    replay_rows = ({r["sha"]: r for r in read_jsonl(args.dir / "replay_set.jsonl")}
                   if (args.dir / "replay_set.jsonl").is_file() else {})
    replayed = sorted(p.stem[len("replay_"):] for p in args.dir.glob("replay_a*.jsonl"))
    replay_scores = {a: score_replay(replay_rows, {r["sha"]: r for r in read_jsonl(
        args.dir / "replay_{0}.jsonl".format(a))}) for a in replayed}
    if replay_scores:
        def rline(title: str, cell) -> str:
            return "| {0} | {1} |".format(title, " | ".join(cell(replay_scores[a])
                                                           for a in replayed))
        out += ["", "## Replay with the log in place", "",
                "{0} recorded decisions where the goal was seen {1}-{2} steps earlier and "
                "is now out of view, plus in-view controls (`replay_set.jsonl`). `a04` "
                "gets its recorded log; an agent with a goal identifier gets a log of "
                "ground-truth goal reports and its identifier's live answer. *Places the "
                "goal now*: a sentence of the reason says the goal is in view or in a "
                "direction now (`claims_goal()`, eval/agent_evidence.py).".format(
                    len(replay_rows), *REPLAY_AGE), "",
                "| Measure | {0} |".format(" | ".join("`{0}`".format(a) for a in replayed)),
                "|---|{0}".format("---|" * len(replayed)),
                rline("frames answered", lambda s: "{0} / {1}".format(
                    sum(s[g][0] for g in REPLAY_GROUPS), len(replay_rows))),
                rline("**reason places the goal now**, out of view, pooled",
                      lambda s: frac(s["stale"][1], s["stale"][0]))]
        for g in REPLAY_GROUPS[:2]:
            out.append(rline("reason places the goal now, {0}".format(g),
                             lambda s, g=g: frac(s[g][1], s[g][0])))
        out += [rline("goal reported seen, out of view, pooled",
                      lambda s: frac(s["stale"][2], s["stale"][0])),
                rline("reason places the goal now, in view (control)",
                      lambda s: frac(s[REPLAY_GROUPS[2]][1], s[REPLAY_GROUPS[2]][0])),
                rline("goal reported seen, in view (control)",
                      lambda s: frac(s[REPLAY_GROUPS[2]][2], s[REPLAY_GROUPS[2]][0]))]

    if args.gate == "R5" and args.candidate in scores:
        gate = GATES["R5"]
        cand = scores[args.candidate]
        near = cand["bands"][BANDS[0][0]]
        cal_r = replay_scores.get(args.calibration, {}).get("stale", [0, 0, 0])
        cand_r = replay_scores.get(args.candidate, {}).get("stale", [0, 0, 0])
        checks = [
            ("`{0}` early ≥ {1}".format(args.candidate, gate["early_min"]),
             cand["early_seen"] >= gate["early_min"], frac(cand["early_seen"], cand["early"])),
            ("`{0}` seen when visible, pooled ≥ {1:.0%}".format(args.candidate,
                                                                gate["seen_pooled_min"]),
             cand["visible"] > 0 and cand["seen"] / cand["visible"] >= gate["seen_pooled_min"],
             frac(cand["seen"], cand["visible"])),
            ("`{0}` seen when visible, under 5 m ≥ {1:.0%}".format(args.candidate,
                                                                   gate["seen_near_min"]),
             near[1] > 0 and near[0] / near[1] >= gate["seen_near_min"], frac(*near)),
            ("`{0}` false positives ≤ {1:.0%}".format(args.candidate, gate["false_positive_max"]),
             cand["hidden"] > 0
             and cand["false_pos"] / cand["hidden"] <= gate["false_positive_max"],
             frac(cand["false_pos"], cand["hidden"])),
            ("Calibration: `{0}` replay, reason places the goal now ≥ {1:.0%}".format(
                args.calibration, gate["calibration_claim_min"]),
             cal_r[0] > 0 and cal_r[1] / cal_r[0] >= gate["calibration_claim_min"],
             frac(cal_r[1], cal_r[0])),
            ("`{0}` replay, reason places the goal now ≤ {1:.0%}".format(
                args.candidate, gate["claim_max"]),
             cand_r[0] > 0 and cand_r[1] / cand_r[0] <= gate["claim_max"],
             frac(cand_r[1], cand_r[0])),
        ]
        passed = all(ok for _, ok, _ in checks)
        out += ["", "## Gate (R5): **{0}**".format("PASS, fly" if passed else "FAIL, do not fly"),
                "", "| Check | Result | |", "|---|---|---|"]
        out += ["| {0} | {1} | {2} |".format(t, v, "pass" if ok else "**fail**")
                for t, ok, v in checks]
    elif args.gate == "R4" and args.calibration in scores and args.candidate in scores:
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
    sr = sub.add_parser("sample-replay", help="build replay_set.jsonl from recorded rounds")
    sr.add_argument("rounds", nargs="+", type=Path)
    sr.add_argument("--out", type=Path, required=True)
    rr = sub.add_parser("run-replay", help="replay every frame in the set with its log")
    rr.add_argument("--agent", required=True)
    rr.add_argument("--out", type=Path, required=True)
    rr.add_argument("--profile", choices=("remote", "local"), default="remote")
    rr.add_argument("--limit", type=int, default=0, help="first N frames only (smoke test)")
    g = sub.add_parser("report", help="score every probe_aNN.jsonl and write probe.md")
    g.add_argument("dir", type=Path)
    g.add_argument("--calibration", default="a03")
    g.add_argument("--calibration-round", default="R3_memory_log")
    g.add_argument("--candidate", default="a04")
    g.add_argument("--gate", choices=sorted(GATES), default="R4")
    args = parser.parse_args()
    return {"sample": cmd_sample, "run": cmd_run, "sample-replay": cmd_sample_replay,
            "run-replay": cmd_run_replay, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
