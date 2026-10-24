# R10: Goal known to the planner, no double turn (bundle round)

**Agent:** `a14` (`63ad006476b6`) · **Navigator prompt:** `p14` (`31a9f28eaf94`, as `a13`) ·
**Perceiver:** `g03` (`3531e4d9ade9`) · **Strategist:** `q02` (`f3a866c9d927`) · **Spatial
memory:** `eceb875a68a3` (as `a13`) + a14 wording `0075a8a0e5c0` · **Status:** pre-registered,
not flown

Written before the probe and before flying. Spec: `docs/phase2-test-plan.md` (§8, 2026-10-24).
The shas above are re-checked against `config.lock.json` before the round flies. R10 flies beside
a control, **R10C** (`a13`), on the same host at the same SHA (Control).

## Change

**A bundle of three changes on `a13`, by the operator's decisions (2026-10-24).** Credited to the
bundle, not to any part.

| Part | `a13` (R9) | `a14` |
|---|---|---|
| Perceiver | `g03`, clean frame | unchanged |
| Map, notes on actions | `spatial.py` | unchanged |
| Strategist | `q01`; the goal on its list at the perceiver's estimate, only once seen | **`q02`**: told that the system knows where the goal is and that it does not move. The `goal` entry is at the goal's true position (`manifest.goal.position`) on every call, with its distance and direction. "Your target was reached or is no longer open" is split into "the drone has reached the target you chose" and "the doorway you chose is closed or already passed" |
| Navigator | `p14` | `p14` unchanged. For a goal target the planner line reads "head for the goal (approach)." with no distance or direction; the goal's position reaches the navigator only as "toward your target" on an action |
| Turn-around | always offered | **not offered on the step right after a turn-around while some forward action carries no "blocked here before", "stopped short here before" or "wall close (seen now)" note.** Left off the action list and out of the schema's `enum`; p14 already says "You may only pick a number that is listed as available". The annotated frame still shows the 0 marker. Recorded as `hidden` |
| Critic | one retry on a blocked, spin or loop pick | **off** |

**Goal truth goes to the planner only (operator).** No agent has had the goal's position since
R1 (`a01`); Phase 1's `a00` had its distance and bearing in the navigator prompt, and the model
followed the bearing into walls (R0: `initial` 25/30, `final` + `dynamic` 0/30). Here no model is
given coordinates or degrees; the strategist gets distance and an eight-way direction in words, as
for every other target.

**The hidden action is accepted for R10, not as a lasting design (operator).** If R10 is credited,
the first follow-up is `a14` with turn-around always offered.

`a00`–`a13`, `p02`–`p14`, `g01`–`g03` and `q01` keep their shas (every round lock re-checked). a14's
wording is a separate table (`spatial.WORDS_A14`, `wording_sha_a14()`) appended to `agent_sha`
only for an agent that uses it. All 871 R9 decisions re-render with this branch's code exactly
as with R9's: navigator text, notes, strategist trigger and strategist text (2,063 renders).

## Evidence

From R9's records (`eval/phase2/R9_hail_mary/runs`, [R9 summary](../R9_hail_mary/summary.md)):

- **Turn-around is where `a13` failed.** 105 turn-arounds (12% of picks), 33 straight after
  another. All four `spin_failure` runs alternate turn-arounds while forward moves are open and
  marked "new ground": s01 `final` from step 7, s02va `final` 4, s02vc `dynamic` 14, s03
  `dynamic` 18. s01 `final` step 7: every strip open, the model reasons "facing a wall … stopped
  short in the previous step" from the recent-moves line. s02va `final` step 4: the planner line
  says the target is "about 3 m, ahead" and marks [2] "toward your target"; the model reasons the
  target "is behind the current heading" and turns.
- **Soft cues did not move it.** The critic objected 19 times and changed 0 picks.
- **The strategist distrusted the goal.** With the goal out of view and on the list, `q01` chose
  it on 18 of 200 calls, 2 of 20 when the estimate was within 5 m. s01 `dynamic`: estimate within
  1 m from step 3 to step 34, and the strategist chose explore ("far off … may be behind a wall")
  and read "your target was reached or is no longer open" as the goal being blocked. 194 of 871
  steps had no target.
- **The goal estimate is wrong most of the time the goal is out of view** (≥ 5 m off on 180 of
  200 such calls). On a straight approach every sighting lies on one line and the estimate falls
  back to the distance class: s02a/c/va/vc `dynamic` 15–23 m off from step 3, although the goal
  never moves. One phantom sighting moved s01 `dynamic`'s estimate from 1 m to 19 m off (step 35).
- **What `a13` kept:** 0 picks into a known-blocked heading, 34 collisions (R7 60), s03 to the
  crossbar on `initial` and `final` and a tine exit on `dynamic`.

## Hypothesis

With the goal's position known to the planner and back-to-back turn-arounds removed, the agent
heads for the goal around obstacles instead of exploring or spinning, and `final` + `dynamic`
rises above R10C.

## Predictions

| Measure | Prediction |
|---|---|
| `initial` | ≥ 5/6 |
| `final` + `dynamic` | ≥ 4/12, and above R10C |
| cells changed against R10C | more than 6 of 18 (R8N's noise floor), with more gained than lost |
| `spin_failure` runs | 0 |
| turn-arounds | < 8% of picks (R9 12%) |
| steps with no target | < 10% (R9 22%) |
| strategist calls choosing a target ≥ 3 m nearer the goal than the drone | ≥ 60% (R9 35%) |
| collisions | at most R10C's |

## Attribution rule

As R9. R10 is read against R10C only. A success change is credited to the bundle only if R10
changes **more than 6 of 18** outcomes against R10C **and** gains more cells than it loses. Below
that, the mechanism measures are the result. R9C reproduced R8 in 16 of 18 pick sequences and
every outcome, so R10C against R9 is also reported as a determinism check of `a13`.

## Control

**R10C flies `a13`** (`3de550e110e7`), R9's agent, on sctsvr6 at R10's SHA, right after R10.
R10 against R10C measures the three changes on top of `a13`. [R10C README](../R10C_a13_control/README.md).

## Manipulation check

From `python eval/spatial_replay.py manip eval/phase2/R10_goal_planner/runs` (and the same for
R10C):
- `hidden` on every step where the rule applies, never otherwise; the navigator never picks a
  hidden index (schema);
- turn-arounds, longest run of turn-arounds;
- strategist calls by trigger, target kinds, steps with no target, goal-ward calls
  (`strategist_goalward`, ≥ 3 m nearer the true goal than the drone);
- no navigator text carries a distance or direction for a goal target;
- picks carrying "blocked here before", collisions, revisit rate, mean step latency.

## Drop criterion

`a14` is dropped if two or more hold (as R9):
- `final` + `dynamic` below 3/12;
- `initial` below 4/6;
- any run invalid on the wall clock (900 s);
- `spin_failure` on 2 or more runs.

## Probe gate

`eval/r10_probe.py`, on R9's recorded runs, against the live model, before flying. R10 does not
fly if any line fails.

| Check | Set | Threshold |
|---|---|---|
| strategist goal-ward: target ≥ 3 m nearer the true goal than the drone | R9's 321 strategist calls, rebuilt as a14 words them (same map, goal at its true position, a14's trigger sentence), answered by `q02`, text only | ≥ 55% |
| … against `q01` on the same calls | `q01`'s recorded answers, scored the same way: 113/321 (35%) | at least 20 points higher |
| `q02` chooses "explore" | same | ≤ 20% |
| navigator picks an open move with [0] not offered | the 25 R9 steps where a14 would not offer [0] and R9 turned around: R9's navigator text without the [0] line, R9's annotated frame, `p14` | pick carries no blocked, stopped-short or wall note on ≥ 80% |

The strategist set keeps R9's history (the target standing before each call is `q01`'s), so it
tests how `q02` chooses in R9's situations, not how an a14 run unfolds. The turn set needs R9's
frames, on sctsvr6.

    python eval/r10_probe.py sample-strategist eval/phase2/R9_hail_mary/runs --out strat_set.jsonl
    VLM_AGENT=a14 python eval/r10_probe.py run-strategist strat_set.jsonl --out strat_a14.jsonl
    python eval/r10_probe.py sample-turn <R9 runs with frames> --out turn_set.jsonl
    VLM_AGENT=a14 python eval/r10_probe.py run-turn turn_set.jsonl --out turn_a14.jsonl
    python eval/r10_probe.py report strat_a14.jsonl turn_a14.jsonl

## Shakedown

One unscored `dynamic` run per site on the flight host before the round: every decision record
carries the perceiver, the map snapshot, the notes and, where it applies, `hidden`; every
strategist text lists the goal; `/health` reports `a14`'s sha; no run passes 700 s.

## Host

sctsvr6 headless (Docker, Mesa lavapipe), as R7–R9, with R10C there too.

## Builds on

R9 (`a13`: perceiver, map, notes, strategist, navigator); R5 (perceiver on the clean frame); R6
(ground-truth pose); R8 (control on the same host, noise floor); Phase 1 (`a00` had the goal's
bearing).

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to
[summary.md](summary.md).
