"""Smoke for a60 (R27): the real step (orchestrator.decide) on recorded R25D
manifests and their real clean frames, with stub model replies. No model calls.

The perceiver stub answers the clean frame with the step's recorded reading
and the mirrored frame with that reading mirrored, so the step's fused reading
must equal the recorded one. Checks: no failed step, one mirrored read per step
on a frame whose bytes differ from the clean frame, fused = recorded.

    VLM_AGENT=a60 python eval/probes/a60_smoke.py
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

os.environ.setdefault("VLM_AGENT", "a60")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load, runs  # noqa: E402

ROUND = "R25D"


def main() -> int:
    from server.decider import orchestrator, recorder, schema, vlm
    cur = {}

    def mirrored(result):
        swap = orchestrator.MIRRORED
        lanes = {swap[l["strip"]]: dict(l, strip=swap[l["strip"]]) for l in result["lanes"]}
        return dict(result, goal=swap.get(result["goal"], result["goal"]),
                    lanes=[lanes[s] for s in schema.STRIPS])

    async def stub(name, system, text, image_b64, json_schema, validate, max_tokens,
                   follow_up=None):
        rec = cur["rec"]
        if name == schema.PERCEIVER_SCHEMA_NAME:
            assert "reason" not in json_schema["properties"], "a60 asks g07, no reason"
            result = (rec.get("perceiver") or {}).get("result")
            if image_b64 != cur["clean"]:
                cur["mirror_calls"] += 1
                return vlm.SubCall(name, mirrored(result) if result else None, "stub")
            return vlm.SubCall(name, result, "stub")
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
    steps = failed = same = recorded = 0
    cur["mirror_calls"] = 0
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        for run in runs(25, 25):
            if run["round"] != ROUND:
                continue
            rows = [x for x in load(run["path"]) if x.get("clean_frame")]
            r = recorder.Run("smoke-{0}-{1}".format(run["site"], run["arm"]),
                             Path(tmp) / run["site"] / run["arm"])
            r.ensure()
            for rec in rows:
                cur["rec"] = rec
                cur["clean"] = base64.b64encode(
                    (run["path"] / rec["clean_frame"]).read_bytes()).decode()
                request = types.SimpleNamespace(
                    manifest=rec["manifest"], step=rec["step"], frame_size=rec.get("frame_size"),
                    frame_png_b64="AA==", clean_frame_png_b64=cur["clean"])
                asyncio.run(orchestrator.decide(request, r, rec.get("frame")))
            for out, rec in zip(recorder._read_jsonl(r.decisions), rows):
                steps += 1
                failed += bool(out.get("error"))
                want = (rec.get("perceiver") or {}).get("result")
                if want is not None:
                    recorded += 1
                    same += ((out.get("perceiver") or {}).get("result") == want
                             and out.get("perceiver_mirror") is not None)
    secs = time.time() - t0
    ok = failed == 0 and steps > 0 and cur["mirror_calls"] == steps and same == recorded
    print("a60 smoke on {0}: {1} steps, failed {2}; mirrored reads {3}; fused = recorded on "
          "{4}/{5}; {6:.2f} s per step -> {7}".format(
              ROUND, steps, failed, cur["mirror_calls"], same, recorded, secs / max(1, steps),
              "pass" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
