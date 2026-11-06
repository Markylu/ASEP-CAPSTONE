"""Smoke for a63 / a64 (R30): the real step (orchestrator.decide) on recorded
R25D manifests, with stub model replies. No model calls.

The perceiver stub answers with the step's recorded g05 reading and the door
confirmer stub with the step's recorded d01 verdicts, so the memory a63
builds is the one a49 would have built plus a17d's additions; the navigator
stub (a63) picks the recorded action. Checks: no failed step, a planner record
with a route on every step, no view leak, and for a64 the rung "code" with an
offered index on every step.

Real clean frames are used where the run's frames are on disk; elsewhere a
stand-in, since no stub looks at the image.

a78's dead-end confirmer stub answers SMOKE_DEAD_END: "s03" (the default: yes
on s03 runs, no elsewhere), "yes" or "no". It stands in for a model whose
answers are not known yet (probe DE), to run the latch's code on real steps.

    VLM_AGENT=a63 python eval/probes/a63_smoke.py
    VLM_AGENT=a64 python eval/probes/a63_smoke.py
    VLM_AGENT=a78 SMOKE_DEAD_END=yes python eval/probes/a63_smoke.py
"""
from __future__ import annotations

import asyncio
import base64
import collections
import os
import sys
import tempfile
import time
import types
from pathlib import Path

os.environ.setdefault("VLM_AGENT", "a63")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO_ROOT, load, runs  # noqa: E402

ROUND = "R25D"
STAND_IN = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR4nGNgAAAAAgABSK+kcQAA"
            "AABJRU5ErkJggg==")


def run_dir(run):
    if Path(run["path"]).exists():
        return Path(run["path"])
    return (REPO_ROOT / "eval" / "phase2" / run["folder"] / "runs" / run["site"] / run["arm"]
            / run["seed"])


def main() -> int:
    from server.decider import agent, orchestrator, recorder, schema, vlm
    version = agent.current().version
    cur = {}

    async def stub(name, system, text, image_b64, json_schema, validate, max_tokens,
                   follow_up=None):
        rec = cur["rec"]
        if name == schema.PERCEIVER_SCHEMA_NAME:
            return vlm.SubCall(name, (rec.get("perceiver") or {}).get("result"), "stub")
        if name == schema.DOOR_CONFIRMER_SCHEMA_NAME:
            strips = [k for k in json_schema["properties"] if k != "reason"]
            had = ((rec.get("door_confirmer") or {}).get("result") or {})
            reply = dict({"reason": "stub"}, **{s: had.get(s, "open") for s in strips})
            return vlm.SubCall(name, validate(reply), "stub")
        if name == schema.DEAD_END_CONFIRMER_SCHEMA_NAME:
            say = os.environ.get("SMOKE_DEAD_END", "s03")
            answer = ("yes" if cur["site"] == "s03" else "no") if say == "s03" else say
            return vlm.SubCall(name, validate({"reason": "stub", "dead_end": answer}), "stub")
        if name == schema.STRATEGIST_SCHEMA_NAME:
            raise AssertionError("a63 never asks a strategist")
        enum = json_schema["properties"]["action"]["enum"]
        pick = rec["index"] if rec.get("index") in enum else enum[0]
        return vlm.SubCall(name, validate({"action": pick, "reason": "stub"}), "stub")

    vlm.call_structured = stub
    steps = failed = planned = real = coded = 0
    fallbacks = collections.Counter()
    stalls = door_walls = suspects = behind = critic = 0
    asked = said_yes = latched = latched_out = latched_runs = 0
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        for run in runs(25, 25):
            if run["round"] != ROUND:
                continue
            path = run_dir(run)
            rows = [x for x in load(path) if x.get("clean_frame")]
            r = recorder.Run("smoke-{0}-{1}".format(run["site"], run["arm"]),
                             Path(tmp) / run["site"] / run["arm"])
            r.ensure()
            cur["site"] = run["site"]
            run_latched = False
            for rec in rows:
                cur["rec"] = rec
                frame = path / rec["clean_frame"]
                if frame.exists():
                    real += 1
                    clean = base64.b64encode(frame.read_bytes()).decode()
                else:
                    clean = STAND_IN
                request = types.SimpleNamespace(
                    manifest=rec["manifest"], step=rec["step"], frame_size=rec.get("frame_size"),
                    frame_png_b64="AA==", clean_frame_png_b64=clean)
                asyncio.run(orchestrator.decide(request, r, rec.get("frame")))
            for out in recorder._read_jsonl(r.decisions):
                steps += 1
                if out.get("error"):
                    failed += 1
                    print("  failed step", out.get("step"), out["error"][:120])
                    continue
                plan = out.get("planner") or {}
                planned += plan.get("path_m") is not None and plan.get("waypoint") is not None
                fallbacks[plan.get("fallback")] += 1
                stalls += bool(plan.get("stall"))
                snap = out.get("spatial") or {}
                door_walls += snap.get("cells_door_wall", 0) > 0
                suspects += snap.get("cells_suspect", 0) > 0
                if out.get("rung") == "code":
                    coded += out["index"] in [a["index"] for a in out["manifest"]["actions"]]
                behind += bool(out.get("route_behind"))
                critic += bool(out.get("critic"))
                answer = (out.get("dead_end_confirmer") or {}).get("result")
                asked += answer is not None
                said_yes += bool(answer and answer["dead_end"] == "yes")
                latch = plan.get("latch")
                latched += bool(latch)
                latched_out += bool(latch and latch["out"])
                run_latched = run_latched or bool(latch)
            latched_runs += run_latched
    secs = time.time() - t0
    ok = failed == 0 and steps > 0 and planned == steps
    if version == "a64":
        ok = ok and coded == steps
    print("{0} smoke on {1}: {2} steps ({3} real frames), failed {4}; planned {5}/{2}; "
          "fallbacks {6}; stall steps {7}; steps with door walls {8}, with suspects {9}; "
          "code picks {10}; route-behind sentences {11}, critic asks {12}; "
          "{13:.2f} s per step -> {14}".format(
              version, ROUND, steps, real, failed, planned, dict(fallbacks), stalls, door_walls,
              suspects, coded, behind, critic, secs / max(1, steps), "pass" if ok else "FAIL"))
    if version == "a78":
        print("  dead-end confirmer asked on {0} steps, yes on {1}; latch held on {2} steps "
              "in {3} runs, {4} of them after the drone was out".format(
                  asked, said_yes, latched, latched_runs, latched_out))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
