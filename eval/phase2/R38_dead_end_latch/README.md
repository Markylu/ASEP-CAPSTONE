# R38: a66 with a dead-end latch, contested cells

**Agent:** `a78` (`d2c5d0f26cf4`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Dead-end confirmer:** `e01` (`4bd77647a0d7`) · **Memory:** `a17f` ·
**Planner:** `PATHFINDER_A78` · **Status:** laid out 2026-11-05 from the recorded runs of Round
F, R32P and R35; offline readouts measured (below); probe DE run the same day on the operator's
instruction ("Run probe DE"): **gate failed for both prompts, `a78` dropped, round not flown**

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R32P (`a66`, 15/30), no control lane. The round is aimed at one cell,
s03 `dynamic`, and at the s03 `final` losses that begin in the shut tine.

## Change

One change against `a66` (R30, R32P 15/30, F 64/90), in three parts that only work together:
`g05`, `d01`, `p17`, memory `a17f`, the cost map, the tags and the turn rule are `a66`'s.

- **Dead-end confirmer (`e01`, `orchestrator.confirm_dead_end`).** On a step where a closed
  door is read in the centre three strips (after `d01`), one more call on the same clean frame:
  is the drone in a corridor that ends at that closed door? Yes or no, after a description. The
  answer is kept in the perceiver's result (`dead_end`), so the memory and the route rebuild
  from `decisions.jsonl`. Not asked once the latch holds.
- **Latch (`planner.dead_end_latch`, `agent.PATHFINDER_A78`).** Two yes among the confirmer's
  last three answers, none older than 15 steps, latch a corridor as a dead end for the rest of
  the run. The corridor is the longest straight run of trail (segments within 30° of its axis,
  3 m or more) that ended no more than 12 steps before the first of those answers and whose
  lane the drone is still in. It is shut on the route's map as one rectangle: from 2 m down the
  run to 2 m beyond the farthest the drone has been, 8 cells (6.8 m) either side, whatever the
  perceiver painted in it. A lane 1.5 m either side of the axis stays open back to the mouth.
  The first step the drone is back out past the mouth, the lane is shut too.
- **Sentence (`agent.NAVIGATOR_A78`, `orchestrator.behind_note`).** While latched and inside,
  on a step where "toward your target" sits on the turn-around, the planner line gets: "This
  corridor ends at a closed door: it is a dead end. The next point on your route is behind
  you: the turn around is the move toward it." The second sentence is `a70`'s. No critic.

How this differs from `a68` (`planner.dead_end_seal`, R30 shakedown), which sealed the same
corridor and did leave the tine in flight:

| | `a68` | `a78` |
|---|---|---|
| Trigger | a closed-door read within 5 m, and a wall seen beside the trail | the confirmer's answer, twice |
| What is shut | cells beside the trail that are not known floor | every cell of the rectangle but the lane |
| Later floor reads | reopen the seal | change nothing |
| After the drone is out | nothing | the lane is shut |
| Memory | `a17g` (18 lobby steps in its s03 run) | `a17f` (`a66`: 4) |
| Navigator | as `a66` | the sentence while latched |

## Evidence

- **s03 `dynamic` is 0/52 in Phase 2.** Round F (`eval/phase2/final/summary.md`): 0/5, with 40,
  37, 41 and 30 steps in the shut tine after the closed read and none in the open tine. R35
  (`eval/phase2/R35_wall_turn_only/summary.md`): 0/3. s03 `final` is lost when the first tine
  is the shut one (F seed 1, R35 seed 1).
- **The route in the shut tine never points out.** Of the shut-tine steps after the first
  closed read, the recorded route leaves by the crossbar on 0 of 444 (`a73` 2%, `a74` 10%,
  `docs/research/round-f-analysis.md` §4, §6); 205 of 223 leave through floor the perceiver
  painted through the tine's walls (§3.3).
- **`a68`'s seal worked in flight and failed elsewhere** (`eval/phase2/R30_pathfinder/README.md`,
  shakedown): the drone left the tine at s37–39 and reached the crossbar at s53–55, then flew
  back in with five steps left; s02a and s02vc were boxed in the hall by the same seal. `a69`:
  nothing in `g05`'s per-strip reads tells a 3 m corridor from a hall.
- **A closed-door read is not a trigger, and neither is the trail's shape**
  ([probe dead_end_trigger](../_probes/dead_end/README.md), 120 change-arm runs, no model). A
  closed door in the centre three strips is read on 1126 s02 steps, 90 steps in the shut tine
  facing its door, and 24 elsewhere in s03. A strict rule on the reads fires in 67 of 98 s02
  runs and 2 of 11 s03 `dynamic` runs; a straight run after a turn fires in 73 of 98 and 9 of
  11. Every s03 `dynamic` loss has a closed-door read in the shut tine, first at step 23
  (median), 9 of 11 with 25 or more steps left.
- **The navigator declines the turn-around about half the time it carries "toward your
  target"** (R30 shakedown, `a63`, `a67`, `a68`); with `a70`'s sentence it took it 46 of 46.
  `a68` needed 16 steps from its seal to the crossbar, 9 m away.
- **A lead, not evidence.** A side experiment outside the project's rules (one run per
  condition, a different model, no lock or replay; brief at
  `eval/personal/opus_s03_dynamic/NEXT_ROUND_PROMPT.md` on branch
  `m/map3-pitchfork-subagent-087aa3`, untracked) had Claude Opus solve s03 `dynamic` seed 1
  with a text record of its own steps and fail without one; the record's working content was
  one sentence, that the corridor is a dead end. It is why the question is put to the model
  directly here. It enters no table and no count.

## Hypothesis

With the corridor it stands in latched as a dead end on the confirmer's word, `a78` leaves the
shut s03 tine and takes the other one, where `a66` stays; the confirmer stays silent in the s02
hall, so the s02 cells are `a66`'s. It scores at least 15/30, with s03 `dynamic` above 0/3.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a78` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 5–7 (the latch silent: `a66`'s draw) |
| s02 `dynamic` ×4 | 6/12 | 5–7 |
| s03 `final` | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 1–2 (the recovery is about 20 steps from the door; the latch comes at step 19–37 in the recorded runs) |
| **total** | **15/30** | **15–18** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule). The best case here is +3, so the
total alone cannot carry this round; s03 `dynamic` is read as a cell, 0/52 before it.

## Manipulation check

Code only, from `decisions.jsonl` (`planner.latch`, `dead_end_confirmer`, `route_behind`,
`eval/r30_check.py`, `eval/r28_flight.py`):
- In every s03 run that enters the shut tine: a latch, no more than 10 steps after the first
  closed-door read in that tine; its axis within 20° of the tine's; its mouth between the
  tine's trigger line and the crossbar (0 ≤ x ≤ 8).
- After the latch: the drone out past x = 5 within 10 steps; 0 steps in the shut tine after
  that.
- The sentence on every latched step with "toward your target" on the turn-around, and the
  turn-around taken on at least 70% of them.
- s02: a latch in at most 2 of the 24 runs.
- A route on at least 95% of steps; walls in flight within 4 points of Round F's (missed
  16.7%, phantom 12.4%).

## Drop criterion

Not carried forward below 15/30, or with s03 `dynamic` at 0/3, or with a latch in more than 4
of the 24 s02 runs.

## Probe gate

Two gates. The first needs the model; it was run after this section was written and failed
([Outcome](#outcome)). The second needs no model and was read while the latch was being built.

**Gate 1, probe DE: can the model call the corridor?** `eval/probes/dead_end.py`, write-up
[_probes/dead_end](../_probes/dead_end/README.md). `e01` and `e02` (the same question put as
"is turning back the only way on?") are asked on the clean frame of every step of Round F, R32P
and R35 with a closed-door read in the centre three strips: 1240 frames, on the lane checkouts.
Set here, before any call:

| Readout | Gate |
|---|---|
| Yes on steps in the shut tine facing its door (90) | at least 80% |
| Yes on s02 steps (1126) | at most 5% |
| s03 `dynamic` runs the latch's rule fires in with 25 or more steps left (11 runs) | at least 7 |
| s02 runs the rule fires in before the drone crosses (88 runs have an asked step) | at most 5 |
| Asked steps answered | all |

A confirmer that is never wrong reaches 8 on the third row: in three runs the first closed-door
read in the shut tine comes at step 29, 36 and 54. The plan written before that was measured
said 9; 7 is one under the ceiling. A prompt passes on all five rows. If neither passes, there
is no honest trigger, as `a69` found for wall reads: R38 is not flown and `a78` is dropped. If
only `e02` passes, the agent is a new version with `e02` (an agent is never edited once its
round is laid out), and this round's entry moves to it before anything flies.

**Gate 2, offline replay.** `eval/probes/a78_replay.py`, write-up
[_probes/a78](../_probes/a78/README.md). Open loop on the same 120 runs: the drone flew `a66`'s
picks, so this is what `a78`'s route says from where that drone stood. **The latch's
parameters (`look_back_steps`, `recent_steps`, `lane_m`, the axis rule) were set while reading
this replay on these runs, with the confirmer replaced by one that is never wrong. It is a
record, not a pre-registration.**

| Readout | Gate | `a66` | `a78`, confirmer never wrong | `a78`, confirmer always yes |
|---|---|---|---|---|
| s03 shut-tine steps from the latch on whose route leaves by the crossbar | at least 80% | 0/444 | **354/396 (89%)** | 374/428 (87%) |
| Round F s03 `dynamic` runs latched with 25 or more steps left | at least 4 of 5 | — | **4 of 5** (steps 25, 37, 20, 19, 35) | 5 of 5 |
| Won s02 runs latched before their crossing | 0 | — | **0 of 53** | 43 of 53 |
| Lost s02 runs latched before a crossing | — | — | 0 of 45 | 45 of 45 |
| Steps with no route | — | — | 4 of 5653 | 257 of 5653 |

Met with a confirmer that is never wrong, which says the latch does its part if the trigger
does. The last column is what the trigger's failure costs: a latch in 88 of 98 s02 runs. Gate 2
is read again with probe DE's own answers (`--answers probe:e01`) before a shakedown. What the
replay cannot show: the recorded drone never leaves the tine, so the lane shut after the drone
is out is covered by unit tests only, and whether the navigator flies the route back is a
flight question.

Two runs the latch does not reach, with any confirmer: R35 s03 `dynamic` seed 3 (the drone cut
into the tine at an angle, the straight run begins at x = 3.3, and the corridor's mouth lands
inside the tine: 0 of 23 routes out) and R32P s03 `dynamic` seed 3 (the door shut at step 32
and the first closed-door read facing it came at 54).

## Builds on

R35 (`a66` still the best agent: F 64/90, R32P 15/30). Branch `phase2/r38-dead-end-latch` from
`phase2/r33-deadlock-costmap` (`a87e188`).

## Notes for the operator

- **Tests and smoke (no model):** `python -m pytest server/decider/tests -q` (43 pass);
  `VLM_AGENT=a78 python eval/probes/a63_smoke.py` (R25D's 627 recorded steps, 0 failed, with the
  confirmer stubbed: `SMOKE_DEAD_END=s03`, `yes` or `no`).
- **Readouts (no model):** `python eval/probes/dead_end_trigger.py` (a few seconds);
  `python eval/probes/a78_replay.py --answers oracle` (about 70 s); `--answers always` (over
  10 min).
- **Probe DE (model calls, on the host that holds the frames):**
  `python eval/probes/dead_end.py sample <lane roots>`, then `run --prompt e01`, `run --prompt
  e02`, then `score`. 2480 calls at concurrency 1. I have not seen the lane checkouts: the
  roots in the script's docstring are a guess at their names.
- **Preflight, if flown:** `python -m server.decider --profile remote --agent a78`; `/health`
  should report `d2c5d0f26cf4`. Earlier agents keep their shas (`a66` `de7f23d07186`, `a75`
  `81d682c1424b`, `a77` `6744446339b0`): the confirmer stage and the latch run only for an agent
  that names them.
- **Shakedown, if gate 1 passes:** seed 1, alone on `:8004`: s03 `dynamic`, s03 `final`, s02c
  `dynamic`, and the two cells `a68` boxed, s02a `dynamic` and s02vc `dynamic`. Scored by the
  manipulation check above; a latch in any of the three s02 runs fails it.
- **Not built:** a flight along the Opus routes with the picks forced (the plan's optional
  step 4). The Opus runs kept annotated frames only, and `g05` reads the clean frame, so the
  brief's items 1 and 4 cannot be run on them as they are.

## Outcome

Round not flown. **Probe DE (2026-11-05, operator: "Run probe DE"): gate 1 failed for both
prompts.** 2480 calls, one at a time, alone on sctsvr6's `:8004`, from `bfd0cf6`; no failed
call. Write-up and tables: [_probes/dead_end](../_probes/dead_end/README.md).

| Readout | Gate | `e01` | `e02` |
|---|---|---|---|
| Yes in the shut tine facing its door | at least 80% | 85/90 (94%) | **15/90 (17%)** |
| Yes on s02 steps | at most 5% | **420/1126 (37%)** | 15/1126 (1%) |
| s03 `dynamic` runs fired in with 25 or more steps left | at least 7 of 11 | 8 | **3** |
| s02 runs fired in before the crossing | at most 5 of 88 | **65** | 0 |

- **`e01` cannot be the trigger.** It calls the s02 hall a dead-end corridor on 37% of asked
  steps: 84% within 2 m of the divider, 80% on looks 30–60° off square to it, 1% from 8 m out.
  The rule fires in 65 of 88 s02 runs, 21 of them runs `a66` won.
- **`e02` is quiet and nearly blind.** Yes on 1% of s02 steps and 17% of shut-tine steps; in
  the tine it counts the floor beside the door as a way past it.
- **Drop criterion met before flight:** by the rule set above, with neither prompt passing,
  `a78` is dropped and R38 is not flown. The hypothesis is not tested; its premise, that the
  model can be asked what `g05`'s strips cannot say, did not hold on single frames.

Gate 2 read again with the probe's own answers (`eval/probes/a78_replay.py --answers
probe:e02`, [_probes/a78](../_probes/a78/README.md)): with `e02` the latch fires in 3 of the 11
s03 `dynamic` runs (steps 35, 19, 35, with 25, 41 and 25 steps left) and in none of the 98 s02
runs; in those three the route leaves the tine on 87 of 89 steps. That is a latch that does no
harm in s02 and reaches about a quarter of the cell it was built for. With `e01` it fires in
all 11 and in 65 of the 98 s02 runs (21 of the 53 `a66` won), with no route on 220 of 5653
steps. Both are read after the gate and do not reopen it.

**After the gate (same day, operator: "check filter").** `e01`'s answers were read against
what the agent has at each step ([_probes/dead_end §3](../_probes/dead_end/README.md)). Kept
only while the memory knows at most two closed-door places, the latch's rule fires in all 11
s03 `dynamic` runs (8 in time) and in 1 of the 88 s02 runs, and it holds in each of the three
rounds separately. That is a fit to the answers the gate failed on, on a narrow range of
settings, with the `initial` arms never sampled; it is a lead for a new agent and a held-out
probe (561 asked steps on R30, R32 and F's `initial` runs), and it changes nothing above.

What stands: the latch itself is sound on the record (gate 2 with a confirmer that is never
wrong), and it has no trigger. `a66` is still the best agent (F 64/90, R32P 15/30).
