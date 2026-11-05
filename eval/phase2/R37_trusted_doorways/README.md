# R37: a66 with doorway reads trusted by the look, contested cells

**Agent:** `a77` (`6744446339b0`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17k` · **Planner:** `PATHFINDER_A77` · **Status:**
laid out 2026-11-05 on the operator's instruction ("Build it"); offline readouts measured
(below); **not flown**

Written before flying. Spec: `docs/phase2-test-plan.md`. Analysis:
[docs/research/round-f-analysis.md](../../../docs/research/round-f-analysis.md) §9 and §10.
Design: the ten contested cells, seeds 1–3, 30 runs, read against R32P (`a66`, 15/30).

## Change

Against `a66`, code only:

- **Doorway reads trusted by the look** (memory `a17k`, `SpatialConfig.door_trust`,
  `spatial.look_angle`). A read is strong when the doorway sits in the centre strip and the
  look is within 20° of square to the wall, the wall's line being taken from the frame itself:
  the floor ends of the nearest strip each side that is not an open doorway. Only a strong
  read paints floor through the gap and marks the opening strong. Any other open read is weak:
  the opening is remembered and counted, nothing is written on the map, and a doorway read
  closed is not reopened.
- **Approach on trusted doorways** (`agent.PATHFINDER_A77`). `a76`'s approach pose (R36) on
  doorways with a strong read only, one read being enough.
- **Look.** A doorway known from weak reads alone, seen twice, 2–8 m off and within 2.5 m of
  the route, takes the waypoint for two steps over the run, so the drone faces it and the next
  frame holds it in the centre strip.

`g05`, `d01`, `p17`, the cost map, tags and turn rule are `a66`'s.

## Evidence

- Probe [door_read](../_probes/door_read/README.md): at 2–9 m a look within 20° of square read
  the open door on 157 of 158 looks and a blank wall strip as open on 1 of 366; beyond 60°,
  112 of 231 and 76 of 393.
- The same frames, each strip read open after `d01` (`eval/probes/door_trust.py`, 1675 reads):
  856 are on the open door and 819 are not. In the centre strip with a level look: 415 and 54
  (88% on the door, 48% of the door's reads). Centre strip alone 491 and 140; level look alone
  499 and 190.

## Hypothesis

With only square looks trusted, the memory's doorways are mostly the door, the route stops
crossing on floor painted through phantom doorways, and the approach pose is spent on the
door: `a77` scores at least 15/30.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a77` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 5–8 |
| s02 `dynamic` ×4 | 6/12 | 5–8 |
| s03 `final` | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 0–1 |
| **total** | **15/30** | **12–20** |

**Noise:** a gap under 3 on 30 runs is a draw (R32's rule).

## Manipulation check

Code only, from `decisions.jsonl` and the memory rebuilt from it:
- Of s02 near-side steps with `planner.door` in phase `line_up` or `through`, the doorway is
  within 2 m of the true open door on at least 50% (open loop: 35 of 112).
- No doorway label on more than two `look` steps or six approach steps of a run.
- Of doorways looked at, a strong read or a close follows within two steps on at least 60%.
- Strong doorways not within 2 m of the open door, per s02 near-side step: at most 0.1
  (open loop 0.08; `a66`'s live doorways elsewhere 0.62).

## Drop criterion

Not carried forward below 15/30; or if the shakedown's s02a `final` is lost with the open
door never strong in the memory.

## Probe gate

Offline, no model (`eval/probes/a76_replay.py --agent a77`,
[_probes/a77/replay.txt](../_probes/a77/replay.txt)), on the 110 change-arm runs of Round F,
R32P and R35. **Measured while the agent was being built: a record, not a pre-registration.**
Open loop: a look's effect on the next frame is not simulated.

| s02 near side | `a76`, lost | `a77`, lost | `a76`, won | `a77`, won |
|---|---|---|---|---|
| Approach steps on the true open door | 15 | 22 | 49 | 13 |
| Approach steps on other doorways | 190 | 28 | 154 | 49 |
| Look steps on the door / on others | – | 1 / 62 | – | 6 / 56 |
| Runs where the rule fires on the door | 4 of 45 | 6 of 45 | 16 of 43 | 9 of 43 |
| Within 4 m of the door: waypoint toward it (as flown 30, 72) | 30 of 175 | 29 of 175 | 63 of 206 | 67 of 206 |
| Route crosses inside the door's gap (as flown 30, 85) | – | 31 of 2477 | – | 63 of 1066 |

Memory, lost runs' near-side steps (2480): a strong doorway at the door on 167, strong
doorways elsewhere 186 (0.08 per step). `a66`'s memory: a live doorway at the door on 192,
live doorways elsewhere 1532. s03: 12 of 128 fires are on an exit door, 38 of them in the lobby.

Against the gate (the losses that stood at the door): **failed open loop**, the waypoint
points at the door no more often. What moved: approach steps spent on doorways that are not
the door fall from 190 to 28 in lost runs, and the trusted memory is about half the door
against a tenth. What it costs: in won runs the route crosses inside the gap on 63 steps
against 85, because a door seen at an angle no longer paints its gap.

By the test plan's rule this probe does not carry `a77` to a round. Open loop cannot fly the
look, which is the part that turns a weak doorway into a strong one or a closed one. If flown:
shakedown first, alone on `:8004`, s02a `final`, s02c `dynamic`, s03 `final`, s03 `dynamic`,
scored by the manipulation check.

## Builds on

`a66`; `a76` (R36, unflown). Branch `phase2/r33-deadlock-costmap`.

## Notes for the operator

- **Tests and smoke (no model):** `python -m pytest server/decider/tests -q` (33 pass);
  `VLM_AGENT=a77 python eval/probes/a63_smoke.py`.
- **Replay:** `python eval/probes/a76_replay.py --agent a77` (about 4 min).
- **Preflight, if flown:** `python -m server.decider --profile remote --agent a77`; `/health`
  should report `6744446339b0`. `a66` `de7f23d07186`, `a76` `32498e44d94d` unchanged.

## Outcome

Not flown.
