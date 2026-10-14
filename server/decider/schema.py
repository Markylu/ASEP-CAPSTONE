"""Per-step output schema.

`action` is an enum of exactly the indices drawn on this step's frame, so the
model cannot name an action the image never offered. That is the same invariant
`VLMNavController.execute_index()` enforces on the Godot side; stating it in the
schema means an invalid pick is impossible rather than merely rejected.
"""
from __future__ import annotations

from typing import Any, Dict, List

SCHEMA_NAME = "vlmnav_action"

#: Where the goal is in the current frame, for an agent whose reply reports it
#: (agent.py: memory fields include "goal"). Relative to the drone's heading.
GOAL_REPORTS = ["ahead", "left", "right", "not_visible"]


def visible_indices(manifest: Dict[str, Any]) -> List[int]:
    """The indices on this frame, straight from the manifest.

    The manifest is filtered by the same projection test that decides what gets
    drawn, so image, panel and schema can never disagree.
    """
    return [int(a["index"]) for a in manifest.get("actions", [])]


def action_schema(indices: List[int], goal: bool = False) -> Dict[str, Any]:
    """`goal` adds a report of where the goal is, emitted first, so the model
    states what the current frame shows before it argues from anything else."""
    properties: Dict[str, Any] = {}
    if goal:
        properties["goal"] = {
            "type": "string",
            "enum": GOAL_REPORTS,
            "description": "Where the goal (red sphere, red beam) is in this image now.",
        }
    # `reason` before `action` on purpose: with a strict schema the model emits
    # properties in declared order, so it argues before it commits.
    properties["reason"] = {
        "type": "string",
        "description": "What you see and why this heading is the best of those offered.",
    }
    properties["action"] = {
        "type": "integer",
        "enum": indices,
        "description": "The number of the action you are taking.",
    }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def response_format(indices: List[int], goal: bool = False) -> Dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": SCHEMA_NAME,
            "strict": True,
            "schema": action_schema(indices, goal),
        },
    }


def tool_spec(indices: List[int], goal: bool = False) -> Dict[str, Any]:
    """Fallback rung 3: the same contract expressed as a single tool."""
    return {
        "type": "function",
        "function": {
            "name": "choose_action",
            "description": "Take one of the numbered actions drawn on the frame.",
            "parameters": action_schema(indices, goal),
        },
    }
