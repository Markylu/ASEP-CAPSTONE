# R2 Text memory, full run: summary

**Hypothesis did not hold (screening).** With its whole run in the prompt, the agent did not stop
doubling back. It stopped re-planning. Success fell from 8/18 in R1 to **1/18**: `initial` 5/6 → 1/6,
and `final` + `dynamic` 3/12 → 0/12. Collisions rose from 31 to 596. The memory was delivered and
read. The model used it to repeat itself: every failing run settles on one marker within the
first 10 steps and keeps it to the end. All three parts of the drop criterion are met. `a02` is
dropped, and `a01` remains the best agent. This is one seed per cell, so it is a screen, not an
effect size (`docs/phase2-test-plan.md` §3). Pre-registration: [README.md](README.md).

**Not citable.** Flown at `dd20d3b` on 2026-10-09, 17:15–17:51 UTC. The runs used
`Qwen3-VL-30B-A3B` on the remote profile, at temperature 0, with agent `a02` (`f53deb3d5b14`) and
prompt `p04` (`d514fe7a2ded`). The decider ran on :8011, because the R1 decider still held :8010.
The served context is 32,768 tokens. Labels were reviewed by Claude and are **pending operator
confirmation**.

- **18 / 18 runs valid on the first attempt.** Every replay was exact, every `run.json` has
  `git_dirty: false`, and the agent sha matches the round lock.
- Spawn jitter for seed 1 is the same as in R0 and R1.

## Result

| Arm | R0 | R1 | R2 | success | ignore | replan | collision | pre-change | latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|
| initial | 5/6 | 5/6 | **1/6** | 1 | – | 1 | 4 | – | 1.46 / 2.38 s |
| final | 0/6 | 2/6 | **0/6** | 0 | – | 4 | 2 | – | 1.56 / 2.50 s |
| dynamic | 0/6 | 1/6 | **0/6** | 0 | 5 | 0 | 0 | 1 | 1.50 / 2.31 s |

Collisions over all 18 runs: **596** (R1: 31, R0: 675). Latency rose from R1's ~1.4 / 1.8 s. At
step 60 the prompt is 8.8k tokens (median), and 13.7k at most.

### Every cell

✓ steps to goal, or ✗ label.

| Site | initial R1 → R2 | final R1 → R2 | dynamic R1 → R2 |
|---|---|---|---|
| s01 | ✓ 14 → ✓ 14 | ✗ timeout → ✗ replan | ✗ replan → ✗ ignore |
| s02a | ✓ 14 → ✗ collision | ✗ timeout → ✗ replan | **✓ 60 → ✗ ignore** |
| s02c | ✓ 14 → ✗ collision | **✓ 34 → ✗ collision** | ✗ timeout → ✗ ignore |
| s02va | ✓ 55 → ✗ collision | ✗ replan → ✗ replan | ✗ timeout → ✗ ignore |
| s02vc | ✓ 55 → ✗ collision | **✓ 24 → ✗ replan** | ✗ timeout → ✗ ignore |
| s03 | ✗ replan → ✗ replan | ✗ replan → ✗ replan | ✗ replan → ✗ pre-change |

The `dynamic` column has the same labels as R0, the Phase 1 agent: five `ignore_change` and s03
`pre_change_failure`. R1's s03 `dynamic` run reached the trigger at step 44; R2's never did.

## Manipulation check

`python eval/agent_evidence.py eval/phase2/R2_text_memory`, saved as
[manipulation_check.md](manipulation_check.md), against R1's numbers in [evidence.md](evidence.md):

| Measure | R1 | R2 | Pre-registered expectation |
|---|---|---|---|
| `memory_steps` = number of earlier decisions | – | **1034 / 1034** | every decision: passed |
| `prompt_tokens` rises every step | flat 922 | **strictly rising, every run** | passed |
| reason cites memory | 1–2% | **39% / 67% / 61%** (final / dynamic / initial); 54% after step 5 | clearly above R1: passed |
| revisit rate, `final` / `dynamic` | 28% / 33% | **74% / 77%** | below R1: **failed**, it rose |
| turn-around pick | 8% / 12% | **0% / 0%** | – |
| same pick as the step before | 60% | **97%** | – |
| reason identical, word for word, to the step before | – | **62%** | perseveration watch: **triggered** |

Delivery and use both pass, and behaviour moved the wrong way. The README said to read the reasons
in any run where revisits do not fall. They fell in no run.

## What the model did

**It locks onto one marker and never changes.** Leave out s01 `initial`, which arrives in 14 steps.
Each of the other 17 runs settles on one marker and keeps it to step 59. The lock starts at step 0
on 9 runs, by step 4 on 14, and by step 9 on all 17. The marker is `[3]` (straight) on 12 runs,
`[1]` (hard left) on 2 and `[5]` (hard right) on 3. The turn-around was never picked in 1034
decisions. In R1, s01 `dynamic` turned around at step 4 and s02c `dynamic` at step 5.

**It treats its own history as a plan.** The reasons count the streak and use it as the
justification:

- s01 `dynamic`, step 40: "I have been moving forward in a straight corridor using marker 3 for 38
  consecutive steps". The cube is in front of it, and it is pinned there.
- s02a `initial`, step 15: "I have been moving forward through the doorway (marker 3) in every step
  since the beginning". It passed 1.1 m from the goal at step 14 (arrival radius 1.0 m) and flew on
  to the back wall.
- s02c `final`, step 45: "for 44 consecutive steps, consistently choosing marker [3]", against the
  back wall at x = −24, which it calls "a doorway straight ahead".

**The history it describes is often false.** It writes summaries of its own past that do not match
what it did, then copies them forward:

- s01 `final`: from step 5 to step 59 the reason is the same, word for word: "turning left at each
  step ... a large open space ahead, with no visible obstacles". It picked `[3]` every step and hit
  the cube 51 times.
- s02a `final` circles the spawn room on `[1]` with 0 collisions while it reports "moving forward
  through a series of open doorways on the left ... for 22 consecutive steps".
- s03 (all arms): "I have already explored the left path extensively". It picked `[1]` on 4 steps,
  then `[5]` for 51.

**It stops looking at the frame.** In R1 the model read the door switch correctly on s02va and
s02vc `dynamic` at step 4. In R2 all four s02 `dynamic` runs fly `[3]` into the closed middle door,
with 49–54 collisions. Their reasons say "the central door remains open" and "The environment has
not changed" (s02va, step 20). 12 of the 18 runs are tagged `path_hallucination`. The memory
overrides perception: the record says the path is clear, so the reason says so too.

**Identical runs.** Because the agent locks so early, many cells fly the same trajectory with the
same reasons. Within each group the runs are identical:

- s02a and s02c `dynamic`.
- s02va and s02vc `dynamic`.
- s02a and s02c `initial`.
- s02va and s02vc `initial`.
- All three s03 arms.

So R2 holds fewer independent observations than 18 runs suggest.

**Cost.** `initial` arms that succeeded in 14–55 steps in R1 now run all 60 steps, so flying took
36 min against R1's 31. Per-decision latency p95 rose from ~1.8 s to ~2.4 s with the longer prompt.

## Against the predictions

| Prediction (README) | Outcome |
|---|---|
| `initial` 5/6, s02va/vc in fewer than 55 steps | **Wrong**: 1/6. Four `initial` cells pass the goal and grind on the back wall |
| `final` ≥ 3/6 | **Wrong**: 0/6. Lost both of R1's successes |
| `dynamic` ≥ 2/6, s02c most likely | **Wrong**: 0/6. Lost R1's s02a success; s02c ignores the change |
| Fewer than R1's 5 `timeout` | Held trivially: 0 `timeout`, because nothing gets through and then wanders |
| s03 unchanged | **Held** on label; it no longer reaches the `dynamic` trigger |
| Revisit rate falls | **Wrong**: 28% / 33% → 74% / 77% |

**Drop criterion: met on all three counts.** `final` + `dynamic` is 0/12 (≤ 3/12) while the check
shows use, `initial` is 1/6 (≤ 3/6), and revisits rose. `a02` is not carried forward. The next round
builds on `a01`.

## For the next round

R2 separates two parts of "memory". The information R1 lacked (where it had been, where it last saw
the goal) may still help. The form R2 delivered it in clearly does not. The failure is the model
misunderstanding its own system. It read a verbatim log of its reasons as a plan to continue, counted
streaks in marker numbers whose meaning changes every step, and trusted its own old claims over the
current frame.

### R3 plan: a memory log, formatted for the model (operator's choice)

Chosen by the operator: fix the memory's **format**, and the prompt that explains it, without
spending more compute. Collision feedback stays out, so R3 remains one change. It builds on `a01`,
not `a02`. To be written up as `eval/phase2/R3_<slug>/README.md` before flight (§4.1).

**Change: agent `a03`, prompt `p05` (from `p03`).**

1. **The log is written by code, not by the model.** One line per earlier step, full run, in a fixed
   format, for example:

   ```
   Log of your earlier steps (what happened, not a plan):
   Step 25: flew straight. Goal: not visible.
   Step 26: flew slight left. Goal: ahead.
   Step 27: flew straight. Goal: right.
   Step 28: turned around. Goal: not visible.
   ```

   - The **move** comes from the chosen action's heading in the manifest: straight (0°), slight
     left/right (±22°), sharp left/right (±44°), or turned around. It records what the drone did,
     so it cannot be false the way R2's "turning left at each step" was.
   - There are **no marker numbers**, so there is no "marker 3 for 38 consecutive steps".
   - There are **no reasons**, so there is no prose to copy. R2 copied 62% of its reasons word for
     word.
2. **Goal sighting is a structured field in the same call.** The reply schema gains
   `goal: ahead | left | right | not_visible`, emitted before `reason`, so the model reports the
   current frame before it argues. The log shows this field. There is no extra model call: about
   5 more output tokens per step.
3. **The prompt explains the system.** `p05` adds a short paragraph:
   - The log is a record of what happened, kept by the system, not a plan.
   - Directions in the log are relative to the heading at that step.
   - The current image is the only view of the world now; if it disagrees with the log, trust the
     image.
   - Repeating a move is right only while the image shows it is still working.
   - Turning around is a normal move when the way ahead is blocked. R2 picked it 0 times in 1034
     decisions.

**Compute.** About 10 tokens per log line, so at most ~600 tokens at step 60. The prompt is about
R1's 922 plus that, against R2's 8.8k median at step 60. It is still one model call per step. Latency
should be close to R1's ~1.4 / 1.8 s, not R2's 1.5 / 2.4 s.

**Evidence.**
- R1 lost the goal after finding the route: sightings 15–30 steps apart and 5 timeouts (R2 README,
  Evidence 1–2).
- R2's verbatim log drove the lock-in: 97% same pick as the step before, 62% copied reasons and 0
  turn-arounds. Its reasons count streaks in markers and repeat false history (sections above).
- R1 showed the model reads the frame correctly when nothing tells it otherwise (door switch on
  s02va and s02vc).

**Hypothesis.** The model can use a record of its moves and goal sightings when the record is
factual, compact and framed as history. It keeps R1's reading of the frame and gains the persistence
R1 lacked.

**Predictions** against R1 (best so far):
- `initial` 5/6.
- `final` + `dynamic` ≥ 4/12 (R1: 3/12), with gains in R1's `timeout` cells.
- s03 is unchanged.

**Manipulation check.**
- The goal field is filled on every decision, and it agrees with the manifest's `line_of_sight`
  well above chance. This is a new `agent_evidence.py` column. It also measures perception
  directly.
- Same pick as the step before stays near R1's 60%, not R2's 97%.
- Reasons copied word for word from the step before stay rare (< 10%).
- The turn-around is picked again (R1: 8–12%).
- The revisit rate falls below R1's 28% / 33%.

**Drop criterion.** Drop `a03` if any of these holds:
- `final` + `dynamic` ≤ 3/12 while the log is read.
- `initial` ≤ 3/6.
- The lock-in returns: same pick as the step before ≥ 90%.

**Code, building on what R2 added.**
- `schema.py`: the `goal` field, only when the agent's memory feature asks for it, and a `GOAL:`
  line on the text rung.
- `recorder.Run.memory()`: return the move and the goal, not the reason.
- `prompt.py`: `p05` and its renderer.
- `agent.py`: `a03`, with `memory: {kind: log, scope: full_run, fields: [move, goal]}`.
- `fake_litellm.py`: emit `goal` so the dry run exercises it.
- `agent_evidence.py`: goal-report accuracy, same-pick rate and copied-reason rate as columns.

**If R3 fails** with the log in use, the next candidates are, in order:
- **Collision feedback:** "hit something" as a fact in the log.
- **A short buffer.**

Both build on `a01` or `a03`, depending on what R3 shows.

## Validity notes

- The auto-labeller's acknowledgement detector gave three false positives on `dynamic`: s02a,
  s02c and s02va were pre-labelled `replan_failure` because their reasons say "doorway ... open" or
  "the central door remains open". None of them mentions the closed door. Manual review overrode
  all three to `ignore_change` (`labels.csv` notes). The rubric and thresholds are unchanged. R1
  already flagged this detector for `p03`-style wording; it fires on `p04` too.
- Static-arm `ack_step` values are cleared, as in R1.
- The keyword list for "reason cites memory" counts raw hits. In R2 most hits are the model
  counting its own streak, which is use of the memory, not good use of it.
