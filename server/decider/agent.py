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
from typing import Any, Dict, Optional

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
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


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
)}

DEFAULT_AGENT = "a00"


def get(version: str) -> Agent:
    if version not in AGENTS:
        raise KeyError("unknown agent version {0!r}; known: {1}".format(
            version, ", ".join(AGENTS)))
    return AGENTS[version]


def wants_clean_frame(version: str) -> bool:
    """Whether the agent's goal identifier reads the frame without annotations."""
    ident = get(version).features.get("goal_identifier") or {}
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
    return out


def record() -> Dict[str, Any]:
    """What run.json, metrics.json, each decision and /health carry."""
    return describe(current().version)
