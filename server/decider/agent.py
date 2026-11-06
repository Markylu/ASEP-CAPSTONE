"""The agent under test, versioned.

Phase 2 changes the agent, never the model: a new prompt, a memory of past
steps, feedback about the last move. Only some of that is prompt text, so the
prompt sha alone cannot say which agent produced a run. An agent version names
the whole thing: one prompt version plus a set of feature flags.

Every run records `agent_version` and `agent_sha` beside the prompt's version
and sha. The rules are the prompt's rules:

- Never edit an existing entry. A new idea is a new version (a01, a02, ...).
- `agent_sha` hashes the prompt's sha and the features, so two versions that
  differ in anything a run depends on cannot share a sha.
- A feature only exists once code reads it. Add the flag here, then read it
  where it acts (vlm.py for what the model is shown, app.py for what is kept
  between steps), keyed on `current().features`.

The decider serves one agent for its lifetime, chosen at start-up:

    python -m server.decider --profile remote --agent a00
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import prompt as prompts


@dataclass(frozen=True)
class Agent:
    version: str
    prompt_version: str
    features: Dict[str, Any] = field(default_factory=dict)
    note: str = ""

    @property
    def prompt(self) -> prompts.Prompt:
        return prompts.get(self.prompt_version)

    @property
    def identifier_prompt(self) -> Optional[prompts.Prompt]:
        """The goal identifier's prompt (a05 on), None for an agent without one."""
        ident = self.features.get("goal_identifier")
        return prompts.get(ident["prompt"]) if ident else None

    def sha(self) -> str:
        blob = self.prompt.sha() + "\x00" + json.dumps(self.features, sort_keys=True)
        # The identifier's wording is part of the agent too. Appended only when
        # there is one, so every earlier agent keeps its sha.
        if self.identifier_prompt is not None:
            blob += "\x00" + self.identifier_prompt.sha()
        # An orchestrated agent (a13 on) is also its subagents' wording and the
        # spatial memory's parameters and notes. Appended only for such an agent,
        # so every earlier agent keeps its sha.
        for sub in self.subagent_prompts:
            blob += "\x00" + sub.version + ":" + sub.sha()
        # The memory's parameters and wording (spatial.SpatialConfig): a13's,
        # then a14's added wording (R10), then a15's (R11), each appended only
        # for an agent that uses it, so every earlier agent keeps its sha.
        if self.spatial_config is not None:
            for segment in self.spatial_config.sha_segments():
                blob += "\x00" + segment
        # a17's stage machine and evaluator thresholds (planner.py), appended
        # only for the staged policy.
        if self.staged:
            blob += "\x00planner_a17:" + planner_a17_sha()
        # a20's verify stage (planner.py), appended only for that policy.
        if self.verifies:
            blob += "\x00planner_a20:" + planner_a20_sha()
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]

    @property
    def staged(self) -> bool:
        return (self.features.get("orchestrator") or {}).get("target_policy") in (
            "staged_search", "staged_verify")

    @property
    def verifies(self) -> bool:
        return (self.features.get("orchestrator") or {}).get("target_policy") == "staged_verify"

    @property
    def spatial_config(self):
        """The orchestrated agent's spatial.SpatialConfig, or None."""
        orch = self.features.get("orchestrator")
        if not orch:
            return None
        from . import spatial
        return spatial.config_for(orch)

    @property
    def uses_a14_wording(self) -> bool:
        cfg = self.spatial_config
        return bool(cfg is not None and cfg.a14_words)

    @property
    def subagent_prompts(self) -> List[prompts.Prompt]:
        """The perceiver's and strategist's prompts (a13 on), in that order, then
        the goal confirmer's (a27 on), the doorway confirmer's (a37 on) and the
        wall reader's (a61 on)."""
        orch = self.features.get("orchestrator") or {}
        return [prompts.get(orch[k])
                for k in ("perceiver", "strategist", "confirmer", "door_confirmer",
                          "wall_reader", "dead_end_confirmer")
                if orch.get(k)]


#: a39: along-the-wall detours (planner.along_wall). In the features, so the sha.
ALONG_WALL_A39: Dict[str, Any] = {
    "max_m": 5.0,
    "min_m": 1.5,
    "step_m": 0.25,
    "look_m": 3.0,
    "look_within_deg": 60.0,
    "min_wall_cells": 3,
    "hand_back_after": 2,
    "hand_back_within_deg": 60.0,
    "words": {
        "item": "along the wall, {side} of the way to the goal, up to {d:.0f} m",
        "followed": "you followed this way {n} time(s) already",
        "fresh": "not followed yet",
        "other_ended": "the {side} way along this wall ends at a wall",
    },
}


#: a46: detours through a confirmed gap in the blocking wall
#: (planner.through_doorways). In the features, so the sha.
THROUGH_A46: Dict[str, Any] = {
    "recent_steps": 20,
    "from_m": 10.0,
    "ray_m": 10.0,
    "merge_m": 1.5,
    "min_rays": 2,
    "min_steps": 2,
    "front_m": 1.5,
    "beyond_m": 2.0,
    "blocked_near_m": 2.0,
    "words": {
        "item": "through the opening in this wall ({n} open-doorway sightings point at it)",
    },
}


#: a50: the other way at the fork, and closed doors in the situation
#: (planner.other_way, planner.closed_door_line). In the features, so the sha.
OTHER_WAY_A50: Dict[str, Any] = {
    "from_m": 6.0,
    "reached_m": 1.5,
    "reach_within_m": 4.0,
    "max_steps": 24,
    "recent_steps": 5,
    "words": {
        "item": "the other way along the wall you met at step {step} (you never went "
                "there), {path:.0f} m back over known floor",
        "closed": "A closed door was seen ahead at step(s) {steps}.",
    },
}


#: a52: a50's other way, listed only in a dead end (planner.dead_end).
OTHER_WAY_A52: Dict[str, Any] = dict(OTHER_WAY_A50, only_dead_end=True,
                                     dead_end_max_along=1)


#: a58: a52's listing, and the closed-door line only beside the other way.
OTHER_WAY_A58: Dict[str, Any] = dict(OTHER_WAY_A52, closed_only_with_item=True)


#: a63 (R30): the route planner (planner.pathfind over spatial.CostMap). In
#: the features, so the sha. docs/research/pathfinder-plan.md §2.
PATHFINDER_A63: Dict[str, Any] = {
    # Cost per metre through a cell nothing has seen, and through a cell where
    # a strip's floor was seen to end farther out (spatial.PARAMS_A17D).
    "unknown_cost": 2.0,
    "suspect_cost": 4.0,
    # The waypoint: the farthest route point within lookahead_m that a straight
    # flight reaches over passable cells, at least waypoint_min_m away.
    "lookahead_m": 4.0,
    "waypoint_min_m": 1.0,
    # The route has not shortened by stall_gain_m over stall_steps decisions
    # (and the last move was not a turn-around or blocked): the two cells ahead
    # of the last move, one cell either side, are stall cells, impassable.
    "stall_steps": 5,
    "stall_gain_m": 1.0,
    # A stop wall (a move stopped short) is this many cells wide either side,
    # never over seen floor. Two: the s03 divider and the s02 door wall are
    # unknown to the map until bumped (probe pathfinder, first run), and each
    # bump then seals about 4 m of it.
    "inflate_stop_walls": 2,
    # The search box: this many cells beyond the known map.
    "search_margin_cells": 12,
    "words": {"path": "the next point on the planned route"},
}

#: a65: a63's planner with local mobility (spatial.CostMap): the cells around
#: the drone are never stall cells or inflated stop walls.
PATHFINDER_A65: Dict[str, Any] = dict(PATHFINDER_A63, local_mobility=True)

#: a67: floor seen only beyond 2.5 m (memory a17g) costs this per metre, a
#: little under unknown ground: a prior, not knowledge.
PATHFINDER_A67: Dict[str, Any] = dict(
    PATHFINDER_A65, far_free_cost=1.6,
    # planner.dead_end_seal: at a confirmed closed door within door_within_m,
    # the corridor the trail came down is sealed lateral_cells either side,
    # back to a point where known ground opens past open_lateral_m on a side.
    dead_end={"door_within_m": 2.0, "lateral_cells": 3, "open_lateral_m": 2.5,
              "max_back_m": 15.0})

#: a68: the dead end also fires on a closed door read from 3-8 m out whose
#: estimated point is within 5 m (a67 s03 dynamic: at the exit wall the door
#: leaf read no_floor with no doorway, so door_within_m never fired).
PATHFINDER_A68: Dict[str, Any] = dict(
    PATHFINDER_A67,
    # lateral_cells 4: a side is a corridor wall when a seen wall lies within
    # four cells of the trail point; axis_m: the trail length the corridor
    # axis is taken over.
    dead_end={"door_within_m": 2.0, "closed_read_within_m": 5.0, "lateral_cells": 4,
              "seal_cells": 8, "open_cells": 4, "axis_m": 8.0, "max_back_m": 15.0})

#: a69: both sides sealed only for a corridor seen walled on each side; a
#: window walled on one side (the s02 hall along the divider) has that side
#: alone sealed, one_side_cells deep.
PATHFINDER_A69: Dict[str, Any] = dict(
    PATHFINDER_A68, dead_end=dict(PATHFINDER_A68["dead_end"], one_side_cells=3))

#: a72 (R31): a65's planner with route commitment (planner.committed_route):
#: the previous step's route is kept unless the drone has left it by more
#: than leave_cells, it is impassable on this step's map, or a fresh route is
#: at least `gain` cheaper. docs/research/r30-analysis-and-proposals.md P2.
PATHFINDER_A72: Dict[str, Any] = dict(
    PATHFINDER_A65, commit={"gain": 0.25, "leave_cells": 2})

#: a73 (R33): a65's planner with the cost map read against Round F's 90 runs.
#: unknown_cost 2 let the route beeline to the goal through unknown divider
#: cells beside the real door (R31 probe: the route crossed the s02 divider
#: through the true gap on 10% of near-side steps); seal_diagonal closes the
#: diagonal gaps in a one-cell wall line; strict_corners stops the route
#: threading them. docs/research/round-f-analysis.md.
PATHFINDER_A73: Dict[str, Any] = dict(
    PATHFINDER_A65, unknown_cost=4.0, suspect_cost=6.0, far_free_cost=3.0,
    seal_diagonal=True, strict_corners=True)

#: a74 (R34): a73's planner on a map where only ground the drone has stood on
#: is known (spatial.CostMap, ray_floor_known). Floor read along a ray, near or
#: far, costs far_free_cost and a wall beside it seals it; a confirmed open
#: doorway's floor is never sealed. Round F: the route crossed walls over floor
#: the perceiver had painted through them. docs/research/round-f-analysis.md §6.
PATHFINDER_A74: Dict[str, Any] = dict(PATHFINDER_A73, ray_floor_known=False, far_free_cost=2.0)

#: a76 (R36): a65's planner with the door approach pose (planner.door_approach).
#: A remembered open doorway seen min_seen times, within range_m of the drone
#: and route_m of the route, takes the waypoint: pre_m out on the doorway's
#: line (the route's direction past it, over tangent_cells either side) until
#: the drone is within align_m of that line, then through_m beyond the doorway.
#: budget_steps per doorway over the run. docs/research/round-f-analysis.md §8.
PATHFINDER_A76: Dict[str, Any] = dict(
    PATHFINDER_A65, door_approach={"min_seen": 2, "range_m": 8.0, "route_m": 2.5,
                                   "pre_m": 2.5, "through_m": 1.7, "align_m": 0.85,
                                   "pre_reached_m": 1.0, "tangent_cells": 2,
                                   "budget_steps": 6})

#: a77 (R37): a76's door approach on doorways a square look has read
#: (Opening.strong, memory a17k), one such read being enough; a doorway known
#: from weak reads only, seen twice, 2-8 m off and within route_m of the route,
#: takes the waypoint for `look.budget_steps` steps so the drone faces it.
#: docs/research/round-f-analysis.md §9, §10.
PATHFINDER_A77: Dict[str, Any] = dict(
    PATHFINDER_A65, door_approach=dict(
        PATHFINDER_A76["door_approach"], min_seen=1, strong_only=True,
        look={"min_seen": 2, "min_m": 2.0, "range_m": 8.0, "route_m": 2.5, "budget_steps": 2}))

#: a70 (R30): what the navigator is told about the route beyond the tags.
#: `route_behind` is added to the planner line when "toward your target" sits
#: on the turn-around: R30's shakedown (a63, a67, a68 s03 dynamic) lost 18
#: lobby steps each to the navigator reading "head for the goal" as "the goal
#: is ahead" and declining marker 0 ("turn around is only for when the target
#: is behind you"). `critic_route` is the critic's reason when the pick carries
#: no "toward your target" while an open move does; the navigator is asked once
#: more and may keep its pick (a13's critic machinery).
NAVIGATOR_A70: Dict[str, str] = {
    "route_behind": ("The next point on your route is behind you: the turn around is the "
                     "move toward it."),
    "critic_route": "the planned route goes by [{j}] (toward your target), not by [{i}]",
}

#: a78 (R38): a65's planner with the dead-end latch (planner.dead_end_latch).
#: Fires when the dead-end confirmer said yes on this step and on yes_reads of
#: its last of_reads answers, none older than recent_steps (it is asked only on
#: a closed-door read: in Round F's shut tine two such reads lay up to 12 steps
#: apart). The corridor is the longest straight run of trail ending within
#: look_back_steps before the first of those answers whose lane the drone is
#: still in (segments within off_axis_deg of its axis, found from the last
#: axis_m; at least min_run_m, at most max_back_m), from mouth_m down the run
#: to ahead_m beyond the farthest the drone has been,
#: seal_cells either side; a lane lane_m either side of the axis (the tine is
#: 3 m wide) stays open back to the mouth until the drone is out. seal_cells 8
#: is a68's measured depth (a band four deep was skirted through the solid).
#: eval/phase2/R38_dead_end_latch/README.md.
PATHFINDER_A78: Dict[str, Any] = dict(
    PATHFINDER_A65, dead_end_latch={"yes_reads": 2, "of_reads": 3, "recent_steps": 15,
                                    "look_back_steps": 12,
                                    "axis_m": 3.4, "off_axis_deg": 30.0, "min_run_m": 3.0,
                                    "max_back_m": 15.0, "mouth_m": 2.0, "ahead_m": 2.0,
                                    "lane_m": 1.5, "seal_cells": 8})

#: a79 (R39): a78's latch with the trail as its trigger (planner.confined_run)
#: and no confirmer. The drone has not left the lane of a straight run of
#: min_run_m or more that it turned into (half_m either side of its axis,
#: back_m behind its start), has got no more than advance_m farther down it in
#: dwell_steps, has read a closed door in the centre three strips looking along
#: it (within facing_deg) on `reads` steps, and has never stood beside the lane
#: within beside_m. eval/phase2/R39_confined_latch/README.md.
PATHFINDER_A79: Dict[str, Any] = dict(
    PATHFINDER_A65, dead_end_latch=dict(
        PATHFINDER_A78["dead_end_latch"], min_run_m=5.0,
        confined={"half_m": 1.5, "back_m": 1.0, "facing_deg": 70.0, "reads": 2,
                  "dwell_steps": 5, "advance_m": 1.0, "beside_m": 4.0}))

#: a80 (R40): the wall survey (planner.wall_survey). The approach axis is the
#: bearing from the spawn to the goal. A closed door read in the centre strip
#: while the drone heads within goal_deg of the axis, run_m or more along it
#: and never yet more than line_m off the direct line, starts it. Stations lie
#: stations_m to the side of the approach (the side of a remembered open
#: doorway at least side_min_m off it first, else the left; then the other
#: side), back_m behind where it started until the wall has been met, then
#: standoff_m back from the wall; a station is reached within reach_m and
#: given up after stall_steps without coming half a metre nearer. There the
#: drone turns to the wall and flies at it (a waypoint face_m ahead along the
#: axis), each frame within square_deg of the axis a square look, until it
#: meets the wall (wall_m ahead of where it is stopped) or look_steps pass. An
#: open doorway read on a strip whose ray is within open_deg of the axis is
#: kept (the last rays_kept); the doorway's line is where those rays cross
#: (least squares, determinant over cross_det), or meet a wall whose range is
#: known, or reach_ray_m out along the newest; the waypoint is carrot_m ahead
#: of the drone on that line until through_steps pass with no such read, or
#: the drone is through_m beyond a known wall. 7 m: what one square look's
#: 87-degree frame covers of a wall 4 m off.
#: eval/phase2/R40_wall_survey/README.md.
SURVEY_A80: Dict[str, Any] = {
    "goal_deg": 35.0, "run_m": 3.0, "line_m": 2.5, "stations_m": 7.0, "side_min_m": 2.0,
    "back_m": 0.0, "standoff_m": 5.0, "wall_m": 1.0, "reach_m": 1.7, "stall_steps": 6,
    "face_m": 6.0, "square_deg": 25.0, "look_steps": 12, "open_deg": 40.0,
    "reach_ray_m": 5.0, "rays_kept": 6, "cross_det": 0.05, "carrot_m": 3.0,
    "through_m": 3.0, "through_steps": 5, "budget_steps": 44}

#: a80: a65's planner with the wall survey.
PATHFINDER_A80: Dict[str, Any] = dict(PATHFINDER_A65, survey=SURVEY_A80)

#: a81 (R41): a80's survey after its shakedown (R40 README, Outcome). A
#: doorway read across several strips lies at their middle (ray_mean); with
#: the wall's range unknown the newest ray is taken no nearer than a metre
#: beyond the farthest the drone has been toward the wall (been_floor), 4 m
#: out otherwise, and rays must differ by about 18 degrees to be crossed
#: (cross_det 0.1); a move stopped short in the through phase with no doorway
#: read gives the route the waypoint for check_steps, and check_m farther on
#: the drone is through (a jamb clipped), else it was a phantom; flying at the
#: wall in the look phase, every strip blocked is the wall (look_nose_on).
SURVEY_A81: Dict[str, Any] = dict(
    SURVEY_A80, ray_mean=True, been_floor=True, reach_ray_m=4.0, cross_det=0.1,
    check_steps=3, check_m=2.0, look_nose_on=True)
PATHFINDER_A81: Dict[str, Any] = dict(PATHFINDER_A65, survey=SURVEY_A81)

#: a78: a70's route-behind sentence, said only inside a latched corridor and
#: with the reason before it. No critic. R30 shakedown: a63, a67 and a68
#: declined marker 0 on about half its "toward your target" offers, and a68
#: took 16 steps from its seal to the crossbar, 9 m away.
NAVIGATOR_A78: Dict[str, str] = {
    "route_behind": NAVIGATOR_A70["route_behind"],
    "dead_end": "This corridor ends at a closed door: it is a dead end.",
}


AGENTS: Dict[str, Agent] = {a.version: a for a in (
    Agent("a00", "p02", {}, "Phase 1 agent: p02, one frame per step, no memory."),
    Agent("a01", "p03", {}, "No goal hint: p03 drops the goal's distance and bearing "
          "and each action's angle and distance. The goal is found from the image alone."),
    Agent("a02", "p04", {"memory": {"kind": "text", "scope": "full_run"}},
          "Text memory: a01 plus every earlier step of the run in the prompt, oldest "
          "first: the marker picked and the reason given, verbatim."),
    Agent("a03", "p05", {"memory": {"kind": "log", "scope": "full_run",
                                    "fields": ["move", "goal"]}},
          "Memory log: a01 plus a log written by code of every earlier step's move "
          "and reported goal, with no marker numbers or reasons; the reply reports "
          "where the goal is before it reasons."),
    Agent("a04", "p06", {"memory": {"kind": "log", "scope": "full_run",
                                    "fields": ["move", "goal"]},
                         "goal_order": "after_reason"},
          "a03 with the goal report moved after the reason, and the goal described as "
          "a glowing red sphere (no beam). R3: the report answered first stopped the "
          "model seeing the goal."),
    Agent("a05", "p07", {"memory": {"kind": "log", "scope": "full_run",
                                    "fields": ["move", "goal"],
                                    "goal_log": "last_sighting"},
                         "goal_identifier": {"prompt": "g01"}},
          "Goal identifier: a second call per step (g01) with the frame and no log "
          "reports where the goal is. The navigator (p07) gets that answer and a log of "
          "moves with only the last sighting, its age and the turn since; it no longer "
          "reports the goal. R4: the log carried stale sightings forward."),
    Agent("a06", "p07", {"memory": {"kind": "log", "scope": "full_run",
                                    "fields": ["move", "goal"],
                                    "goal_log": "last_sighting"},
                         "goal_identifier": {"prompt": "g02", "frame": "clean"}},
          "a05 with the identifier shown the camera frame without annotations (g02). "
          "R5 probe: g01 took the pink '0 TURN AROUND' marker for the goal."),
    Agent("a07", "p08", {"memory": {"kind": "log", "scope": "full_run",
                                    "fields": ["move", "goal", "pose"],
                                    "goal_log": "last_sighting"},
                         "goal_identifier": {"prompt": "g02", "frame": "clean"}},
          "a06 with the drone's ground-truth position and heading after every move, and "
          "how far it moved, in the log (p08). R5: the log recorded commands, not outcomes, "
          "and the drone turned around in place for up to 36 steps (spin_failure)."),
    Agent("a08", "p09", {"memory": {"kind": "log", "scope": "full_run",
                                    "fields": ["move", "goal", "pose"],
                                    "goal_log": "none"},
                         "goal_identifier": {"prompt": "g02", "frame": "clean"}},
          "a07 without the last-sighting line (p09); the identifier's answer for the "
          "current image stays. R5: the sighting line drove 'goal is behind, turn around'."),
    Agent("a09", "p10", {"memory": {"kind": "log", "scope": "full_run",
                                    "fields": ["move", "goal", "pose"],
                                    "goal_log": "last_sighting",
                                    "pose_compare": True},
                         "goal_identifier": {"prompt": "g02", "frame": "clean"}},
          "a07 with the log comparing each move to the drone's earlier positions "
          "(blocked, stopped short, back at step N) (p10). R6: "
          "143 collisions, 65% of reasons after a blocked move claimed progress. "
          "Probed, not flown: it turned around on 13/25 lost-goal frames (a08: 4/25)."),
    Agent("a10", "p11", {"memory": {"kind": "log", "scope": "full_run",
                                    "fields": ["move", "goal", "pose"],
                                    "goal_log": "none",
                                    "pose_compare": True},
                         "goal_identifier": {"prompt": "g02", "frame": "clean"}},
          "a08 (no sighting line) with the log comparing each move to the drone's earlier "
          "positions (blocked, stopped short, back at step N) (p11). The a09 probe: the "
          "sighting line brings back the turn-around loop on lost-goal frames."),
    Agent("a11", "p12", {"memory": {"kind": "log", "scope": "full_run",
                                    "fields": ["move", "goal", "pose"],
                                    "goal_log": "none",
                                    "pose_compare": True},
                         "goal_identifier": {"prompt": "g02", "frame": "clean"}},
          "a10 with heading as a compass word ('facing south-west') instead of degrees "
          "(p12). R6 and R7: heading arithmetic in reasons, and turn-arounds on a goal in "
          "view to the side."),
    Agent("a12", "p13", {"memory": {"kind": "log", "scope": "full_run",
                                    "fields": ["move", "goal", "pose"],
                                    "goal_log": "none",
                                    "pose_compare": True},
                         "goal_identifier": {"prompt": "g02", "frame": "clean"}},
          "No-op control: a10 plus one sentence that adds nothing (p13). R8N measures how "
          "far a content-free prompt edit moves a round (R7: 5 of 18 first picks moved)."),
    Agent("a13", "p14", {"orchestrator": {"perceiver": "g03", "strategist": "q01",
                                          "critic": "retry", "frame": "clean",
                                          "spatial": "server/decider/spatial.py"}},
          "R9 bundle: one step is several calls with one job each, and code keeps a map. "
          "A perceiver (g03) reports goal strip, open floor and doorways on the clean frame; "
          "code builds the map from pose and those reports; a strategist (q01) picks a "
          "target from a list code builds; the navigator (p14) sees notes from the map "
          "against each action and no coordinates or degrees; a critic asks once more "
          "when the pick was blocked from here, is a third turn-around, or loops. "
          "R1-R7: the model cannot compare positions or headings itself."),
    Agent("a14", "p14", {"orchestrator": {"perceiver": "g03", "strategist": "q02",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "spatial": "server/decider/spatial.py"}},
          "R10 bundle on a13: the strategist (q02) is told the goal's true position, which "
          "no other part sees (the navigator only gets 'toward your target'); turn-around "
          "is not offered right after a turn-around while a move ahead is open; no critic. "
          "R9: four spins of alternating turn-arounds with the way ahead open, the critic "
          "changed 0 of 19 picks, and q01 chose the goal on 18 of 200 calls out of view."),
    Agent("a15", "p14", {"orchestrator": {"perceiver": "g03", "strategist": "q03",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_default_llm_detour",
                                          "memory": "a15",
                                          "spatial": "server/decider/spatial.py"}},
          "R11 bundle on a14: code keeps the goal as the standing target (planner.py) and "
          "asks a detour strategist (q03) only when the way toward it is walled, a move "
          "toward it was blocked, or six steps brought it no nearer; q03 sees each detour "
          "with how much nearer the goal it lies, and not whether the goal is in the image. "
          "Memory a15: a stopped-short move is also recorded where it ended and warns the "
          "next fan action out; 'toward your target' never on a walled or blocked move; a "
          "doorway is listed from its second sighting and dropped after 10 steps unseen. "
          "R10: q02 chose the goal on 70 of 229 calls, 36 of 37 repeat collisions had no "
          "note, 'toward' sat on a walled move 36 times."),
    Agent("a16", "p14", {"orchestrator": {"perceiver": "g03", "strategist": "q03",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_default_llm_detour",
                                          "memory": "a16",
                                          "spatial": "server/decider/spatial.py"}},
          "R11 bundle on a14, after a15's probe failed: a15 with memory a16. A block "
          "warns only its own heading after a move that did not get going, and the next "
          "fan action out after one that stopped short; q03's unexplored ground is "
          "offered at the edge's point nearest the goal. a15's probe: a 45-degree block "
          "window noted every forward move on 28 of R10's steps and the navigator took "
          "the blocked one; 52 of 88 detour menus held nothing 3 m nearer the goal."),
    Agent("a17", "p14", {"orchestrator": {"perceiver": "g04", "strategist": "q04",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "none",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "staged_search",
                                          "memory": "a17",
                                          "spatial": "server/decider/spatial.py"}},
          "R12 bundle, no goal truth anywhere (operator, 2026-10-28): code runs two "
          "stages, explore until the goal is seen and then head for where it was seen "
          "(planner.staged). A coverage map marks ground each look's cone searched; a "
          "search strategist (q04) picks reachable edges of unsearched ground, doorways "
          "or a way back; an evaluator scores each step by ground newly searched and "
          "progress, blacklists a target after four unproductive steps, and drops a "
          "sighting a later look disproves. Perceiver g04 says where far floor ends and "
          "whether a doorway is open. Memory a17: stop walls, reachable targets, doors "
          "passed only when crossed. R11: 34 of 37 detour targets lay behind or inside "
          "a wall; g03 sees the goal at any range in line of sight (612 of 612)."),
    Agent("a18", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q04",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "none",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "staged_search",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "R12 after a17's live probe failed: a17 with perceiver g05, which says where "
          "each strip's floor ends in the image (no floor, bottom quarter, lower, just "
          "below the middle) instead of metres; code maps that to a reach. The camera is "
          "level at 1.75 m, so no floor in a strip means an obstacle under 1.84 m. g04 read "
          "69% of R11's strips open_very_far, 53% of walls under 1 m among them."),
    Agent("a19", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q04",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "none",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "staged_search",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "blocked_near",
                                                        "lower": "open_near",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "R12 after a18's live probe failed narrowly (86.8% of searched cells in sight, "
          "16.2% of walls under 1 m read open): a18 with each g05 floor end mapped one "
          "class nearer, so a misread wall cuts the cone short instead of running it "
          "through. On a18's R11 answers this map gave 90.0% and 6.8% with a third fewer "
          "cells searched; fitted there, so it is gated on R11C's frames."),
    Agent("a20", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q04",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "none",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "staged_verify",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "blocked_near",
                                                        "lower": "open_near",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "R13 (operator, 2026-10-28): a19 with a third stage. The first look without "
          "the goal, unless a detour stands, goes to verify: back to where it was last "
          "seen from, facing the way it was seen, and look again. Seen: goal, the old "
          "sighting dropped if the new one disagrees. Not seen there, no path back or 8 "
          "steps: the sighting is dropped and the stage is explore. a17's cone and "
          "'faces it' disproof rules are not used. R12: in dynamic the goal was reported "
          "at step 0 in 5 of 6 runs, then dropped or chased to a point 10 m out."),
    Agent("a21", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q05",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "strategist",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "staged_verify",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "blocked_near",
                                                        "lower": "open_near",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "R13G, flown beside R13: a20 with the goal's true position in the "
          "strategist's text alone (q05): where the goal is, and each reachable place "
          "worded with how much nearer it lies. The stages, map and navigator see no "
          "goal truth. R11: the menu's goal-side items lay behind walls; a17's menu "
          "offers reachable places only."),
    Agent("a22", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q04",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "none",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "staged_verify",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "verify_budget": {"min_steps": 8,
                                                            "extra_steps": 4,
                                                            "steps_per_m": 0.8},
                                          "spatial": "server/decider/spatial.py"}},
          "R14: a20 with a18's floor map (g05's 'bottom' is open_near, not a wall) and a "
          "verify step limit that grows with the distance back (4 + 0.8 per metre, at "
          "least 8). R12/R13 records against site geometry: of 1574 strips g05 read "
          "'bottom', 3% were truly blocked within 1.9 m (62% open past 8 m), yet a19's map "
          "walled them 0.75 m out; R13 shakedown: three verify timeouts were turn-around "
          "ping-pong on that 'wall close', three were trips back of 5-9 m."),
    Agent("a23", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q05",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "strategist",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "staged_verify",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "verify_budget": {"min_steps": 8,
                                                            "extra_steps": 4,
                                                            "steps_per_m": 0.8},
                                          "spatial": "server/decider/spatial.py"}},
          "R14G, flown beside R14: a21 (goal truth in the strategist's text) with a22's "
          "floor map and verify step limit."),
    Agent("a24", "p14", {"orchestrator": {"perceiver": "g06", "strategist": "q04",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "none",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "staged_verify",
                                          "memory": "a17",
                                          "floor_map": {"wall_at_bottom": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far",
                                                        "runs_on": "open_far"},
                                          "verify_budget": {"min_steps": 8,
                                                            "extra_steps": 4,
                                                            "steps_per_m": 0.8},
                                          "spatial": "server/decider/spatial.py"}},
          "a22 with perceiver g06: g05 with no_floor renamed wall_at_bottom, a runs_on "
          "answer for floor whose end is out of sight, and the bottom edge of each strip "
          "looked at first. R12: 157 of g05's 477 no_floor strips were clear past 8 m, "
          "with reasons saying the floor was visible across the image."),
    Agent("a25", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q03",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "R11's routing with R12's map: code keeps the goal's true position as the "
          "target and asks the detour strategist (q03) only when the way is walled, "
          "blocked or six steps gained nothing (a16, R11 11/18), but q03 chooses from "
          "a17's menu (reachable edges of unsearched ground, reachable doorways, a way "
          "back) on a17's memory, with g05 read as a22. R11's failure analysis: 34 of 37 "
          "detour picks lay behind or inside a wall, 51% of steps stood on them."),
    Agent("a26", "p16", {"orchestrator": {"perceiver": "g05", "strategist": "q03",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a25 with navigator prompt p16: p14 with the notes ranked (goal, then 'toward "
          "your target' including turning around, then new ground). Probe on R11's steps "
          "(eval/r15_nav_probe.py): 'toward' on marker 0 followed 35% (p14 21%)."),
    Agent("a27", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q04",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "none",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "staged_verify",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "verify_budget": {"min_steps": 8,
                                                            "extra_steps": 4,
                                                            "steps_per_m": 0.8,
                                                            "check_within_m": 2.6},
                                          "spatial": "server/decider/spatial.py"}},
          "a22 with a goal confirmer (c01): when g05 reports the goal, a second call on the "
          "same clean frame checks that strip, and a 'no' removes the report before the map "
          "and stages read it; and a verify check look counted within 2.6 m of the vantage. "
          "R13 failure analysis: 21 of 26 losses of sight rested on hallucinated reports; 5 "
          "of 8 timeouts reached the vantage but could not face the bearing inside 1.5 m."),
    Agent("a28", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q03",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a25 (known goal, reachable detours) with the goal confirmer c01: a goal report "
          "the confirmer refuses does not hand a detour back ('goal in view') or put a goal "
          "note on a move. R11: 10 of 14 'goal in view' hand-backs were hallucinated."),
    Agent("a29", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q06",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a25 (known goal, reachable detours) with detour strategist q06: a doorway is the "
          "way round a wall even when farther from the goal, more unexplored ground before "
          "nearer, the way back in a dead end. R11: doorway picked on 1 of 19 menus with one; "
          "backtrack never chosen."),
    Agent("a30", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q06",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a28 (known goal, reachable detours, goal confirmer c01) with detour strategist "
          "q06: the two known-goal changes together."),
    Agent("a31", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q07",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a25 (known goal, reachable detours) with detour strategist q07: q06 (doorway "
          "first, more ground before nearer, the way back in a dead end) with 'nearer the goal' "
          "explained as straight-line only. R11 replay: doorway picked on 10 of 19 menus with "
          "one (q03 1, q06 2)."),
    Agent("a32", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q07",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a28 (known goal, reachable detours, goal confirmer c01) with detour strategist "
          "q07: the two known-goal changes together."),
    Agent("a33", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q07",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a31 (known goal, reachable detours, q07) with a detour handed back when 4 moves "
          "bring it under 0.5 m nearer, and detours handed back stalled or too long left off "
          "later menus. R15 s01 final: 12 steps circling a frontier 3-4 m abeam."),
    Agent("a34", "p14", {"orchestrator": {"perceiver": "g05", "strategist": "q07",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a32 (known goal, reachable detours, q07, goal confirmer c01) with a33's stalled "
          "detour hand-back."),
    Agent("a35", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q03",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a26 (known goal, reachable detours, p16) with navigator prompt p17 ('searched "
          "already this way' defined; turn around only on marker-0 toward or every forward "
          "move blocked) and a33's stalled-detour hand-back. R15/R15N: 50 turn-arounds a "
          "round against a forward 'toward' (R11 3)."),
    Agent("a36", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q03",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a35 with the goal confirmer c01."),
    Agent("a37", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q03",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a35 (known goal, reachable detours, p17, stalled-detour hand-back) with the "
          "doorway confirmer d01: an open doorway the perceiver reports is checked on the "
          "same frame before the map lists it. R15/R15N: 4 of 54 menu doorways real."),
    Agent("a38", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q03",
                                          "door_confirmer": "d01",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a37 with the goal confirmer c01."),
    Agent("a39", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q08",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a35 with along-the-wall detours: on a walled or blocked call code lists the two "
          "ways along the wall between the drone and the goal, and strategist q08 follows "
          "one to its end before the other. R15/R15N mode B (no along-wall search) primary "
          "in 7 of 17 failures."),
    Agent("a40", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q08",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a37 (a35 + doorway confirmer d01) with a39's along-the-wall detours and q08."),
    Agent("a41", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q08",
                                          "door_confirmer": "d01",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "memory": "a17",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a38 (a37 + goal confirmer c01) with a39's along-the-wall detours and q08."),
    Agent("a42", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q08",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a40 on memory a17b: no wall written at the end of an open_near (g05 'bottom') "
          "strip, so the move ahead is not 'searched already' 2.5 m out. s03 R15-R17K: "
          "first turn-arounds all came on that note (eval/phase2/R17_doorway_first/"
          "s03_analysis.md)."),
    Agent("a43", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q08",
                                          "door_confirmer": "d01",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a41 on memory a17b (as a42)."),
    Agent("a44", "p18", {"orchestrator": {"perceiver": "g05", "strategist": "q08",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "memory": "a17c",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a42 with navigator p18 and memory a17c: an open doorway and a closed door "
          "tagged apart, and an open doorway next to 'toward your target' taken straight "
          "through. R19/R19K s02 failure analysis mode K: the goal line clips the door "
          "frame."),
    Agent("a45", "p18", {"orchestrator": {"perceiver": "g05", "strategist": "q08",
                                          "door_confirmer": "d01",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "memory": "a17c",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a43 with p18 and a17c (as a44)."),
    Agent("a46", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q09",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "through": THROUGH_A46,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a42 with detours through a confirmed gap in the blocking wall: code places "
          "the gap where open-doorway sighting rays meet that wall and offers a point "
          "square in front of it, then one beyond; strategist q09 takes it first. R19/R19K "
          "s02 failure analysis mode K."),
    Agent("a47", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q09",
                                          "door_confirmer": "d01",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "through": THROUGH_A46,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a43 with a46's through-the-doorway detours and q09."),
    Agent("a48", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q03",
                                          "door_confirmer": "d01",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a38 (R20K, 12/18) on memory a17b: no wall written at the end of an open_near "
          "strip (R22's change without R21's along-the-wall detours)."),
    Agent("a49", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q03",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a37 (R20) on memory a17b (as a48)."),
    Agent("a50", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q10",
                                          "door_confirmer": "d01",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "other_way": OTHER_WAY_A50,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a43 with the other way at the fork (planner.other_way: the newest "
          "along-the-wall end offered at an earlier call 6 m or more away that the drone "
          "never reached), closed doors seen in the last 5 steps in the situation, and "
          "strategist q10 (q08 + a dead-end rule). s03 tines analysis."),
    Agent("a51", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q10",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "other_way": OTHER_WAY_A50,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a42 with a50's other way at the fork, closed-door line and q10."),
    Agent("a52", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q11",
                                          "door_confirmer": "d01",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "other_way": OTHER_WAY_A52,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a50 with the other way listed only in a dead end (a closed door seen in the "
          "last 5 steps, at most one along-the-wall item) and strategist q11, which takes "
          "it when listed. R26 probe: q10 took it off the dead end too."),
    Agent("a53", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q11",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "other_way": OTHER_WAY_A52,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a51 with a52's dead-end listing and q11."),
    Agent("a54", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q12",
                                          "door_confirmer": "d01",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "other_way": OTHER_WAY_A52,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a52 with strategist q12: the dead-end rule before rules 1-4. R26 q11 probe: "
          "the one way left along the wall taken on 3 of 10 dead-end calls."),
    Agent("a55", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q12",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "other_way": OTHER_WAY_A52,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a53 with q12 (as a54)."),
    Agent("a56", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q13",
                                          "door_confirmer": "d01",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "other_way": OTHER_WAY_A52,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a52 with strategist q13: the dead-end rule before rules 1-4, nothing else "
          "(q12's extra sentence sent the divider calls back)."),
    Agent("a57", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q13",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "other_way": OTHER_WAY_A52,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a53 with q13 (as a56)."),
    Agent("a58", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q13",
                                          "door_confirmer": "d01",
                                          "confirmer": "c01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "other_way": OTHER_WAY_A58,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a56 with the closed-door line only when the other way is listed. R26 q13 probe: "
          "with the line on ordinary divider calls, q13 read them as dead ends (63 ways back)."),
    Agent("a59", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q13",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "along_wall": ALONG_WALL_A39,
                                          "other_way": OTHER_WAY_A58,
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a57 with a58's closed-door line (as a58)."),
    Agent("a60", "p17", {"orchestrator": {"perceiver": "g07", "perceiver_mirror": "image_right",
                                          "strategist": "q03",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a49 (R25D, 14/18) with perceiver g07 (g05 without describe-first) read twice, on "
          "the clean frame and on it mirrored; far_left and left from the mirrored read "
          "(probes F1, C2)."),
    Agent("a61", "p17", {"orchestrator": {"perceiver": "g05", "wall_reader": "w01",
                                          "strategist": "q03",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a49 (R25D, 14/18) with a wall reader (w01, g05's floor job alone) asked beside "
          "g05; each strip's floor from w01, doorways and the goal from g05 "
          "(what-we-learned, idea 1)."),
    Agent("a62", "p17", {"orchestrator": {"perceiver": "g05", "strategist": "q03",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "goal_reach_detour",
                                          "detour_stall": {"steps": 4, "gain_m": 0.5},
                                          "memory": "a17b",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "reason_cap": 2000,
                                          "spatial": "server/decider/spatial.py"}},
          "a49 (R25D, 14/18) with the perceiver's describe-first reason capped at 2,000 "
          "characters (schema.REASON_MAX_CHARS), so the 2% of calls whose reason loops past "
          "the token budget still return their strips (probe LD recall). Not flown yet."),
    Agent("a63", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A63,
                                          "memory": "a17d",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a49 (R25D, 14/18) with a code route planner (planner.pathfind: A* over the "
          "memory's cost map, spatial.CostMap) in place of the goal-way test and the q03 "
          "detour strategist; memory a17d (a17b plus walls at confirmed closed doors and "
          "suspect cells at far floor ends). The navigator p17 and its tags are a49's. "
          "docs/research/pathfinder-plan.md."),
    Agent("a64", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A63,
                                          "navigator": "code",
                                          "memory": "a17d",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a63 with code taking the action the map tags \"toward your target\" "
          "(orchestrator.code_pick), no navigator call. A diagnostic for the shakedown "
          "only (the ceiling of perceiver plus planner); its rung \"code\" fails the "
          "validity check, so it can never be a round."),
    Agent("a65", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A65,
                                          "memory": "a17e",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a63 after the R30 shakedown's s03 dynamic run: memory a17e (a17d plus near "
          "walls from the two side strips, 2.5 m at a bottom floor end) so a corridor's "
          "side walls are on the map as the drone flies it, and local mobility (stall "
          "cells and inflated stop walls never within a cell of the drone). "
          "eval/phase2/R30_pathfinder/README.md, Probe gate 2."),
    Agent("a66", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A65,
                                          "memory": "a17f",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a65 with memory a17f: a nose-on wall run and a confirmed closed door are firm "
          "walls, erased only by a visit. R30 shakedown, a63 s02c dynamic and a64 s03 "
          "dynamic: the walls seen nose-on at the divider and the exit wall were popped by "
          "the next grazing look along them, and the drone oscillated at the wall."),
    Agent("a67", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A67,
                                          "memory": "a17g",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a66 with memory a17g: floor seen only beyond 2.5 m is weak for the route (costs "
          "1.6, sealable); floor within 2.5 m, visits and a confirmed open door's rays are "
          "known ground. R30 shakedown, a66 s03 dynamic s21-34: the route ran through "
          "floor the perceiver had read 4 m deep inside the solid beyond the tine's outer "
          "wall, and the drone bumped it cell by cell."),
    Agent("a68", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A68,
                                          "memory": "a17g",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a67 with the dead end also fired by a closed door read from 3-8 m out whose "
          "point lies within 5 m. a67's s03 dynamic shakedown run: at the exit wall the "
          "door leaf read no_floor with no doorway on every nose-on look, so no door wall "
          "was ever written and the seal never fired; the door read closed at s46 and s51 "
          "from 4.5 m out."),
    Agent("a69", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A69,
                                          "memory": "a17g",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a68 with the dead-end seal on both sides only for a corridor seen walled on "
          "each side; a window walled on one side has that side alone sealed, three deep. "
          "a68's shakedown: s03 dynamic left the shut tine and reached the crossbar (the "
          "seal worked in flight), but s02a and s02vc dynamic were boxed in the hall by "
          "the both-sides seal (route on 53% of steps, 32 m from the goal)."),
    Agent("a70", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "route", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A65,
                                          "memory": "a17f",
                                          "navigator_notes": NAVIGATOR_A70,
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a66 with the navigator told when the route's next point is behind it (one "
          "sentence after the planner line while 'toward your target' is on the "
          "turn-around) and a critic that asks once more when the pick carries no 'toward "
          "your target' while an open move does (the second answer stands, as a13). "
          "R30 shakedown: a63, a67 and a68 s03 dynamic each spent 18 steps in the lobby "
          "declining marker 0 while it carried 'toward your target', reasoning that "
          "'head for the goal' meant the goal was ahead; a64 (code picks) left in 4."),
    Agent("a71", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "route", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A68,
                                          "memory": "a17g",
                                          "navigator_notes": NAVIGATOR_A70,
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a70's navigator on a68's planner (memory a17g, the dead-end seal). a70's "
          "shakedown: the navigator took every 'toward your target' on marker 0 (46/46) "
          "and left the lobby in 11 steps, and s03 dynamic then oscillated 30 steps in the "
          "shut tine as the route alternated between the shut door and the way out; a68's "
          "seal had taken the drone out of that tine in flight."),
    Agent("a72", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A72,
                                          "memory": "a17h",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a66 with memory a17h (one look is soft: an open doorway's floor through the "
          "gap is a soft claim until seen open from two poses 1 m apart; a nose-on wall "
          "run or a closed-door wall is firm only after a second read from 1 m away; two "
          "strong closes kill an opening) and route commitment (the previous route is "
          "kept unless left, impassable or a fresh one is 25% cheaper). R30 and its "
          "shakedown: a70/a71 lost s02 runs to one confirmed phantom doorway the route "
          "trusted, a71 lost s03 to one nose-on no_floor read down the stem made firm, "
          "and s03 dynamic oscillated at the shut door as single cells sealed."),
    Agent("a73", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A73,
                                          "memory": "a17i",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a66 with the wall-turn rule (memory a17i: the step after a turn-around taken "
          "facing a wall, 'toward your target' goes to the open move nearest the target "
          "instead of the turn-around, so the turn rule hides it; a move onto ground the "
          "drone has stood on is open whatever the look says; memory a17g's weak far floor) "
          "and a73's cost map (unknown cells cost 4 not 2, far floor 3, suspects 6; walls "
          "seal their diagonal neighbours; no diagonal past an impassable cell). Round F, "
          "64/90: 373 nose-on frames and "
          "61 back-to-back turn-arounds, 13-21 wasted steps per s03 dynamic run; 10 of 20 "
          "s02 losses stood within 2 m of the open door while the route crossed the "
          "divider beside it. docs/research/round-f-analysis.md."),
    Agent("a74", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A74,
                                          "memory": "a17i",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a73 on a cost map where only ground the drone has stood on is known: floor "
          "read along a ray costs 2 per metre and a wall beside it seals it; a confirmed "
          "open doorway's floor is never sealed. Round F replayed under a73: 1106 of 1634 "
          "s02 route crossings of the divider and 205 of 223 s03 shut-tine exits ran over "
          "floor the perceiver had painted through a wall. "
          "docs/research/round-f-analysis.md §6."),
    Agent("a75", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A65,
                                          "memory": "a17j",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a66 with the wall-turn rule alone (memory a17j = a17f + wall_turn): the step "
          "after a turn-around taken facing a wall, 'toward your target' goes to the open "
          "move nearest the target instead of the turn-around, so the turn rule hides it, "
          "and a move onto ground the drone has stood on carries no wall or block note. "
          "a66's planner and cost map unchanged. R33's shakedown of a73: 10 wall turns, no "
          "repeat turn, s02c dynamic solved at 30; s03 dynamic lost to a73's cost map "
          "(seal_diagonal closed the stem)."),
    Agent("a76", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A76,
                                          "memory": "a17f",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a66 with the door approach pose: a remembered open doorway seen twice, within "
          "8 m of the drone and 2.5 m of the route, takes the waypoint. Off the doorway's "
          "line (the route's direction past it) the waypoint is 2.5 m out on that line; "
          "within one cell of the line it is 1.7 m beyond the doorway. Six steps per "
          "doorway over the run. Round F, R32P and R35: within 4 m of the true open door "
          "the drone stood more than 30 degrees off its line on 309 of 381 steps and the "
          "waypoint pointed at the door on 102. docs/research/round-f-analysis.md §8."),
    Agent("a77", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A77,
                                          "memory": "a17k",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a66 with doorway reads trusted by the look they came from (memory a17k). A "
          "strong read sits in the centre strip with the floor ending level either side; "
          "only a strong read paints floor through the gap, and only a doorway with a "
          "strong read gets a76's approach pose. A doorway known from weak reads alone "
          "takes the waypoint for two steps so the drone faces it. Probe door_read: at "
          "2-9 m a square look read the open door on 157 of 158 looks and a wall strip as "
          "open on 1 of 366; beyond 60 degrees, 112 of 231 and 76 of 393. "
          "docs/research/round-f-analysis.md §9, §10."),
    Agent("a78", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "dead_end_confirmer": "e01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A78,
                                          "memory": "a17f",
                                          "navigator_notes": NAVIGATOR_A78,
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a66 with a dead-end latch. On a closed-door read in the centre three strips a "
          "confirmer (e01) is asked whether the drone is in a corridor that ends at that "
          "door; two yes in three asked steps latch the straight run of trail behind the "
          "drone as a dead end for the rest of the run: shut on the route's map whatever "
          "the perceiver painted in it, a lane left open back to its mouth, and that shut "
          "too once the drone is out. While latched and inside, the navigator is told the "
          "corridor is a dead end when the route's next point is behind it. s03 dynamic is "
          "0/52 in Phase 2; a68's seal left the tine in flight but yielded to later floor "
          "reads and fired in the s02 hall. Not flown before probe DE passes "
          "(eval/phase2/R38_dead_end_latch/README.md)."),
    Agent("a79", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A79,
                                          "memory": "a17f",
                                          "navigator_notes": NAVIGATOR_A78,
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a66 with a78's dead-end latch fired by the drone's own trail, no confirmer. "
          "The latch fires when the drone has not left the lane of a straight run of 5 m "
          "or more that it turned into (1.5 m either side of its axis), has got no "
          "farther down it for five steps, has read a closed door in the centre three "
          "strips twice while looking along it, and has never stood beside the lane "
          "within 4 m: a corridor confines the drone, a hall does not. The corridor is "
          "then shut on the route's map as a78 shuts it, and the navigator is told it is "
          "a dead end when the route's next point is behind it. R38: the latch was sound "
          "on the record with a confirmer that is never wrong, and the model could not be "
          "that confirmer (e01 yes on 37% of s02 steps). Round F, R32P and R35: the rule "
          "fires in the shut tine in 9 of 11 s03 dynamic runs and in none of 53 won s02 "
          "runs before the crossing (eval/phase2/R39_confined_latch/README.md)."),
    Agent("a80", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A80,
                                          "memory": "a17f",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a66 with the wall survey: the square looks the route never takes. A closed "
          "door read dead ahead on the first way in along the direct line from the spawn "
          "to the goal starts it. The drone steps 7 m to the side of that line (the side "
          "of a remembered open doorway first, else the left), turns back to the line's "
          "bearing and flies at the wall, every frame on the way in a look square to it; "
          "at the wall with no door it goes 5 m back and to the other side and flies in "
          "again. An open doorway read on a strip within 40 degrees of square is kept as a "
          "ray; the doorway's line is where the rays cross, and the waypoint runs 3 m "
          "ahead of the drone on it until the drone is through. The wall's range is taken "
          "only from where the drone is stopped. Probe door_read: at 2-9 m a look within "
          "20 degrees of square read the open door on 157 of 158 looks and a blank wall "
          "strip as open on 1 of 366; beyond 60 degrees, 112 of 231 and 76 of 393; the "
          "open door was in view within 20 degrees of square at 2-6 m on 58 of 4256 "
          "near-side frames (eval/phase2/R40_wall_survey/README.md)."),
    Agent("a81", "p17", {"orchestrator": {"perceiver": "g05",
                                          "door_confirmer": "d01",
                                          "critic": "none", "frame": "clean",
                                          "goal_truth": "planner",
                                          "turn_rule": "no_repeat_when_open",
                                          "target_policy": "pathfinder",
                                          "pathfinder": PATHFINDER_A81,
                                          "memory": "a17f",
                                          "floor_map": {"no_floor": "blocked_near",
                                                        "bottom": "open_near",
                                                        "lower": "open_far",
                                                        "middle": "open_far"},
                                          "spatial": "server/decider/spatial.py"}},
          "a80 after its shakedown: the survey's through phase made sure. A doorway read "
          "across several strips lies at their middle; with the wall's range unknown the "
          "ray is taken 4 m out and no nearer than a metre beyond the farthest the drone "
          "has been toward the wall, and rays are crossed only when they differ by about "
          "18 degrees; a move stopped short with no doorway read hands the waypoint to the "
          "route for three steps, and 2 m farther on the drone is through (it clipped a "
          "jamb), else the doorway was a phantom; flying at the wall, every strip blocked "
          "is the wall. R40 shakedown, s02c dynamic seed 1: the survey read the open door "
          "at step 12 and the drone was through it at 16, but two near-parallel rays put "
          "the door's line 1.7 m off its centre, the drone clipped the jamb, and the survey "
          "called the door a phantom and pointed the tags back at the other station for "
          "the nine steps the navigator took to the goal "
          "(eval/phase2/R41_survey_check/README.md)."),
)}

DEFAULT_AGENT = "a00"


def get(version: str) -> Agent:
    if version not in AGENTS:
        raise KeyError("unknown agent version {0!r}; known: {1}".format(
            version, ", ".join(AGENTS)))
    return AGENTS[version]


def wants_clean_frame(version: str) -> bool:
    """Whether the agent's goal identifier reads the frame without annotations."""
    features = get(version).features
    if (features.get("orchestrator") or {}).get("frame") == "clean":
        return True
    ident = features.get("goal_identifier") or {}
    return ident.get("frame") == "clean"


def current() -> Agent:
    """The agent this process serves. Read per call so --agent can set the env first."""
    return get(os.environ.get("VLM_AGENT", DEFAULT_AGENT).strip() or DEFAULT_AGENT)


def describe(version: str) -> Dict[str, Any]:
    """An agent's identity as run.json records it; eval/phase2.py locks rounds on it."""
    agent = get(version)
    out = {
        "agent_version": agent.version,
        "agent_sha": agent.sha(),
        "prompt_version": agent.prompt_version,
        "prompt_sha": agent.prompt.sha(),
    }
    if agent.identifier_prompt is not None:
        out["identifier_prompt_version"] = agent.identifier_prompt.version
        out["identifier_prompt_sha"] = agent.identifier_prompt.sha()
    for sub in agent.subagent_prompts:
        out["subagent_prompts"] = out.get("subagent_prompts", {})
        out["subagent_prompts"][sub.version] = sub.sha()
    if agent.spatial_config is not None:
        from . import spatial
        out["spatial_sha"] = spatial.wording_sha()
        if agent.uses_a14_wording:
            out["spatial_a14_sha"] = spatial.wording_sha_a14()
        if agent.spatial_config.name == "a15":
            out["spatial_a15_sha"] = spatial.wording_sha_a15()
        if agent.spatial_config.name == "a16":
            out["spatial_a16_sha"] = spatial.wording_sha_a16()
        if agent.spatial_config.name in ("a17", "a17b", "a17c", "a17d"):
            out["spatial_a17_sha"] = spatial.wording_sha_a17()
        if agent.spatial_config.door_walls or agent.spatial_config.suspects:
            out["spatial_a17d_sha"] = spatial.wording_sha_a17d()
    if agent.staged:
        out["planner_a17_sha"] = planner_a17_sha()
    if agent.verifies:
        out["planner_a20_sha"] = planner_a20_sha()
    return out


def planner_a17_sha() -> str:
    """Identity of a17's stage machine parameters and q04 trigger wording."""
    from . import planner
    blob = json.dumps(planner.stage_sha_blob(), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def planner_a20_sha() -> str:
    """Identity of a20's verify stage parameters and wording."""
    from . import planner
    blob = json.dumps(planner.verify_sha_blob(), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def record() -> Dict[str, Any]:
    """What run.json, metrics.json, each decision and /health carry."""
    return describe(current().version)
