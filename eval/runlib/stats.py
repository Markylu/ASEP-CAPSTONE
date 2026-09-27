"""Flatten runs into dataframes, so comparison is a query and not new UI code.

The TUI only ever shows one run, but every question worth asking later — how
latency moves with rung, whether the fallback ladder correlates with collisions,
how two runs' trajectories diverge — is a groupby over these two frames. They
exist now so that adding those answers does not mean re-reading JSONL.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from .model import Run


def decisions_frame(runs: Iterable[Run]) -> pd.DataFrame:
    """One row per model call, keyed (run_id, step). Steps count from 0 here."""
    rows = []  # type: List[Dict[str, Any]]
    for run in runs:
        for decision in run.decisions:
            rows.append({
                "run_id": run.run_id,
                "step": decision.step,
                "index": decision.index,
                "failed": decision.failed,
                "rung": decision.rung,
                "latency_ms": decision.latency_ms,
                "prompt_tokens": decision.prompt_tokens,
                "completion_tokens": decision.completion_tokens,
                "n_attempts": len(decision.attempts),
                "reason_chars": len(decision.reason),
                # From the manifest, so these survive a run cloned from git
                # where steps.jsonl is absent.
                "seen_goal_distance": decision.goal.get("distance"),
                "seen_goal_bearing_deg": decision.goal.get("bearing_deg"),
                "model": run.model,
                "prompt_version": run.meta.get("prompt_version"),
                "git_sha": run.meta.get("git_sha"),
            })
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.set_index(["run_id", "step"]).sort_index()
    return frame


def steps_frame(runs: Iterable[Run]) -> pd.DataFrame:
    """One row per executed step, keyed (run_id, step). Steps count from 1 here.

    `path_m` is cumulative distance flown, which is the honest denominator for
    efficiency: a run that reaches the goal by circling is not a good run.
    """
    rows = []  # type: List[Dict[str, Any]]
    for run in runs:
        previous = None
        travelled = 0.0
        for step in run.steps:
            if previous is not None and len(step.position) == len(previous) == 3:
                travelled += math.sqrt(sum(
                    (a - b) ** 2 for a, b in zip(step.position, previous)))
            previous = step.position
            rows.append({
                "run_id": run.run_id,
                "step": step.step,
                "t": step.t,
                "x": step.position[0] if len(step.position) > 0 else None,
                "y": step.position[1] if len(step.position) > 1 else None,
                "z": step.position[2] if len(step.position) > 2 else None,
                "yaw": step.yaw,
                "action_index": step.action.get("index"),
                "action_theta_deg": step.action.get("theta_deg"),
                "collided": step.collided,
                "goal_distance": step.goal.get("distance"),
                "goal_bearing_deg": step.goal.get("bearing_deg"),
                "goal_reached": step.goal.get("reached"),
                "path_m": travelled,
            })
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.set_index(["run_id", "step"]).sort_index()
    return frame


def summary_frame(runs: Iterable[Run]) -> pd.DataFrame:
    """One row per run — the table a results section actually quotes."""
    rows = []
    for run in runs:
        latency = run.metrics.get("latency_ms") or {}
        tokens = run.metrics.get("tokens_total") or {}
        rows.append({
            "run_id": run.run_id,
            "started": run.started,
            "model": run.model,
            "prompt_version": run.meta.get("prompt_version"),
            "steps": run.n_steps,
            "collisions": run.collisions,
            "goal_reached": run.goal_reached,
            "end_reason": run.end_reason,
            "final_goal_distance_m": run.metrics.get("final_goal_distance_m"),
            "latency_p50": latency.get("p50"),
            "latency_p95": latency.get("p95"),
            "latency_mean": latency.get("mean"),
            "prompt_tokens": tokens.get("prompt"),
            "completion_tokens": tokens.get("completion"),
            "replayable": run.replayable,
            "git_sha": run.meta.get("git_sha"),
            "git_dirty": run.meta.get("git_dirty"),
        })
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.set_index("run_id")
    return frame


def rung_counts(run: Run) -> Dict[str, int]:
    """Prefer the recorded metric; derive it when metrics.json is absent."""
    recorded = run.metrics.get("rungs_used")
    if recorded:
        return {str(k): int(v) for k, v in recorded.items()}
    counts = {}  # type: Dict[str, int]
    for decision in run.decisions:
        key = decision.rung or "?"
        counts[key] = counts.get(key, 0) + 1
    return counts


def pose_drift(a: Run, b: Run) -> pd.DataFrame:
    """Per-step divergence between two runs' trajectories.

    Deliberately not used by the verify action — that shells out to
    eval/replay.py so the repo keeps exactly one authoritative drift check.
    This is for comparing two *different* runs, which replay.py cannot do.
    """
    rows = []
    for step_a, step_b in zip(a.steps, b.steps):
        pos_drift = max((abs(x - y) for x, y in
                         zip(step_a.position, step_b.position)), default=float("nan"))
        rows.append({
            "step": step_a.step,
            "pos_drift_m": pos_drift,
            "yaw_drift_rad": abs(step_a.yaw - step_b.yaw),
            "action_a": step_a.action.get("index"),
            "action_b": step_b.action.get("index"),
            "collided_a": step_a.collided,
            "collided_b": step_b.collided,
        })
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.set_index("step")
    return frame
