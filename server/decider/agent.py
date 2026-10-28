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
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]

    @property
    def staged(self) -> bool:
        return (self.features.get("orchestrator") or {}).get("target_policy") == "staged_search"

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
        """The perceiver's and strategist's prompts (a13 on), in that order."""
        orch = self.features.get("orchestrator") or {}
        return [prompts.get(orch[k]) for k in ("perceiver", "strategist") if orch.get(k)]


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
        if agent.spatial_config.name == "a17":
            out["spatial_a17_sha"] = spatial.wording_sha_a17()
    if agent.staged:
        out["planner_a17_sha"] = planner_a17_sha()
    return out


def planner_a17_sha() -> str:
    """Identity of a17's stage machine parameters and q04 trigger wording."""
    from . import planner
    blob = json.dumps(planner.stage_sha_blob(), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def record() -> Dict[str, Any]:
    """What run.json, metrics.json, each decision and /health carry."""
    return describe(current().version)
