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

    indices = _indices_from(body)
    if not indices:
        return JSONResponse({"error": {"message": "no actions found in request"}}, status_code=400)
    choice = _pick(body, indices)
    reason = "stub router: taking the straightest of {0}".format(indices)

    if rung == "tool_call":
        message: Dict[str, Any] = {
            "role": "assistant",
            "tool_calls": [{
                "id": "call_stub", "type": "function",
                "function": {"name": "choose_action",
                             "arguments": json.dumps({"reason": reason, "action": choice})},
            }],
        }
    elif rung == "text":
        message = {"role": "assistant",
                   "content": "REASON: {0}\nACTION: {1}".format(reason, choice)}
    else:
        message = {"role": "assistant",
                   "content": json.dumps({"reason": reason, "action": choice})}

    return {
        "id": "chatcmpl-stub",
        "object": "chat.completion",
        "model": body.get("model", "fake") + "-stub",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 900, "completion_tokens": 30, "total_tokens": 930},
    }
