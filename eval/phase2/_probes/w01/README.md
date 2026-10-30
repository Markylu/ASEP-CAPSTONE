# Probe W01: the wall reader alone

Script: `eval/probes/w01.py`, committed before any call (`8df688b`). Gate and method:
[R28 README](../../R28_wall_reader/README.md), "Probe gate". Output: [score.txt](score.txt).

## Belief

One perceiver prompt does three jobs, so it sets one missed-wall / phantom-wall trade-off for all
of them. `w01` is `g05`'s floor job alone, describe-first kept. If the goal and doorway questions
crowd the floor reading, `w01` should miss fewer real walls than `g05` without adding phantom walls.

## Run

2026-10-30, on `phase2/r28-wall-reader` at `8df688b` (checkout `~/asep-r28-probe` on sctsvr6).
- 1176 `w01` calls: set F 576, set P 300, C2 300. `g05`'s reads are the recorded ones.
- Four shards, one call at a time each: `:8004` (no flights running) and three copies on GPUs 3–5
  (`:8006`–`:8008`, same image and flags), stopped afterwards.
- Median latency 1.64 s per `w01` call (`g05` 1.34–1.45 s in AG).
- **30 calls failed (2.6%)**: F 16, P 4, C2 10. Every rung failed because the describe-first
  `reason` ran past the token limit, even after doubling to 1536 ("Unterminated string"). Re-calling
  4 of them, 2 succeeded, so this is not a fixed property of the frame. The first call stands. As in
  flight (`orchestrator.perceive_walls`), a failed `w01` leaves `g05`'s floors on that frame. The
  score was changed to do this after the run (`full` had dropped those frames); the gate's wording,
  "scored as the merged reading `a61` would build", already asked for it.

## Result

**Failed**: 3 of 5 checks pass (both phantom checks and s03); both missed-wall checks fail.

| Set | Read | Missed wall | Phantom wall | s03 phantom |
|---|---|---|---|---|
| F | `g05` | 16.5% | 9.4% | 9.7% |
| F | `w01` | 16.5% | 9.6% | 10.4% |
| P | `g05` | 16.5% | 11.7% | 19.8% |
| P | `w01` | 19.6% | 8.3% | 12.4% |
| C2 | `g05` | 17.0% | 14.6% | 9.1% |
| C2 | `w01` | 17.5% | 11.1% | 10.4% |

| | Gate | Value | |
|---|---|---|---|
| 1 | F missed ≤ half of `g05`'s | 16.5% vs 16.5% | FAIL |
| 2 | F phantom ≤ `g05` + 2 pts | +0.2 pts | pass |
| 3 | F s03 phantom ≤ `g05` + 4 pts | +0.7 pts | pass |
| 4 | P missed ≤ half of `g05`'s | 19.6% vs 16.5% | FAIL |
| 5 | P phantom ≤ `g05` + 2 pts | −3.4 pts | pass |

Reading:
- **Taking out the goal and doorway does not change how walls are read.** `w01` misses real walls
  at `g05`'s rate on all three sets (16.5 / 19.6 / 17.5% against 16.5 / 16.5 / 17.0%).
- Phantom walls drop 3.4–3.5 pts on P and C2 and hold on F. That is inside the repeat-read noise
  (18.6% of strip fields differ between repeat reads), and it is not what the gate asked for.
- **The missed walls belong to describe-first, not to the task load.** Only dropping describe-first
  (`g07`) cut them (2.5–6%), and that brought the phantom walls (R27, AG). With describe-first
  wording, one job or three gives the same walls.
- **Cost:** a second call per step (+1.6 s, more batch on `:8004`) and 2.6% failed reads, for no
  gain.

R28 does not fly. The next wall reader has to change the question itself, not what is asked beside
it. Two ideas from the write-up's list fit: a narrower per-strip question (the floor at the bottom
edge only) or per-strip crops. Each is a new version (`w02`, …) with its own gate.
