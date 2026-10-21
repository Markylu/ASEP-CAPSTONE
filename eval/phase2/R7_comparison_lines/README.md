# R7: Comparison lines in the log

**Agent:** `a10` (`b5b7bcd218cc`) · **Prompt:** `p11` (`55414df4bc89`) · **Identifier prompt:**
`g02` · **Status:** pre-registered, `a10` probe gate passed, not flown. `a09` (`67d052bc6c3a`, `p10`
`3d203bf87060`) was probed first and set aside (see Probe history).

Written before the `a10` probe and before flying; the probe result is added below. Spec: `docs/phase2-test-plan.md`. The agent and
prompt shas above are re-checked against `config.lock.json` before the round flies.

## Change

`a10` builds on `a08` (`p09`: pose log with position and heading, **no** last-sighting line,
identifier `g02` on the clean frame; the agent R6 flew). It makes **one change**: comparison lines.

The code compares each move with the drone's own earlier positions and writes the result into the
log line. Thresholds come from the R6 pose records, where a normal move is 1.7 m (655 of 876
steps):
- a flight that moved < 0.3 m: `Did not move (blocked).`
- a flight that moved 0.3–1.5 m: `Stopped short (blocked).`
- a turn-around that moved < 0.3 m: `Turned in place.`
- a full move that ends within 0.5 m of where an earlier move ended (not the step just before):
  `Back where you were after step N.`

The system prompt's pose paragraph keeps its text and gains a paragraph explaining these lines,
and that a blocked or revisiting move is not progress. Position and heading stay in the log.
Heading degrees were considered for removal (R6's compass-versus-image errors) and kept: two runs
are thin evidence, and heading is the only orientation the log gives. Left for a later round.

Example (R6 s03 `final`, step 24, as `p10` renders it; `p11` is the same without the sighting
line):

```
Step 19: flew straight. Ended at (15.2, -11.2), heading 221 degrees, moved 1.7 m.
Step 20: flew straight. Ended at (15.2, -11.5), heading 221 degrees, moved 0.4 m. Stopped short (blocked).
Step 21: flew sharp left. Ended at (15.2, -11.5), heading 265 degrees, moved 0.0 m. Did not move (blocked).
Step 22: flew straight. Ended at (15.2, -11.5), heading 265 degrees, moved 0.0 m. Did not move (blocked).
```

The goal's position is **not** given (Phase 1 gave it and went 0/30 on `final` and `dynamic`).
`a00`–`a09` and `p02`–`p10` keep their shas.

## Evidence

From the [R6 summary](../R6_pose_log/summary.md), its
[manipulation check](../R6_pose_log/manipulation_check.md) and its
[reasoning analysis](../R6_pose_log/reasoning_analysis.md):

- The pose log removed the loop: two turn-arounds in a row fell to 0% (`final`) and 2% (`dynamic`),
  against 26% and 58% in R5.
- It did not raise success: `final` + `dynamic` 2/12, as in R5. `initial` fell from 6/6 to 3/6.
- The model quoted its position and did not compare it: 143 collisions (R5: 38), and 65% of
  reasons after a blocked move still claimed progress. s03 pins at x = 15.2 on all three arms.
- Heading arithmetic failed in two runs: s02va and s02vc `initial` at step 12 turned around with
  the goal 12 m away and in view. Not addressed in R7.
- With no sighting line (`a08`), three runs saw the goal, lost it and never found it again. R7
  does not address this; the sighting line is what brings the loop back (Probe history).

## Hypothesis

Having the code state "blocked" and "back at step N" beside the position lowers blocked-move
collisions and false progress claims, without bringing back the turn-around spin.

## Predictions

Per arm, 6 sites, seed 1. R0 is Phase 1's seed-1 baseline; R6 is `a08`.

| Arm | Baseline (R0) | R6 | Predicted R7 |
|---|---|---|---|
| initial | 5/6 | 3/6 | 3–5/6 |
| final | 0/6 | 2/6 | 2–3/6 |
| dynamic | 0/6 | 0/6 | 1/6 or more |

- Collisions: well below R6's 143, near R5's 38 or lower.
- Reasons after a blocked move that still claim progress: below 30% (R6: 65%).
- s03: no run pinned at x = 15.2 for more than 5 steps.
- Two turn-arounds in a row on `dynamic` stays under 20% (R6 2%, R5 58%).
- `final` + `dynamic` at least 3/12, which beats R1's best.
- Lost goals (seen, then never found again) are not expected to improve: R7 does not touch them.

## Manipulation check

`eval/agent_evidence.py` needs new measures before the round is labelled. They are not written yet.
- Comparison lines delivered: share of steps after a blocked move whose prompt carries
  "Did not move" or "Stopped short".
- Reasons after a blocked move that claim progress (the R6 65% measure, same classifier).
- Two turn-arounds in a row, and reasons that cite position (carried over from R6).

## Drop criterion

`a10` is not carried forward if two or more of these hold:
- `final` + `dynamic` is below 2/12 (R5 and R6 level);
- collisions are not at least a third below R6's 143;
- reasons after a blocked move that claim progress stay above 50%;
- `initial` is not above 3/6.

One change, so the result is attributed to it.

## Probe gate

Required: the log and prompt change what the model is shown. The probe runs on sctsvr6 against the
model at 127.0.0.1:8004 there, in a scratch directory; results are copied back to `probe/`. The
server matches the laptop: `a08` on R6's spin set gave 78 of 80 identical picks and identical
turn-around counts (6/40, 2/20, 0/20).

Sets (`eval/goal_probe.py`: `sample-r7`, `run-r7`, `report-r7`, and R6's `run-spin`):
- `lost`: a true sighting 1–5 steps back, goal out of view now. 25 frames, from a pool of 81 (R5
  and R6 runs, seed 0).
- `offcentre`: goal in view to the left or right, 9–15 m away. The pool holds only **11** frames
  (6 R6, 5 R5), all used. It includes the two R6 failures (s02va and s02vc `initial`, step 12,
  goal 12.0 m right, recorded pick a turn-around). Read as counts, not a rate.
- spin: R6's `spin_set.jsonl`, 80 frames.

**Probe history.** `a09` (`a07` plus the same lines, sighting line kept) was probed first. It did
not pass its pre-registered gate (13/25 `lost` turn-arounds against `a07`'s 12/25) and is not
flown. The same run showed `a08` at 4/25. The sighting line is what brings the loop back, so
`a10` builds on `a08`. Results: `probe/probe_r7.md`, `probe/spin_*.jsonl`.

| Agent | spin turn-around | `lost` turn-around | `offcentre` turn-around |
|---|---|---|---|
| a07 | 17/40 | 12/25 | 0/11 |
| a08 | 6/40 | 4/25 | 2/11 |
| a09 | 17/40 | 13/25 | 0/11 |
| a10 | 5/40 | 3/25 | 1/11 |

**Thresholds for `a10`**, set after the `a09` probe and before `a10` is probed, relative to `a08`
(its base) with a margin of three frames for the 25-frame groups, five for spin (temperature-0
noise on the server was 2 of 80 picks):
- spin turn-around at most 11/40 (`a08`: 6);
- `lost` turn-around at most 7/25 (`a08`: 4);
- `offcentre` turn-around at most 3/11 (`a08`: 2);
- a valid reply on every frame.

**`a10` result: gate passed.** Spin 5/40 (limit 11), `lost` 3/25 (limit 7), `offcentre` 1/11
(limit 3), 0 errors on all 116 frames. The server's `a10` shas matched this lock
(`b5b7bcd218cc`, `55414df4bc89`). The probe does not test the comparison lines themselves:
blocked moves are rare in these frames. It shows `a10` kept `a08`'s low turn-around rate.
If the gate had failed, `a10` would not fly.

## Host

R7 is flown on sctsvr6 (headless Linux, Xvfb, Mesa lavapipe CPU Vulkan, in Docker; the host
pieces come from the `linux-headless` branch), not on the Mac that flew R1–R6. Frames rendered by
lavapipe are not the pixels Metal renders, so the host is a config change. The model is the same
(`Qwen3-VL-30B-A3B` at 127.0.0.1:8004 there, no tunnel); only the renderer and the client
differ. `a08` (R7C) is flown on the same host so R7 can be read against a like-for-like
baseline. R7 and R7C stay non-citable; the final round is flown on the Mac.

## Builds on

R6 and agent `a08` (`p09` + `g02`), the agent R6 flew. Branch cut from `phase2/r6-pose-log`
(`b5bf686`), tag `p2-r6`.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
