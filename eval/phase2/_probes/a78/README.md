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

Not covered: the lane shut once the drone is out (the recorded drone never leaves; unit tests
`test_latch_is_carried_by_the_record_and_shuts_the_lane_once_out`), and anything the navigator
does with the route.
