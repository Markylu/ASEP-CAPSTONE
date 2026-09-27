# Decider service

Answers the simulator's question "which of these numbered actions do I take?"
with a VLM. Runs locally next to Godot; only the model call crosses the network
to the LiteLLM router on the H100.

```
Godot ──POST /decide (frame + manifest)──▶ decider ──▶ LiteLLM ──▶ VLM
      ◀──────────── {index, reason} ──────┘
```

## Why not MCP

MCP hands tools to an agentic host, and that host owns the loop, the retries and
the context window. An experiment needs the opposite: one fixed prompt, one
model tag, a known token count and N identical steps. A thin MCP wrapper over
these same endpoints is the right way to fly the sim by hand for debugging; it
is not the way to produce a number that goes in the paper.

## Setup

```bash
pip install -r server/requirements.txt
cp server/.env.example server/.env   # then fill in LITELLM_BASE_URL / VLM_MODEL
```

`server/.env` is gitignored. Never commit router keys.

## Run

```bash
python -m server.decider --profile remote --port 8000   # off-site router
python -m server.decider --profile local  --port 8000   # model on this laptop
```

`--profile` is sugar for `VLM_PROFILE=...`; `python -m uvicorn
server.decider.app:app --port 8000` still works and takes the profile from
`server/.env`. See "Switching provider" below.

Then, from the repo root, with a window (see "Headless" below):

```bash
godot --path first-project -- \
    --run-id=run_$(date +%Y-%m-%d_%H%M) \
    --decider-url=http://127.0.0.1:8000 \
    --max-steps=30
```

Check it is talking to the right router first: `curl localhost:8000/health`.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /run/start` | Opens `eval/runs/<run_id>/`, stamps model, prompt hash, git SHA |
| `POST /decide` | Frame + manifest in, action index out. Saves the frame. |
| `POST /step` | What the executed action actually did, including collisions |
| `POST /event` | Something in the site changed on its own — a box deployed, a door opened |
| `POST /run/end` | Writes `metrics.json` |
| `GET /health` | Which router and model this process would use |

The service is the only writer of the run directory — it is the side that knows
the model tag, the prompt version and the git SHA. Godot writes nothing to disk.

`/event` writes `events.jsonl`, one line per thing the site did without being
asked. `step` is the 1-based move the event belongs to, the same numbering
`steps.jsonl` uses, so "deployed at step 3" and the step 3 record describe the
same move. `/run/start` also carries `site_id` and `site_version`, which is what
makes a run citable as `s01@v1` — both are null for a run flown on `main.tscn`,
which has no `site.json`.

From those plus `goal.line_of_sight` on each step, `metrics.json` gains
`occlusion_step`, `goal_visible_steps`, `goal_first_hidden_step` and
`steps_to_reacquire`. Each is `null`, never `0`, when the run cannot answer —
an older run with no visibility recorded, or a site with no occluder — because a
zero there would read as a measurement.

## The output contract

`action` is an **enum of exactly the indices drawn on this step's frame**, so
the model cannot name an action the image never offered — the same invariant
`VLMNavController.execute_index()` enforces on the Godot side. `reason` is
declared before `action` so a strict schema makes the model argue before it
commits.

Not every model honours a strict schema, so `vlm.py` walks a ladder and records
which rung answered:

1. `response_format: json_schema`, `strict: true`
2. `response_format: json_object` with the schema in the prompt
3. a single `choose_action` tool call (`tool_choice: "required"`)
4. plain text, `ACTION: <n>` parsed out

A run that used rung 4 is weaker than one that used rung 1, and `metrics.json`
says which under `rungs_used`.

Two rules keep the ladder honest:

- **Only an HTTP 4xx marks a rung unsupported**, and that is remembered for the
  process. A parse failure does not: it is bad luck, not a missing capability,
  and pinning the rest of the run to a weaker rung because of one bad reply
  would quietly degrade every later step.
- **A reply cut off by the token budget is a truncation, not a failure.** The
  same rung is retried with double the budget. Reasoning-first output is long,
  and `finish_reason: length` mid-JSON otherwise looks exactly like a model that
  cannot do schemas.

## Switching provider

Two providers, selected by `VLM_PROFILE` (`remote` | `local`), each reading its
own prefixed vars out of `server/.env`:

| | `remote` | `local` |
|---|---|---|
| what | `Qwen3-VL-30B-A3B` on sctsvr6 (vLLM) | LM Studio / llama.cpp on this laptop |
| vars | `REMOTE_LITELLM_BASE_URL`, `REMOTE_LITELLM_API_KEY`, `REMOTE_VLM_MODEL`, `REMOTE_VLM_TIMEOUT_S`, `REMOTE_VLM_MAX_TOKENS` | the same names under `LOCAL_` |
| default base URL | `http://127.0.0.1:8004` | `http://127.0.0.1:1234` |

Resolution order for each setting: an unprefixed var (`LITELLM_BASE_URL`, …)
wins over the profile's prefixed one, which wins over a built-in default. So a
one-off override — pointing at `fake_litellm.py`, say — needs no profile edit,
and a pre-profile `.env` keeps working unchanged.

The remote profile assumes the tunnel is up:

```bash
ssh -N -L 8004:127.0.0.1:8004 sctsvr6
```

**Not the LiteLLM router on :4000.** That proxy's `model_list` covers the text
models on :8000-:8003 only — MiniMax, DeepSeek, the Qwen coders — and has no
entry for the VL container, so a vision request through it fails on the model
name. `:8004` is that container's own OpenAI-compatible server: the same
interface one hop earlier, image tokens included. Giving the router a VL alias
would work too and would put runs back behind one endpoint; until someone adds
it, `:8004` is the honest address.

`GET /v1/models` on the tunnel reports the served name — `Qwen3-VL-30B-A3B`,
which is what `REMOTE_VLM_MODEL` must say, not the HuggingFace path
(`Qwen/Qwen3-VL-30B-A3B-Instruct-FP8`) it was loaded from.

`GET /health` says which profile the running process resolved, and the profile
name is written into every `run.json` as `vlm_profile`. That matters because
the two are not interchangeable as evidence — see below.

### Against LM Studio (the `local` profile)

LM Studio's OpenAI-compatible server drops into the same slot as LiteLLM. Name
a loaded **vision** model: `GET http://localhost:1234/v1/models` lists what is
loaded, and just-in-time loading means the first call can take a minute.

Two things differ from LiteLLM and are worth knowing before reading any number
off a `local` run:

- **It does not count image tokens.** A frame that should be ~1000 prompt tokens
  is reported as ~30. `tokens_per_frame` and anything cost-shaped in
  `metrics.json` is therefore meaningless here. Latency and behaviour are real;
  token economics are not.
- **It rejects `response_format: {"type": "json_object"}`** ("must be
  'json_schema' or 'text'"), so rung 2 is permanently skipped after the first
  step. Harmless — rung 1 is what it does support.

## Testing without a model

`fake_litellm.py` is a stand-in router. It does not look at the image — it picks
the straightest heading, or cycles the fan — so it proves the plumbing and
nothing about navigation. Never point a run that produces numbers at it.

```bash
python -m uvicorn server.decider.fake_litellm:app --port 4001
LITELLM_BASE_URL=http://127.0.0.1:4001 VLM_MODEL=stub \
    python -m uvicorn server.decider.app:app --port 8000
```

`FAKE_PICK=cycle` walks the whole fan instead of flying straight.
`FAKE_SUPPORTS=text` makes it reject the upper rungs, which is how the fallback
ladder gets tested.
`FAKE_DELAY=5` holds every reply five seconds, standing in for model latency.

## Headless

Godot's `--headless` uses a dummy display server and does not render, so there
is no frame to send. VLM runs must be windowed. This matters for any plan to
sweep runs unattended on the H100 — that needs a real GPU context there, not
`--headless`.
