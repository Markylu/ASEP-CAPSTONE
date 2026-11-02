# What we learned: research probes, R27 and probe AG

Written 2026-10-30. This covers the work on `research/probes`:
- the literature scan ([spatial-memory-and-prompting.md](spatial-memory-and-prompting.md));
- the probes A0, A1, B0, E0, N1, C1, F1 and C2 ([probe-plan.md](probe-plan.md), "Results so far");
- one flown round, R27 ([summary](../../eval/phase2/R27_mirrored_nr_perceiver/summary.md));
- a follow-up probe, AG ([README](../../eval/phase2/_probes/agree/README.md)).

The best agent is still `a49` (R25D, 14/18).

## In one paragraph

`a49`'s perceiver misses about one real wall in six. Dropping its describe-first paragraph (`g07`)
cuts that to about one in forty, which held on three fresh samples and in flight. But the same
change makes the reader see walls that are not there. On the recorded frames that cost looked
small (17% of open strips with two reads fused). In flight the drone met the views it reads worst:
- On s03, 60% of open strips became walls.
- The drone turned around in place until its steps ran out.
- R27 scored 12/18.

Missed walls and phantom walls trade against each other through the prompt. A phantom wall costs
more in flight than a missed one. A gate built on frames from other agents' paths cannot see a
change that alters where the drone goes.

R28 (2026-10-31) tried the split's wall reader first: five readers (`w01`, `k01`, `w02`, `w03`,
`w04`), none passed its gate, not flown ([R28](../../eval/phase2/R28_wall_reader/README.md)).
Next idea: `w05`, a code reader with depth cues from higher in the frame.

Probe LD (2026-11-01) then changed the image instead of the prompt: 1,680 re-lit renders, 10,080
calls. Refuted: the sites' lighting is the best of seven for walls, and every brighter floor traded
misses for phantoms as the prompts had ([LD](../../eval/phase2/_probes/ld/README.md)). Two side
results matter more:
- alone, with a warm prefix cache, the model is deterministic (3,359 of 3,360 repeats identical);
- two thirds of the walls `g05` missed in flight are found when the same frame is read alone.
So the wall-reading lever is exhausted on this model, and the next round changes the host, not the
agent: R29N/R29S fly `a49` shared and alone
([README](../../eval/phase2/R29N_host_noise_shared/README.md)). `w05` is set aside unless R29S
still misses more than 10% of walls.

## Lessons

### About measuring the perceiver

1. **Raw floor accuracy misleads.**
   - Ground truth is 78% `open_far`, so a reader that says "far" more often scores higher without
     reading better. C1's apparent +7.7 pts was this (C2's correction).
   - Use two error rates instead:
     - *missed wall*: truly blocked within 1 m, read open;
     - *phantom wall*: truly open, read `no_floor`.
   - `eval/r27_flight.py` scores them on any flown round. It reproduces R25D's 17.3% and 12.7%.
2. **Repeat reads are not independent.**
   - Under batching, 16–28% of strip fields change with 7 neighbours in the batch (N1).
   - Even alone, 18.6% of strip fields differ between repeat reads, and the first (cold) call is the
     odd one out.
   - Temperature 0 does not make a read deterministic on vLLM.
   - It does when the call is alone and the prefix is cached: probe LD's three repeats at
     concurrency 1 were identical on 3,359 of 3,360 image/read pairs. The noise is the server's
     state, not sampling.
   - One seed-1 round cannot resolve ±1 run (`a17b` family: 11.3 ± 1.4).
3. **Errors follow the image side.**
   - `g05` reads the image's left half worse (C1).
   - `g07` reads 40–42% of open image-left strips as walls (C2).
   - A mirrored second read moves that error to the other side, so taking each strip from the read
     that saw it on the image's right half cancels it.
4. **Fusion only removes errors the two reads do not share.**
   - The image-side bias was not shared, and fusion cut it.
   - On s03's views both `g07` reads mark the same phantom walls (about 65% each). Neither
     image-right fusion (59%) nor "wall only if both agree" (55%) helps. `g05` reads the same
     frames at 10% (AG).

### About gates and flying

5. **A gate on recorded frames is an open-loop test of a closed-loop change.**
   - R27's gate frames came from R22–R26N, flown by agents with `g05`.
   - `a60`'s phantom walls sent it to views those agents never stood in front of: turned around in
     s03's lobby and in the tines. Its own reader is worst on exactly those views.
   - On a60's own 576 flight frames, phantom walls were 28.5% at concurrency 1, against the gate's
     17.0%.
   - Batching was not the cause: the fresh reads match the flight records within 1 pt.
6. **Phantom walls are costlier than missed walls, at least on s03.**
   - R25D won 14/18 while missing 17% of walls.
   - R27 missed 2.5% and lost all three s03 runs, two of them in turn-around loops of 33 and 36.
   - A missed wall costs a collision or a blocked step. A phantom wall in front and behind traps the
     drone, because both ways read blocked.
7. **Fast is not free.**
   - `g07` takes 0.85 s against `g05`'s 1.43 s (F1), and two concurrent `g07` reads still beat one
     `g05` read.
   - The latency gain is real, but it came bundled with the phantom walls.

### About the rest of the agent (earlier probes)

8. **The strategist has no position bias (A1).** Its choices re-roll under any change to the text,
   including a reorder: repeat agreement 73% against 59% when reordered.
9. **The s03 dead end is a perception-of-progress gap, not a missing rule (B0).** In the shut tine,
   `planner.way` reads `open` on 78% of decisions, so no "pocket exhausted" rule could fire.
10. **Doors go stale (E0).** Door B is still listed open after it shuts in 32% of `dynamic` runs.
11. **The s02 failures are about the door wall, not the walls (R27 review).**
    - Failed s02 runs walk along the door wall, with 9–22 false door reports each and the open door
      seldom in view.
    - R25D's two s02 failures look the same.

## Ideas for the next round

### 1. Separate the perceiver's tasks into different agents (proposed lead)

Today one perceiver call does three jobs at once:
- floor per strip (walls);
- doorway per strip;
- the goal's strip.

One prompt therefore sets the trade-off for all three, and the probes show the three want
different prompts:

| Task | `g05` (describe-first) | `g07` (no describe-first) | Better |
|---|---|---|---|
| Phantom walls, R27's flight frames (AG) | 9.4% | 35.3% | `g05` |
| Missed walls, same frames | 16.5% | 2.5% | `g07` |
| Doorway, three samples (C2, R27 gate, AG) | 82.8 / 83.7 / 89.9% | 81.1 / 81.7 / 86.7% | `g05`, 1.7–3.2 pts on each |
| Goal strip, same three samples | 90.0 / 92.3 / 93.8% | 92.3 / 93.7 / 95.1% | `g07`, 1.3–2.3 pts on each |

No single prompt wins all four rows. Splitting the perceiver into single-task agents lets each
task get the prompt, schema and fusion that suit it:

- **Wall reader.** One job: for each strip, is there floor for one drone length? Candidates to
  probe:
  - `g05`'s describe-first wording, kept for its low phantom rate;
  - a narrower question per strip (bottom-of-strip floor only, a three-way answer);
  - per-strip crops of the frame, so one strip's wall cannot spill into its neighbour's answer;
  - a mix of the two errors through fusion, for example a wall only where the describe-first read
    and a `g07`-style read agree.
- **Doorway reader.** Doorways already have a confirmer (`d01`, which carried in R20). Making a
  doorway agent the primary source, not a check on the perceiver, is the natural next step. The
  s02 failures (false door reports along the door wall) are its target.
- **Goal reader.** `g07`'s format reads the goal best. A goal-only agent has precedent: R5's goal
  identifier (`a06`) scored `initial` 6/6.

Why this fits what we found:
- *Mind Your Step* (ICML 2025) found that reasoning before answering can hurt recognition while it
  helps elsewhere. Here describe-first helps walls and doorways and hurts the goal.
- *Let Me Speak Freely?* (EMNLP 2024) found that format effects differ by task type.
- GSM-IC (ICML 2023) found that unneeded context costs accuracy. A single-task prompt carries only
  what its task needs.

Costs and risks:
- Three perceiver calls a step instead of one. They run concurrently, so latency is about the
  slowest call, but `:8004`'s batch grows, and batch size moves readings (N1).
- More parts, and the repo's history says extra machinery often fails to carry (along-wall
  detours, the "other way" item, goal confirmer `c01`).
- Each agent must pass its own gate against `g05`'s same field before any round flies.

How to probe it before building a round. This needs no flying, and the truth and metrics exist:
- **Frames.** Score each single-task candidate on three sets:
  - AG's set F, R27's 576 flight frames, the hard s03 views;
  - set P, R27's 300-frame probe sample;
  - C2's sample.
- **Gate per task against `g05`**, concurrency 1:
  - wall reader: missed ≤ half and phantom ≤ +2 pts on F and P, and s03 phantom ≤ +4 pts;
  - doorway reader: ≥ `g05`;
  - goal reader: ≥ `g05`.
- **Then fly in stages:**
  - first a wall-reader-only agent (doorway and goal as `a49`), so the round has one change;
  - the doorway and goal agents in later rounds.

### 2. Test on the agent's own path before a full round

Any change that can alter where the drone goes needs an on-policy check before 18 runs. Steps:
1. Fly one unscored run per site, s03 first (about 5 min on lanes).
2. Run `eval/r27_flight.py` on it.
3. Re-read those frames with the old reader, as AG did.

This would have stopped R27 at the shakedown. Also keep AG's set F as a standing hard-frame set.

### 3. Carried over (not yet tried)

- **s03:** `planner.way` reads `open` in the shut tine (B0). Fix what "open" means there before
  adding menu items. The R26 history says new items do not carry.
- **`dynamic`:** stale-open doorways after a door shuts (E0, 32% of runs).
- **s02, last 3 m:** draw the doorway on the navigator frame (probe D, not run).

## Where the evidence is

| What | Path |
|---|---|
| Literature scan | `docs/research/spatial-memory-and-prompting.md` |
| Probe plan and results table | `docs/research/probe-plan.md` |
| Probe write-ups | `eval/phase2/_probes/{a0,a1,b0,c1f1,c2,e0,n1,agree}/README.md` |
| R27 write-up, summary, labels | `eval/phase2/R27_mirrored_nr_perceiver/` |
| R27 probe gate | `eval/r27_probe.py`, `R27…/probe/score.txt` |
| In-flight wall check | `eval/r27_flight.py`, `R27…/walls.txt` |
| AG probe | `eval/probes/agree.py`, `_probes/agree/score.txt` |
