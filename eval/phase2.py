#!/usr/bin/env python3
"""Phase 2 runner: fly a round of the iterative-improvement loop, then check it.

The spec is docs/phase2-test-plan.md; validity (§10) and the rubric (§9) are
Phase 1's, docs/phase1-test-plan.md. The engine is eval/phaselib.py.

    python eval/phase2.py init                     # lay out eval/phase2/ (idempotent)
    python eval/phase2.py run --round P2.0         # fly order.txt, skip valid runs
    python eval/phase2.py run --round R1 --only s01/dynamic/1
    python eval/phase2.py validate --round R1      # re-check without flying
    python eval/phase2.py status
    python eval/phase2.py results                  # round comparison -> eval/phase2/results/

A round tests one agent version (server/decider/agent.py) on every site, every
arm, seed 1: 18 runs. The decider must be serving that agent:

    python -m server.decider --profile remote --agent a01

Adding a round: add the agent version in agent.py, add an entry to ROUNDS, run
`init`. A round's lock includes its agent's sha, so editing an agent after its
round is laid out is refused.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phaselib import (ARMS, ALL_SITES, REPO_ROOT, SEEDS, SITES, Phase,  # noqa: E402
                      s11_tables, write_runs_csv)
from server.decider import agent as agents  # noqa: E402

import phase1  # noqa: E402

PHASE_DIR = REPO_ROOT / "eval" / "phase2"

#: What every screening round flies: all six sites, all three arms, one seed.
ROUND_SITES = list(SITES)
ROUND_SEEDS = [1]

#: Rounds in the order they were flown. Never edit a flown round; add one.
#:   "R1": {"folder": "R1_<slug>", "title": "...", "agent": "a01",
#:          "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
#: The final round is the full Phase 1 design under the chosen agent:
#:   "F": {"folder": "final", "title": "Final: <agent>", "agent": "aNN",
#:         "sites": ROUND_SITES, "seeds": list(SEEDS), "citable": True},
ROUNDS: Dict[str, Dict[str, Any]] = {
    "P2.0": {"folder": "P2.0_shakedown", "title": "Shakedown (fake decider)",
             "agent": "a00", "sites": ROUND_SITES, "seeds": ROUND_SEEDS,
             "citable": False},
    "R1": {"folder": "R1_no_goal_hint", "title": "No goal hint", "agent": "a01",
           "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R2": {"folder": "R2_text_memory", "title": "Text memory, full run", "agent": "a02",
           "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R3": {"folder": "R3_memory_log", "title": "Memory log, code-written", "agent": "a03",
           "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R4": {"folder": "R4_goal_after_reason", "title": "Memory log, goal reported last",
           "agent": "a04", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # Defined with a05; its probe failed (the identifier took the drawn turn-around
    # marker for the goal), so before flying the round moved to a06, which shows
    # the identifier the unannotated frame. R5 README, "Change".
    "R5": {"folder": "R5_goal_identifier", "title": "Goal identifier on the clean frame, sighting age",
           "agent": "a06", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # Two candidates were probed: a07 (pose log, sighting line kept) and a08 (pose
    # log, no sighting line). Defined with a07, the tie-break; a08 won the probe
    # (spin turn-around 6/40 against 17/40) and flies. R6 README, "Probe gate".
    "R6": {"folder": "R6_pose_log", "title": "Ground-truth pose in the memory log",
           "agent": "a08", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # a10 is a08 (no sighting line) plus comparison lines in the log. a09 (a07 plus
    # the same lines) was probed first and did not fly. R7 README, "Change".
    "R7": {"folder": "R7_comparison_lines", "title": "Comparison lines in the log",
           "agent": "a10", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R7C: a08 (R6's agent) flown on sctsvr6 under lavapipe, the host R7 flies on, so R7
    # against R6 can be read without the renderer change. Not a round of its own: no
    # change, no prediction. R7 README, "Host".
    "R7C": {"folder": "R7C_a08_control", "title": "a08 control on the R7 host",
            "agent": "a08", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    "R8": {"folder": "R8_heading_word", "title": "Heading as a compass word",
           "agent": "a11", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R8N: a12 is a10 plus one sentence with no content, flown beside R8 on the same
    # host and SHA. R8N against R7 is the noise floor of a prompt edit; R8 is read
    # against it. R8 README, "Attribution rule".
    "R8N": {"folder": "R8N_noop_control", "title": "No-op prompt edit (noise floor)",
            "agent": "a12", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
    # R9: the bundle round (operator, 2026-10-22). a13 is several calls with one job
    # each plus a code-kept map (server/decider/orchestrator.py, spatial.py). More than
    # one change, by decision: success is credited to the bundle, not its parts. Its
    # control R9C (the agent R8 carries forward, on the same host) is added when R8 is
    # read. R9 README, "Change".
    "R9": {"folder": "R9_hail_mary", "title": "Orchestrated agent with a spatial memory",
           "agent": "a13", "sites": ROUND_SITES, "seeds": ROUND_SEEDS, "citable": False},
}

#: Phase 1 §3 and §6, minus the prompt: in Phase 2 the prompt is part of the
#: agent, and each round's own config.lock.json adds the agent's version and
#: sha and its prompt's version and sha.
LOCK: Dict[str, Any] = {
    "spec": "docs/phase2-test-plan.md",
    "model": "Qwen3-VL-30B-A3B",
    "vlm_profile": "remote",
    "temperature": 0.0,
    "frame_size": [768, 768],
    "freeze_world": True,
    "physics_ticks_per_second": 60,
    "godot_version": "4.7.2-stable (official)",
    "config": {"fov_deg": 87.0, "camera_pitch": 0.0, "num_actions": 5,
               "include_turn_around": True, "fan_spread": 1.0,
               "action_dist": 1.7, "annotation_distance": 6.0},
    "max_steps": 60,
    "max_collisions": -1,
    "stop_on_goal": True,
    "wall_clock_s": 900,
    "seeds": list(SEEDS),
    "spawn_jitter": {"dz_m": 0.5, "dyaw_deg": 5.0},
    "sites": {site_id: version for site_id, version in SITES.values()},
    # P2.0 flies the stand-in router (server/decider/fake_litellm.py), as 1.0 did.
    "overrides": {"P2.0": {"model": "stub"}},
}

for _round, _spec in ROUNDS.items():
    if not _spec.get("agent"):
        raise SystemExit("round {0} names no agent".format(_round))

def round_readme(unit: str) -> str:
    """Stub for a round's write-up (docs/phase2-test-plan.md §4 step 1).

    Filled in and committed before the round flies; after it flies only the
    Outcome section changes. Every claim under Evidence cites a path.
    """
    spec = ROUNDS[unit]
    ident = agents.describe(spec["agent"])
    return "\n".join([
        "# {0}: {1}".format(unit, spec["title"]), "",
        "**Agent:** `{agent_version}` (`{agent_sha}`) · **Prompt:** `{prompt_version}` "
        "(`{prompt_sha}`) · **Status:** pre-registered, not flown".format(**ident), "",
        "Written before flying. Spec: `docs/phase2-test-plan.md`.", "",
        "## Change", "", "<!-- One change, and how it differs from the agent it builds on. -->", "",
        "## Evidence", "",
        "<!-- Past data that points at this change. Every claim cites a path: results tables,",
        "     summary.md, run IDs and steps, evidence.md (python eval/agent_evidence.py ...). -->", "",
        "## Hypothesis", "", "<!-- One falsifiable sentence. -->", "",
        "## Predictions", "", "<!-- Per arm, and per site where it differs. Direction and size. -->", "",
        "| Arm | Baseline (R0) | Predicted |", "|---|---|---|",
        "| initial | | |", "| final | | |", "| dynamic | | |", "",
        "## Manipulation check", "",
        "<!-- A measurable sign the change took effect, independent of success. -->", "",
        "## Drop criterion", "", "<!-- The result that means this change is not carried forward. -->", "",
        "## Probe gate", "",
        "<!-- Required when the change touches what the model is asked to perceive (§4 step 2):",
        "     eval/goal_probe.py thresholds, set before the probe runs. Otherwise \"Not needed\". -->", "",
        "## Builds on", "", "<!-- Previous round and agent. -->", "",
        "## Outcome", "", "Not flown. After the round: one line on whether the hypothesis held, "
        "and a link to [summary.md](summary.md).", ""])


PHASE = Phase(number=2, root=PHASE_DIR, unit_key="round", unit_label="Round",
              units=ROUNDS, lock=LOCK, script="eval/phase2.py",
              spec="docs/phase2-test-plan.md", agent_lock=agents.describe,
              unit_readme=round_readme)

BASELINE = "R0"
BASELINE_NOTE = ("R0 is the Phase 1 agent (a00), not flown again: its seed-1 runs from "
                 "eval/phase1/, under the same lock apart from the agent fields.")


def baseline_runs() -> List[Dict[str, Any]]:
    """Phase 1's seed-1 runs, as the round every Phase 2 round is compared with."""
    units = phase1.PHASE.complete_units(citable_only=True)
    return [dict(r, unit=BASELINE) for r in phase1.PHASE.collect_runs(units)
            if r["seed"] in ROUND_SEEDS]


def cell(run: Dict[str, Any]) -> str:
    if run["goal_reached"]:
        return "✓ {0}".format(run["steps"])
    return "✗ {0}".format(run["label"] or run["end_reason"])


def cmd_results(_args: argparse.Namespace) -> int:
    """Every complete round side by side, R0 first. Deterministic, like Phase 1's."""
    screening = [u for u in PHASE.complete_units(citable_only=False)
                 if not ROUNDS[u]["citable"] and u != "P2.0"]
    finals = PHASE.complete_units(citable_only=True)
    columns = [(BASELINE, baseline_runs())]
    columns += [(u, PHASE.collect_runs([u])) for u in screening]

    lines = ["# Phase 2 results", "",
             "Generated by `python eval/phase2.py results`. Do not edit by hand.", "",
             "Spec: `docs/phase2-test-plan.md`. One run per cell (seed 1), so each "
             "cell is a screen, not an estimate. " + BASELINE_NOTE, ""]
    pending = sum(1 for _, runs in columns[1:] for r in runs if not r["label"])
    if pending:
        lines += ["> **{0} runs have no manual label yet.** Rerun after labelling."
                  .format(pending), ""]

    lines += ["## Rounds", "",
              "| Round | Agent | Title |", "|---|---|---|",
              "| {0} | a00 | Phase 1 baseline |".format(BASELINE)]
    lines += ["| {0} | {1} | {2} |".format(u, ROUNDS[u]["agent"], ROUNDS[u]["title"])
              for u in screening]
    lines.append("")

    lines += ["## Success by arm", "",
              "| Arm | " + " | ".join(name for name, _ in columns) + " |",
              "|---" * (len(columns) + 1) + "|"]
    for arm in ARMS:
        counts = []
        for _, runs in columns:
            in_arm = [r for r in runs if r["arm"] == arm]
            counts.append("{0}/{1}".format(sum(r["goal_reached"] for r in in_arm),
                                           len(in_arm)))
        lines.append("| {0} | {1} |".format(arm, " | ".join(counts)))
    lines.append("")

    lines += ["## Every cell", "",
              "✓ steps to goal, or ✗ and the §9 label (end reason if not yet labelled).", "",
              "| Site | Arm | " + " | ".join(name for name, _ in columns) + " |",
              "|---|---" + "|---" * len(columns) + "|"]
    for site in ALL_SITES:
        for arm in ARMS:
            row = []
            for _, runs in columns:
                match = [r for r in runs if r["site"] == site and r["arm"] == arm]
                row.append(cell(match[0]) if match else "")
            lines.append("| {0} | {1} | {2} |".format(site, arm, " | ".join(row)))
    lines.append("")

    final_runs: List[Dict[str, Any]] = []
    if finals:
        final_runs = PHASE.collect_runs(finals)
        lines += ["# Final round ({0}, agent {1})".format(
            ", ".join(finals), ", ".join(ROUNDS[u]["agent"] for u in finals)), ""]
        lines += s11_tables(final_runs)

    PHASE.results_dir.mkdir(parents=True, exist_ok=True)
    (PHASE.results_dir / "results.md").write_text("\n".join(lines))
    flown = [r for _, runs in columns[1:] for r in runs] + final_runs
    write_runs_csv(PHASE.results_dir / "runs.csv", flown, PHASE.unit_key)
    print("{0} rounds + {1} -> {2}".format(len(screening), BASELINE,
                                           PHASE.results_dir.relative_to(REPO_ROOT)))
    return 0


def main() -> int:
    return PHASE.main(__doc__, extra=lambda sub: sub.add_parser("results")
                      .set_defaults(func=cmd_results))


if __name__ == "__main__":
    raise SystemExit(main())
