# R49: a88's planner without the route-behind sentence outside a latched corridor, contested cells

**Agent:** `a89` (`85cda76df25b`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A89` ·
**Navigator notes:** `NAVIGATOR_A78` (`a85`'s) ·
**Status:** laid out 2026-11-06 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason) from R46's flight, while R47 was in the air and R48 queued;
shakedown flown 2026-11-06 (one of four solved, gate passed by its letter); round flight below

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R45 (`a85`, 23/30, the bar), no control lane.

## Change

Against `a88`, two things, both removals:

- **The navigator's notes are `a85`'s again** (`NAVIGATOR_A78`): the route-behind sentence is
  said only inside a latched corridor. `a86` said it on every step the route asked for the
  turn-around (`always`), and `a87` and `a88` inherited that.
- **The reopening is bounded** (`reopen_inside`): `a88` opens the latched corridor's lane again
  to a drone back inside it; `a89` does so only short of the rectangle's far end. Code only.

Everything else is `a88`'s planner: the wall survey with stations shut only by walls the drone
has met (`a87`) and a short second look in place of the through-by-distance rule (`a86`); the
dead-end latch kept off the direct line and held back while the survey runs (`a86`); the lane
reopened to a drone back inside (`a88`). Against the bar `a85`, `a89` is the planner changes
of `a86`–`a88` without `a86`'s sentence.

## Evidence

- **R46 (`a86`, 21/30 against `a85`'s 23/30, a draw):** the sentence was taken on 98 of 98
  steps it was said (s03 26 of 26, s02 72 of 72). s03 went 5/6 (R45 4/6) and s02 16/24
  (R45 19/24). **The survey started in 15 of the 24 s02 runs (R45: 23 of 24), and 5 of the 9
  runs without one were lost.** On the record the turn-arounds the route asks for on the way in
  are often spurious (a frame with every strip blocked at step 1 in s02a dynamic seed 2: the
  tag sat on the turn-around, the sentence was said, the drone turned its back to the wall and
  never read the shut door in the centre strip; s02c final seed 3 drifted at heading 160 the
  same way). `a85`'s navigator ignored those tags; `a86`'s was told to take them.
- **The sentence's gain is inside the corridor**, where `a85` already says it: R46's three s03
  dynamic runs latched at 27, 37 and 21 and the two that got out in time were solved.
- **Station guard (`a87`):** on R44's records both stations stand at the start in 22 of 22
  surveys (14 under `a86`'s rule); R47's shakedown solved four of four s02c runs.
- **Reopening (`a88`):** R45's s03 dynamic seed 1 flew back into the plugged corridor and had
  no route on 21 steps. In R48's shakedown the rule also fired once for a drone already
  through the other tine's door, beyond the rectangle's far end (harmless there); `a89` bounds
  it.

## Hypothesis

With `a85`'s navigator the survey starts as often as in R45, and with `a87`'s stations and
`a86`'s latch guards the s02 runs R45 lost after the survey ended early are won. `a89` scores
at least `a85`'s 23/30, with s02 at 19/24 or more.

## Predictions

| Cell group | R45 (`a85`) | R46 (`a86`) | Predicted `a89` |
|---|---|---|---|
| s02 ×8 cells | 19/24 | 16/24 | 19–22 |
| s03 `final` | 3/3 | 3/3 | 2–3 |
| s03 `dynamic` | 1/3 | 2/3 | 1–2 |
| **total** | **23/30** | **21/30** | **22–26** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule): 21–25 is a draw with `a85`; `a89`
replaces it as the bar only at 26 or more. Read also against R47 and R48 as they land.

## Manipulation check

From `decisions.jsonl` (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`):
- The sentence is said on no step without a latch in force.
- The survey starts in at least 20 of the 24 s02 runs, by step 8; in none of the 6 s03 runs.
- No latch fires in an s02 run before its survey has ended.
- A reopening only for a drone inside the rectangle.
- A route on at least 95% of steps; walls in flight within 4 points of R45's.

## Drop criterion

Not carried below 21/30 or with s02 under 17/24. The bar at 26/30 or more; between, a draw
with `a85`, and the better of the two on s02 and s03 separately is what the next round builds
on.

## Probe gate

**No model probe.** What the model is asked and told is `a85`'s to the letter (prompt `p17`,
notes `NAVIGATOR_A78`), flown on 30 runs in R45. The planner settings are `a86`'s to `a88`'s,
each shaken down on-policy tonight (R46 four of four, R47 four of four, R48 two of four with
the gate passed).

**Offline gates:** `python -m pytest server/decider/tests -q` (78 pass; the new one holds
`a89`'s notes to `a85`'s, its planner to `a88`'s, and the reopening to the rectangle);
`VLM_AGENT=a89 python eval/probes/a63_smoke.py` (627/627); the closed-loop simulation
(`eval/probes/a80_sim.py --far 20`, `eval/phase2/_probes/a89/`): truthful perceiver 48/48
(change arms 32/32), measured noise with 20% of moves random 116/144 (change arms 70/96;
`a87` 70, `a86` 69, `a85` 67). The simulation's navigator takes the tagged move, so it says
nothing about the sentence. Earlier agents keep their shas (`a85` `a43435111dff`, `a88`
`144756aca5a8`).

**Shakedown gate** (on-policy, a fifth client beside R47's lanes on `:8004`): s02a `dynamic`
seed 2, s02c `final` seed 3, s02vc `final` seed 1 (the three lost in R46 with no survey) and
s03 `dynamic` seed 2 (lost in R45 and R46). Passes if the survey starts by step 8 in the three
s02 runs with a frame square to the wall in each, the sentence is said on no step without a
latch, and a route is on at least 95% of steps. Wins are not required.

## Builds on

`a88` (R48, queued) and, for the navigator, `a85` (R45, 23/30). Branch
`phase2/r49-no-sentence` from `phase2/r48-latch-reopen` (`8679066`); R46's, R47's and R48's
results are merged in before this round's PR.

## Outcome

Not flown yet. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).

**Shakedown (2026-11-06, 07:59–08:27 UTC): four unscored runs, slot 5 (port 8105) as a fifth
client beside R47's lanes (and, from 08:14, `a91`'s shakedown on two freed lanes), sctsvr6
`~/asep-r33-shake` at `12c2814`, log `~/r49_shake_a89.log`. All valid, one of four solved.
Gate passed by its letter.** (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`.)

| Cell (seed) | `a89` | Earlier tonight, same cell and seed | What happened | Sentence |
|---|---|---|---|---|
| s02a `dynamic` (2) | lost | solved at 26 in R45 (one station); no survey and lost in R46 | survey from 4; the first station on the side of the door that had shut (looks 11–15), 18 steps to the second (two turn-arounds the tags did not ask for), at the door at step 36 beside the jamb, turned away, survey over at 45 | none |
| s03 `dynamic` (2) | lost | lost in R45 and R46 | door shut at 18, latch at 35, 17 steps later, out at 39, not out of the tine in time | 1, latched, taken |
| s02c `final` (3) | lost | lost in R45 and R46; solved at 25 in `a91`'s shakedown | survey from 5, both stations (looks at 13 and 24, two square), no doorway flown at, over at 28 | none |
| s02vc `final` (1) | solved, 31 | lost in R45 and R46 | survey from 2, the door flown at from 3, through at 23 | none |

- **Gate:** the survey by step 8 in the three s02 runs: 4, 5, 2. A frame square to the wall
  in each: 2, 2, 1. The sentence on no step without a latch: held. A route on every step.
  Passed.
- **What it does not show:** a win where R46 lost for want of a survey. The survey started in
  all three (R46: none of the three), and two of the three were still lost, at the stations
  and at the door. `a91` (R51: this agent without the station guard) solved three of four on
  its own shakedown beside this one and flies first; R49 follows it on the same lanes.
