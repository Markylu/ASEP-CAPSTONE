# R6: Ground-truth pose in the memory log

**Agent:** `a08` (`e8c66be05bd3`) · **Prompt:** `p09` (`7642a3e1056d`) · **Identifier prompt:**
`g02` (`bf175c973dfb`) · **Status:** probed, `a08` chosen, not flown. `a07` (`8062799be32e`,
`p08` `e6bdfd04534d`) was the other candidate.

Written before the probe and before flying. Spec: `docs/phase2-test-plan.md`.

## Change

R6 gives the memory log the drone's own ground-truth pose. Each log line now says where the
move left the drone and how far it went:

```
Start: at (12.0, 0.2), heading 178 degrees.
Step 23: flew sharp left. Ended at (3.5, 4.6), heading 178 degrees, moved 1.7 m.
Step 24: turned around. Ended at (3.5, 4.6), heading 358 degrees, moved 0.0 m.
Step 25: turned around. Ended at (3.5, 4.6), heading 178 degrees, moved 0.0 m.
Position now: (3.5, 4.6), heading 178 degrees.
```

(s02a `dynamic`, R5, as `p08` renders it at step 30.)

- **Position** is the floor-plane (x, −z) of the manifest's `pose.position`, in metres, rounded
  to 0.1 m.
- **Heading** is `yaw` + 90°, in whole degrees from 0 to 359, counter-clockwise from +x. A left
  turn raises it, as the turn angles do. This mapping was checked on recorded R5 moves: a flight
  goes along (−sin yaw, −cos yaw) in Godot's (x, z).
- **"moved"** is the straight-line distance between the pose at the step and the pose at the
  next recorded step. A turn-around, or a flight into a wall, reads 0.0 m.
- The pose comes from `manifest.pose`, which every decision has recorded since Phase 1.
  `Run.memory()` now carries each step's pose and the next step's pose. The last move ends at
  the current manifest's pose.
- One paragraph is added to the system prompt. It says what the numbers are, and that "moved
  0.0 m" and a repeated position mean the drone has not moved. No code-written summary of the
  loop is added: the model reads the numbers itself.

The goal's position is **not** given. Phase 1 gave the goal's distance and bearing on every step
and went 0/30 on both `final` and `dynamic` (`eval/phase1/results/results.md`). In R5, the
navigator worked out the goal's direction correctly 76 / 77 times and still steered into the
closed route (`R5_goal_identifier/reasoning_analysis.md` §3).

**Two candidates.** Both keep `a06`'s goal identifier (`g02`, clean frame):
- `a07` (`p08`): `a06` plus the pose log. The last-sighting line stays.
- `a08` (`p09`): `a07` without the last-sighting line or the sentences that explain it. The
  identifier's answer for the current image stays.

The probe decides which one flies (Probe gate). The operator chose to probe both, because the
`dynamic` loop has a second cause that the pose does not touch: the sighting line's "goal is
behind, turn around".

- `a00`–`a06` and `p02`–`p07` keep their shas.
- `p07` renders byte-identical requests when the memory entries carry the new pose keys (checked
  on s02a `dynamic` step 30).

## Evidence

From the [R5 summary](../R5_goal_identifier/summary.md), its
[manipulation check](../R5_goal_identifier/manipulation_check.md) and its
[reasoning analysis](../R5_goal_identifier/reasoning_analysis.md):

**1. The failure is a loop of turn-arounds in place.**
- Two turn-arounds in a row: 26% of `final` decisions and 58% of `dynamic` (R1 0% / 1%).
- 9 of 10 failed runs carry `spin_failure` (≥ 5 turn-arounds in a row). The longest streaks are
  36, 26 and 22 steps (s02a, s01 and s02vc `dynamic`).

**2. The log hides that the drone is not moving.**
- The log records the command. Turning around 36 times reads as 36 moves.
- s02c `final` flew "straight" into the door jamb 23 times. 23 of 37 reasons after a collision
  claim the drone "has been moving forward" (reasoning analysis §2.3).

**3. The model notices the repetition but not the standstill.** 183 of 217 reasons that mention
repeated turning pick a turn-around again (reasoning analysis §2.4). It counts turns. Nothing in
the log tells it that it has not moved.

**4. The `final` loop runs without a sighting.**
- s01, s02a and s02vc `final` never see the goal and still turn around 15, 9 and 12 times in a
  row, citing a wall ahead.
- 54% of the wall-justified turn-arounds had ≥ 5 m of free floor ahead.

The sighting line cannot cause these; a record of the standstill might break them.

**5. The `dynamic` loop is fed by the sighting line.**
- A reason that says the goal is behind ends in a turn-around 83 / 92 times.
- The line is cited in 90% of `dynamic` decisions.

Hence `a08`.

## Hypothesis

If the log gives the drone's ground-truth position, heading and distance moved after every move,
the navigator sees that it is standing still and stops turning around in place, and `final` +
`dynamic` beats R5.

## Predictions

| Arm | R0 | R1 | R5 | Predicted |
|---|---|---|---|---|
| initial | 5/6 | 5/6 | 6/6 | ≥ 5/6 |
| final | 0/6 | 2/6 | 2/6 | ≥ 2/6 |
| dynamic | 0/6 | 1/6 | 0/6 | ≥ 2/6 |

So `final` + `dynamic` ≥ 4/12, against R5's 2/12 and R1's 3/12.
- Two turn-arounds in a row: `final` ≤ 10%, `dynamic` ≤ 20% (R5: 26% / 58%).
- `spin_failure` in ≤ 3 failed runs (R5: 9).
- Collisions ≤ 20 (R5: 38). s02c `final` gets through door C.
- If `a07` flies: `dynamic` improves less than `final`, because the sighting line still argues
  "goal behind".
- If `a08` flies: `initial` may slow down where a sighting carried the approach, but stays
  ≥ 5/6. `initial` used the identifier's current answer, not the line (reasoning analysis §5).

## Manipulation check

Run `python eval/agent_evidence.py eval/phase2/R6_pose_log` and compare with R5's
[manipulation_check.md](../R5_goal_identifier/manipulation_check.md).

- **Delivery:**
  - every valid decision has a pose in its manifest;
  - `memory_steps` equals the number of earlier valid decisions;
  - re-rendering each decision's prompt from `decisions.jsonl` gives one pose line per earlier
    move, and the last "Ended at" equals the current pose.
- **Identifier unchanged:** goal seen when visible ≥ 90%; reported when not in view ≤ 10% (R5:
  114 / 114 and 1.4%).
- **The record is read:** share of `final`/`dynamic` reasons that cite position, coordinates,
  "moved 0.0 m" or staying in the same spot. Reported, not judged.
- **The loop:**
  - two turn-arounds in a row, per arm;
  - longest streak, per arm;
  - turn-around share after a turn-around.
- Reported as in R5:
  - same pick;
  - revisit;
  - reason cites memory;
  - navigator reason places the goal now, out of view (≤ 10%).

## Drop criterion

Drop the flown agent (do not build on it) if any of these holds:
- `final` + `dynamic` ≤ 3/12.
- Two turn-arounds in a row is not below half of R5's on both `final` and `dynamic` (≥ 13% and
  ≥ 29%), while the pose is delivered. The record was there and the model did not act on it.
- `initial` ≤ 4/6.

If the loop breaks and success does not move, the drone leaves the spot but still cannot find a
route. The next candidate is then the goal position (an R7 idea), tested against a baseline that
no longer spins.

## Probe gate

The probe is required, because R6 changes what the navigator is shown about its own past. The
identifier is `a06`'s unchanged, so no single-frame probe is run. Both parts replay recorded R5
decisions with the log in place, one model call per frame and no Godot (`eval/goal_probe.py`).

**Part 1, the spin replay** ([spin_set.jsonl](probe/spin_set.jsonl), `sample-spin
eval/phase2/R5_goal_identifier`, seed 0). Each row is a recorded R5 decision, its frame, the
clean frame recorded in flight, and the log `Run.memory()` gives at that step, poses included.
The goal entries are the ones recorded in flight.

| Group | Frames | Pool | R5 turned around, in flight |
|---|---|---|---|
| `spin`: `final`/`dynamic`, the move before was a turn-around | 40 | 286 | 33 / 40 (pool 212 / 286) |
| `moving`: `final`/`dynamic`, the move before went ≥ 1 m, flight did not turn around (control) | 20 | 149 | 0 / 20 |
| `visible`: the goal in view, flight did not turn around (control) | 20 | 64 | 0 / 20 |

`run-spin --agent a06` (calibration), `a07` and `a08` each answer every frame with their own
log rendered from the same memory.

**Part 2, the goal-placement replay** ([replay_set.jsonl](probe/replay_set.jsonl), `sample-replay
eval/phase2/R5_goal_identifier`). This is R5's instrument on R5's own runs: 20 stale sightings
turned < 90°, 20 turned ≥ 90°, and 20 in view. It checks that the pose does not bring back the
phantom goal. R5 placed the goal now in 0 / 40 of the stale rows in flight, so there is no
calibration.

| Check | Pass |
|---|---|
| Calibration: `a06` spin replay turns around on `spin` frames | ≥ 60% (in flight: 33 / 40). Otherwise stop and look at the probe |
| Candidate: turn-around on `spin` frames | ≤ half of `a06`'s replay rate |
| Candidate: turn-around on `visible` frames | ≤ 5% (R5 in flight: 0 / 114) |
| Candidate: goal-placement replay, reason places the goal now, out of view | ≤ 10% |

**Winner.** Of the candidates that pass, the one with the lower `spin` turn-around rate flies. If
the two are within 5 points, `a07` flies, because it is one change from `a06`. If neither passes,
R6 does not fly: the Outcome records the probe.

Reported but not gated:
- turn-around on `moving` frames;
- same pick as in flight, per group;
- the in-view goal-placement control.

`python eval/goal_probe.py report eval/phase2/R6_pose_log/probe --gate R6 --calibration a06
--candidate a07,a08`.

**Result: passed, `a08` flies** ([probe/probe.md](probe/probe.md)). Thresholds unchanged.

| | `a06` (calibration) | `a07` | `a08` |
|---|---|---|---|
| turn-around, `spin` | 34 / 40 (85%) | 17 / 40 (42%) | **6 / 40 (15%)** |
| turn-around, `moving` (not gated) | 0 / 20 | 2 / 20 | 2 / 20 |
| turn-around, `visible` | 0 / 20 | 0 / 20 | 0 / 20 |
| goal-placement replay, places the goal now, out of view | – | 1 / 40 | 0 / 40 |

- Both candidates pass. `a08` is 27 points below `a07`, beyond the 5-point tie margin.
- The calibration reproduces flight: `a06` turns around on 34 / 40 `spin` frames (33 / 40 in
  flight).
- `a08`'s `spin` reasons read the pose: 32 / 40 cite the position or the heading. For example,
  "The drone is currently at position (2.7, −1.8) facing 29 degrees … move forward in a direction
  that explores new territory" (s02c `dynamic`, step 56).
- One heading slip: "facing 85 degrees, which is roughly northeast" (s01 `final`, step 49). In
  this convention, 85° is about +y.
- The first pass lost 192 `spin` rows to a tunnel drop (`ConnectError`). They were rerun after
  the operator confirmed the tunnel. `replay()` now retries errored rows on resume.

**Limit.** The replay is one step off-policy. It shows whether the record changes the pick at a
spin state, not whether the drone escapes the loop over a whole run.

## Builds on

- `a06` (`9cc1e3f9a121`, R5): the goal identifier on the clean frame, the move log and the
  sighting line. `a06` was dropped. Its identifier is kept.
- `a01` (sha `48f6b3973760`), R1, is the baseline together with R5.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
