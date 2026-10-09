"""The prompt, versioned.

Every run records its prompt version and prompt_sha(), so a number in the paper
can name the exact wording that produced it. Change the text, bump the version:
add a new entry to PROMPTS and never edit an old one, since that would change its
sha and silently break comparability with every run already recorded.

Which prompt a run uses is chosen by the agent (agent.py), not here.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass(frozen=True)
class Prompt:
    version: str
    system: str
    user_template: str
    #: manifest -> user text. Most versions share render_goal_and_actions; a
    #: version that shows the model something new brings its own. A version
    #: whose agent has memory also takes the run's earlier decisions.
    render: Callable[..., str]

    def sha(self) -> str:
        """Identity of the wording, independent of the version label."""
        blob = (self.system + "\x00" + self.user_template).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:12]


def render_goal_and_actions(prompt: Prompt, manifest: Dict[str, Any]) -> str:
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

    return prompt.user_template.format(
        step=manifest.get("step", 0),
        goal_line=goal_line,
        action_lines="\n".join(lines) if lines else "  (none)",
    )


# --- p02: Phase 1 (docs/phase1-test-plan.md §3), sha 26260774b60e ---------

P02 = Prompt(
    version="p02",
    system="""You are flying a small indoor drone. You see one image per step.

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

Give your reasoning first, then the number.""",
    user_template="""Step {step}.

{goal_line}

Available actions this step:
{action_lines}

Pick one number.""",
    render=render_goal_and_actions,
)

def render_actions_only(prompt: Prompt, manifest: Dict[str, Any]) -> str:
    """The step and the marker numbers, nothing else: no goal distance or
    bearing, and no turn angle or flight distance per action."""
    lines: List[str] = []
    for action in manifest.get("actions", []):
        if action.get("turn_around"):
            lines.append("  [{i}] turn around in place".format(i=action["index"]))
        else:
            lines.append("  [{i}]".format(i=action["index"]))

    return prompt.user_template.format(
        step=manifest.get("step", 0),
        action_lines="\n".join(lines) if lines else "  (none)",
    )


# --- p03: Phase 2 R1, no goal hint (eval/phase2/R1_no_goal_hint/README.md) --
#
# p02 minus every number about where things are: the goal's distance and
# bearing, and each action's turn angle and flight distance. The goal has to be
# found in the image.

P03 = Prompt(
    version="p03",
    system="""You are flying a small indoor drone. You see one image per step.

Numbered markers are drawn on the image. Each marker is an action you may take:
the drone turns to face that marker, then flies a short distance forward.
Marker 0, when offered, turns the drone around in place without moving.

Rules of this interface:
- You may only pick a number that is listed as available for this step.
- Nothing checks your choice before it is executed. There is no depth sensor and
  no obstacle filter. If you pick a heading that runs into a wall, the drone
  hits the wall and that counts against the run.
- You cannot strafe, climb, or descend. Altitude is held for you.
- You cannot open doors or manipulate anything around you. A closed door is a
  wall. Find a route through openings that are already clear.
- Judge distance and clearance from the image alone.

Your objective is to reach the goal: a glowing red sphere with a tall red beam
of light rising above it. You are not told where it is. The image is the only
information you get. If the goal is in view, fly toward it along a clear path.
If it is not, explore through open space and openings until you find it. Avoid
collisions, and prefer headings with visible open floor ahead of them.

Give your reasoning first, then the number.""",
    user_template="""Step {step}.

Available actions this step:
{action_lines}

Pick one number.""",
    render=render_actions_only,
)

def render_actions_with_memory(prompt: Prompt, manifest: Dict[str, Any],
                               memory: List[Dict[str, Any]]) -> str:
    """p03's step and marker numbers, after the agent's own earlier steps.

    `memory` is every earlier decision of this run, oldest first, as
    recorder.Run.memory() reads it from decisions.jsonl: the step, the marker
    picked, whether it was the turn-around, and the reason verbatim.
    """
    if memory:
        lines = ["Your earlier steps in this run, oldest first:"]
        for entry in memory:
            if entry.get("turn_around"):
                picked = "you turned around [0]"
            else:
                picked = "you picked [{0}]".format(entry["index"])
            reason = " ".join(str(entry.get("reason", "")).split())
            lines.append("Step {0}: {1}. Your reasoning: {2}".format(
                entry["step"], picked, reason or "(none given)"))
        memory_block = "\n".join(lines)
    else:
        memory_block = "Your earlier steps in this run: none yet, this is the first step."

    actions: List[str] = []
    for action in manifest.get("actions", []):
        if action.get("turn_around"):
            actions.append("  [{i}] turn around in place".format(i=action["index"]))
        else:
            actions.append("  [{i}]".format(i=action["index"]))

    return prompt.user_template.format(
        step=manifest.get("step", 0),
        memory_block=memory_block,
        action_lines="\n".join(actions) if actions else "  (none)",
    )


# --- p04: Phase 2 R2, text memory of the whole run --------------------------
# (eval/phase2/R2_text_memory/README.md)
#
# p03 plus the agent's own earlier steps in this run: the marker it picked and
# the reasoning it gave, every step, oldest first. Still no numbers about where
# anything is; the record holds only what the model itself wrote.

P04 = Prompt(
    version="p04",
    system="""You are flying a small indoor drone. You see one image per step.

Numbered markers are drawn on the image. Each marker is an action you may take:
the drone turns to face that marker, then flies a short distance forward.
Marker 0, when offered, turns the drone around in place without moving.

Rules of this interface:
- You may only pick a number that is listed as available for this step.
- Nothing checks your choice before it is executed. There is no depth sensor and
  no obstacle filter. If you pick a heading that runs into a wall, the drone
  hits the wall and that counts against the run.
- You cannot strafe, climb, or descend. Altitude is held for you.
- You cannot open doors or manipulate anything around you. A closed door is a
  wall. Find a route through openings that are already clear.
- Judge distance and clearance from the image alone.

Your objective is to reach the goal: a glowing red sphere with a tall red beam
of light rising above it. You are not told where it is. The image is the only
information you get. If the goal is in view, fly toward it along a clear path.
If it is not, explore through open space and openings until you find it. Avoid
collisions, and prefer headings with visible open floor ahead of them.

Each step also lists your own earlier steps in this run, oldest first: the
marker you picked and the reasoning you gave. Marker numbers refer to the view
at that step, so read the reasoning to know where you went. Use this record to
avoid going back over ground you have already covered, and to remember where
you last saw the goal.

Give your reasoning first, then the number.""",
    user_template="""Step {step}.

{memory_block}

Available actions this step:
{action_lines}

Pick one number.""",
    render=render_actions_with_memory,
)

PROMPTS: Dict[str, Prompt] = {p.version: p for p in (P02, P03, P04)}


def get(version: str) -> Prompt:
    if version not in PROMPTS:
        raise KeyError("unknown prompt version {0!r}; known: {1}".format(
            version, ", ".join(PROMPTS)))
    return PROMPTS[version]


# Phase 1 names, kept so older scripts and notebooks still import. They always
# mean p02; live code asks the agent which prompt it uses.
PROMPT_VERSION = P02.version
SYSTEM_PROMPT = P02.system
_USER_TEMPLATE = P02.user_template


def render_user_prompt(manifest: Dict[str, Any]) -> str:
    return P02.render(P02, manifest)


def prompt_sha() -> str:
    return P02.sha()
