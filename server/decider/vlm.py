"""The VLM call, with a fallback ladder.

Target is a strict JSON schema whose `action` is an enum of this frame's
indices. Not every model behind the LiteLLM proxy supports that, so the call
walks down a ladder until something works and records which rung answered. A run
that used rung 4 is a weaker run than one that used rung 1, and the paper should
be able to say so.

Each call is also timed as a budget rather than a single number, because "5.7s
per decision" does not say whether the fix is a better link or a smaller image.
See `Timing`.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import httpx

from . import agent, config, schema

RUNGS = ["json_schema", "json_object", "tool_call", "text"]

# Rungs the provider has REJECTED outright (HTTP 4xx), remembered per process so
# later steps do not pay for them again. Deliberately not "the rung that last
# worked": a one-off parse failure — a truncated reply, say — must not pin the
# whole run to a weaker rung. Capability is sticky, bad luck is not.
_unsupported: set = set()

#: Tries per rung when the connection itself fails (dropped tunnel, reset,
#: timeout). That is the network, not the rung: falling to a weaker rung would
#: record a capability problem the model does not have (phase 1A, a01).
TRANSPORT_TRIES = 3


class VLMError(RuntimeError):
    pass


#: Request body is pushed in chunks this size so the moment the last one is
#: handed to the socket is observable. Small enough that a ~400 KB frame is
#: many writes, large enough not to matter for syscall overhead.
_UPLOAD_CHUNK = 64 * 1024


@dataclass
class Timing:
    """Where a decision's wall time actually went.

    The four measured segments are meant to add up:

        total_ms = rtt_ms + upload_ms + prefill_ms + decode_ms + unaccounted_ms

    - `rtt_ms` is a tiny GET on the already-open connection: one round trip
      with no compute behind it. The transport floor.
    - `upload_ms` is the time to hand the request body to the socket, timed by
      exhausting the body iterator. It scales with the base64 frame, so it is
      the number that moves when the capture resolution changes. Over a fast
      link the kernel buffers the write and this reads low; it is a lower
      bound on transport cost, not an upper one.
    - `prefill_ms` is time-to-first-token minus the upload and one round trip:
      server queue, vision encoder, and prefill over the image tokens. The
      segment an image-heavy prompt inflates.
    - `decode_ms` is first token to last: generation, at `decode_tok_s`. The
      segment a talkative reasoning-first prompt inflates.

    `unaccounted_ms` is whatever the four do not explain — stream teardown,
    JSON parsing, scheduling. It is kept rather than distributed so the budget
    stays auditable: a large value means this decomposition is wrong, and that
    should be visible instead of smeared into the other segments.

    `network_ms` and `compute_ms` are the two-way split the name promises:
    (rtt + upload) against (prefill + decode).

    Without streaming — `VLM_STREAM=0`, or a provider that rejected it — only
    `rtt_ms`, `upload_ms` and `total_ms` are real; the rest are None. None
    rather than 0, because a zero here would read as "no time spent".
    """

    total_ms: float
    request_bytes: int
    streamed: bool
    rtt_ms: Optional[float] = None
    upload_ms: Optional[float] = None
    ttfb_ms: Optional[float] = None
    ttft_ms: Optional[float] = None
    prefill_ms: Optional[float] = None
    decode_ms: Optional[float] = None
    decode_tok_s: Optional[float] = None
    unaccounted_ms: Optional[float] = None
    network_ms: Optional[float] = None
    compute_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        def r(value: Optional[float], places: int = 1) -> Optional[float]:
            return None if value is None else round(value, places)
        return {
            "total_ms": r(self.total_ms),
            "rtt_ms": r(self.rtt_ms),
            "upload_ms": r(self.upload_ms),
            "ttfb_ms": r(self.ttfb_ms),
            "ttft_ms": r(self.ttft_ms),
            "prefill_ms": r(self.prefill_ms),
            "decode_ms": r(self.decode_ms),
            "decode_tok_s": r(self.decode_tok_s, 2),
            "unaccounted_ms": r(self.unaccounted_ms),
            "network_ms": r(self.network_ms),
            "compute_ms": r(self.compute_ms),
            "request_bytes": self.request_bytes,
            "streamed": self.streamed,
        }


@dataclass
class Decision:
    index: int
    reason: str
    rung: str
    latency_ms: float
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    raw: str = ""
    #: Breakdown of the winning request only. `latency_ms` above is the whole
    #: ladder, including rungs that failed first, so the two differ on any step
    #: that had to fall back — deliberately: one answers "what did this step
    #: cost", the other "what did the model cost once it worked".
    timing: Optional[Timing] = None
    #: Where the model said the goal is in this frame (schema.GOAL_REPORTS), for
    #: an agent whose reply reports it; None otherwise, and then not recorded.
    goal: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "index": self.index,
            "reason": self.reason,
            "rung": self.rung,
            "latency_ms": round(self.latency_ms, 1),
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "attempts": self.attempts,
            "raw": self.raw,
            "timing": self.timing.to_dict() if self.timing else None,
        }
        if self.goal is not None:
            out["goal"] = self.goal
        return out


def _messages(manifest: Dict[str, Any], frame_b64: str, schema_hint: str = "",
              memory: Optional[List[Dict[str, Any]]] = None,
              sighting: Optional[str] = None) -> List[Dict[str, Any]]:
    prompt = agent.current().prompt
    if memory is None:
        text = prompt.render(prompt, manifest)
    elif agent.current().features.get("goal_identifier"):
        text = prompt.render(prompt, manifest, memory, sighting)
    else:
        text = prompt.render(prompt, manifest, memory)
    if schema_hint:
        text += "\n\n" + schema_hint
    return [
        {"role": "system", "content": prompt.system},
        {"role": "user", "content": [
            {"type": "text", "text": text},
            {"type": "image_url",
             "image_url": {"url": "data:image/png;base64," + frame_b64}},
        ]},
    ]


def _reports_goal() -> bool:
    """Whether this agent's reply carries a goal report (agent.py features).

    Never when a goal identifier reports it instead (a05 on): the navigator's
    reply is then reason and action only."""
    features = agent.current().features
    if features.get("goal_identifier"):
        return False
    memory = features.get("memory") or {}
    return "goal" in memory.get("fields", [])


def _goal_after_reason() -> bool:
    """Whether the goal report comes after the reason, not first (a04)."""
    return agent.current().features.get("goal_order") == "after_reason"


def _body(rung: str, manifest: Dict[str, Any], frame_b64: str, indices: List[int],
          memory: Optional[List[Dict[str, Any]]] = None,
          sighting: Optional[str] = None) -> Dict[str, Any]:
    goal = _reports_goal()
    after = _goal_after_reason()
    body: Dict[str, Any] = {
        "model": config.VLM_MODEL,
        "max_tokens": config.MAX_TOKENS,
        "temperature": config.TEMPERATURE,
    }
    if rung == "json_schema":
        body["messages"] = _messages(manifest, frame_b64, memory=memory, sighting=sighting)
        body["response_format"] = schema.response_format(indices, goal, after)
    elif rung == "json_object":
        hint = ("Reply with JSON only, matching this schema exactly:\n"
                + json.dumps(schema.action_schema(indices, goal, after)))
        body["messages"] = _messages(manifest, frame_b64, hint, memory, sighting)
        body["response_format"] = {"type": "json_object"}
    elif rung == "tool_call":
        body["messages"] = _messages(manifest, frame_b64, memory=memory, sighting=sighting)
        body["tools"] = [schema.tool_spec(indices, goal, after)]
        # "required" rather than the object form: with exactly one tool it means
        # the same thing, and LM Studio rejects {"type": "function", ...} with
        # "Invalid tool_choice type: 'object'".
        body["tool_choice"] = "required"
    else:
        if goal and after:
            hint = ('Reply with a line "REASON: ...", then a line "GOAL: '
                    + "|".join(schema.GOAL_REPORTS) + '", then a line "ACTION: <number>".')
        elif goal:
            hint = ('Reply with a line "GOAL: ' + "|".join(schema.GOAL_REPORTS) + '", then a '
                    'line "REASON: ...", then a line "ACTION: <number>".')
        else:
            hint = ('Reply with a line "REASON: ..." then a line "ACTION: <number>".')
        body["messages"] = _messages(manifest, frame_b64, hint, memory, sighting)
    return body


def _extract(rung: str, payload: Dict[str, Any], indices: List[int]) -> Dict[str, Any]:
    """Pull (index, reason, goal, raw) out of a completion, or raise VLMError.

    `goal` is None when the reply has no valid goal report; that never fails
    the decision, which is about the action."""
    choice = payload["choices"][0]
    message = choice.get("message", {})

    if rung == "tool_call":
        calls = message.get("tool_calls") or []
        if not calls:
            raise VLMError("no tool call in response")
        raw = calls[0]["function"]["arguments"]
        parsed = json.loads(raw)
    elif rung == "text":
        raw = message.get("content") or ""
        match = re.search(r"ACTION:\s*(-?\d+)", raw) or re.search(r"(-?\d+)", raw)
        if not match:
            raise VLMError("no integer in response")
        reason_match = re.search(r"REASON:\s*(.+)", raw)
        goal_match = re.search(r"GOAL:\s*(\w+)", raw)
        parsed = {
            "action": int(match.group(1)),
            "reason": reason_match.group(1).strip() if reason_match else raw.strip()[:500],
            "goal": goal_match.group(1).lower() if goal_match else None,
        }
    else:
        raw = message.get("content") or ""
        # Some models wrap JSON in a fenced block even under json_object.
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
        parsed = json.loads(fenced.group(1) if fenced else raw)

    index = int(parsed["action"])
    if index not in indices:
        raise VLMError("model chose {0}, not on this frame ({1})".format(index, indices))
    goal = parsed.get("goal")
    return {"index": index, "reason": str(parsed.get("reason", "")),
            "goal": goal if goal in schema.GOAL_REPORTS else None, "raw": raw}


# Set False for the process the first time a provider refuses a streamed
# request. Same reasoning as `_unsupported` above: a capability the server does
# not have is worth remembering, so later steps do not pay for it again.
_stream_ok = config.VLM_STREAM


#: The process has opened a connection to the provider at least once. Until it
#: has, the first request pays TCP — and, over an SSH tunnel, channel — setup,
#: which measured ~250ms against sctsvr6 and is not what "round trip" means.
_connection_warm = False

#: One shared client for the life of the process, so connections are reused
#: between decisions. A client per call would make every step pay setup again,
#: and would hide that cost inside whichever segment happened to go first.
_client: Optional[httpx.AsyncClient] = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=config.VLM_TIMEOUT_S,
            limits=httpx.Limits(max_keepalive_connections=4,
                                keepalive_expiry=600.0),
        )
    return _client


async def aclose() -> None:
    """Shut the shared client down. Wired to the app's lifespan."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


async def _probe_rtt(http: httpx.AsyncClient, base_url: str,
                     headers: Dict[str, str]) -> Optional[float]:
    """One small round trip with no compute behind it: the transport floor.

    Runs before the real call, on the connection that call will reuse. The
    very first probe of the process is thrown away and repeated, because that
    one carries the handshake: counting it would inflate `rtt_ms` on step 1 and
    make step 1 look like a network problem when it is a startup cost.
    """
    global _connection_warm
    if not config.VLM_RTT_PROBE:
        return None
    url = base_url + "/v1/models"
    try:
        if not _connection_warm:
            await (await http.get(url, headers=headers, timeout=15.0)).aclose()
            _connection_warm = True
        started = time.perf_counter()
        response = await http.get(url, headers=headers, timeout=10.0)
        await response.aread()
    except httpx.HTTPError:
        return None
    return (time.perf_counter() - started) * 1000.0


class _TimedBody:
    """Request body as an iterator, so the last write is observable.

    httpx hands the body to the transport chunk by chunk; the timestamp after
    the final chunk is when the frame finished going out. `Content-Length` is
    set by the caller so this stays an ordinary request rather than a chunked
    one, which not every OpenAI-compatible server accepts.
    """

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.sent_at: Optional[float] = None

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for start in range(0, len(self.payload), _UPLOAD_CHUNK):
            yield self.payload[start:start + _UPLOAD_CHUNK]
        self.sent_at = time.perf_counter()


def _merge_delta(acc: Dict[str, Any], delta: Dict[str, Any]) -> bool:
    """Fold one SSE delta into the accumulating message. True if it had content.

    Tool-call arguments arrive split across chunks exactly as content does, so
    both are concatenated; `index` is honoured because a provider may interleave
    calls even when only one tool was offered.
    """
    produced = False
    content = delta.get("content")
    if content:
        acc["content"] = (acc.get("content") or "") + content
        produced = True
    for call in delta.get("tool_calls") or []:
        slot = call.get("index", 0)
        calls = acc.setdefault("tool_calls", [])
        while len(calls) <= slot:
            calls.append({"function": {"name": "", "arguments": ""}})
        function = call.get("function") or {}
        if function.get("name"):
            calls[slot]["function"]["name"] = function["name"]
        if function.get("arguments"):
            calls[slot]["function"]["arguments"] += function["arguments"]
            produced = True
    return produced


async def _post_stream(client: httpx.AsyncClient, url: str,
                       headers: Dict[str, str], body: Dict[str, Any],
                       rtt_ms: Optional[float]):
    """Streamed request, reassembled into the shape a plain reply has.

    Returns (status, payload, error_text, timing). `_extract` never learns that
    the reply arrived in pieces.
    """
    body = dict(body, stream=True, stream_options={"include_usage": True})
    raw = json.dumps(body).encode()
    sender = _TimedBody(raw)
    send_headers = dict(headers, **{"Content-Length": str(len(raw))})

    started = time.perf_counter()
    first_token_at: Optional[float] = None
    last_token_at: Optional[float] = None
    message: Dict[str, Any] = {}
    finish_reason = None
    usage = None
    model = body["model"]

    async with client.stream("POST", url, headers=send_headers,
                             content=sender.__aiter__()) as response:
        headers_at = time.perf_counter()
        if response.status_code >= 400:
            text = (await response.aread()).decode(errors="replace")
            return response.status_code, None, text, None
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if not chunk or chunk == "[DONE]":
                continue
            parsed = json.loads(chunk)
            model = parsed.get("model") or model
            if parsed.get("usage"):
                usage = parsed["usage"]
            for choice in parsed.get("choices") or []:
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
                if _merge_delta(message, choice.get("delta") or {}):
                    now = time.perf_counter()
                    if first_token_at is None:
                        first_token_at = now
                    last_token_at = now

    ended = time.perf_counter()
    payload = {
        "choices": [{"message": message, "finish_reason": finish_reason}],
        "usage": usage or {},
        "model": model,
    }
    timing = _assemble_timing(
        started=started, ended=ended, sent_at=sender.sent_at,
        headers_at=headers_at, first_token_at=first_token_at,
        last_token_at=last_token_at, rtt_ms=rtt_ms,
        request_bytes=len(raw), streamed=True,
        completion_tokens=(usage or {}).get("completion_tokens"),
    )
    return response.status_code, payload, "", timing


async def _post_plain(client: httpx.AsyncClient, url: str,
                      headers: Dict[str, str], body: Dict[str, Any],
                      rtt_ms: Optional[float]):
    """Unstreamed request. Upload is still timed; the model's half is opaque."""
    raw = json.dumps(body).encode()
    sender = _TimedBody(raw)
    send_headers = dict(headers, **{"Content-Length": str(len(raw))})

    started = time.perf_counter()
    response = await client.post(url, headers=send_headers,
                                 content=sender.__aiter__())
    ended = time.perf_counter()
    if response.status_code >= 400:
        return response.status_code, None, response.text, None
    timing = _assemble_timing(
        started=started, ended=ended, sent_at=sender.sent_at,
        headers_at=None, first_token_at=None, last_token_at=None,
        rtt_ms=rtt_ms, request_bytes=len(raw), streamed=False,
        completion_tokens=None,
    )
    return response.status_code, response.json(), "", timing


def _assemble_timing(*, started: float, ended: float, sent_at: Optional[float],
                     headers_at: Optional[float],
                     first_token_at: Optional[float],
                     last_token_at: Optional[float], rtt_ms: Optional[float],
                     request_bytes: int, streamed: bool,
                     completion_tokens: Optional[int]) -> Timing:
    ms = lambda t: (t - started) * 1000.0  # noqa: E731

    total_ms = ms(ended)
    upload_ms = ms(sent_at) if sent_at is not None else None
    timing = Timing(total_ms=total_ms, request_bytes=request_bytes,
                    streamed=streamed, rtt_ms=rtt_ms, upload_ms=upload_ms)

    if first_token_at is None:
        return timing

    timing.ttfb_ms = ms(headers_at) if headers_at is not None else None
    timing.ttft_ms = ms(first_token_at)
    # Time-to-first-token minus what was spent pushing the body and minus one
    # round trip is the server's own prefill: queue, vision encoder, attention
    # over the image tokens. Floored at zero because the probe is a separate
    # round trip and can come back marginally slower than the real one; a
    # negative prefill would read as a bug rather than as measurement noise.
    known_transport = (upload_ms or 0.0) + (rtt_ms or 0.0)
    timing.prefill_ms = max(0.0, timing.ttft_ms - known_transport)
    timing.decode_ms = (last_token_at - first_token_at) * 1000.0

    if completion_tokens and timing.decode_ms > 0:
        timing.decode_tok_s = completion_tokens / (timing.decode_ms / 1000.0)

    timing.network_ms = known_transport
    timing.compute_ms = timing.prefill_ms + timing.decode_ms
    timing.unaccounted_ms = max(
        0.0, total_ms - timing.network_ms - timing.compute_ms)
    return timing


async def _request(client: httpx.AsyncClient, url: str,
                   headers: Dict[str, str], body: Dict[str, Any],
                   rtt_ms: Optional[float]):
    """Streamed if the provider allows it, plain otherwise.

    A provider that rejects the streamed form rejects it every time, so the
    first 4xx turns streaming off for the process and the same request is
    retried plain. The rung is not blamed for it: losing the breakdown is a
    missing measurement, not a missing capability, and must not push the run
    down to a weaker rung.
    """
    global _stream_ok
    if _stream_ok:
        try:
            status, payload, error_text, timing = await _post_stream(
                client, url, headers, body, rtt_ms)
        except httpx.TransportError:
            # A dropped connection says nothing about streaming support.
            raise
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
            _stream_ok = False
            log_note = "stream failed ({0}); falling back".format(type(exc).__name__)
        else:
            if status < 400:
                return status, payload, error_text, timing
            if status >= 500:
                return status, payload, error_text, timing
            _stream_ok = False
            log_note = "provider rejected stream (HTTP {0}); falling back".format(status)
        logging.getLogger("decider").info("%s", log_note)

    return await _post_plain(client, url, headers, body, rtt_ms)


#: How much of an unparseable reply a failed attempt keeps.
FAILED_TEXT_CHARS = 1500


def _reply_text(payload: Dict[str, Any]) -> str:
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    calls = message.get("tool_calls") or []
    if calls:
        return str(calls[0].get("function", {}).get("arguments") or "")
    return str(message.get("content") or "")


async def _ladder(build_body: Callable[[str], Dict[str, Any]],
                  extract: Callable[[str, Dict[str, Any]], Dict[str, Any]],
                  max_tokens: int) -> Dict[str, Any]:
    """Walk the rungs until one answers; shared by the navigator and the goal
    identifier, so both get the same transport retries, truncation doubling
    and memory of rejected rungs.

    `build_body(rung)` gives the request, `extract(rung, payload)` the parsed
    reply or an exception. Returns the winning rung, its parsed result, the
    payload, its timing and every failed attempt; raises VLMError if none.
    """
    headers = {"Content-Type": "application/json"}
    if config.LITELLM_API_KEY:
        headers["Authorization"] = "Bearer " + config.LITELLM_API_KEY
    url = config.LITELLM_BASE_URL + "/v1/chat/completions"

    ladder = [r for r in RUNGS if r not in _unsupported]
    attempts: List[Dict[str, Any]] = []
    started = time.perf_counter()

    http = client()

    # Before the ladder, not inside it: one probe per call, on a
    # connection the real call then reuses.
    rtt_ms = await _probe_rtt(http, config.LITELLM_BASE_URL, headers)

    for rung in ladder:
        # A reply cut off by the token budget is a truncation, not a missing
        # capability. Retrying the same rung with more room is the right
        # answer; dropping to a weaker rung would hide the real cause and
        # make every later step weaker too.
        budget = max_tokens
        attempt = 0
        transport_failures = 0
        while attempt < 2:
            payload = None
            try:
                body = build_body(rung)
                body["max_tokens"] = budget
                status, payload, error_text, timing = await _request(
                    http, url, headers, body, rtt_ms)
                if status >= 400:
                    # 4xx on a well-formed request means the provider does
                    # not support this rung. Remember that; 5xx is transient.
                    if status < 500:
                        _unsupported.add(rung)
                    attempts.append({"rung": rung, "http": status,
                                     "error": error_text[:300]})
                    break
                truncated = (payload.get("choices") or [{}])[0].get("finish_reason") == "length"
                result = extract(rung, payload)
            except (httpx.HTTPError, VLMError, KeyError, ValueError,
                    json.JSONDecodeError) as exc:
                note = {"rung": rung, "error": "{0}: {1}".format(type(exc).__name__, exc)[:300]}
                if isinstance(exc, httpx.TransportError):
                    transport_failures += 1
                    if transport_failures < TRANSPORT_TRIES:
                        note["retry"] = "transport error, same rung"
                        attempts.append(note)
                        continue
                    attempts.append(note)
                    break
                # Keep what the model wrote: a reply that fails to parse is
                # otherwise lost, and 2% of perceiver calls did (probe LD).
                if payload is not None:
                    note["text"] = _reply_text(payload)[:FAILED_TEXT_CHARS]
                retry_worth_it = (attempt == 0 and isinstance(
                    exc, (json.JSONDecodeError, ValueError)))
                if retry_worth_it:
                    note["retry"] = "doubling max_tokens to {0}".format(budget * 2)
                    attempts.append(note)
                    budget *= 2
                    attempt += 1
                    continue
                attempts.append(note)
                break
            if truncated:
                attempts.append({"rung": rung, "error": "finish_reason=length",
                                 "retry": "doubling max_tokens to {0}".format(budget * 2)})
                if attempt == 0:
                    budget *= 2
                    attempt += 1
                    continue

            return {"rung": rung, "result": result, "payload": payload, "timing": timing,
                    "attempts": attempts,
                    "latency_ms": (time.perf_counter() - started) * 1000.0}

    raise VLMError("every rung failed: " + json.dumps(attempts))


async def decide(manifest: Dict[str, Any], frame_b64: str,
                 memory: Optional[List[Dict[str, Any]]] = None,
                 sighting: Optional[str] = None) -> Decision:
    """`memory` is the run's earlier decisions for an agent that has memory,
    None for one that does not (the prompt is then rendered without it).
    `sighting` is the goal identifier's report for this frame, for an agent
    that has one (identify_goal)."""
    indices = schema.visible_indices(manifest)
    if not indices:
        raise VLMError("manifest offers no actions")

    won = await _ladder(
        lambda rung: _body(rung, manifest, frame_b64, indices, memory, sighting),
        lambda rung, payload: _extract(rung, payload, indices),
        config.MAX_TOKENS)
    result, payload = won["result"], won["payload"]
    usage = payload.get("usage") or {}
    return Decision(
        index=result["index"],
        reason=result["reason"],
        rung=won["rung"],
        latency_ms=won["latency_ms"],
        model=payload.get("model", config.VLM_MODEL),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        attempts=won["attempts"],
        raw=result["raw"],
        timing=won["timing"],
        goal=result["goal"],
    )


#: The identifier's reply is a short description and one word.
IDENTIFIER_MAX_TOKENS = 512


@dataclass
class Sighting:
    """The goal identifier's answer for one frame (agent feature
    `goal_identifier`). `goal` is None when it gave no valid report; the step
    then goes on without one, it never fails because of the identifier."""
    goal: Optional[str]
    reason: str = ""
    rung: Optional[str] = None
    latency_ms: float = 0.0
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    raw: str = ""
    timing: Optional[Timing] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "goal": self.goal,
            "reason": self.reason,
            "rung": self.rung,
            "latency_ms": round(self.latency_ms, 1),
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "attempts": self.attempts,
            "raw": self.raw,
            "timing": self.timing.to_dict() if self.timing else None,
        }
        if self.error is not None:
            out["error"] = self.error
        return out


def _identifier_messages(manifest: Dict[str, Any], frame_b64: str,
                         schema_hint: str = "") -> List[Dict[str, Any]]:
    prompt = agent.current().identifier_prompt
    text = prompt.render(prompt, manifest)
    if schema_hint:
        text += "\n\n" + schema_hint
    return [
        {"role": "system", "content": prompt.system},
        {"role": "user", "content": [
            {"type": "text", "text": text},
            {"type": "image_url",
             "image_url": {"url": "data:image/png;base64," + frame_b64}},
        ]},
    ]


def _identifier_body(rung: str, manifest: Dict[str, Any], frame_b64: str) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "model": config.VLM_MODEL,
        "max_tokens": IDENTIFIER_MAX_TOKENS,
        "temperature": config.TEMPERATURE,
    }
    if rung == "json_schema":
        body["messages"] = _identifier_messages(manifest, frame_b64)
        body["response_format"] = schema.identifier_response_format()
    elif rung == "json_object":
        hint = ("Reply with JSON only, matching this schema exactly:\n"
                + json.dumps(schema.identifier_schema()))
        body["messages"] = _identifier_messages(manifest, frame_b64, hint)
        body["response_format"] = {"type": "json_object"}
    elif rung == "tool_call":
        body["messages"] = _identifier_messages(manifest, frame_b64)
        body["tools"] = [schema.identifier_tool_spec()]
        body["tool_choice"] = "required"
    else:
        hint = ('Reply with a line "REASON: ...", then a line "GOAL: '
                + "|".join(schema.GOAL_REPORTS) + '".')
        body["messages"] = _identifier_messages(manifest, frame_b64, hint)
    return body


def _identifier_extract(rung: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Pull (goal, reason, raw) out of an identifier reply, or raise. Unlike
    the navigator, a reply without a valid goal is a failed rung: the goal is
    the identifier's whole answer."""
    message = payload["choices"][0].get("message", {})
    if rung == "tool_call":
        calls = message.get("tool_calls") or []
        if not calls:
            raise VLMError("no tool call in response")
        raw = calls[0]["function"]["arguments"]
        parsed = json.loads(raw)
    elif rung == "text":
        raw = message.get("content") or ""
        goal_match = re.search(r"GOAL:\s*(\w+)", raw)
        reason_match = re.search(r"REASON:\s*(.+)", raw)
        parsed = {"goal": goal_match.group(1).lower() if goal_match else None,
                  "reason": reason_match.group(1).strip() if reason_match else raw.strip()[:500]}
    else:
        raw = message.get("content") or ""
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
        parsed = json.loads(fenced.group(1) if fenced else raw)
    goal = parsed.get("goal")
    if goal not in schema.GOAL_REPORTS:
        raise VLMError("identifier gave no valid goal report: {0!r}".format(goal))
    return {"goal": goal, "reason": str(parsed.get("reason", "")), "raw": raw}


async def identify_goal(manifest: Dict[str, Any], frame_b64: str) -> Sighting:
    """The goal identifier: this frame and nothing else, asked only where the
    goal is. Never raises for a model failure; returns Sighting(goal=None)."""
    try:
        won = await _ladder(
            lambda rung: _identifier_body(rung, manifest, frame_b64),
            _identifier_extract,
            IDENTIFIER_MAX_TOKENS)
    except VLMError as exc:
        return Sighting(goal=None, error=str(exc)[:1000])
    result, payload = won["result"], won["payload"]
    usage = payload.get("usage") or {}
    return Sighting(
        goal=result["goal"],
        reason=result["reason"],
        rung=won["rung"],
        latency_ms=won["latency_ms"],
        model=payload.get("model", config.VLM_MODEL),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        attempts=won["attempts"],
        raw=result["raw"],
        timing=won["timing"],
    )


# --- R9: one structured call per subagent (a13) ----------------------------------

@dataclass
class SubCall:
    """One subagent's reply for one step: the parsed object, or an error. Shaped
    like Sighting so a decision record reads the same for every subagent."""
    name: str
    result: Optional[Dict[str, Any]]
    rung: Optional[str] = None
    latency_ms: float = 0.0
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    raw: str = ""
    timing: Optional[Timing] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "result": self.result,
            "rung": self.rung,
            "latency_ms": round(self.latency_ms, 1),
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "attempts": self.attempts,
            "raw": self.raw,
            "timing": self.timing.to_dict() if self.timing else None,
        }
        if self.error is not None:
            out["error"] = self.error
        return out


def _structured_messages(system: str, text: str, image_b64: Optional[str],
                         hint: str = "",
                         follow_up: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if hint:
        text = text + "\n\n" + hint
    content: Any = text
    if image_b64 is not None:
        # One image, or several in order (w02's strips, R28).
        images = image_b64 if isinstance(image_b64, list) else [image_b64]
        content = [{"type": "text", "text": text}] + [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}
            for b64 in images]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": content}]
    return messages + list(follow_up or [])


def _structured_body(rung: str, name: str, json_schema: Dict[str, Any], system: str,
                     text: str, image_b64: Optional[str], max_tokens: int,
                     follow_up: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    body: Dict[str, Any] = {"model": config.VLM_MODEL, "max_tokens": max_tokens,
                            "temperature": config.TEMPERATURE}
    if rung == "json_schema":
        body["messages"] = _structured_messages(system, text, image_b64, follow_up=follow_up)
        body["response_format"] = {"type": "json_schema", "json_schema": {
            "name": name, "strict": True, "schema": json_schema}}
    elif rung == "json_object":
        hint = "Reply with JSON only, matching this schema exactly:\n" + json.dumps(json_schema)
        body["messages"] = _structured_messages(system, text, image_b64, hint, follow_up)
        body["response_format"] = {"type": "json_object"}
    elif rung == "tool_call":
        body["messages"] = _structured_messages(system, text, image_b64, follow_up=follow_up)
        body["tools"] = [{"type": "function", "function": {
            "name": name, "description": "Give your answer.", "parameters": json_schema}}]
        body["tool_choice"] = "required"
    else:
        hint = ("Reply with one JSON object only, no other text, matching this schema:\n"
                + json.dumps(json_schema))
        body["messages"] = _structured_messages(system, text, image_b64, hint, follow_up)
    return body


def _structured_extract(rung: str, payload: Dict[str, Any],
                        validate: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    message = payload["choices"][0].get("message", {})
    if rung == "tool_call":
        calls = message.get("tool_calls") or []
        if not calls:
            raise VLMError("no tool call in response")
        raw = calls[0]["function"]["arguments"]
        parsed = json.loads(raw)
    else:
        raw = message.get("content") or ""
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
        if fenced:
            parsed = json.loads(fenced.group(1))
        elif rung == "text":
            match = re.search(r"\{.*\}", raw, re.S)
            if not match:
                raise VLMError("no JSON object in response")
            parsed = json.loads(match.group(0))
        else:
            parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise VLMError("reply is not a JSON object")
    return {"parsed": validate(parsed), "raw": raw}


async def call_structured(name: str, system: str, text: str, image_b64: Optional[str],
                          json_schema: Dict[str, Any],
                          validate: Callable[[Dict[str, Any]], Dict[str, Any]],
                          max_tokens: int,
                          follow_up: Optional[List[Dict[str, Any]]] = None) -> SubCall:
    """One subagent call on the shared ladder. `validate` returns the cleaned
    reply or raises VLMError (a failed rung). Never raises for a model failure:
    returns SubCall(result=None, error=...) and the orchestrator decides what
    a missing answer means. `follow_up` appends turns after the first user
    message (the critic's retry)."""
    try:
        won = await _ladder(
            lambda rung: _structured_body(rung, name, json_schema, system, text, image_b64,
                                          max_tokens, follow_up),
            lambda rung, payload: _structured_extract(rung, payload, validate),
            max_tokens)
    except VLMError as exc:
        return SubCall(name=name, result=None, error=str(exc)[:1000])
    usage = won["payload"].get("usage") or {}
    return SubCall(
        name=name,
        result=won["result"]["parsed"],
        rung=won["rung"],
        latency_ms=won["latency_ms"],
        model=won["payload"].get("model", config.VLM_MODEL),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        attempts=won["attempts"],
        raw=won["result"]["raw"],
        timing=won["timing"],
    )
