"""The prompt, versioned.

Every run records its prompt version and prompt_sha(), so a number in the paper
can name the exact wording that produced it. Change the text, bump the version:
add a new entry to PROMPTS and never edit an old one, since that would change its
sha and silently break comparability with every run already recorded.

Which prompt a run uses is chosen by the agent (agent.py), not here.
"""
from __future__ import annotations

import hashlib
import math
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

def _move(entry: Dict[str, Any]) -> str:
    """What the drone did at a step, from the chosen action's heading.

    Nearest of the fan's headings (0, about 22 and about 44 degrees either
    side; positive is left), so it states the command executed, which no
    reasoning can misreport.
    """
    if entry.get("turn_around"):
        return "turned around"
    theta = entry.get("theta_deg")
    if theta is None:
        return "flew (heading not recorded)"
    theta = float(theta)
    if abs(theta) < 11.0:
        return "flew straight"
    side = "left" if theta > 0 else "right"
    return "flew {0} {1}".format("slight" if abs(theta) < 33.0 else "sharp", side)


GOAL_WORDS = {"ahead": "ahead", "left": "to the left", "right": "to the right",
              "not_visible": "not visible"}


def render_memory_log(prompt: Prompt, manifest: Dict[str, Any],
                      memory: List[Dict[str, Any]]) -> str:
    """p03's step and marker numbers, after a log the system writes.

    One line per earlier step of this run, oldest first: the move the drone
    made and where the model said the goal was. No marker numbers (they mean
    something else in every view) and no reasons (R2: copied forward as a plan).
    """
    if memory:
        lines = ["Log of your earlier steps (what happened, not a plan):"]
        for entry in memory:
            lines.append("Step {0}: {1}. Goal: {2}.".format(
                entry["step"], _move(entry),
                GOAL_WORDS.get(entry.get("goal") or "", "not reported")))
        memory_block = "\n".join(lines)
    else:
        memory_block = "Log of your earlier steps: none yet, this is the first step."

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


# --- p05: Phase 2 R3, a memory log written by code ---------------------------
# (eval/phase2/R3_memory_log/README.md)
#
# p03 plus a log of every earlier step: the move made and the goal report the
# reply gave (the reply now reports the goal first, schema.GOAL_REPORTS). One
# paragraph says what the log is and that the current image outranks it.

P05 = Prompt(
    version="p05",
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

Each step also shows a log of your earlier steps in this run, kept by the
system. It records the move the drone made at each step and where you said the
goal was. It is a record of what happened, not a plan. Directions in the log
are relative to the way the drone faced at that step. The current image is your
only view of the world now: if it disagrees with the log, trust the image.
Repeat a move only while the image shows it is still working. Turning around is
a normal move when the way ahead is blocked. Use the log to remember where you
last saw the goal and to avoid flying back over ground you have already covered.

First say where the goal is in this image, then give your reasoning, then the
number.""",
    user_template="""Step {step}.

{memory_block}

Available actions this step:
{action_lines}

Pick one number.""",
    render=render_memory_log,
)

# --- p06: Phase 2 R4, the goal reported after the reason -----------------------
# (eval/phase2/R4_goal_after_reason/README.md)
#
# p05 with two edits. The goal is "a glowing red sphere": the beam is gone,
# since close up it leaves the frame and R3 ruled out spheres for lacking one.
# The last line asks for the reasoning before the goal report: R3's "First say
# where the goal is" stopped the model seeing the goal (R3 summary).

P06 = Prompt(
    version="p06",
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

Your objective is to reach the goal: a glowing red sphere. You are not told
where it is. The image is the only information you get. If the goal is in view,
fly toward it along a clear path. If it is not, explore through open space and
openings until you find it. Avoid collisions, and prefer headings with visible
open floor ahead of them.

Each step also shows a log of your earlier steps in this run, kept by the
system. It records the move the drone made at each step and where you said the
goal was. It is a record of what happened, not a plan. Directions in the log
are relative to the way the drone faced at that step. The current image is your
only view of the world now: if it disagrees with the log, trust the image.
Repeat a move only while the image shows it is still working. Turning around is
a normal move when the way ahead is blocked. Use the log to remember where you
last saw the goal and to avoid flying back over ground you have already covered.

Give your reasoning first, then say where the goal is, then the number.""",
    user_template=P05.user_template,
    render=render_memory_log,
)

def render_identifier_question(prompt: Prompt, manifest: Dict[str, Any]) -> str:
    """The identifier's question. It gets the frame and nothing else: no log,
    no step number, no actions."""
    return prompt.user_template


# --- g01: Phase 2 R5, the goal identifier --------------------------------------
# (eval/phase2/R5_goal_identifier/README.md)
#
# A second call per step with one job: is the goal in this image, and where.
# It never sees the log, so a stale sighting cannot reach it (R4 summary: 342
# phantom reports, 272 of them argued from the log). Its reply is reason, then
# goal (schema.identifier_schema), the order that saw the goal in R4.

G01 = Prompt(
    version="g01",
    system="""You check one image from the front camera of a small indoor drone.

Your only job is to say whether the goal is in this image, and where. The goal
is a glowing red sphere. Numbered markers are drawn on the image; they are not
the goal. Judge this image alone.

First describe what you see that could be the goal. Then report where the goal
is: "ahead" if it is near the vertical centre line of the image, "left" or
"right" if it is clearly to that side, "not_visible" if it is not in the image.""",
    user_template="Is the goal in this image?",
    render=render_identifier_question,
)


# --- g02: Phase 2 R5, the goal identifier on the unmarked frame ----------------
# (eval/phase2/R5_goal_identifier/README.md)
#
# g01 minus the sentence about markers: the identifier now gets the camera image
# with nothing drawn on it (agent a06, `goal_identifier.frame: clean`). g01 took
# the pink "0 TURN AROUND" marker for the sphere (R5 probe).

G02 = Prompt(
    version="g02",
    system="""You check one image from the front camera of a small indoor drone.

Your only job is to say whether the goal is in this image, and where. The goal
is a glowing red sphere. Judge this image alone.

First describe what you see that could be the goal. Then report where the goal
is: "ahead" if it is near the vertical centre line of the image, "left" or
"right" if it is clearly to that side, "not_visible" if it is not in the image.""",
    user_template="Is the goal in this image?",
    render=render_identifier_question,
)


IDENTIFIER_WORDS = {"ahead": "ahead", "left": "to the left", "right": "to the right",
                    "not_visible": "not visible"}


def _turn(entry: Dict[str, Any]) -> float:
    """Degrees the drone turned at a step, positive left; turn-around is 180."""
    if entry.get("turn_around"):
        return 180.0
    theta = entry.get("theta_deg")
    return float(theta) if theta is not None else 0.0


def _net_turn(turns: List[float]) -> str:
    """Sum of executed turns, wrapped to (-180, 180] and rounded to 10 degrees."""
    total = sum(turns) % 360.0
    if total > 180.0:
        total -= 360.0
    total = 10.0 * round(total / 10.0)
    if total == 0.0:
        return "net turn 0 degrees"
    if abs(total) == 180.0:
        return "net turn 180 degrees (now facing the opposite way)"
    return "net turn {0:.0f} degrees {1}".format(abs(total), "left" if total > 0 else "right")


def render_identifier_log(prompt: Prompt, manifest: Dict[str, Any],
                          memory: List[Dict[str, Any]], sighting: Any = None) -> str:
    """p03's step and marker numbers, after a log the system writes and the goal
    identifier's answer for this image.

    The log has one line per earlier step with the move only. The goal appears
    once, as the last step the identifier reported it, with how many moves and
    how much turning have happened since. `sighting` is the identifier's report
    for the current frame (schema.GOAL_REPORTS), or None when it gave none.
    """
    if memory:
        lines = ["Log of your earlier steps (what happened, not a plan):"]
        for entry in memory:
            lines.append("Step {0}: {1}.".format(entry["step"], _move(entry)))
        last = None
        for i, entry in enumerate(memory):
            if entry.get("goal") in ("ahead", "left", "right"):
                last = i
        if last is None:
            lines.append("No goal sighting yet in this run.")
        else:
            seen = memory[last]
            since = memory[last:]  # the move made at the sighting step counts too
            lines.append(
                "Last goal sighting: step {0}, {1} (relative to the way the drone faced then). "
                "Since then: {2} {3}, {4}.".format(
                    seen["step"], IDENTIFIER_WORDS[seen["goal"]],
                    len(since), "move" if len(since) == 1 else "moves",
                    _net_turn([_turn(e) for e in since])))
        memory_block = "\n".join(lines)
    else:
        memory_block = "Log of your earlier steps: none yet, this is the first step."

    if sighting == "not_visible":
        sighting_line = "Goal identifier, this image: the goal is not visible."
    elif sighting in IDENTIFIER_WORDS:
        sighting_line = "Goal identifier, this image: the goal is {0}.".format(
            IDENTIFIER_WORDS[sighting])
    else:
        sighting_line = "Goal identifier, this image: no answer this step."

    actions: List[str] = []
    for action in manifest.get("actions", []):
        if action.get("turn_around"):
            actions.append("  [{i}] turn around in place".format(i=action["index"]))
        else:
            actions.append("  [{i}]".format(i=action["index"]))

    return prompt.user_template.format(
        step=manifest.get("step", 0),
        memory_block=memory_block,
        sighting_line=sighting_line,
        action_lines="\n".join(actions) if actions else "  (none)",
    )


# --- p07: Phase 2 R5, navigator fed by the goal identifier ---------------------
# (eval/phase2/R5_goal_identifier/README.md)
#
# p06 with the goal report taken away from the navigator. A separate call
# (g01) reports the goal for each image; the navigator is told its answer for
# this image, and the log names only the last sighting with its age and the
# turning since (R4 summary, option 2).

P07 = Prompt(
    version="p07",
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

Your objective is to reach the goal: a glowing red sphere. You are not told
where it is. If the goal is in view, fly toward it along a clear path. If it is
not, explore through open space and openings until you find it. Avoid
collisions, and prefer headings with visible open floor ahead of them.

A goal identifier looks at each image before you do. Its only job is to say
whether the goal is in that image and where. Each step gives you its answer for
the current image. It describes this image only, not where the goal was before.

Each step also shows a log of your earlier steps in this run, kept by the
system. It records the move the drone made at each step. It is a record of what
happened, not a plan. Below the moves it gives the last step at which the goal
identifier saw the goal, which way it was then, and how many moves and how much
turning there have been since. That direction is relative to the way the drone
faced at that step, not now. If the identifier says the goal is not visible
now, it is not in the current image, whatever the log says. Repeat a move only
while the image shows it is still working. Turning around is a normal move when
the way ahead is blocked. Use the log to work out where the goal is likely to be
now and to avoid flying back over ground you have already covered.

Give your reasoning first, then the number.""",
    user_template="""Step {step}.

{memory_block}

{sighting_line}

Available actions this step:
{action_lines}

Pick one number.""",
    render=render_identifier_log,
)

def _where(pose: Any) -> Any:
    """A recorded pose as the log shows it: (x, y, heading), or None.

    x is Godot's x and y is minus its z, so the floor reads as an ordinary map.
    Heading is counter-clockwise from +x in degrees, 0 to 359: the drone flies
    along (-sin yaw, -cos yaw) in Godot's (x, z), which is yaw + 90 on this map,
    and a left turn raises it, as it raises yaw."""
    if not pose or pose.get("position") is None or pose.get("yaw") is None:
        return None
    x, _, z = (float(v) for v in pose["position"])
    heading = int(round(math.degrees(float(pose["yaw"])) + 90.0)) % 360
    return x, -z, heading


def _at(where: Any) -> str:
    return "({0:.1f}, {1:.1f}), heading {2} degrees".format(*where)


def _pose_log(manifest: Dict[str, Any], memory: List[Dict[str, Any]],
              with_sighting: bool) -> str:
    """The move log with the drone's ground-truth position after every move.

    Each line gives the move, where the drone ended up and how far the move took
    it, from the pose recorded at the next step (recorder.Run.memory). The last
    move ends at the current manifest's pose. With `with_sighting`, the last
    goal sighting follows as in p07."""
    now = _where(manifest.get("pose"))
    if not memory:
        lines = ["Log of your earlier steps: none yet, this is the first step."]
    else:
        lines = ["Log of your earlier steps (what happened, not a plan):"]
        start = _where(memory[0].get("pose"))
        if start is not None:
            lines.append("Start: at {0}.".format(_at(start)))
        for entry in memory:
            before = _where(entry.get("pose"))
            after = _where(entry["pose_after"]) if entry.get("pose_after") else now
            if after is None:
                lines.append("Step {0}: {1}. Position not recorded.".format(
                    entry["step"], _move(entry)))
                continue
            moved = ("" if before is None else ", moved {0:.1f} m".format(
                math.hypot(after[0] - before[0], after[1] - before[1])))
            lines.append("Step {0}: {1}. Ended at {2}{3}.".format(
                entry["step"], _move(entry), _at(after), moved))
        if with_sighting:
            last = None
            for i, entry in enumerate(memory):
                if entry.get("goal") in ("ahead", "left", "right"):
                    last = i
            if last is None:
                lines.append("No goal sighting yet in this run.")
            else:
                seen = memory[last]
                since = memory[last:]  # the move made at the sighting step counts too
                lines.append(
                    "Last goal sighting: step {0}, {1} (relative to the way the drone faced then). "
                    "Since then: {2} {3}, {4}.".format(
                        seen["step"], IDENTIFIER_WORDS[seen["goal"]],
                        len(since), "move" if len(since) == 1 else "moves",
                        _net_turn([_turn(e) for e in since])))
    if now is not None:
        lines.append("Position now: {0}.".format(_at(now)))
    return "\n".join(lines)


def _sighting_line(sighting: Any) -> str:
    if sighting == "not_visible":
        return "Goal identifier, this image: the goal is not visible."
    if sighting in IDENTIFIER_WORDS:
        return "Goal identifier, this image: the goal is {0}.".format(IDENTIFIER_WORDS[sighting])
    return "Goal identifier, this image: no answer this step."


def _render_pose(prompt: Prompt, manifest: Dict[str, Any], memory: List[Dict[str, Any]],
                 sighting: Any, with_sighting: bool) -> str:
    actions: List[str] = []
    for action in manifest.get("actions", []):
        if action.get("turn_around"):
            actions.append("  [{i}] turn around in place".format(i=action["index"]))
        else:
            actions.append("  [{i}]".format(i=action["index"]))

    return prompt.user_template.format(
        step=manifest.get("step", 0),
        memory_block=_pose_log(manifest, memory, with_sighting),
        sighting_line=_sighting_line(sighting),
        action_lines="\n".join(actions) if actions else "  (none)",
    )


def render_pose_log(prompt: Prompt, manifest: Dict[str, Any],
                    memory: List[Dict[str, Any]], sighting: Any = None) -> str:
    """p07's prompt with the drone's position and heading after each move."""
    return _render_pose(prompt, manifest, memory, sighting, with_sighting=True)


def render_pose_log_no_sighting(prompt: Prompt, manifest: Dict[str, Any],
                                memory: List[Dict[str, Any]], sighting: Any = None) -> str:
    """render_pose_log without the last-sighting line; the identifier's answer
    for the current image stays."""
    return _render_pose(prompt, manifest, memory, sighting, with_sighting=False)


_POSE_PARAGRAPH = """Each log line also gives where the drone ended up after that move and how far
the move took it, measured by the system. Position is (x, y) in metres on the
floor, from a fixed origin. Heading is the way the drone faces, in degrees
counter-clockwise from the +x direction: turning left raises it, and turning
around changes it by 180. "moved 0.0 m" means the drone did not move: it turned
in place or something stopped it. The same position on several lines means the
drone has stayed in the same spot."""


# --- p08: Phase 2 R6, the drone's ground-truth pose in the log -----------------
# (eval/phase2/R6_pose_log/README.md)
#
# p07 with the drone's position and heading after every move, and how far each
# move took it, from the recorded ground-truth pose. The log recorded the
# command, not the outcome: a turn-around in place or a move into a wall read
# like progress (R5 summary, spin_failure). The sighting line stays.

P08 = Prompt(
    version="p08",
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

Your objective is to reach the goal: a glowing red sphere. You are not told
where it is. If the goal is in view, fly toward it along a clear path. If it is
not, explore through open space and openings until you find it. Avoid
collisions, and prefer headings with visible open floor ahead of them.

A goal identifier looks at each image before you do. Its only job is to say
whether the goal is in that image and where. Each step gives you its answer for
the current image. It describes this image only, not where the goal was before.

Each step also shows a log of your earlier steps in this run, kept by the
system. It records the move the drone made at each step. It is a record of what
happened, not a plan. Below the moves it gives the last step at which the goal
identifier saw the goal, which way it was then, and how many moves and how much
turning there have been since. That direction is relative to the way the drone
faced at that step, not now. If the identifier says the goal is not visible
now, it is not in the current image, whatever the log says. Repeat a move only
while the image shows it is still working. Turning around is a normal move when
the way ahead is blocked. Use the log to work out where the goal is likely to be
now and to avoid flying back over ground you have already covered.

""" + _POSE_PARAGRAPH + """

Give your reasoning first, then the number.""",
    user_template=P07.user_template,
    render=render_pose_log,
)


# --- p09: Phase 2 R6, the pose log without the sighting line -------------------
# (eval/phase2/R6_pose_log/README.md)
#
# p08 minus the last goal sighting and the sentences that explain it. The
# sighting line carried R5's "goal is behind, turn around" argument (83 of 92).
# The identifier's answer for the current image stays.

P09 = Prompt(
    version="p09",
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

Your objective is to reach the goal: a glowing red sphere. You are not told
where it is. If the goal is in view, fly toward it along a clear path. If it is
not, explore through open space and openings until you find it. Avoid
collisions, and prefer headings with visible open floor ahead of them.

A goal identifier looks at each image before you do. Its only job is to say
whether the goal is in that image and where. Each step gives you its answer for
the current image. It describes this image only.

Each step also shows a log of your earlier steps in this run, kept by the
system. It records the move the drone made at each step. It is a record of what
happened, not a plan. Repeat a move only while the image shows it is still
working. Turning around is a normal move when the way ahead is blocked. Use the
log to avoid flying back over ground you have already covered.

""" + _POSE_PARAGRAPH + """

Give your reasoning first, then the number.""",
    user_template=P07.user_template,
    render=render_pose_log_no_sighting,
)

# --- p10: Phase 2 R7, the pose log with comparison lines ----------------------
# (eval/phase2/R7_comparison_lines/README.md)
#
# p08 plus one change: the code states what each move did against the drone's
# own earlier positions, "did not move (blocked)", "stopped short (blocked)",
# "back where you were after step N". R6: the log quoted positions and the model
# never compared them (143 collisions, 65% of reasons after a blocked move still
# claimed progress). Position and heading stay as in p08; the sighting line stays.

#: A normal move covers about 1.7 m (R6 pose records: 655 of 876 steps).
BLOCKED_BELOW_M = 0.3
SHORT_BELOW_M = 1.5
REVISIT_WITHIN_M = 0.5


def _compare(i: int, memory: List[Dict[str, Any]], before: Any, after: Any,
             ends: List[Any]) -> str:
    """The comparison the model did not make itself, for the move at memory[i].

    `ends[j]` is where move j ended (None if unknown); index -1 is not used, the
    start is handled by the caller."""
    entry = memory[i]
    notes: List[str] = []
    moved = None if before is None else math.hypot(after[0] - before[0], after[1] - before[1])
    if entry.get("turn_around"):
        if moved is not None and moved < BLOCKED_BELOW_M:
            notes.append("turned in place")
    elif moved is not None:
        if moved < BLOCKED_BELOW_M:
            notes.append("did not move (blocked)")
        elif moved < SHORT_BELOW_M:
            notes.append("stopped short (blocked)")
    if moved is not None and moved >= SHORT_BELOW_M:
        # Not the step just before: a move that ended where it started is
        # already "did not move".
        for j in range(i - 2, -1, -1):
            e = ends[j]
            if e is not None and math.hypot(after[0] - e[0], after[1] - e[1]) < REVISIT_WITHIN_M:
                notes.append("back where you were after step {0}".format(memory[j]["step"]))
                break
    return " ".join("{0}.".format(n[0].upper() + n[1:]) for n in notes)


def _compare_log(manifest: Dict[str, Any], memory: List[Dict[str, Any]],
                 with_sighting: bool = True) -> str:
    now = _where(manifest.get("pose"))
    if not memory:
        lines = ["Log of your earlier steps: none yet, this is the first step."]
    else:
        lines = ["Log of your earlier steps (what happened, not a plan):"]
        start = _where(memory[0].get("pose"))
        if start is not None:
            lines.append("Start: at {0}.".format(_at(start)))
        ends: List[Any] = []
        for i, entry in enumerate(memory):
            before = _where(entry.get("pose"))
            after = _where(entry["pose_after"]) if entry.get("pose_after") else now
            ends.append(after)
            if after is None:
                lines.append("Step {0}: {1}. Position not recorded.".format(
                    entry["step"], _move(entry)))
                continue
            moved = ("" if before is None else ", moved {0:.1f} m".format(
                math.hypot(after[0] - before[0], after[1] - before[1])))
            note = _compare(i, memory, before, after, ends)
            lines.append("Step {0}: {1}. Ended at {2}{3}.{4}".format(
                entry["step"], _move(entry), _at(after), moved, " " + note if note else ""))
        last = None
        for i, entry in enumerate(memory):
            if with_sighting and entry.get("goal") in ("ahead", "left", "right"):
                last = i
        if with_sighting and last is None:
            lines.append("No goal sighting yet in this run.")
        elif with_sighting:
            seen = memory[last]
            since = memory[last:]
            lines.append(
                "Last goal sighting: step {0}, {1} (relative to the way the drone faced then). "
                "Since then: {2} {3}, {4}.".format(
                    seen["step"], IDENTIFIER_WORDS[seen["goal"]],
                    len(since), "move" if len(since) == 1 else "moves",
                    _net_turn([_turn(e) for e in since])))
    if now is not None:
        lines.append("Position now: {0}.".format(_at(now)))
    return "\n".join(lines)


def render_pose_compare(prompt: Prompt, manifest: Dict[str, Any],
                        memory: List[Dict[str, Any]], sighting: Any = None,
                        with_sighting: bool = True) -> str:
    actions: List[str] = []
    for action in manifest.get("actions", []):
        if action.get("turn_around"):
            actions.append("  [{i}] turn around in place".format(i=action["index"]))
        else:
            actions.append("  [{i}]".format(i=action["index"]))
    return prompt.user_template.format(
        step=manifest.get("step", 0),
        memory_block=_compare_log(manifest, memory, with_sighting),
        sighting_line=_sighting_line(sighting),
        action_lines="\n".join(actions) if actions else "  (none)",
    )


_COMPARE_PARAGRAPH = _POSE_PARAGRAPH + """
The system also compares each move with where the drone has been. "Did not move
(blocked)" and "stopped short (blocked)" mean a wall stopped the move, so that
heading does not work from there. "Back where you were after step N" means the
drone is at a place it already visited. A move that is blocked or goes back to an
earlier place is not progress."""

P10 = Prompt(
    version="p10",
    system=P08.system.replace(_POSE_PARAGRAPH, _COMPARE_PARAGRAPH),
    user_template=P07.user_template,
    render=render_pose_compare,
)

def render_pose_compare_no_sighting(prompt: Prompt, manifest: Dict[str, Any],
                                    memory: List[Dict[str, Any]], sighting: Any = None) -> str:
    return render_pose_compare(prompt, manifest, memory, sighting, with_sighting=False)


# --- p11: Phase 2 R7, p09 with comparison lines ---------------------------------
# (eval/phase2/R7_comparison_lines/README.md)
#
# p09 (the pose log without the sighting line) plus p10's comparison lines. The
# a09 probe (p10, sighting line kept) turned around on 13/25 `lost` frames against
# a08's 4/25: the sighting line brings the "goal is behind" argument back. The
# identifier's answer for the current image stays.

P11 = Prompt(
    version="p11",
    system=P09.system.replace(_POSE_PARAGRAPH, _COMPARE_PARAGRAPH),
    user_template=P07.user_template,
    render=render_pose_compare_no_sighting,
)

PROMPTS: Dict[str, Prompt] = {p.version: p for p in (P02, P03, P04, P05, P06, P07, P08, P09,
                                                      P10, P11, G01, G02)}


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
