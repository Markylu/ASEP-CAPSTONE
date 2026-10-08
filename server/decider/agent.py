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
from typing import Any, Dict

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

    def sha(self) -> str:
        blob = self.prompt.sha() + "\x00" + json.dumps(self.features, sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


AGENTS: Dict[str, Agent] = {a.version: a for a in (
    Agent("a00", "p02", {}, "Phase 1 agent: p02, one frame per step, no memory."),
    Agent("a01", "p03", {}, "No goal hint: p03 drops the goal's distance and bearing "
          "and each action's angle and distance. The goal is found from the image alone."),
)}

DEFAULT_AGENT = "a00"


def get(version: str) -> Agent:
    if version not in AGENTS:
        raise KeyError("unknown agent version {0!r}; known: {1}".format(
            version, ", ".join(AGENTS)))
    return AGENTS[version]


def current() -> Agent:
    """The agent this process serves. Read per call so --agent can set the env first."""
    return get(os.environ.get("VLM_AGENT", DEFAULT_AGENT).strip() or DEFAULT_AGENT)


def describe(version: str) -> Dict[str, Any]:
    """An agent's identity as run.json records it; eval/phase2.py locks rounds on it."""
    agent = get(version)
    return {
        "agent_version": agent.version,
        "agent_sha": agent.sha(),
        "prompt_version": agent.prompt_version,
        "prompt_sha": agent.prompt.sha(),
    }


def record() -> Dict[str, Any]:
    """What run.json, metrics.json, each decision and /health carry."""
    return describe(current().version)
