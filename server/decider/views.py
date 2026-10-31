"""What each model in an orchestrated step is shown (R11).

Every model call of an orchestrated agent goes through a View: its role, its
system prompt, its text and its image, built here and nowhere else. What a role
may see (evidence §3, eval/phase2/R11_goal_default/evidence.md):

    perceiver   the clean frame and g03's question. No map, no plan, no history.
    strategist  text only: the map in distances and eight directions, the targets
                code lists and, for a14 on, the goal's true position.
    navigator   the annotated frame, the planner's line, the perceiver's line, the
                last three moves and one note per fact per action. The goal only
                as "head for the goal" and "toward your target": never its
                distance or direction.

The goal's true position enters the agent on the planner side only (operator,
2026-10-24 for the strategist, 2026-10-26 for planner code). check() refuses a
navigator or perceiver view that words it; eval/spatial_replay.py runs the same
goal_leaks() over recorded texts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from . import prompt as prompts, spatial

#: The roles whose texts must never carry the goal's true position.
NO_GOAL_TRUTH = ("perceiver", "navigator", "confirmer", "door_confirmer", "wall_reader",
                 "wall_confirmer")


@dataclass(frozen=True)
class View:
    role: str
    system: str
    text: str
    image_b64: Optional[str]


class LeakError(RuntimeError):
    """A view words what its role may not see."""


def perceiver(prompt: prompts.Prompt, manifest: Dict[str, Any], clean_b64: str) -> View:
    return View("perceiver", prompt.system, prompt.render(prompt, manifest), clean_b64)


def wall_reader(prompt: prompts.Prompt, manifest: Dict[str, Any], clean_b64: str) -> View:
    """a61: the clean frame and w01's question, as the perceiver's."""
    return View("wall_reader", prompt.system, prompt.render(prompt, manifest), clean_b64)


def wall_confirmer(prompt: prompts.Prompt, strips: List[str], clean_b64: str) -> View:
    """k01 (R28): the clean frame and the strips read open, as d01's view."""
    return View("wall_confirmer", prompt.system, prompt.render(prompt, strips), clean_b64)


def confirmer(prompt: prompts.Prompt, report: Dict[str, Any], clean_b64: str) -> View:
    return View("confirmer", prompt.system, prompt.render(prompt, report), clean_b64)


def door_confirmer(prompt: prompts.Prompt, strips: List[str], clean_b64: str) -> View:
    return View("door_confirmer", prompt.system, prompt.render(prompt, strips), clean_b64)


def strategist(prompt: prompts.Prompt, situation: str) -> View:
    return View("strategist", prompt.system, prompt.render(prompt, situation), None)


def navigator(prompt: prompts.Prompt, offered: Dict[str, Any], tags: Dict[int, List[str]],
              plan_line: str, perceiver_line: str, recent_moves: str,
              frame_b64: str) -> View:
    return View("navigator", prompt.system,
                prompt.render(prompt, offered, tags, plan_line, perceiver_line, recent_moves),
                frame_b64)


def goal_leaks(role: str, text: str, manifest: Dict[str, Any]) -> List[str]:
    """Lines of a perceiver or navigator text that word the goal's true
    distance and direction from the drone, or the goal-known sentence."""
    if role not in NO_GOAL_TRUTH:
        return []
    here = spatial.pose_xyh(manifest.get("pose"))
    position = (manifest.get("goal") or {}).get("position")
    known = spatial.WORDS_A14["goal_known"].split(":")[0]
    out = []
    for line in text.splitlines():
        if known in line:
            out.append(line)
        elif here is not None and position and "goal" in line:
            truth = (float(position[0]), -float(position[2]))
            if spatial.where_words(here, truth) in line:
                out.append(line)
    return out


def check(view: View, manifest: Dict[str, Any], goal_known: bool) -> None:
    """Refuse a view that shows its role more than it may see. Only an agent
    given the goal's truth can leak it, so only its views are scanned."""
    if view.role == "strategist" and view.image_b64 is not None:
        raise LeakError("the strategist is text only")
    if goal_known:
        leaks = goal_leaks(view.role, view.text, manifest)
        if leaks:
            raise LeakError("{0} text words the goal's position: {1!r}".format(
                view.role, leaks[0]))
