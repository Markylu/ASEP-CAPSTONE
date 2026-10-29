# Probe plan: test the idea behind each candidate before building a round

Companion to [spatial-memory-and-prompting.md](spatial-memory-and-prompting.md). Each candidate rests
on one belief taken from the literature. Each probe below tests that belief on our own recorded
runs, before any agent version is written. A probe that fails means the candidate is dropped, not
tuned.

Rules carried over from the Phase 2 test plan:
- **Gate first.** Each probe's gate is committed before its first model call (§4 step 2).
- **4 model instances at most, counting :8004.** Extra Qwen3-VL-30B-A3B vLLM instances (one GPU
  each, same weights and settings as :8004) may be started to run probes in parallel. Never more
  than 4 instances at once, and stop the extras when the batch ends. Check
  `nvidia-smi --query-compute-apps` before starting one. Whether the idle TP=2 vLLM on GPUs 0–1
  counts toward the 4 is still open; ask before going past 4 GPUs in use.
- **Flights keep :8004.** Probes may use :8004 only while no round is flying. The offline probes
  use CPU only and may run beside a flight.
- **The tunnel belongs to the operator.** Probes run on sctsvr6 itself, so they do not need it.
  Pushing code there and reading results back goes over plain ssh. If the host cannot be reached,
  stop and say so.
- **Same model.** Qwen3-VL-30B-A3B, temperature 0, the recorded prompts unless the probe changes one.

Where things run: **everything on sctsvr6.** That host has all the data: `decisions.jsonl` and the
frames (gitignored, R6 on) on the lane checkouts `asep-rNN-l1..4`. Running every probe there means
one checkout, one code SHA and no tunnel dependence.

Code: all probes need `phase2/r13-verify` (this branch is cut from `main` and has no decider
code). One branch off it, `research/probes`, pushed and checked out on sctsvr6. Scripts live in
`eval/probes/<id>.py`. Outputs go to `eval/phase2/_probes/<id>/` (`items.jsonl`, `calls.jsonl`,
`score.txt`, and a `README.md` holding the gate and result), committed from sctsvr6 and pulled back.

## Order

| Batch | Probes | Load | Model calls |
|---|---|---|---|
| 0 | Lane index | CPU | 0 |
| 1 | A0, B0, E0 | CPU | 0 |
| 2 | N1 | GPU 2 (existing vLLM) | ~80 |
| 3 | A1 | GPU 2 (existing vLLM) | ~900 |
| 4 | C1 + F1 (one frame sample) | GPU 2 (existing vLLM) | ~1,200 |
| 5 | D1 | GPU 2 (existing vLLM) | ~600 |

**Batch 0, lane index.** `eval/probes/lanes.py` reads each round's `phase.json` "lanes" field. It
writes `eval/phase2/_probes/lanes.jsonl`, one row per run (round, site, arm), giving that run's
directory on its lane, whether frames are present, and the frame count. Every later probe loads runs
through this index, never through a hard-coded path. Check before going on: every R15–R26N run is
found, and every run from R6 on has frames.

Batches 3–5 may run side by side, one per model instance. N1 runs first and on its own: its
*alone* arm needs an instance with no other traffic. A fresh instance must first reproduce a few
recorded :8004 perceiver calls; if it does not match :8004 as closely as :8004 matches itself, it is
not a stand-in. Every call records which instance answered it.

N1 comes before the other model probes. Its noise figure decides how large an effect A1, C1, F1 and
D1 must show before it counts.

---

## N. Noise: is the step-0 lottery caused by batching?

**Belief.** Temperature 0 is not deterministic on a shared server, because batch composition
changes kernel reduction order (Thinking Machines, 2025). If that holds, the ±1.4 spread between
rounds is host noise, not agent behaviour. That bounds what any 18-run round can show.

**N1, repeat calls (sctsvr6).**
- Inputs: the byte-identical step-0 clean frames of s02 and s03 (`f000000.png`, as in `why_14.md` §4),
  with g05 at a49's settings.
- Arm *alone*: 20 sequential calls per frame, concurrency 1, no other load.
- Arm *loaded*: 20 calls per frame, with 7 parallel filler requests (recorded perceiver calls)
  running beside each one.
- Score: unique raw outputs per arm, and strip classes (floor, doorway) that differ from the arm's
  mode.
- Reuse: the `vlm.call_structured` loop from `r16_confirm_probe.py`.

**Gate (set before).**
- Belief holds if *alone* gives ≤ 2 unique outputs per frame and *loaded* gives ≥ 5.
- It is refuted if *alone* is as varied as *loaded*. Then the noise is in the model path itself,
  and a batch-invariant host would not help.

**Outcome feeds:**
- the effect sizes required of A1, C1, F1 and D1: at least 2× the strip disagreement rate seen
  under load;
- the operator's decision on `VLLM_BATCH_INVARIANT=1`, which is not part of this plan.

---

## A. Menu order: does the model pick by position or by content?

**Belief.** LLMs favour some list positions and labels, with swings of 13–75 points (Zheng 2024;
Pezeshkpour 2024). If ours does, menu order is a hidden lever and part of every past result.

**A0, offline (no model).**
- Strategist: every recorded call with a `menu` (R11 on). Record each item's position, its kind
  (frontier, doorway, backtrack, explore) and whether geo says it gets closer to the goal
  (`geo.world`, `segment_clear`).
- Navigator: every call. Record the picked index, its tags (`toward`, `doorway`, `searched`) and its
  angle.
- Fit pick ~ position + kind + good for the strategist, and pick ~ angle + tags for the navigator.
  For the navigator, angle and position are the same thing, so read that part as left/right lean only.
- Also report: when a `back_to_step_N` item is listed, how often is it picked? (This is the "listed
  but ignored" pattern behind B.)
- Reuse: `spatial_replay.runs_under`, `spatial_replay.label`, `agent_evidence.run_dirs`.

**A1, permutation (local, text).**
- Inputs: up to 300 recorded q03 strategist calls with at least 3 items (R19–R26N, a49 family first).
- Re-ask each in three orders: recorded, reversed, and one fixed shuffle. Item IDs and wording stay
  the same; `explore` stays last.
- Render with `planner.detour_situation` and `orchestrator._strategy` (pattern:
  `r26_other_way_probe.py run`).
- Score:
  - *consistency*: the same item ID is picked in all three orders;
  - the pick rate of the first-listed item, whatever it is.

**Gate (set before).**
- Belief refuted (drop A) if consistency ≥ 90% and the first-listed rate moves ≤ 5 points across
  orders.
- Belief holds if consistency ≤ 75% or the first-listed rate moves ≥ 15 points. Then the next step
  is a round that orders the menu by code rank (best first), not a shuffle.
- Between those bands, no call: report the numbers and move on.

---

## B. Dead ends: should code, not the model, decide that a pocket is exhausted?

**Belief.** When the model keeps ignoring a listed way out (25 of 33 calls, 0 picks), asking again
in new words will not work (R26: 9/18). Frontier explorers (VLFM, 3D-Mem) and CogEval's loop
finding say: let code detect that the pocket is used up, and move the target.

**B0, offline (no model).**
- Write 2–3 candidate exhaustion rules as pure functions of the rebuilt memory (`spatial.rebuild`,
  `search_frontiers`). Starting point: the staged policies' `ask = "exhausted"` (`planner.py`
  L719). Candidates:
  - **R-pocket:** the last 10 poses fit within a 3 m radius, and no listed frontier is more than
    3 m of path away from that circle.
  - **R-blacklist:** every top-3 frontier is within 1.5 m of a failed detour, and `goal_way` is
    walled.
  - **R-stall:** under 1 m of net gain toward the goal over 12 steps with the goal way walled.
- On fire, the rule's target is the best frontier more than 3 m of path outside the pocket.
- Replay every recorded run from R15 to R26N. For each rule, record the first fire step and the
  target there.
- Score against geo:
  - **Hit:** fires in the s03 shut-tine failures (the five in `s03_tines_analysis.md`, plus R25D s03
    `final`) within 5 steps of first reaching the exit wall.
  - **Useful target:** the target sits on the crossbar or in the other tine (geo regions as in
    `R17_doorway_first/s03_analysis.md`), and BFS path length plus the steps used fit in 60.
  - **Harm:** fires before success in runs that were solved, and any fire in `initial`.

**Gate (set before).** A rule passes only if all three hold:
- hits ≥ 5 of the 6 tine failures;
- a useful target on ≥ 80% of its fires in failed runs;
- fires before success in ≤ 10% of solved runs.

If no rule passes, the belief that "the pocket is detectable from our memory" is refuted, and B is
dropped. That points back at the memory, not the prompt.

---

## C. Mirrored second read: does agreement between two views clean up perception?

**Belief.** Temperature is locked at 0, but we can still get a second, independent read by
changing the input. Keeping only what both reads agree on should cut noise and cancel any
left/right lean (self-consistency; egocentric left/right studies).

**C1 (sctsvr6).**
- Sample: 300 clean frames from s02 and s03 runs, R22–R26N (a17b family). Stratify by arm and by
  door in view (`geo.open_doors`, `r12_probe.in_view`). The same sample serves F1.
- Three calls per frame with g05:
  - original;
  - the original again (noise control);
  - mirrored left-right, with `far_left↔far_right`, `left↔right` and goal strip swapped back on
    the result.
- Score per strip against geo rays (reuse `r12_probe` `score-g04` geometry, and `r20_door_probe.genuine`
  for doorways):
  - accuracy of a single read;
  - agreement rate between original and mirror;
  - accuracy of the strips where the two agree;
  - left-strip vs right-strip error, to measure lean.

**Gate (set before).** The belief holds if either:
- agreed strips are ≥ 5 points more accurate than single reads, with agreement ≥ 80%; or
- the left-vs-right error gap is ≥ 10 points on the original reads and ≤ 3 points on agreed strips.

It is refuted if mirror-vs-original disagreement is no higher than original-vs-original. Then the
mirror adds nothing that a plain repeat would not.

---

## D. Doorway marked on the image: does a visible mark beat a text note?

**Belief.** Open-source VLMs gain more from marks on the image than from the same fact in text
(PIVOT, VLMnav, disjoint-frames study). Our doorway lives only in text tags today (§4).

**D1 (sctsvr6).**
- Inputs: s02 navigator calls from a17b rounds within 3 m of the open door, with the doorway
  listed in memory. Use the recorded annotated frame `frames/f*.png` and the recorded
  `navigator_text`.
- Four variants:
  1. **Control:** recorded frame and text, re-asked. This measures the noise.
  2. **Marked:** a ring and the word "DOOR" drawn with PIL at the doorway's projection. Bearing
     comes from memory; `spatial.strip_offset`'s pinhole model (87°, 768 px) gives the image column.
  3. **Marked + tag:** variant 2 plus the text "doorway (marked on the image)" on that action.
  4. **False mark:** the same drawing on the shut door's bearing, in s02 frames where it is in view.
- Score:
  - the rate of picking a move through the open door (`r23_nav_probe` `through` set, geo
    `segment_clear`);
  - for variant 4, the rate of picking the move toward the false mark.
- Reuse: the `r23_nav_probe.py` sampling and scoring, plus a PIL draw helper.

**Gate (set before).**
- Belief holds if variant 2 or 3 raises the through rate ≥ 15 points over variant 1, and variant 4
  raises moves toward the shut door by ≤ 5 points over variant 1.
- If marks are obeyed blindly (variant 4 up ≥ 15 points), the round would depend on perceiver
  doorway accuracy. Record that, and go no further without d01 numbers on the same frames.

---

## E. Stale memory: do old blocks and "searched" cells mislead after a door switch?

**Belief.** A map for a changing world has to forget (DynaMem, LiSoNav, EvoNav). Doorways already
update newest-first. Blocks and seen cells never expire, so after a switch, old verdicts may point
the drone away from the new way.

**E0, offline (no model).**
- Inputs: every s02 and s03 `dynamic` run, a17 and a17b families. Find the switch step
  (`doors_switched` / geo `world(site, arm, step)`).
- After the switch, for each navigator call:
  - does an action carry "blocked here before" that geo now says is clear (`segment_clear`)?
  - does it carry "searched already this way" pointing through a door that is now open?
  - is there a wall cell within 1 m of a now-open doorway?
- Rebuild with `spatial.rebuild` and `spatial.project` as in `r22_floor_ends_probe.py`.
- Score: stale tags per run, and whether they fall on the action that leads to the open door; then
  solved rates for runs with and without them.

**Gate (set before).**
- Belief holds if ≥ 30% of dynamic runs show at least one stale tag on the door-ward action. The
  next step is then an expiry rule: a later look that sees floor clears the block or seen cell.
- Below 10%: drop E.

---

## F. Perceiver reasoning first: does writing a reason hurt the reading?

**Belief.** Deliberating in words can hurt visual recognition ("Mind Your Step"), and strict JSON
helps classification but hurts reasoning ("Let Me Speak Freely?"). g05 writes a reason first under
strict JSON, which is the worst of both for a pure reader.

**F1 (sctsvr6, same 300 frames as C1).**
- Variant g05-nr: g05's schema without `reason`, and its instruction to describe each strip removed.
  Classes and wording are otherwise the same.
- One call per frame. Score exactly as C1 (per-strip floor and doorway accuracy, goal strip).
- Compare to C1's original read, using C1's original-vs-repeat noise as the band.

**Gate (set before).**
- Belief holds if g05-nr is ≥ 3 points more accurate on floor or doorway, and no worse than −1 on
  the goal strip.
- Refuted if g05-nr is ≥ 3 points worse: reasoning helps our perceiver, so keep it.

---

## Results so far

| Probe | Run | Result | Belief |
|---|---|---|---|
| Batch 0, lane index | 2026-10-29 | 702/702 repo runs found on the lanes, all R15–R26N among them, and every lane copy matches the repo. **Check fails on R6 only**: none of its 18 runs has frames on the lanes. No planned probe uses R6 frames | — |
| A0 | 2026-10-29 | Position effect +41/+42 pts (first-listed picked 49–57%, later 8–16%); content effect +8/+9 pts. Navigator lean −32 pts (right favoured on "toward"), but ties go left 70% | Position signal **yes** → A1 first. Lean flagged for C1 |
| B0 | 2026-10-29 | All three rules fail (hits 0–1 of 17). In the shut tine `planner.way` reads `open` on 78% of decisions, so no rule could fire | **Refuted**, B dropped. The gap is `goal_way` reading open in a dead end |
| E0 | 2026-10-29 | 17/56 = 30% of runs have a "searched" note on a door-ward action (upper bound; no stale blocks); those runs solved more often. Door B is still listed open after shutting in 32% of runs | Holds, weakly, on the threshold. The stale-open doorway is the stronger lead |

| N1 | 2026-10-29 | Same step-0 frame: alone, 2 distinct readings of 20 (2–3% strip fields differ); with 7 neighbours, 6 and 11 of 20 (16–28%). The `:8006` copy passes as a stand-in | **Holds**: the lottery is batching. Noise floor under load is 21.9%, so C1/F1 must run alone |
| A1 | 2026-10-29 | Repeat agreement 73% vs reordered 59%: +14.2 pts, no call. The code-first item is picked 19% when first, 18% when last; changed picks follow position 1 of 124 times, and 110 of 124 are explore↔item flips | Not supported. A dropped (no primacy bias). The strategist re-rolls under any text change |
| C1 | 2026-10-29 | 300 frames, concurrency 1. Fields where orig and mirror agree are 81.0% accurate against 67.8% for orig (+13.2; the repeat control gives +5.5), but they agree on only 67.7%. Floor error follows the *image* side: by strip from far_left to far_right, orig reads 42/48/62/62/59%, and the mirror flips that. Post hoc, taking each strip from the read that saw it on the image's right half gives floor +7.7 pts | **No call** (agreement < 80%; lean on all fields +9.5, just under 10). Lead: two-read image-right fusion, needs its own test |
| F1 | 2026-10-29 | Without reason-first: floor +2.9, doorway −0.6, goal +1.3 pts; none counts. 40% faster (0.85 s vs 1.42 s) | **No call**: reason neither helps nor clearly hurts. g05-nr is a free latency cut |
| (noise) | 2026-10-29 | Repeat reads disagree on 18.6% of strip fields even at concurrency 1. N1's alone runs differ only on trial 0, which points to cold vs prefix-cached calls | Repeats on vLLM are not independent. Prefix caching is the operator's call |

Details and readings: each probe's README under `eval/phase2/_probes/`.

## After the probes

- Write one line per probe into the research note, giving the result and whether the belief held.
- A candidate becomes a round only if its probe passed. The round README cites the probe folder as
  Evidence, and its own probe gate repeats the passed threshold on the new agent version.
- Never more than one change per round. If several pass, fly the one with the largest probe effect
  first.
