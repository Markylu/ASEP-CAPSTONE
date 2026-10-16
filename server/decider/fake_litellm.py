"""A stand-in for the LiteLLM router, for testing the loop without a model.

Speaks enough of /v1/chat/completions to exercise every rung of the ladder and
returns a valid choice for the frame it is given. It does not look at the image
— it picks the straightest action available — so it proves the plumbing and
nothing about navigation. Never point a run that produces numbers at this.

    uvicorn server.decider.fake_litellm:app --port 4001

`--rung` behaviour is chosen by env FAKE_SUPPORTS, a comma list of the rungs it
will honour (default all), so the fallback ladder can be tested deliberately:

    FAKE_SUPPORTS=tool_call uvicorn server.decider.fake_litellm:app --port 4001

FAKE_DELAY=<seconds> holds every reply that long, standing in for model
latency — how the frozen-world mode is checked for latency independence.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="fake litellm")

SUPPORTS = [r.strip() for r in os.environ.get(
    "FAKE_SUPPORTS", "json_schema,json_object,tool_call,text").split(",") if r.strip()]

# "straight" always takes the middle heading; "cycle" walks the whole fan, which
# exercises turns and collisions. Neither looks at the image.
PICK = os.environ.get("FAKE_PICK", "straight")
DELAY = float(os.environ.get("FAKE_DELAY", "0"))
_calls = {"n": 0}


def _indices_from(body: Dict[str, Any]) -> List[int]:
    fmt = body.get("response_format") or {}
    schema = (fmt.get("json_schema") or {}).get("schema")
    if schema:
        return list(schema["properties"]["action"]["enum"])
    for tool in body.get("tools") or []:
        params = tool["function"]["parameters"]
        return list(params["properties"]["action"]["enum"])
    # Rung 4 has no schema at all; read the numbers off the prompt text.
    text = json.dumps(body.get("messages", []))
    return [int(n) for n in re.findall(r"\\n  \[(\d+)\]", text)] or \
           [int(n) for n in re.findall(r"\[(\d+)\] turn", text)]


def _wants_goal(body: Dict[str, Any]) -> bool:
    """Whether the request asks for a goal report (agent a03 and later)."""
    fmt = body.get("response_format") or {}
    schema = (fmt.get("json_schema") or {}).get("schema")
    if schema:
        return "goal" in schema["properties"]
    for tool in body.get("tools") or []:
        return "goal" in tool["function"]["parameters"]["properties"]
    # json_object and text carry the contract in the prompt text.
    text = json.dumps(body.get("messages", []))
    return '\\"goal\\"' in text or "GOAL:" in text


def _goal_last(body: Dict[str, Any]) -> bool:
    """Whether the goal report is asked for after the reason (agent a04)."""
    fmt = body.get("response_format") or {}
    schema = (fmt.get("json_schema") or {}).get("schema")
    for tool in body.get("tools") or []:
        schema = tool["function"]["parameters"]
    if schema:
        keys = list(schema["properties"])
        return "goal" in keys and keys.index("goal") > keys.index("reason")
    # json_object embeds the schema in the prompt; text names the line order.
    text = json.dumps(body.get("messages", []))
    reason_at, goal_at = text.find('\\"reason\\": {'), text.find('\\"goal\\": {')
    if reason_at >= 0 and goal_at >= 0:
        return reason_at < goal_at
    return 'then a line \\"GOAL:' in text


def _is_identifier(body: Dict[str, Any]) -> bool:
    """Whether this is a goal identifier request (agent a05 on): its system
    prompt is g01's, whatever the rung."""
    messages = body.get("messages") or []
    system = messages[0].get("content") if messages else ""
    return isinstance(system, str) and system.startswith(
        "You check one image from the front camera")


def _identifier_goal(body: Dict[str, Any]) -> str:
    """A goal report fixed by the frame's bytes, so the same frame always gets
    the same answer, and some frames get a sighting (which exercises the log's
    sighting line). It says nothing about the image."""
    text = json.dumps(body.get("messages", []))
    digest = hashlib.sha256(text.encode("utf-8")).digest()[0]
    return ["ahead", "left", "right", "not_visible", "not_visible"][digest % 5]


def _identifier_reply(body: Dict[str, Any], rung: str) -> Dict[str, Any]:
    reply = {"reason": "stub identifier: does not look at the image",
             "goal": _identifier_goal(body)}
    if rung == "tool_call":
        message: Dict[str, Any] = {
            "role": "assistant",
            "tool_calls": [{"id": "call_stub", "type": "function",
                            "function": {"name": "report_goal",
                                         "arguments": json.dumps(reply)}}],
        }
    elif rung == "text":
        message = {"role": "assistant",
                   "content": "REASON: {0}\nGOAL: {1}".format(reply["reason"], reply["goal"])}
    else:
        message = {"role": "assistant", "content": json.dumps(reply)}
    return {
        "id": "chatcmpl-stub",
        "object": "chat.completion",
        "model": body.get("model", "fake") + "-stub",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 800, "completion_tokens": 20, "total_tokens": 820},
    }


def _pick(body: Dict[str, Any], indices: List[int]) -> int:
    """Index 0 is turn-around, so the forward headings are everything else."""
    forward = [i for i in indices if i != 0]
    if not forward:
        return indices[0]
    if PICK == "cycle":
        choice = forward[_calls["n"] % len(forward)]
        _calls["n"] += 1
        return choice
    return forward[len(forward) // 2]


@app.post("/v1/chat/completions")
async def completions(body: Dict[str, Any]):
    if DELAY > 0:
        await asyncio.sleep(DELAY)
    if "response_format" in body:
        rung = "json_schema" if body["response_format"].get("type") == "json_schema" else "json_object"
    elif "tools" in body:
        rung = "tool_call"
    else:
        rung = "text"

    if rung not in SUPPORTS:
        return JSONResponse(
            {"error": {"message": "fake router does not support " + rung}}, status_code=400)

    if _is_identifier(body):
        return _identifier_reply(body, rung)

    indices = _indices_from(body)
    if not indices:
        return JSONResponse({"error": {"message": "no actions found in request"}}, status_code=400)
    choice = _pick(body, indices)
    reason = "stub router: taking the straightest of {0}".format(indices)
    # It never looks at the image, so it never claims to see the goal.
    reply: Dict[str, Any] = {"reason": reason, "action": choice}
    if _wants_goal(body):
        if _goal_last(body):
            reply = {"reason": reason, "goal": "not_visible", "action": choice}
        else:
            reply = {"goal": "not_visible", **reply}

    if rung == "tool_call":
        message: Dict[str, Any] = {
            "role": "assistant",
            "tool_calls": [{
                "id": "call_stub", "type": "function",
                "function": {"name": "choose_action",
                             "arguments": json.dumps(reply)},
            }],
        }
    elif rung == "text":
        message = {"role": "assistant",
                   "content": "\n".join("{0}: {1}".format(k.upper(), v)
                                        for k, v in reply.items())}
    else:
        message = {"role": "assistant",
                   "content": json.dumps(reply)}

    return {
        "id": "chatcmpl-stub",
        "object": "chat.completion",
        "model": body.get("model", "fake") + "-stub",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 900, "completion_tokens": 30, "total_tokens": 930},
    }
