"""Per-step output schema.

`action` is an enum of exactly the indices drawn on this step's frame, so the
model cannot name an action the image never offered. That is the same invariant
`VLMNavController.execute_index()` enforces on the Godot side; stating it in the
schema means an invalid pick is impossible rather than merely rejected.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

SCHEMA_NAME = "vlmnav_action"

#: Where the goal is in the current frame, for an agent whose reply reports it
#: (agent.py: memory fields include "goal"). Relative to the drone's heading.
GOAL_REPORTS = ["ahead", "left", "right", "not_visible"]

#: Cap on the describe-first `reason` of the perceiver, wall reader and distance
#: reader, applied only when the agent's `reason_cap` feature asks for it (a62 on;
#: a49 flew with an open reason and keeps it). About 2% of these calls ran the
#: reason past the token budget, twice (768 then 1536 tokens), and failed every
#: rung with an unterminated string (W01 2.6%, LD 2.0%; the same image fails
#: every time, and the capped text is one sentence repeated: a loop, not a long
#: thought, so a larger budget would not help). The server's grammar closes the
#: string at this length, so the report fields that follow always arrive. A
#: normal reason is 850 characters, the 95th percentile 2,400. The navigator,
#: strategist and confirmers keep an open reason.
REASON_MAX_CHARS = 2000


def visible_indices(manifest: Dict[str, Any]) -> List[int]:
    """The indices on this frame, straight from the manifest.

    The manifest is filtered by the same projection test that decides what gets
    drawn, so image, panel and schema can never disagree.
    """
    return [int(a["index"]) for a in manifest.get("actions", [])]


def action_schema(indices: List[int], goal: bool = False,
                  goal_after_reason: bool = False) -> Dict[str, Any]:
    """`goal` adds a report of where the goal is, emitted first, so the model
    states what the current frame shows before it argues from anything else.

    `goal_after_reason` moves that report between `reason` and `action` (a04):
    answered first, it stopped the model seeing the goal (R3 summary)."""
    properties: Dict[str, Any] = {}
    if goal and not goal_after_reason:
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
    if goal and goal_after_reason:
        properties["goal"] = {
            "type": "string",
            "enum": GOAL_REPORTS,
            "description": ("Where the goal (the glowing red sphere) is in this image "
                            "now, as described in your reason."),
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


def response_format(indices: List[int], goal: bool = False,
                    goal_after_reason: bool = False) -> Dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": SCHEMA_NAME,
            "strict": True,
            "schema": action_schema(indices, goal, goal_after_reason),
        },
    }


def tool_spec(indices: List[int], goal: bool = False,
              goal_after_reason: bool = False) -> Dict[str, Any]:
    """Fallback rung 3: the same contract expressed as a single tool."""
    return {
        "type": "function",
        "function": {
            "name": "choose_action",
            "description": "Take one of the numbered actions drawn on the frame.",
            "parameters": action_schema(indices, goal, goal_after_reason),
        },
    }


#: The goal identifier's reply (agent.py: feature `goal_identifier`, a05 on).
IDENTIFIER_SCHEMA_NAME = "goal_identifier"


def identifier_schema() -> Dict[str, Any]:
    """What the goal identifier answers: a description, then where the goal is.

    Reason first, the order that saw the goal in R4 (a04: 107/107 in the probe);
    goal first stopped the model seeing it (R3 summary)."""
    return {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "What you see in this image that could be the goal.",
            },
            "goal": {
                "type": "string",
                "enum": GOAL_REPORTS,
                "description": ("Where the goal (the glowing red sphere) is in this image, "
                                "as described in your reason."),
            },
        },
        "required": ["reason", "goal"],
        "additionalProperties": False,
    }


def identifier_response_format() -> Dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": IDENTIFIER_SCHEMA_NAME,
            "strict": True,
            "schema": identifier_schema(),
        },
    }


def identifier_tool_spec() -> Dict[str, Any]:
    """Fallback rung 3 for the identifier: the same contract as a single tool."""
    return {
        "type": "function",
        "function": {
            "name": "report_goal",
            "description": "Report whether the goal is in this image, and where.",
            "parameters": identifier_schema(),
        },
    }


# --- R9: the orchestrated agent (a13) -------------------------------------------
# One schema per subagent. Every one puts `reason` first, the order that saw
# the goal in R4. Fixed properties rather than arrays: strict decoding handles
# them on every rung.

#: The perceiver's five image strips, left to right (spatial.STRIPS).
STRIPS = ["far_left", "left", "centre", "right", "far_right"]
GOAL_RANGES = ["touching", "near", "mid", "far", "none"]
FLOOR_CLASSES = ["open_far", "open_near", "blocked_near"]
MODES = ["approach", "explore", "backtrack", "escape"]

PERCEIVER_SCHEMA_NAME = "perceiver"
CONFIRMER_SCHEMA_NAME = "confirmer"
STRATEGIST_SCHEMA_NAME = "strategist"


#: g04 (a17): the far floor split by whether a wall ends it, and a doorway said
#: open or closed.
FLOOR_CLASSES_G04 = ["open_very_far", "wall_far", "open_near", "blocked_near"]
DOORWAYS_G04 = ["open", "closed", "none"]

#: g05 (a18): where the strip's floor ends in the image, lowest first; the
#: agent's floor_map turns it into a floor class. Doorways as g04.
FLOOR_ENDS_G05 = ["no_floor", "bottom", "lower", "middle"]

#: g06 (a24): g05's floor ends with no_floor renamed for what it means and
#: runs_on for floor whose end is not in sight. Doorways as g04.
FLOOR_ENDS_G06 = ["wall_at_bottom", "bottom", "lower", "middle", "runs_on"]


def floor_classes(version: str = "g03") -> List[str]:
    if version in ("g05", "g07"):
        return FLOOR_ENDS_G05
    if version == "g06":
        return FLOOR_ENDS_G06
    return FLOOR_CLASSES_G04 if version == "g04" else FLOOR_CLASSES


def perceiver_schema(version: str = "g03",
                     reason_cap: Optional[int] = None) -> Dict[str, Any]:
    """The perceiver's reply. `reason_cap` (the agent's `reason_cap` feature) puts
    a maxLength on the reason; None leaves it open, as every agent up to a61."""
    if version == "g06":
        lane_props: Dict[str, Any] = {
            "floor": {"type": "string", "enum": FLOOR_ENDS_G06,
                      "description": "Where this strip's floor ends in the image: a wall at "
                                     "its bottom edge, the bottom quarter, lower, just below "
                                     "the middle, or runs on out of sight."},
            "doorway": {"type": "string", "enum": DOORWAYS_G04,
                        "description": "An opening in a wall in this strip: open, closed by "
                                       "a door, or none."},
        }
    elif version in ("g05", "g07"):
        lane_props = {
            "floor": {"type": "string", "enum": FLOOR_ENDS_G05,
                      "description": "Where this strip's floor ends in the image: no floor "
                                     "at its bottom, the bottom quarter, lower, or just "
                                     "below the middle."},
            "doorway": {"type": "string", "enum": DOORWAYS_G04,
                        "description": "An opening in a wall in this strip: open, closed by "
                                       "a door, or none."},
        }
    elif version == "g04":
        lane_props = {
            "floor": {"type": "string", "enum": FLOOR_CLASSES_G04,
                      "description": "Where the open floor straight ahead in this strip ends."},
            "doorway": {"type": "string", "enum": DOORWAYS_G04,
                        "description": "An opening in a wall in this strip: open, closed by "
                                       "a door, or none."},
        }
    else:
        lane_props = {
            "floor": {"type": "string", "enum": FLOOR_CLASSES,
                      "description": "How far open floor runs straight ahead in this strip."},
            "doorway": {"type": "boolean",
                        "description": "Whether this strip shows an opening in a wall."},
        }
    lane = {
        "type": "object",
        "properties": lane_props,
        "required": ["floor", "doorway"],
        "additionalProperties": False,
    }
    properties: Dict[str, Any] = {
        "reason": {"type": "string",
                   "description": "Walls, openings, obstacles and anything that could be "
                                  "the goal in this image."},
        "goal": {"type": "string", "enum": STRIPS + ["not_visible"],
                 "description": "The strip the glowing red sphere is in."},
        "goal_range": {"type": "string", "enum": GOAL_RANGES,
                       "description": "How far away the goal looks; none if not visible."},
    }
    if version == "g07":  # g05 without the reason written first (probe F1)
        del properties["reason"]
    elif reason_cap:
        properties["reason"]["maxLength"] = reason_cap
    for strip in STRIPS:
        properties[strip] = dict(lane, description="The {0} strip.".format(strip))
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


WALL_READER_SCHEMA_NAME = "wall_reader"


def wall_reader_schema(reason_cap: Optional[int] = None) -> Dict[str, Any]:
    """w01 (a61 on): g05's floor per strip and nothing else, after a description.
    `reason_cap` as perceiver_schema."""
    properties: Dict[str, Any] = {
        "reason": {"type": "string",
                   "description": "What fills the bottom of each strip and where its floor "
                                  "ends; walls, openings and doors."},
    }
    if reason_cap:
        properties["reason"]["maxLength"] = reason_cap
    for strip in STRIPS:
        properties[strip] = {
            "type": "object",
            "properties": {"floor": {"type": "string", "enum": FLOOR_ENDS_G05,
                                     "description": "Where this strip's floor ends in the "
                                                    "image: no floor at its bottom, the "
                                                    "bottom quarter, lower, or just below "
                                                    "the middle."}},
            "required": ["floor"],
            "additionalProperties": False,
            "description": "The {0} strip.".format(strip),
        }
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


DISTANCE_READER_SCHEMA_NAME = "distance_reader"


def distance_reader_schema(reason_cap: Optional[int] = None) -> Dict[str, Any]:
    """ld01 (probe LD, never flown): metres to the nearest obstacle per strip,
    after a description. Range checks live in the probe, not the schema.
    `reason_cap` as perceiver_schema."""
    properties: Dict[str, Any] = {
        "reason": {"type": "string",
                   "description": "What fills the bottom of each strip and the cues that "
                                  "give its distance."},
    }
    if reason_cap:
        properties["reason"]["maxLength"] = reason_cap
    for strip in STRIPS:
        properties[strip] = {
            "type": "object",
            "properties": {"metres": {"type": "number",
                                      "description": "Metres from the camera to the nearest "
                                                     "wall, door, pillar or object at the "
                                                     "middle of this strip; 15 if nothing "
                                                     "within 15 m."}},
            "required": ["metres"],
            "additionalProperties": False,
            "description": "The {0} strip.".format(strip),
        }
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


WALL_CONFIRMER_SCHEMA_NAME = "wall_confirmer"


def wall_confirmer_schema(strips: List[str]) -> Dict[str, Any]:
    """k01 (R28): for each strip read open, wall or floor at its bottom edge,
    after a description."""
    properties: Dict[str, Any] = {
        "reason": {"type": "string",
                   "description": "What covers the bottom edge of each reported strip."}}
    for strip in strips:
        properties[strip] = {"type": "string", "enum": ["wall", "floor"]}
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def confirmer_schema() -> Dict[str, Any]:
    """c01 (a27 on): is the reported goal there, after a description."""
    properties = {
        "reason": {"type": "string",
                   "description": "What is in the reported strip and the strips next to it."},
        "present": {"type": "string", "enum": ["yes", "no"],
                    "description": "Whether a glowing red sphere is there."},
    }
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


DOOR_CONFIRMER_SCHEMA_NAME = "door_confirmer"


def door_confirmer_schema(strips: List[str]) -> Dict[str, Any]:
    """d01 (a37 on): for each strip reported to hold an open doorway, open,
    closed or none, after a description."""
    properties: Dict[str, Any] = {
        "reason": {"type": "string",
                   "description": "What is in each reported strip: walls, gaps, doors, floor beyond."}}
    for strip in strips:
        properties[strip] = {"type": "string", "enum": ["open", "closed", "none"]}
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def strategist_schema(target_ids: List[str]) -> Dict[str, Any]:
    properties = {
        "reason": {"type": "string",
                   "description": "What is known and why this target is the best way on."},
        "mode": {"type": "string", "enum": MODES},
        "target": {"type": "string", "enum": target_ids,
                   "description": "One target id exactly as listed."},
    }
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}
