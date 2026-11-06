# Probe a78: the dead-end latch replayed on the recorded runs

For R38 ([round write-up](../../R38_dead_end_latch/README.md), gate 2).
`python eval/probes/a78_replay.py --answers <oracle|always|probe:e01>` on the 120 change-arm
runs of `eval/phase2/final`, R32P and R35. No model. Open loop: the drone flew `a66`'s picks
(`a75`'s in R35), so each step is what `a78`'s planner says from where that drone stood.

`a78`'s latch needs the dead-end confirmer's answers, and no recorded run has them. Two
stand-ins bracket it until probe DE has run:

- **oracle** ([replay_oracle.txt](replay_oracle.txt)): yes on an asked step in the shut tine
  facing its door, no on every other asked step.
- **always** ([replay_always.txt](replay_always.txt)): yes on every asked step.

| Readout | `a66` recorded | oracle | always |
|---|---|---|---|
| s03 shut-tine steps after the first closed read whose route leaves by the crossbar | 0/444 | 354/444 (80%) | 374/444 (84%) |
| The same, from the latch on | — | 354/396 (89%) | 374/428 (87%) |
| s03 `dynamic` runs latched, of 11 | — | 11 | 11 |
| of those, with 25 or more steps left | — | 8 | 9 |
| Latched steps the navigator's sentence would be said on | — | 128 | 140 |
| s02 won runs latched before the crossing, of 53 | — | 0 | 43 |
| s02 lost runs latched before a crossing, of 45 | — | 0 | 45 |
| s02 near-side routes crossing inside the open door's gap, of 3745 | 173 (5%) | 173 (5%) | 731 (20%) |
| Steps with no route, of 5653 | — | 4 | 257 |

- With answers that are never wrong the route points out of the shut tine on 89% of steps
  from the latch on, where `a66`'s never does. In 12 of the 14 runs with a latch it is every
  step or all but four at most.
- The runs it misses: R35 `dynamic` seed 3, 0 of 23 (the straight run begins at x = 3.3, so the
  corridor's mouth is inside the tine and the route leaves the lane there and goes round the
  rectangle through the tine's wall); R32P `dynamic` seed 3, 0 of 5 (latched at step 55); and 14
  steps spread over the others.
- With yes on every step the latch fires in 88 of 98 s02 runs. That column is the cost of a
  confirmer that cannot tell the hall from the tine, and the reason probe DE comes first. The
  rise in s02 routes through the true gap under it (5% to 20%) is open loop, on a map with 6.8
  m of hall shut either side of the drone's approach; it is not read as a gain.
- Building the latch against this replay changed it three times, each recorded in
  `planner.dead_end_latch`: the corridor's axis is found from the run itself (an 8 m window
  reached round the corner into the crossbar); the corridor is the run flown before the
  confirmer's first yes, looked for up to 12 steps back (by the second yes the drone has
  turned about at the door); and the rectangle's far end moves with the drone (a fixed end
  was flown past in the record). So these numbers are a fit to these runs, not a test.

## With probe DE's answers (2026-11-05)

Probe DE failed its gate for both prompts ([_probes/dead_end](../dead_end/README.md)), so `a78`
is dropped. The replay with the answers it recorded, for the record:

| Readout | `e01` | `e02` |
|---|---|---|
| s03 `dynamic` runs latched, of 11 | 11 | 3 (steps 35, 19, 35) |
| of those, with 25 or more steps left | 8 | 3 |
| s03 shut-tine steps from the latch on whose route leaves by the crossbar | 346/421 (82%) | 87/89 (98%) |
| s02 won runs latched before the crossing, of 53 | 21 | 0 |
| s02 lost runs latched before a crossing, of 45 | 44 | 0 |
| Steps with no route, of 5653 | 220 | 4 |

[replay_probe_e01.txt](replay_probe_e01.txt), [replay_probe_e02.txt](replay_probe_e02.txt).
With `e01` the latch holds in 65 of the 98 s02 runs, the same 65 the probe counts for the rule
alone: needing a straight run the drone is still in stops none of them. With `e02` it is
`a66` everywhere but three s03 runs.

`e01` kept only while at most two closed-door places are known
([_probes/dead_end §3](../dead_end/README.md), `--answers probe:e01 --places 2`,
[replay_probe_e01_places2.txt](replay_probe_e01_places2.txt)): 11 of 11 s03 `dynamic` runs
latched, 8 with 25 or more steps left, 346/421 (82%) routes out; 1 of 53 won s02 runs and 0 of
45 lost ones latched; no route on 6 steps. A fit to these runs, read after the gate.

The same on the held-out runs ([_probes/dead_end_heldout](../dead_end_heldout/README.md),
`--answers probe:e01 --places 2 --held-out`,
[replay_probe_e01_places2_heldout.txt](replay_probe_e01_places2_heldout.txt); F's `initial`
arms, R30, R32): 3 of 4 s03 `dynamic` runs latched (2 with 25 or more steps left), 79/102 (77%)
routes out; none of the 34 s02 and s01 change-arm runs latched; no step without a route; and
1 of the 36 `initial` runs latched, F s03 `initial` seed 4 at step 30, a won run, where the
route then runs back down the tine for three steps. That run fails the held-out gate. R32's
runs (`a49`) record no route, so the `a66` columns count R30 only.

Not covered: the lane shut once the drone is out (the recorded drone never leaves; unit tests
`test_latch_is_carried_by_the_record_and_shuts_the_lane_once_out`), and anything the navigator
does with the route.
