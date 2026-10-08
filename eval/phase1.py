#!/usr/bin/env python3
"""Phase 1 runner: fly a mini-phase under the frozen spec, then check it.

The spec is docs/phase1-test-plan.md. Section numbers below point into it.
The engine is eval/phaselib.py; this file is Phase 1's configuration.

    python eval/phase1.py init                       # lay out eval/phase1/ (idempotent)
    python eval/phase1.py run --mini-phase 1.0       # fly order.txt, skip valid runs
    python eval/phase1.py run --mini-phase 1A --only s01/dynamic/3
    python eval/phase1.py validate --mini-phase 1A   # re-check without flying
    python eval/phase1.py status
    python eval/phase1.py results                    # §11 tables -> eval/phase1/results/

One Godot at a time, always (§7.1): parallel runs would inflate decision
latency, which is a dependent variable. A decider must already be running.
Standard library only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phaselib import (ARMS, CHANGE_EVENTS, REPO_ROOT, SEEDS, SITES,  # noqa: E402,F401
                      TRIGGER_X, Phase, change_step_ok, crossing_step, read_json,
                      read_jsonl, s11_tables, write_runs_csv)

PHASE_DIR = REPO_ROOT / "eval" / "phase1"

#: §7 table. seeds: which replicates the mini-phase flies.
MINI_PHASES: Dict[str, Dict[str, Any]] = {
    "1.0": {"folder": "1.0_shakedown", "title": "Shakedown (fake decider)",
            "sites": list(SITES), "seeds": [1], "citable": False},
    "1A": {"folder": "1A_s01", "title": "Object Appearance",
           "sites": ["s01"], "seeds": list(SEEDS), "citable": True},
    "1Ba": {"folder": "1Ba_s02a", "title": "Door Switch, out of view, A opens",
            "sites": ["s02a"], "seeds": list(SEEDS), "citable": True},
    "1Bc": {"folder": "1Bc_s02c", "title": "Door Switch, out of view, C opens",
            "sites": ["s02c"], "seeds": list(SEEDS), "citable": True},
    "1Ca": {"folder": "1Ca_s02va", "title": "Door Switch, in view, A opens",
            "sites": ["s02va"], "seeds": list(SEEDS), "citable": True},
    "1Cc": {"folder": "1Cc_s02vc", "title": "Door Switch, in view, C opens",
            "sites": ["s02vc"], "seeds": list(SEEDS), "citable": True},
    "1D": {"folder": "1D_s03", "title": "Split Path",
           "sites": ["s03"], "seeds": list(SEEDS), "citable": True},
}

#: §7.4, verbatim. 1.0 is not in the spec's list; it is generated the same way.
ORDERS: Dict[str, str] = {
    "1A": """s01/final/1, s01/initial/4, s01/dynamic/4, s01/final/4, s01/final/3, s01/initial/1,
s01/final/2, s01/initial/2, s01/dynamic/1, s01/dynamic/5, s01/initial/5, s01/final/5,
s01/dynamic/2, s01/initial/3, s01/dynamic/3""",
    "1Ba": """s02a/initial/3, s02a/dynamic/5, s02a/dynamic/4, s02a/initial/4, s02a/final/2,
s02a/final/5, s02a/final/1, s02a/initial/5, s02a/initial/1, s02a/final/3, s02a/final/4,
s02a/dynamic/3, s02a/initial/2, s02a/dynamic/1, s02a/dynamic/2""",
    "1Bc": """s02c/initial/1, s02c/initial/5, s02c/initial/2, s02c/dynamic/5, s02c/final/3,
s02c/final/1, s02c/dynamic/1, s02c/dynamic/4, s02c/initial/4, s02c/dynamic/2, s02c/final/2,
s02c/dynamic/3, s02c/final/5, s02c/final/4, s02c/initial/3""",
    "1Ca": """s02va/dynamic/3, s02va/dynamic/2, s02va/final/2, s02va/final/5, s02va/final/4,
s02va/dynamic/1, s02va/initial/2, s02va/dynamic/4, s02va/initial/3, s02va/initial/5,
s02va/initial/1, s02va/dynamic/5, s02va/final/1, s02va/final/3, s02va/initial/4""",
    "1Cc": """s02vc/dynamic/3, s02vc/final/3, s02vc/initial/5, s02vc/initial/2, s02vc/dynamic/2,
s02vc/initial/3, s02vc/final/4, s02vc/initial/1, s02vc/final/1, s02vc/dynamic/1,
s02vc/final/5, s02vc/dynamic/5, s02vc/final/2, s02vc/dynamic/4, s02vc/initial/4""",
    "1D": """s03/final/2, s03/dynamic/4, s03/initial/4, s03/initial/2, s03/dynamic/5, s03/final/3,
s03/initial/3, s03/dynamic/2, s03/final/4, s03/initial/1, s03/dynamic/1, s03/initial/5,
s03/final/1, s03/final/5, s03/dynamic/3""",
}

#: §3 and §6, as recorded per run. `run.json` must agree with every entry.
LOCK: Dict[str, Any] = {
    "spec": "docs/phase1-test-plan.md",
    "model": "Qwen3-VL-30B-A3B",
    "vlm_profile": "remote",
    "temperature": 0.0,
    "prompt_version": "p02",
    "prompt_sha": "26260774b60e",
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
    # 1.0 flies the stand-in router (server/decider/fake_litellm.py) so it
    # spends no H100 time. Everything else is checked as for a citable phase.
    "overrides": {"1.0": {"model": "stub"}},
}

PHASE = Phase(number=1, root=PHASE_DIR, unit_key="mini_phase", unit_label="Mini-phase",
              units=MINI_PHASES, lock=LOCK, orders=ORDERS, script="eval/phase1.py",
              spec="docs/phase1-test-plan.md")

# Module-level names eval/phase1_label.py and older notebooks import.
phase_dir = PHASE.phase_dir
run_dir_for = PHASE.run_dir_for
order_of = PHASE.order_of
latest_row = PHASE.latest_row
load_matrix = PHASE.load_matrix


def cmd_results(_args: argparse.Namespace) -> int:
    """§11 tables and contrasts over every complete citable mini-phase.

    Deterministic: no timestamps, sorted inputs, so a rerun on the same data
    gives byte-identical files.
    """
    mps = PHASE.complete_units(citable_only=True)
    runs = PHASE.collect_runs(mps)
    if not runs:
        print("no complete citable mini-phases")
        return 1
    pending = sum(1 for r in runs if "pending" in r["reviewer"].lower())
    lines = ["# Phase 1 results", "",
             "Generated by `python eval/phase1.py results` from every complete, citable "
             "mini-phase ({0}). Do not edit by hand.".format(", ".join(mps)), "",
             "Spec: `docs/phase1-test-plan.md`. SR CI is Wilson 95% (§8). Latency is "
             "pooled over every decision in the cell, linear-interpolated percentiles. "
             "Label counts come from each mini-phase's `labels.csv` (§9).", ""]
    if pending:
        lines += ["> **{0} of {1} labels are still pending operator confirmation.** "
                  "Rerun this after confirming them.".format(pending, len(runs)), ""]
    lines += s11_tables(runs)

    PHASE.results_dir.mkdir(parents=True, exist_ok=True)
    (PHASE.results_dir / "results.md").write_text("\n".join(lines))
    write_runs_csv(PHASE.results_dir / "runs.csv", runs, PHASE.unit_key)
    print("{0} runs from {1} -> {2}".format(len(runs), ", ".join(mps),
                                             PHASE.results_dir.relative_to(REPO_ROOT)))
    return 0


def main() -> int:
    return PHASE.main(__doc__, extra=lambda sub: sub.add_parser("results")
                      .set_defaults(func=cmd_results))


if __name__ == "__main__":
    raise SystemExit(main())
