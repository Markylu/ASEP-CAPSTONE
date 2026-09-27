"""Per-step output schema.

`action` is an enum of exactly the indices drawn on this step's frame, so the
model cannot name an action the image never offered. That is the same invariant
`VLMNavController.execute_index()` enforces on the Godot side; stating it in the
schema means an invalid pick is impossible rather than merely rejected.
"""
from __future__ import annotations

from typing import Any, Dict, List

SCHEMA_NAME = "vlmnav_action"


def visible_indices(manifest: Dict[str, Any]) -> List[int]:
    """The indices on this frame, straight from the manifest.

    The manifest is filtered by the same projection test that decides what gets
    drawn, so image, panel and schema can never disagree.
    """
    return [int(a["index"]) for a in manifest.get("actions", [])]


def action_schema(indices: List[int]) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            # `reason` first on purpose: with a strict schema the model emits
            # properties in declared order, so it argues before it commits.
            "reason": {
                "type": "string",
                "description": "What you see and why this heading is the best of those offered.",
            },
            "action": {
                "type": "integer",
                "enum": indices,
                "description": "The number of the action you are taking.",
            },
        },
        "required": ["reason", "action"],
        "additionalProperties": False,
    }


def response_format(indices: List[int]) -> Dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": SCHEMA_NAME,
            "strict": True,
            "schema": action_schema(indices),
        },
    }


def tool_spec(indices: List[int]) -> Dict[str, Any]:
    """Fallback rung 3: the same contract expressed as a single tool."""
    return {
        "type": "function",
        "function": {
            "name": "choose_action",
            "description": "Take one of the numbered actions drawn on the frame.",
            "parameters": action_schema(indices),
        },
    }
