"""Shared reading and rendering of recorded VLMnav runs.

The TUI (eval/replay_tui.py) is one consumer; analysis scripts and notebooks
are the other. Anything that would otherwise be re-derived from the JSONL twice
belongs here.

    import sys; sys.path.insert(0, "eval")
    from runlib import list_runs, decisions_frame
    frame = decisions_frame(list_runs())
    frame.groupby("rung")["latency_ms"].describe()
"""
from .model import Decision, Run, Step, list_runs, load_run, read_json, read_jsonl
from .stats import (decisions_frame, pose_drift, rung_counts, steps_frame,
                    summary_frame)

__all__ = [
    "Decision", "Run", "Step",
    "list_runs", "load_run", "read_json", "read_jsonl",
    "decisions_frame", "steps_frame", "summary_frame", "rung_counts", "pose_drift",
]
