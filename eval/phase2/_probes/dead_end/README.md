# Probe dead_end: what could trigger a dead-end latch, and probe DE

For R38 ([round write-up](../../R38_dead_end_latch/README.md)). Two parts: a readout on the
recorded runs with no model, done; and probe DE, which asks the model, not yet run.

## 1. Closed-door reads as a trigger (no model)

`python eval/probes/dead_end_trigger.py` on the 120 change-arm runs of `eval/phase2/final`,
R32P and R35. The reads are the ones recorded in flight (`doorway` per strip, after `d01`).
Table in [trigger.txt](trigger.txt). Three candidate triggers:

- **asked:** a closed door read in the centre three strips. The steps `a78`'s confirmer is
  asked on.
- **strict:** the centre strip reads a closed door within 5 m, the goal within 35° of the
  heading, and the same no more than 3 steps before.
- **trail:** an asked step at the end of a straight run of 5 m or more begun at a turn of 60°
  or more.

| Group | Runs | Strict fired before the crossing | Trail fired before the crossing | Asked steps per run |
|---|---|---|---|---|
| s02 `dynamic` lost | 20 | 17 | 20 | 10–20 |
| s02 `dynamic` won | 29 | 17 | 13 | 0–16 |
| s02 `final` lost | 25 | 20 | 25 | 12–22 |
| s02 `final` won | 24 | 13 | 15 | 0–15 |
| s03 `dynamic` lost | 11 | 2 | 9 | 5–10 |
| s03 `final` lost | 2 | 2 | 2 | 7–12 |
| s03 `final` won | 9 | 1 | 1 | 0–5 |

- Neither rule separates the shut tine from the s02 hall: strict fires in 67 of 98 s02 runs
  and 2 of 11 s03 `dynamic` runs, trail in 73 and 9. The strict rule's goal condition cuts the
  tine itself, where the goal lies about 30° off the corridor.
- Asked steps by where the drone stood: 90 in the shut tine facing its door, 24 elsewhere in
  s03, 1126 in s02. Whatever answers on those steps has to say no about twelve times for every
  yes.
- The trigger is not late. All 11 s03 `dynamic` losses have an asked step in the shut tine
  facing its door, first at step 23 (median), 9 of them with 25 or more steps left. The two
  without: the door shut at steps 32 and 35.
- A closed door is sometimes read before any door has shut (R32P seed 2 at step 4, R35 seed 3
  at step 3, both in the lobby).

## 2. Probe DE: the dead-end confirmer (model calls, not run)

`eval/probes/dead_end.py`. Prompts `e01` ("is the drone in a dead-end corridor that ends at
that closed door?") and `e02` ("is turning back the only way on from here?"), each on the clean
frame of the 1240 asked steps, at concurrency 1. Scored against where the drone stood, and per
run with `a78`'s own rule (yes on a step and on 2 of the last 3 answers, none older than 15
steps). The gate is in the round write-up, set before any call.

Not run: the frames are on the lane checkouts, and the calls need the operator's word.

The scoring code has been run end to end on stand-in frames and made-up answers, outside the
repo: answers that are never wrong pass every row (8 of 11 s03 `dynamic` runs with 25 or more
steps left, the ceiling), and yes on every step fails the two s02 rows (88 of 88 s02 runs with
an asked step fire). Nothing from that dry run is kept here.
