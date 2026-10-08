"""HTTP contract between the Godot sim and the VLM.

    POST /run/start   open a run directory
    POST /decide      frame + manifest -> action index
    POST /step        what the executed action actually did
    POST /event       something in the site changed under the agent
    POST /run/end     close the run, write metrics.json

Deliberately not MCP. MCP hands tools to an agentic host, and that host owns the
loop, the retries and the context window — which is the opposite of what an
experiment needs. A thin MCP wrapper over these same endpoints is the right way
to fly the sim by hand; it is not the way to produce a number.

    uvicorn server.decider.app:app --port 8000
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import config, prompt, vlm
from .recorder import Run, resolve_run_dir

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger("decider")

app = FastAPI(title="VLMnav decider", version=prompt.PROMPT_VERSION)


@app.on_event("shutdown")
async def _close_vlm_client() -> None:
    """The HTTP client outlives single decisions so connections are reused."""
    await vlm.aclose()


class StartRequest(BaseModel):
    run_id: str
    scene: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    frame_size: Optional[list] = None
    godot_version: Optional[str] = None
    max_steps: Optional[int] = None
    # Which geometry, at which version. A run is only citable next to both:
    # `s01@v1` has to mean one fixed map forever (notes/PLAN.md §5.1). Null for
    # a run flown on the unmigrated main.tscn sandbox, which has no site.json.
    site_id: Optional[str] = None
    site_version: Optional[int] = None
    # Site props move in whole physics ticks, so the tick rate is part of what
    # makes a trajectory reproducible.
    physics_ticks_per_second: Optional[int] = None
    # Whether the world was paused for each /decide. Frozen and unfrozen runs
    # are not comparable: unfrozen, props advance by however long the model
    # took. Null for runs from before the flag existed, which were unfrozen.
    freeze_world: Optional[bool] = None
    # Door banks disarmed for the whole run (control arm). Null = not set.
    static_doors: Optional[bool] = None
    # Phase 1 arm: dynamic | initial | final (docs/phase1-test-plan.md §5).
    world: Optional[str] = None
    # Seeded spawn jitter and the offset it produced (§7.3).
    spawn_seed: Optional[int] = None
    spawn_offset: Optional[Dict[str, Any]] = None
    # s03 `final` arm: which fork bank was closed at load.
    final_closed: Optional[list] = None
    # Repo-relative directory to record into, under eval/. Null = RUNS_DIR/run_id.
    run_dir: Optional[str] = None


class DecideRequest(BaseModel):
    run_id: str
    step: int
    manifest: Dict[str, Any]
    frame_png_b64: str = Field(repr=False)
    frame_size: Optional[list] = None


class StepRequest(BaseModel):
    run_id: str
    pose: Dict[str, Any]
    # Carried so steps.jsonl stands on its own: a scripted run or a replay has
    # no decisions.jsonl for metrics to read arrival out of.
    goal: Optional[Dict[str, Any]] = None


class EventRequest(BaseModel):
    """Something in the site changed on its own — a box deployed, a door opened.

    Kept beside the steps rather than inside them so the run still reads
    chronologically when the agent is sitting still, and so an event that fires
    between two steps is not lost.
    """

    run_id: str
    name: str
    step: Optional[int] = None
    data: Optional[Dict[str, Any]] = None


class EndRequest(BaseModel):
    run_id: str
    reason: str = "unspecified"
    steps: Optional[int] = None


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "profile": config.VLM_PROFILE,
        "model": config.VLM_MODEL,
        "litellm_base_url": config.LITELLM_BASE_URL,
        "prompt_version": prompt.PROMPT_VERSION,
        "prompt_sha": prompt.prompt_sha(),
        "runs_dir": str(config.RUNS_DIR),
    }


@app.post("/run/start")
def run_start(request: StartRequest):
    meta = request.model_dump(exclude={"run_id"}, exclude_none=True)
    run_dir = None
    if request.run_dir:
        try:
            run_dir = resolve_run_dir(request.run_dir)
        except ValueError as exc:
            log.error("run %s refused: %s", request.run_id, exc)
            return JSONResponse({"error": str(exc)}, status_code=400)
    run = Run(request.run_id, run_dir)
    record = run.start(meta)
    log.info("run %s started -> %s", request.run_id, run.dir)
    return {"ok": True, "run": record}


@app.post("/decide")
async def decide(request: DecideRequest):
    run = Run(request.run_id)
    frame_path = run.save_frame(request.step, request.frame_png_b64)

    try:
        decision = await vlm.decide(request.manifest, request.frame_png_b64)
    except Exception as exc:
        message = "{0}: {1}".format(type(exc).__name__, exc)
        run.record_decision({
            "step": request.step,
            "frame": frame_path,
            "manifest": request.manifest,
            "error": message,
        })
        log.error("step %d decision failed: %s", request.step, message)
        # 200 with an error body: the client treats this as a failed run, and a
        # transport-level 500 would be indistinguishable from the service being
        # down, which is a different thing to report in the run record.
        return JSONResponse({"error": message}, status_code=200)

    record = decision.to_dict()
    record.update({
        "step": request.step,
        "frame": frame_path,
        "frame_size": request.frame_size,
        "manifest": request.manifest,
        "prompt_version": prompt.PROMPT_VERSION,
        "prompt_sha": prompt.prompt_sha(),
    })
    run.record_decision(record)
    timing = decision.timing.to_dict() if decision.timing else {}
    # net/gpu at a glance: a step that is slow because of the tunnel and one
    # that is slow because of the image look identical in a single total.
    split = ""
    if timing.get("compute_ms") is not None:
        split = " (net {0:.0f} + gpu {1:.0f})".format(
            timing.get("network_ms") or 0.0, timing["compute_ms"])
    log.info("step %-3d -> [%d] %-6s %6.0fms%s  %s",
             request.step, decision.index, decision.rung, decision.latency_ms,
             split, decision.reason[:80].replace("\n", " "))
    return {"index": decision.index, "reason": decision.reason,
            "rung": decision.rung, "latency_ms": decision.latency_ms}


@app.post("/step")
def step(request: StepRequest) -> Dict[str, Any]:
    Run(request.run_id).record_step(request.pose, request.goal)
    return {"ok": True}


@app.post("/event")
def event(request: EventRequest) -> Dict[str, Any]:
    Run(request.run_id).record_event(request.name, request.step, request.data)
    log.info("event %s at step %s", request.name, request.step)
    return {"ok": True}


@app.post("/run/end")
def run_end(request: EndRequest) -> Dict[str, Any]:
    metrics = Run(request.run_id).finish(request.reason, request.steps)
    log.info("run %s ended: %s | %d steps, %d collisions, goal_reached=%s",
             request.run_id, request.reason, metrics["steps"],
             metrics["collisions"], metrics["goal_reached"])
    return {"ok": True, "metrics": metrics}
