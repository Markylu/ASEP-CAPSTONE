# Probe CR: can code commit to a tine at the s03 crossbar, early, without firing on s02?

**Script:** `eval/probes/cr.py` · **Model calls:** none (offline, CPU) · **Status:** gate set
2026-11-02 before the run, run the same day, **refuted**

Follows [DE](../de/README.md) and [PG](../pg/README.md): the s03 dead end cannot be told from
the s02 door wall by the closed door or by the map's shape, and the budget is lost before the
tine: in `dynamic` the drone is at the crossbar by step 9 and spends 15–33 steps there, asking
`q03` every 2–5 steps and getting `explore` or a frontier a cell away. A run that commits to a
tine by step 12, meets the shut door, turns back and takes the other tine reaches the goal by
about step 44.

## Belief

At the crossbar the record shows a fork the code can recognise: the way to the goal is walled,
and the menu lists two frontiers, one each side, both roughly square to the goal line and neither
nearer the goal than the drone. A rule that picks one at once and holds it to the tine's end, then
turns to the other on a confirmed closed door, would spend the crossbar steps in the tines instead.
The same fork shape should be rare on s02 away from the divider; at the divider it may appear,
and there a side commit is at least not the pattern that loses s02 runs (the door wall is walked
already), so that case is reported, not gated.

## Method

Inputs: every recorded strategist call (`planner.ask` set) in a49's R25D, R29N and R29S runs
(228 calls), the recorded menu, poses and goal.

**Fork trigger T** at a call: `ask` is `walled` or `blocked`; the menu holds two frontiers, at
least 1.5 m away, one to the left and one to the right of the goal bearing, each between 60° and
120° off it; and no frontier or doorway on the menu lies within ±45° of the goal bearing or is more
than 0.5 m nearer the goal than the drone.

Per s03 `final`/`dynamic` run: crossbar arrival (first step with x < 8), first call where T fires
and its step, tine entry step (first pose with x < 5 and |y| ≥ 3), the first `d01`-confirmed and
first perceiver-reported closed door after tine entry (the turn-back cue inside a committed tine).
Budget: a commit at the first T fire, then 36 steps for mouth, tine, back, other mouth, other tine
and goal (4 + 7 + 7 + 6 + 7 + 5), must end by step 60: **first fire ≤ step 24**.

Per s02 call: whether T fires, at the divider (|x| < 3) or elsewhere; when it fires, whether one
of the two side frontiers lies toward an open door (R26's `good`). s01 likewise.

## Gate (set before the run)

The rule is worth a round (`a63`) only if all hold:
1. T fires at a crossbar call (4.5 ≤ x < 8) in ≥ 4 of the 5 failed s03 runs;
2. the first fire is at step ≤ 24 in ≥ 4 of those runs (the budget line above);
3. T fires on ≤ 10% of s02 calls away from the divider (|x| ≥ 3) and ≤ 5% of s01 calls;
4. inside the shut tine, a turn-back cue exists in ≥ 4 of 5 runs within 8 steps of entry: a
   `d01`-confirmed closed door, or a perceiver-reported one if the committed-tine state is what
   gates it (reported both ways).

Divider fires on s02 are reported with the good-side count; they do not fail the gate but go into
the round README as the risk its on-policy check must watch (s02 `final` success against R29S).

If the gate passes: `a63` = `a49` + the rule in `planner.route` (fork → target the first mouth,
held; confirmed closed door in a committed tine → target the other mouth, held), smoke on the
recorded steps, on-policy check (one unscored `final` and `dynamic` run per s02/s03 site), then
18 runs. If it fails, s03 stays with the crossbar coin and the record of why.

## Run

2026-11-02, locally, on the committed `a49` records of R25D, R29N and R29S: 228 strategist calls,
23 of them at the s03 crossbar. After the first pass two looser triggers were added and scored
beside T, before any reading was drawn: **T-wide** (the side frontiers may lie 50–150° off the goal
line, so a mouth behind the drone counts) and **T-one** (one side frontier is enough). Output:
[score.txt](score.txt), per call [calls.jsonl](calls.jsonl).

## Result

**Refuted. No trigger passes.**

| Trigger | crossbar fire, failed runs | first fire ≤ step 24 | s02 divider | s02 elsewhere | s01 |
|---|---|---|---|---|---|
| T (two sides, 60–120°) | **1/5** | 0/5 | 3/114 | 0/30 | 0/18 |
| T-wide (two sides, 50–150°) | **3/5** | 2/5 | 17/114 (15%) | 1/30 | 1/18 |
| T-one (one side) | 5/5 | 4/5 | **82/114 (72%)** | **11/30 (37%)** | **14/18 (78%)** |

Gate 3 (s02 away from the divider, s01) and gate 4 (a turn-back cue within 8 steps of tine entry:
perceiver 5/5, `d01` 2/5) hold for T; gates 1 and 2 do not, for any trigger that stays specific.

- **The fork is not on the menu when the drone arrives.** At the crossbar at steps 9–20 the drone
  stands at the x = 5 wall facing the goal; the perceiver reads that wall, and the memory knows the
  stem behind and a cell or two of crossbar either side. The frontiers listed are behind it (the
  stem, x > 6) and a backtrack point; the tine mouths at y = ±5 are unknown ground, not frontiers.
  `q03` answers `explore`. The two-sided fork appears only after the crossbar has been seen along
  its length: at step 32 in the two `final` runs that wandered the lobby first (and in R25D
  `dynamic` once, at step 10, where the earlier lobby look happened to cover it).
- **Loosening the trigger makes it the s02 divider.** T-one is "walled, and nothing listed toward
  the goal", which is every call at a blocking wall: 72% of s02 divider calls, 78% of s01 calls.
  T-wide sits between: 3 of 5 runs, 15% of divider calls.
- **The turn-back half would work.** Inside the shut tine the perceiver reports the closed door
  within 8 steps of entry in 5 of 5 runs (`d01` confirms in 2); a committed-tine state could gate
  on it safely, since the state would exist only after a fork fire. But there is no early fork to
  commit at.

**Where this leaves the belief.** The crossbar coin is not a choice the record offers early: the
drone does not see the crossbar's arms, because at a blocking wall it looks at the wall. All three
s03 probes (DE, PG, CR) end at the same place: the s03 loss is time spent at a blocking wall
(crossbar 15–33 steps in `dynamic`, lobby 31 in two `final` runs) without looking along it. The
mechanism that would look along it, along-the-wall detours, was R21/R22 (`final` 4 → 2 and 2 of
6) and was dropped. No `a63`. The s03 `final`/`dynamic` cells stay where R29 left them: a coin at
the crossbar when the drone gets there in time, lost otherwise.
