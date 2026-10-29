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
                 with_sighting: bool = True, at: Callable[[Any], str] = _at) -> str:
    now = _where(manifest.get("pose"))
    if not memory:
        lines = ["Log of your earlier steps: none yet, this is the first step."]
    else:
        lines = ["Log of your earlier steps (what happened, not a plan):"]
        start = _where(memory[0].get("pose"))
        if start is not None:
            lines.append("Start: at {0}.".format(at(start)))
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
                entry["step"], _move(entry), at(after), moved, " " + note if note else ""))
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
        lines.append("Position now: {0}.".format(at(now)))
    return "\n".join(lines)


def render_pose_compare(prompt: Prompt, manifest: Dict[str, Any],
                        memory: List[Dict[str, Any]], sighting: Any = None,
                        with_sighting: bool = True, at: Callable[[Any], str] = _at) -> str:
    actions: List[str] = []
    for action in manifest.get("actions", []):
        if action.get("turn_around"):
            actions.append("  [{i}] turn around in place".format(i=action["index"]))
        else:
            actions.append("  [{i}]".format(i=action["index"]))
    return prompt.user_template.format(
        step=manifest.get("step", 0),
        memory_block=_compare_log(manifest, memory, with_sighting, at),
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

# --- p12: Phase 2 R8, heading as a compass word ----------------------------------
# (eval/phase2/R8_heading_word/README.md)
#
# p11 with one change: the log gives the drone's heading as one of eight compass
# words ("facing south-west") instead of degrees, and the pose paragraph states
# the map's axes in those words. R7 and R6: the model added and subtracted
# degrees in its reasons ("287 + 180", 11 reasons in R7) and turned around on a
# goal it could see to the side (s02vc `initial`, step 12, in both rounds).

#: Eight compass words, counter-clockwise from +x, as `_where()` measures heading.
COMPASS = ("east", "north-east", "north", "north-west",
           "west", "south-west", "south", "south-east")


def _compass(heading: float) -> str:
    """The nearest of the eight compass words: 45-degree bins centred on east (0),
    north (90), west (180) and south (270), with x east and y north."""
    return COMPASS[int(((float(heading) + 22.5) % 360.0) // 45.0)]


def _at_word(where: Any) -> str:
    return "({0:.1f}, {1:.1f}), facing {2}".format(where[0], where[1], _compass(where[2]))


def render_pose_compare_word(prompt: Prompt, manifest: Dict[str, Any],
                             memory: List[Dict[str, Any]], sighting: Any = None) -> str:
    """p11's log with heading as a compass word."""
    return render_pose_compare(prompt, manifest, memory, sighting,
                               with_sighting=False, at=_at_word)


_POSE_PARAGRAPH_WORD = _POSE_PARAGRAPH.replace(
    """floor, from a fixed origin. Heading is the way the drone faces, in degrees
counter-clockwise from the +x direction: turning left raises it, and turning
around changes it by 180.""",
    """floor, from a fixed origin: east is +x and north is +y. "Facing" is the
compass direction the drone faces, to the nearest of eight: east, north-east,
north, north-west, west, south-west, south, south-east. Turning left goes from
east toward north, then west, then south; turning around gives the opposite
direction.""")
assert _POSE_PARAGRAPH_WORD != _POSE_PARAGRAPH

P12 = Prompt(
    version="p12",
    system=P09.system.replace(_POSE_PARAGRAPH, _COMPARE_PARAGRAPH.replace(
        _POSE_PARAGRAPH, _POSE_PARAGRAPH_WORD)),
    user_template=P07.user_template,
    render=render_pose_compare_word,
)

# --- p13: Phase 2 R8N, a no-op edit of p11 ------------------------------------------
# (eval/phase2/R8N_noop_control/README.md)
#
# p11 plus one sentence that is true and adds nothing the log does not already
# show. R7: one added paragraph moved 5 of 18 first picks before any comparison
# line existed. R8N measures how far an edit with no content moves a round.

NOOP_SENTENCE = "The log lists your steps in the order they happened, oldest first."

P13 = Prompt(
    version="p13",
    system=P09.system.replace(_POSE_PARAGRAPH, _COMPARE_PARAGRAPH + "\n" + NOOP_SENTENCE),
    user_template=P07.user_template,
    render=render_pose_compare_no_sighting,
)

# --- R9: the orchestrated agent (a13), three calls with one job each ------------
# (eval/phase2/R9_hail_mary/README.md)
#
# Code keeps a map of the run (server/decider/spatial.py) and does every spatial
# comparison. The perceiver (g03) reads the clean frame, the strategist (q01)
# picks a target from a list code builds, and the navigator (p14) picks an
# action whose notes say what the map knows about it. No model call is shown a
# coordinate or a heading in degrees: R6 and R7 show the model quoting numbers
# without comparing them and turning away from a goal it could see.

# g03: g02's job, plus how much open floor each strip of the image shows and
# where the doorways are. Same isolation as g02: the clean frame, no log, no
# step number. The goal is reported by strip, not left/ahead/right, so code can
# turn it into a direction on the map.

G03 = Prompt(
    version="g03",
    system="""You check one image from the front camera of a small indoor drone.
Judge this image alone.

Think of the image as five equal vertical strips, from left to right:
far_left, left, centre, right, far_right.

1. The goal is a glowing red sphere. Say which strip it is in, or not_visible.
   If you can see it, say how far away it looks: touching (it is large in the
   image, under 2 m away), near (2 to 6 m), mid (6 to 15 m), far (over 15 m).
   If it is not visible, its distance is none.
2. For each strip, look along the floor straight ahead in that strip and say
   how far the open floor runs before a wall or obstacle:
   open_far if it runs well into the distance (more than about 5 m),
   open_near if a wall or obstacle stands a few metres away (about 2 to 5 m),
   blocked_near if a wall or obstacle is right in front (under about 2 m).
   Also say whether that strip shows a doorway: an opening in a wall the drone
   could fly through.

First describe what you see: walls, openings, obstacles, and anything that
could be the goal. Then give the report.""",
    user_template="Report on this image.",
    render=render_identifier_question,
)


# q01: chooses what the drone heads for. It gets no image and no numbers but
# distances: a description code writes from the map, and a list of targets.

def render_strategist(prompt: Prompt, situation: str) -> str:
    return prompt.user_template.format(situation=situation)


Q01 = Prompt(
    version="q01",
    system="""You plan the route of a small indoor drone that is looking for a goal,
a glowing red sphere. Another model flies the drone one step at a time; you
choose what it should head for. You do not see the camera image.

The system keeps a map from the drone's own moves and from what its camera has
seen. It tells you what is known now and lists the targets you can choose from,
each with its distance and direction from the drone as it faces now.

Choose a mode and a target:
- approach: head for the goal.
- explore: head for a doorway not yet passed or for unexplored ground.
- backtrack: go back to an earlier place that still had an untried way on.
- escape: the drone keeps returning to the same ground; pick a target in a
  direction it has not been trying.

The goal is often behind a wall. If moves toward it have been blocked, a
doorway or unexplored ground is a better target than the goal itself. Doors
can close; the list only shows doorways not known to be closed. Choose
"explore" as the target when nothing listed looks useful.

Give your reasoning first, then the mode, then one target id exactly as listed.""",
    user_template="""{situation}

Choose a mode and a target.""",
    render=render_strategist,
)


# q02: the strategist for a14 (R10). q01, told that the system knows where the
# goal is and that it does not move; the goal is always on the list at its true
# position. R9: q01 chose the goal on 18 of 200 calls with it out of view.

Q02 = Prompt(
    version="q02",
    system="""You plan the route of a small indoor drone that is flying to a goal,
a glowing red sphere. Another model flies the drone one step at a time; you
choose what it should head for. You do not see the camera image.

The system knows exactly where the goal is, and the goal does not move. It is
always on the list of targets, with its distance and direction from the drone
as it faces now, whether or not the camera can see it.

The system also keeps a map from the drone's own moves and from what its camera
has seen. It tells you what is known now and lists the other targets you can
choose from, each with its distance and direction.

Choose a mode and a target:
- approach: head for the goal.
- explore: head for a doorway not yet passed or for unexplored ground, to find
  a way around a wall between the drone and the goal.
- backtrack: go back to an earlier place that still had an untried way on.
- escape: the drone keeps returning to the same ground; pick a target in a
  direction it has not been trying.

Head for the goal unless moves toward it have been blocked. When they have, a
doorway or unexplored ground on the goal's side is a better target than the
goal itself. Doors can close; the list only shows doorways not known to be
closed. Choose "explore" as the target when nothing listed looks useful.

Give your reasoning first, then the mode, then one target id exactly as listed.""",
    user_template="""{situation}

Choose a mode and a target.""",
    render=render_strategist,
)


# q03: the detour strategist for a15 (R11). Code keeps the goal as the target
# (planner.py); q03 is asked only when the way toward it is shut, and chooses
# from detours each worded with how much nearer the goal it lies. R10: q02 chose
# the goal on 70 of 229 calls and read "not in the image" as "a wall is in the way".

Q03 = Prompt(
    version="q03",
    system="""You plan a detour for a small indoor drone that is flying to a goal, a
glowing red sphere. Another model flies the drone one step at a time. You do
not see the camera image.

The system knows exactly where the goal is, and the goal does not move. The
drone heads for the goal by itself. You are asked only when the way toward it
is shut: a wall is close that way, a move that way was blocked, or the drone
has stopped getting nearer.

The system keeps a map from the drone's own moves and from what its camera has
seen. It lists the detours you can choose from, each with its distance and
direction from the drone as it faces now, and how much nearer the goal it lies
than the drone is. Once the drone reaches the detour, it heads for the goal
again.

Choose a mode and a detour:
- explore: a doorway or unexplored ground, to get round the wall between the
  drone and the goal.
- backtrack: go back to an earlier place that still had an untried way on.
- escape: the drone keeps returning to the same ground; pick a detour in a
  direction it has not been trying.

Prefer a detour that lies nearer the goal than the drone. Doors can close; the
list only shows doorways not known to be closed. Choose "explore" as the target
when nothing listed looks useful.

Give your reasoning first, then the mode, then one target id exactly as listed.""",
    user_template="""{situation}

Choose a mode and a detour.""",
    render=render_strategist,
)


# g04: the perceiver for a17 (R12). g03, with the far floor split by whether a
# wall ends it (wall_far, 4 to 8 m) or not (open_very_far), and a doorway said
# open or closed. a17's coverage map ends each strip's cone where its floor
# ends, so the far class decides how much ground one look searches. R11 against
# the site geometry: open_far had a wall within 6 m on 849 of 2589 lane reads,
# and a featureless wall face within 1 m read open_far on 33% of blocked_near
# lanes (failure_analysis.md Q4).

G04 = Prompt(
    version="g04",
    system="""You check one image from the front camera of a small indoor drone.
Judge this image alone.

Think of the image as five equal vertical strips, from left to right:
far_left, left, centre, right, far_right.

1. The goal is a glowing red sphere. Say which strip it is in, or not_visible.
   If you can see it, say how far away it looks: touching (it is large in the
   image, under 2 m away), near (2 to 6 m), mid (6 to 15 m), far (over 15 m).
   If it is not visible, its distance is none.
2. For each strip, look along the floor straight ahead in that strip and say
   where the open floor ends:
   blocked_near if a wall or obstacle is right in front (under about 2 m);
   open_near if a wall or obstacle stands a few metres away (about 2 to 4 m);
   wall_far if the floor runs on but a wall or door ends it in the distance
   (about 4 to 8 m);
   open_very_far if no wall ends the floor within about 8 m.
   A surface that fills the strip with no floor line across it is a wall right
   in front: blocked_near.
   Also say whether that strip shows a doorway: open if there is an opening in
   a wall the drone could fly through, closed if a door fills the opening, or
   none.

First describe what you see: walls, openings, doors, obstacles, and anything
that could be the goal. Then give the report.""",
    user_template="Report on this image.",
    render=render_identifier_question,
)


# q04: the search strategist for a17 (R12). No goal truth: code sets the stage
# (explore until the goal is seen, then head for where it was seen) and asks
# q04 only for a place to search, or for a detour when the way toward a seen
# goal is shut. Each place is worded by how much unsearched ground it opens and
# its path length over known floor; nothing is worded "nearer the goal". R11:
# q03 picked the item worded largest gain toward the goal on 35 of 38 calls,
# and 34 of 37 of those lay behind or inside a wall.

Q04 = Prompt(
    version="q04",
    system="""You plan where a small indoor drone searches for a goal, a glowing red
sphere. Another model flies the drone one step at a time. You do not see the
camera image.

The system keeps a map from the drone's own moves and from what its camera has
seen. Ground the camera has looked over without seeing the goal is searched;
the goal is not there. The system tells you whether the goal has been seen and
lists the places you can choose from, each with its distance and direction from
the drone as it faces now:
- unsearched ground: the edge of ground the camera has not yet looked over,
  with how much of it there is and how far the path there is over known floor;
- doorways: openings seen in a wall, which lead to ground not yet searched;
- a place the drone was at before, which still had an untried way on.
Every place listed can be reached over known floor.

Choose a mode and a place:
- explore: search unsearched ground or go through a doorway.
- approach: get round a wall toward the goal, when it has been seen.
- backtrack: go back to an earlier place; use it when no unsearched ground is
  left here, as in a dead end.
- escape: the drone keeps returning to the same ground; pick a place in a
  direction it has not been trying.

Prefer more unsearched ground over a shorter path, and a doorway when no
unsearched ground is listed. Choose "explore" as the place when nothing listed
looks useful.

Give your reasoning first, then the mode, then one place id exactly as listed.""",
    user_template="""{situation}

Choose a mode and a place.""",
    render=render_strategist,
)


# q05: a21's search strategist (R13G). q04 word for word, with one paragraph
# more: the system also says where the goal truly is, and each place how much
# nearer the goal it lies. Every place is still reachable over known floor
# (R11's q03 picked the item worded nearest the goal on 35 of 38 calls, and
# 34 of 37 of those lay behind or inside a wall; a17's menu has no such item).

Q05 = Prompt(
    version="q05",
    system=Q04.system.replace(
        "Every place listed can be reached over known floor.\n",
        "Every place listed can be reached over known floor.\n\n"
        "The system also tells you where the goal truly is, and for each place how\n"
        "much nearer the goal it lies than the drone. The goal may be behind a wall:\n"
        "a place nearer the goal is worth more only when it also leads somewhere new.\n"),
    user_template=Q04.user_template,
    render=render_strategist,
)


# q06: the detour strategist for the known-goal agents on a17's reachable menu
# (a25 onward). q03, with its closing advice replaced: every detour is
# reachable, a doorway is the way round a wall even when it lies farther from
# the goal, and a dead end calls for the way back. R11 failure analysis Q6:
# doorway picks 1 of 19 menus that held one; backtrack never chosen (s03
# dynamic, 32 steps in a dead end).

Q06 = Prompt(
    version="q06",
    system=Q03.system.replace(
        """Prefer a detour that lies nearer the goal than the drone. Doors can close; the
list only shows doorways not known to be closed. Choose "explore" as the target
when nothing listed looks useful.""",
        """Every detour listed can be reached over known floor. The goal is usually
behind a wall, and unexplored ground nearer the goal is often still on the
drone's side of that wall. So:
1. A doorway is the way round the wall: choose it even when it lies farther
   from the goal than the drone, unless the drone has just come back through it.
2. With no doorway listed, choose unexplored ground, the most of it first;
   nearer the goal only breaks a tie.
3. If moves from here were blocked on several sides, the drone is in a dead
   end: go back to an earlier place.
Doors can close; the list only shows doorways not known to be closed. Choose
"explore" as the target when nothing listed looks useful."""),
    user_template=Q03.user_template,
    render=render_strategist,
)


# q07: q06 with the reason spelt out. On R11's 38 recorded calls q06 still
# picked the unexplored ground worded nearest the goal on 34 (doorway on 2 of
# 19 menus with one): its reasoning read "N m nearer the goal" as progress.

Q07 = Prompt(
    version="q07",
    system=Q06.system.replace(
        """Every detour listed can be reached over known floor. The goal is usually
behind a wall,""",
        """Every detour listed can be reached over known floor. "Nearer the goal" is
straight-line distance only: it says nothing about the wall in between, and the
drone has just been stopped by that wall. Unexplored ground worded nearer the
goal is usually more of the same wall. The goal is usually behind a wall,"""),
    user_template=Q03.user_template,
    render=render_strategist,
)

# q08: the detour strategist for a39 (along-the-wall detours). q03 with the
# advice to follow the wall that stopped the drone, one way to its end before
# the other. R15/R15N failure analysis mode B: no along-wall search at the s02
# divider was primary in 7 of 17 failures; menu doorways were real 4 of 54.

Q08 = Prompt(
    version="q08",
    system=Q03.system.replace(
        """Prefer a detour that lies nearer the goal than the drone. Doors can close; the
list only shows doorways not known to be closed. Choose "explore" as the target
when nothing listed looks useful.""",
        """When you are asked, a wall usually stands between the drone and the goal, and
the way round it is along it: a gap or an open door somewhere along that wall.
The two "along the wall" detours follow it, on the left or the right of the
way to the goal. So:
1. Follow the wall one way until that way ends: choose the side you followed
   last time again. Each item says how often its side was followed.
2. When that side ends at a wall, or is no longer listed, take the other side.
3. To start, take the side worded nearer the goal; if both are the same, the
   side with more room.
4. Choose a doorway or unexplored ground only when no "along the wall" item is
   listed. "Nearer the goal" is straight-line distance only and says nothing
   about the wall in between.
Choose "explore" as the target when nothing listed looks useful."""),
    user_template=Q03.user_template,
    render=render_strategist,
)

# q09: the detour strategist for a46. q08 with the "through the opening" detour
# first: a gap in the blocking wall that confirmed open-doorway sightings point
# at (planner.through_doorways). R19/R19K s02 failure analysis, mode K.

Q09 = Prompt(
    version="q09",
    system=Q08.system.replace(
        """So:
1. Follow the wall one way until that way ends""",
        """So:
0. A "through the opening" detour comes first: open-doorway sightings, each
   checked a second time, point at that gap in the wall. It takes the drone to
   a spot square in front of the gap, then through it.
1. Otherwise follow the wall one way until that way ends"""),
    user_template=Q03.user_template,
    render=render_strategist,
)

# q10: the detour strategist for a50. q08 with a dead-end rule and the "other way
# at the fork" detour (planner.other_way): s03 analysis, the drones stayed in the
# tine whose door was shut and never took the other one.

Q10 = Prompt(
    version="q10",
    system=Q08.system.replace(
        """Choose "explore" as the target when nothing listed looks useful.""",
        """5. A dead end: a closed door was seen in the last few steps (the situation
   says so) and at most one "along the wall" item is listed, or both were
   followed twice or more. Then the way on is not here: choose the "other way"
   detour, the end of the wall you met earlier that the drone never went to,
   even though it lies behind and farther from the goal.
Choose "explore" as the target when nothing listed looks useful."""),
    user_template=Q03.user_template,
    render=render_strategist,
)

# q11: the detour strategist for a52. q08 with the "other way" detour, which a52
# lists only in a dead end (a closed door seen, at most one way along the wall).
# q10 took it off the dead end too (R26 probe: 36 of 82 divider calls).

Q11 = Prompt(
    version="q11",
    system=Q08.system.replace(
        """Choose "explore" as the target when nothing listed looks useful.""",
        """5. An "other way" detour is listed only in a dead end: a closed door was seen
   ahead and the wall offers no more way along it. When it is listed, choose
   it, even though it lies behind and farther from the goal: it is the end of
   the wall you met earlier that the drone never went to.
Choose "explore" as the target when nothing listed looks useful."""),
    user_template=Q03.user_template,
    render=render_strategist,
)

# p14: the navigator. The frame with its markers, the planner's target, the
# perceiver's answer for this image, the last three moves in words, and notes
# from the map against each action.

FAN_WORDS = {43.5: "sharp left", 21.75: "slight left", 0.0: "straight",
             -21.75: "slight right", -43.5: "sharp right"}


def _fan_word(theta_deg: Any) -> str:
    theta = float(theta_deg or 0.0)
    return FAN_WORDS[min(FAN_WORDS, key=lambda t: abs(t - theta))]


def render_orchestrated(prompt: Prompt, manifest: Dict[str, Any],
                        tags: Dict[int, List[str]], plan_line: str,
                        perceiver_line: str, recent_moves: str) -> str:
    actions: List[str] = []
    for action in manifest.get("actions", []):
        i = int(action["index"])
        what = ("turn around in place" if action.get("turn_around")
                else _fan_word(action.get("theta_deg")))
        notes = tags.get(i) or []
        actions.append("  [{0}] {1}{2}".format(i, what, ": " + "; ".join(notes) if notes else ""))
    return prompt.user_template.format(
        step=manifest.get("step", 0),
        plan_line=plan_line,
        perceiver_line=perceiver_line,
        recent_moves=recent_moves,
        action_lines="\n".join(actions) if actions else "  (none)",
    )


P14 = Prompt(
    version="p14",
    system="""You are flying a small indoor drone. You see one image per step.

Numbered markers are drawn on the image. Each marker is an action you may take:
the drone turns to face that marker, then flies a short distance forward.
Marker 0, when offered, turns the drone around in place without moving.

Rules of this interface:
- You may only pick a number that is listed as available for this step.
- If you pick a heading that runs into a wall, the drone hits the wall and that
  counts against the run.
- You cannot strafe, climb, or descend. Altitude is held for you.
- You cannot open doors or manipulate anything around you. A closed door is a
  wall. Find a route through openings that are already clear.

Your objective is to reach the goal: a glowing red sphere. If the goal is in
view and the way to it is clear, fly toward it. If it is not, explore through
open space and openings until you find it.

Helpers work with you. A perceiver looks at each image before you and says
where the goal is in it. A planner sets a target from a map the system keeps of
where the drone has been and what its camera has seen. Next to each action the
system writes what that map says about it:
- "blocked here before" or "stopped short here before": that move was tried
  from this spot and a wall stopped it.
- "wall close (seen now)" or "doorway (seen now)": what the perceiver sees that
  way in this image.
- "goal this way (seen now, ...)" and "goal about one move ahead": the goal is
  in this image, that way.
- "toward your target": the move that heads most directly for the planner's
  target.
- "new ground" or "been there N times": whether the drone has already been
  where the move ends.
These notes are measured by the system; trust them over your own guesses about
where you have been. The image is your guide to what is in front of you now.
Prefer the move toward your target when the image shows it is open, avoid moves
that were blocked before, and prefer new ground over ground you have covered.
Turning around is a normal move when every way ahead is blocked.

Give your reasoning first, then the number.""",
    user_template="""Step {step}.

Planner: {plan_line}
Perceiver, this image: {perceiver_line}
Your last moves: {recent_moves}

Available actions this step:
{action_lines}

Pick one number.""",
    render=render_orchestrated,
)


# --- p15: Phase 2 R15, the navigator turns around toward a target behind --------
# p14 says "Turning around is a normal move when every way ahead is blocked",
# and R11's navigator took "toward your target" on marker 0 on 43 of 181 offers
# (24%) against 71% on a forward move; the 138 ignored and 47 hidden steps moved
# the drone 158.5 m away from the goal (R11 failure analysis, Q2). p15 is p14
# with that sentence replaced.

P15 = Prompt(
    version="p15",
    system="""You are flying a small indoor drone. You see one image per step.

Numbered markers are drawn on the image. Each marker is an action you may take:
the drone turns to face that marker, then flies a short distance forward.
Marker 0, when offered, turns the drone around in place without moving.

Rules of this interface:
- You may only pick a number that is listed as available for this step.
- If you pick a heading that runs into a wall, the drone hits the wall and that
  counts against the run.
- You cannot strafe, climb, or descend. Altitude is held for you.
- You cannot open doors or manipulate anything around you. A closed door is a
  wall. Find a route through openings that are already clear.

Your objective is to reach the goal: a glowing red sphere. If the goal is in
view and the way to it is clear, fly toward it. If it is not, explore through
open space and openings until you find it.

Helpers work with you. A perceiver looks at each image before you and says
where the goal is in it. A planner sets a target from a map the system keeps of
where the drone has been and what its camera has seen. Next to each action the
system writes what that map says about it:
- "blocked here before" or "stopped short here before": that move was tried
  from this spot and a wall stopped it.
- "wall close (seen now)" or "doorway (seen now)": what the perceiver sees that
  way in this image.
- "goal this way (seen now, ...)" and "goal about one move ahead": the goal is
  in this image, that way.
- "toward your target": the move that heads most directly for the planner's
  target.
- "new ground" or "been there N times": whether the drone has already been
  where the move ends.
These notes are measured by the system; trust them over your own guesses about
where you have been. The image is your guide to what is in front of you now.
Prefer the move toward your target when the image shows it is open, avoid moves
that were blocked before, and prefer new ground over ground you have covered.
When "toward your target" is on marker 0, your target is behind you: turn
around (pick 0) even when the way ahead looks open, unless the goal is in view
ahead. Flying on ahead would take you away from the target. Turning around is
also the move when every way ahead is blocked.

Give your reasoning first, then the number.""",
    user_template="""Step {step}.

Planner: {plan_line}
Perceiver, this image: {perceiver_line}
Your last moves: {recent_moves}

Available actions this step:
{action_lines}

Pick one number.""",
    render=render_orchestrated,
)


# --- g05: Phase 2 R12, where the floor ends in the image -------------------------
# g04 asked for metres and read 69% of strips open_very_far, walls under 1 m
# among them (R12 line 7). The camera is level at 1.75 m with a 87-degree view,
# so a floor line at fraction v of the half-height below the image centre is
# 1.84 / v metres away, and a wall under 1.84 m hides the floor. g05 asks where
# the floor ends in the image; code turns that into a reach (agent floor_map).

G05 = Prompt(
    version="g05",
    system="""You check one image from the front camera of a small indoor drone.
Judge this image alone.

Think of the image as five equal vertical strips, from left to right:
far_left, left, centre, right, far_right.

1. The goal is a glowing red sphere. Say which strip it is in, or not_visible.
   If you can see it, say how far away it looks: touching (it is large in the
   image, under 2 m away), near (2 to 6 m), mid (6 to 15 m), far (over 15 m).
   If it is not visible, its distance is none.
2. For each strip, find where its floor ends: the line where the floor meets a
   wall, door or obstacle. The camera is level, so the nearer the obstacle, the
   lower that line sits in the image, and an obstacle close in front hides the
   floor completely. Say:
   no_floor if no floor shows at the bottom of the strip: a wall, door, pillar
   or plain surface fills it from the bottom up. A dark plain surface is a wall
   close in front, not open space;
   bottom if floor shows but ends within the bottom quarter of the image;
   lower if the floor ends higher than that but well below the middle of the
   image;
   middle if the floor runs up to just below the middle of the image.
   Judge by the floor you can see, its edges and lines, never by darkness.
   Also say whether that strip shows a doorway: open if there is an opening in
   a wall the drone could fly through, closed if a door fills the opening, or
   none.

First say, for each strip from left to right, what fills the bottom of the
strip and where its floor ends. Then describe walls, openings, doors and
anything that could be the goal. Then give the report.""",
    user_template="Report on this image.",
    render=render_identifier_question,
)

# --- g06: Phase 2 R15, the floor that runs on ------------------------------------
# g05 had no answer for floor that is plainly there but whose far end is not in
# sight, and answered no_floor for it: of R12's 477 no_floor strips, 157 were
# clear past 8 m, with reasons such as "the floor is visible across the entire
# image ... the floor line is not visible". g06 renames no_floor (a wall at the
# bottom of the strip), adds runs_on, and has the model look at the bottom of
# the strip first.

G06 = Prompt(
    version="g06",
    system="""You check one image from the front camera of a small indoor drone.
Judge this image alone.

Think of the image as five equal vertical strips, from left to right:
far_left, left, centre, right, far_right.

1. The goal is a glowing red sphere. Say which strip it is in, or not_visible.
   If you can see it, say how far away it looks: touching (it is large in the
   image, under 2 m away), near (2 to 6 m), mid (6 to 15 m), far (over 15 m).
   If it is not visible, its distance is none.
2. For each strip, first look at the very bottom edge of the strip. The floor
   is a flat surface with grid lines. The camera is level, so floor at the
   bottom edge means nothing stands within about 2 m that way.
   wall_at_bottom only if the bottom edge of the strip shows no floor at all:
   a wall, door, pillar or object covers it. Darkness or shadow on the floor
   is still floor.
   If floor shows at the bottom edge, follow it up the strip and say where it
   ends, at the line where it meets a wall, door or obstacle:
   bottom if that line is within the bottom quarter of the image;
   lower if it is higher than that but well below the middle;
   middle if it is just below the middle of the image;
   runs_on if the floor goes on into the distance and you cannot see where it
   ends, or it ends at the middle of the image.
   Also say whether that strip shows a doorway: open if there is an opening in
   a wall the drone could fly through, closed if a door fills the opening, or
   none.

First say, for each strip from left to right, what is at its bottom edge and
where its floor ends. Then describe walls, openings, doors and anything that
could be the goal. Then give the report.""",
    user_template="Report on this image.",
    render=render_identifier_question,
)

# --- p16: Phase 2 R15, the notes in an order -------------------------------------
# p15's probe on R11's steps: "toward your target" on marker 0 followed 31% (p14
# 18%). p14 also says to prefer new ground, and marker 0 nearly always carries
# "behind you is ground you have covered" while the forward moves say "new
# ground". p16 is p14 with the notes ranked: goal, then toward (marker 0
# included), then new ground.

P16 = Prompt(
    version="p16",
    system="""You are flying a small indoor drone. You see one image per step.

Numbered markers are drawn on the image. Each marker is an action you may take:
the drone turns to face that marker, then flies a short distance forward.
Marker 0, when offered, turns the drone around in place without moving.

Rules of this interface:
- You may only pick a number that is listed as available for this step.
- If you pick a heading that runs into a wall, the drone hits the wall and that
  counts against the run.
- You cannot strafe, climb, or descend. Altitude is held for you.
- You cannot open doors or manipulate anything around you. A closed door is a
  wall. Find a route through openings that are already clear.

Your objective is to reach the goal: a glowing red sphere. If the goal is in
view and the way to it is clear, fly toward it. If it is not, explore through
open space and openings until you find it.

Helpers work with you. A perceiver looks at each image before you and says
where the goal is in it. A planner sets a target from a map the system keeps of
where the drone has been and what its camera has seen. Next to each action the
system writes what that map says about it:
- "blocked here before" or "stopped short here before": that move was tried
  from this spot and a wall stopped it.
- "wall close (seen now)" or "doorway (seen now)": what the perceiver sees that
  way in this image.
- "goal this way (seen now, ...)" and "goal about one move ahead": the goal is
  in this image, that way.
- "toward your target": the move that heads most directly for the planner's
  target.
- "new ground" or "been there N times": whether the drone has already been
  where the move ends.
These notes are measured by the system; trust them over your own guesses about
where you have been. The image is your guide to what is in front of you now.
Choose in this order:
1. A move with "goal this way" or "goal about one move ahead".
2. The move with "toward your target", whether it is a forward move or marker 0.
   "toward your target" on marker 0 means your target is behind you: turn
   around, even when the way ahead looks open and new; every forward move
   would take you away from the target. Skip it only when it is blocked before
   or "wall close".
3. Otherwise a move onto new ground rather than ground you have covered, never
   one that was blocked before.
Turning around is also the move when every way ahead is blocked.

Give your reasoning first, then the number.""",
    user_template="""Step {step}.

Planner: {plan_line}
Perceiver, this image: {perceiver_line}
Your last moves: {recent_moves}

Available actions this step:
{action_lines}

Pick one number.""",
    render=render_orchestrated,
)

# --- p17: Phase 2 R19, "searched already this way" defined ------------------------
# R15/R15N failure analysis: a17's coverage note "searched already this way" is
# on every forward move on 40-42% of steps, and the navigator turned around
# against a forward "toward your target" 50 times a round (R11: 3), reading the
# note as "explored, did not lead to the goal". p14-p16 never define it. p17 is
# p16 with the note defined and turning around limited.

P17 = Prompt(
    version="p17",
    system=P16.system.replace(
        """- "new ground" or "been there N times": whether the drone has already been
  where the move ends.""",
        """- "new ground" or "been there N times": whether the drone has already been
  where the move ends.
- "searched already this way": the camera has looked that way before; the drone
  has not flown there. It is not a dead end and no reason to turn around.""").replace(
        """Turning around is also the move when every way ahead is blocked.""",
        """Turn around only when "toward your target" is on marker 0, or when every
forward move is blocked before, stopped short or "wall close"."""),
    user_template=P16.user_template,
    render=render_orchestrated,
)

# --- p18: Phase 2 R23, through the open doorway -----------------------------------
# R19/R19K s02 failure analysis (eval/phase2/R19_searched_defined/s02_failure_analysis.md):
# from the side of the open door nearer closed door B, the straight line to the
# goal clips the door frame on 197 of 202 steps; 36 moves straight through the
# door were not taken near it. The memory a17c tags an open doorway and a closed
# door apart ("doorway (seen now)" was also on 362 of 1188 strips called closed).
# p18 is p17 with those tags defined and the doorway put before "toward".

P18 = Prompt(
    version="p18",
    system=P17.system.replace(
        """- "wall close (seen now)" or "doorway (seen now)": what the perceiver sees that
  way in this image.""",
        """- "wall close (seen now)", "open doorway (seen now)" or "closed door (seen
  now)": what the perceiver sees that way in this image. A closed door is a
  wall.""").replace(
        """2. The move with "toward your target", whether it is a forward move or marker 0.""",
        """2. A move with "open doorway (seen now)" next to the move with "toward your
   target" (the same marker or one beside it): fly straight through the
   opening. Near a door, "toward your target" often cuts across the door frame.
3. The move with "toward your target", whether it is a forward move or marker 0.""").replace(
        """3. Otherwise a move onto new ground""",
        """4. Otherwise a move onto new ground"""),
    user_template=P17.user_template,
    render=render_orchestrated,
)

# --- c01: Phase 2 R16, the goal confirmer ----------------------------------------
# R13 failure analysis: of 26 losses of sight, 21 rested on a hallucinated goal
# report and 4 on a stale frame at a door switch; only 1 was genuine. R11: 10 of
# 14 "goal in view" hand-backs were hallucinated. c01 is a second look, asked
# only when the perceiver reports the goal: the same clean frame and one question
# about the strip it named. A "no" removes the report before anything acts on it.


def render_confirm_question(prompt: Prompt, report: Dict[str, Any]) -> str:
    """The confirmer's question: the strip and range the perceiver reported."""
    return prompt.user_template.format(
        strip=str(report.get("strip", "")).replace("_", " "),
        range=report.get("range") or "distance unknown")


C01 = Prompt(
    version="c01",
    system="""You check one image from the front camera of a small indoor drone.
Another model looked at this image and reported the goal in it. Reports like
that are often wrong. Your job is to check it.

The goal is a glowing red sphere: a round ball, bright red, clearly glowing,
brighter than anything around it. These are not the goal: red or orange marks,
labels, stripes or text on walls, door frames, a red tint or reflection, a
light or bright patch that is not a round red ball, shadows, and anything flat.

Think of the image as five equal vertical strips, from left to right:
far_left, left, centre, right, far_right.

First describe exactly what you see in the strip that was reported and in the
strips next to it: shapes, colours, brightness. Then answer present: yes only
if you clearly see a glowing red sphere in that strip or a strip next to it;
otherwise no.""",
    user_template="""The goal was reported in the {strip} strip, {range}. Is a glowing red sphere there?""",
    render=render_confirm_question,
)

# --- d01: Phase 2 R20, the doorway confirmer ---------------------------------------
# R15/R15N failure analysis: doorway items on the detour menus were at a truly
# open door 4 of 54 and 5 of 52 times; the strategist's doorway picks were real
# once a round, and the closed exit was picked 3 times in a dead end. g05 reports
# an open doorway on about 30% of steps. d01 is a second look, asked when the
# perceiver reports an open doorway: the same clean frame and the strips it
# named. "closed" or "none" replaces the report before the map reads it.


def render_door_question(prompt: Prompt, strips: List[str]) -> str:
    """The doorway confirmer's question: the strips reported open."""
    return prompt.user_template.format(
        strips=", ".join(s.replace("_", " ") for s in strips))


D01 = Prompt(
    version="d01",
    system="""You check one image from the front camera of a small indoor drone.
Another model looked at this image and reported an open doorway in some parts
of it. Reports like that are often wrong. Your job is to check them.

An open doorway is a gap in a wall that the drone could fly through: you can
see floor continuing on the far side of the gap, and the gap is at least as
wide as a door. These are not open doorways: a closed door or a door leaf
filling the gap (that is closed), a plain wall, a corner where two walls meet,
a darker or lighter panel, a shadow, a window, a frame with a wall behind it,
and open floor with no wall around it.

Think of the image as five equal vertical strips, from left to right:
far_left, left, centre, right, far_right.

First describe what you see in each reported strip: walls, gaps, doors, and
whether floor continues beyond any gap. Then answer for each reported strip:
open, closed or none.""",
    user_template="""An open doorway was reported in: {strips}. For each of those strips, is there an open doorway?""",
    render=render_door_question,
)

PROMPTS: Dict[str, Prompt] = {p.version: p for p in (P02, P03, P04, P05, P06, P07, P08, P09,
                                                      P10, P11, P12, P13, P14, G01, G02,
                                                      G03, Q01, Q02, Q03, G04, Q04, G05,
                                                      Q05, G06, P15, P16, C01, Q06, Q07, P17, D01, Q08, P18, Q09, Q10, Q11)}


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
