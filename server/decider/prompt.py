"""The prompt, versioned.

Every run records PROMPT_VERSION and prompt_sha(), so a number in the paper can
name the exact wording that produced it. Change the text, bump the version.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List

PROMPT_VERSION = "p02"

SYSTEM_PROMPT = """You are flying a small indoor drone. You see one image per step.

Numbered markers are drawn on the image. Each marker is an action you may take:
the drone turns to face that marker's heading, then flies forward a fixed
distance. Marker 0, when offered, turns the drone around 180 degrees in place
without moving.

Rules of this interface:
- You may only pick a number that is listed as available for this step.
- Nothing checks your choice before it is executed. There is no depth sensor and
  no obstacle filter. If you pick a heading that runs into a wall, the drone
  hits the wall and that counts against the run.
- You cannot strafe, climb, or descend. Altitude is held for you.
- You cannot open doors or manipulate anything around you. A closed door is a
  wall. Find a route through openings that are already clear.
- Judge distance and clearance from the image alone.

Your objective is stated each step as a distance and a bearing to the goal. A
positive bearing is to your left, negative to your right. Close that distance
without collisions, and prefer headings with visible open floor ahead of them.

Give your reasoning first, then the number."""

_USER_TEMPLATE = """Step {step}.

{goal_line}

Available actions this step:
{action_lines}

Pick one number."""


def render_user_prompt(manifest: Dict[str, Any]) -> str:
    goal = manifest.get("goal")
    if goal:
        goal_line = (
            "Goal: {dist:.1f} m away, bearing {bearing:+.0f} degrees "
            "({side}). Arrival radius {radius:.1f} m.".format(
                dist=float(goal["distance"]),
                bearing=float(goal["bearing_deg"]),
                side="left" if float(goal["bearing_deg"]) > 0 else "right",
                radius=float(goal.get("arrival_radius", 0.0)),
            )
        )
        if goal.get("reached"):
            goal_line += " You are inside the arrival radius."
    else:
        goal_line = "No goal is set. Explore without colliding."

    lines: List[str] = []
    for action in manifest.get("actions", []):
        if action.get("turn_around"):
            lines.append("  [{i}] turn around 180 degrees, do not move".format(i=action["index"]))
        else:
            lines.append(
                "  [{i}] turn {theta:+.0f} degrees, then fly {r:.1f} m forward".format(
                    i=action["index"], theta=float(action["theta_deg"]), r=float(action["r"])
                )
            )

    return _USER_TEMPLATE.format(
        step=manifest.get("step", 0),
        goal_line=goal_line,
        action_lines="\n".join(lines) if lines else "  (none)",
    )


def prompt_sha() -> str:
    """Identity of the prompt wording, independent of the version label."""
    blob = (SYSTEM_PROMPT + "\x00" + _USER_TEMPLATE).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]
