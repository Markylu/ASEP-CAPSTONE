# R9 probe: a13

Run 2026-10-22 on the Mac against `Qwen3-VL-30B-A3B` (remote profile, :8004), at `8b6056f`, agent
`a13` (`3de550e110e7`). Sets: `perceiver_set.jsonl` (158 clean frames from R5 and R6 flights) and
`trap_set.jsonl` (255 steps from R5 and R6 where the drone stood within 0.85 m of an earlier blocked
move). Results: `perceiver_a13.jsonl`, `trap_a13.jsonl`; log `r9_probe.log`.

    python eval/r9_probe.py report eval/phase2/R9_hail_mary/probe/perceiver_a13.jsonl
    python eval/r9_probe.py report-trap eval/phase2/R9_hail_mary/probe/trap_a13.jsonl

**Result: gate passed on every line.**

## Gate

| Check | Threshold | a13 |
|---|---|---|
| goal strip within one of truth, goal in view | ≥ 90% | **100%** (47/47; exact 95.7%) |
| phantom: goal reported, not in view | ≤ 5% | **3.6%** (4/111) |
| left/ahead/right against g02's in-flight answer, both on truth | not lower by > 5 points | **96.2% vs 96.2%** |
| false wall: completed move whose strip was called "wall close" | ≤ 20% | **6%** (6/100) |
| trap repeat: a13 picks the known-blocked heading again | ≤ 25% | **0.4%** (1/255; recorded agents 36.1%) |

## Not gated, read before flying

- **Goal missed when in view:** 0/47.
- **Wall recall:** 75% of strips where the next move was blocked were called "wall close" (33/44).
- **Distance class exact:** 19.1%. The goal estimate falls back on the distance class when there is
  one sighting, so single-sighting estimates are rough; the ray intersection does not use it.
- **Doorway reported** on 37% of frames.
- **Perceiver latency:** mean 1.96 s (g02 about 0.5 s). Trap steps through the whole a13 step:
  mean 5.1 s, so a 60-step run is about 5 minutes, inside the 900 s wall clock.

## Trap replay

- a13 turned around on 181 of 255 trap steps (71%; the recorded agents 85, 33%). On 177 of those
  181, every forward move carried "blocked here before" or "wall close (seen now)"; only 4 turned
  around with a forward move marked new ground and clear.
- **Critic:** fired 40 times, 39 on "third turn-around in four steps" and 1 on a blocked pick; the
  second answer changed the pick twice. In a corner the spin rule objects and the model keeps the
  turn-around. Whether that becomes a ping-pong in flight is a manipulation-check item
  (`spin_failure`, turn-arounds in a row).
- **Strategist:** asked on 254 of 255 steps (the replay marks it as last asked 8 steps earlier, so
  the blocked and loop triggers fire). It chose no fixed target on 206: R5 and R6 runs carry no
  perceiver reports, so the rebuilt map before each trap step has no seen floor, doorways or
  unexplored ground to offer. **Targets are not tested by this probe**; only flight tests them.
