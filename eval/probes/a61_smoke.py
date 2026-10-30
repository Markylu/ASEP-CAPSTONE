"""Smoke for a61 (R28): the real step (orchestrator.decide) on recorded R25D
manifests, with stub model replies. No model calls.

The perceiver stub answers with the step's recorded g05 reading, and the wall
reader stub with that reading's floor ends, so the step's merged reading must
equal the recorded one. Checks: no failed step, one wall-reader call per step,
merged = recorded, and a wall-reader record on every step.

Real clean frames are used where the run's frames are on disk (the lanes on
sctsvr6); elsewhere a stand-in frame, since neither stub looks at the image.

    VLM_AGENT=a61 python eval/probes/a61_smoke.py
"""
from __future__ import annotations

import asyncio
import base64
import os
import sys
import tempfile
import time
import types
from pathlib import Path

os.environ.setdefault("VLM_AGENT", "a61")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO_ROOT, load, runs  # noqa: E402

ROUND = "R25D"
#: A 1x1 PNG, for runs whose frames are not on this machine.
STAND_IN = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR4nGNgAAAAAgABSK+kcQAA"
            "AABJRU5ErkJggg==")


def run_dir(run):
    """The run's folder: the lane copy where it exists, else the repo's."""
    if Path(run["path"]).exists():
        return Path(run["path"])
    return (REPO_ROOT / "eval" / "phase2" / run["folder"] / "runs" / run["site"] / run["arm"]
            / run["seed"])


def main() -> int:
    from server.decider import orchestrator, recorder, schema, vlm
    cur = {}

    async def stub(name, system, text, image_b64, json_schema, validate, max_tokens,
                   follow_up=None):
        rec = cur["rec"]
        if name == schema.PERCEIVER_SCHEMA_NAME:
            return vlm.SubCall(name, (rec.get("perceiver") or {}).get("result"), "stub")
        if name == schema.WALL_READER_SCHEMA_NAME:
            cur["wall_calls"] += 1
            assert set(json_schema["properties"]) == {"reason"} | set(schema.STRIPS)
            result = (rec.get("perceiver") or {}).get("result")
            if not result:
                return vlm.SubCall(name, None, "stub")
            reply = dict({"reason": "stub"},
                         **{l["strip"]: {"floor": l["floor_end"]} for l in result["lanes"]})
            return vlm.SubCall(name, validate(reply), "stub")
        if name == schema.STRATEGIST_SCHEMA_NAME:
            ids = json_schema["properties"]["target"]["enum"]
            return vlm.SubCall(name, validate({"reason": "stub", "mode": "explore",
                                               "target": ids[0]}), "stub")
        if name == schema.DOOR_CONFIRMER_SCHEMA_NAME:  # keep every report
            strips = [k for k in json_schema["properties"] if k != "reason"]
            return vlm.SubCall(name, validate(dict({"reason": "stub"},
                                                   **{s: "open" for s in strips})), "stub")
        enum = json_schema["properties"]["action"]["enum"]
        pick = rec["index"] if rec.get("index") in enum else enum[0]
        return vlm.SubCall(name, validate({"action": pick, "reason": "stub"}), "stub")

    vlm.call_structured = stub
    steps = failed = same = recorded = walled = real = 0
    cur["wall_calls"] = 0
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
            for out, rec in zip(recorder._read_jsonl(r.decisions), rows):
                steps += 1
                failed += bool(out.get("error"))
                walled += out.get("wall_reader") is not None
                want = (rec.get("perceiver") or {}).get("result")
                if want is not None:
                    recorded += 1
                    got = (out.get("perceiver") or {}).get("result")
                    same += got == want and (out.get("perceiver") or {}).get("result_own") == want
    secs = time.time() - t0
    ok = (failed == 0 and steps > 0 and cur["wall_calls"] == steps and walled == steps
          and same == recorded)
    print("a61 smoke on {0}: {1} steps ({2} real frames), failed {3}; wall-reader calls {4}, "
          "records {5}; merged = recorded on {6}/{7}; {8:.2f} s per step -> {9}".format(
              ROUND, steps, real, failed, cur["wall_calls"], walled, same, recorded,
              secs / max(1, steps), "pass" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
