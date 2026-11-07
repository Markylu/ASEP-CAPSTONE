# R57 a95 (a93 with the survey started for a drone on the direct line now) on the ten contested cells, seeds 1-3: summary

**a95 22/30 against the reference lane's 20/30 (R58, `a93`, same batch, same renderer): two above, a
draw by the rule (under 3), not carried. s02 19/24 against 17/24, s03 3/6 against 3/6. The hypothesis
(at least as many runs as the reference, the gain on s02) held on the numbers, but the change itself was
exercised in only two runs, both lost: the two runs that lost without a survey in R55 did not leave the
line this time, and the s02 gain came in cells where the rule did not act (s02a 6/6).**

| cell | `a93` (R58, reference) | `a93` (R54) | `a95` (R57), steps to the goal |
|---|---|---|---|
| s02a `final` | 2/3 | 2/3 | **3/3** (24, 32, 43) |
| s02a `dynamic` | 2/3 | 2/3 | **3/3** (53, 39, 39) |
| s02c `final` | 2/3 | 1/3 | 2/3 (—, 51, 60) |
| s02c `dynamic` | 1/3 | 3/3 | **2/3** (27, 47, —) |
| s02va `final` | 2/3 | 3/3 | 2/3 (—, 26, 23) |
| s02va `dynamic` | 3/3 | 3/3 | 2/3 (60, —, 37) |
| s02vc `final` | 3/3 | 1/3 | 3/3 (38, 25, 30) |
| s02vc `dynamic` | 2/3 | 2/3 | 2/3 (—, 28, 32) |
| s03 `final` | 3/3 | 1/3 | 2/3 (—, 29, 52) |
| s03 `dynamic` | 0/3 | 1/3 | **1/3** (45, —, —) |
| **total** | **20/30** | **19/30** | **22/30** |
| s02 | 17/24 | 17/24 | 19/24 |
| s03 | 3/6 | 2/6 | 3/6 |

Against the predictions (README): reference +0 to +2 predicted, +2 landed; s02 +0 to +2 (+2), a survey in
at least 23 of 24 (23); s03 within 1 (3 against 3).

What the runs say (scratch `batch_check.py`, the survey timelines, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R57_survey_line_now`):
- **Where the new rule acted.** Two s02 runs had been more than 2.5 m off the direct line before their
  survey started, so the old rule would have refused them: s02c `final` 1 (2.9 m off, survey from step 6:
  first station looked 12–24, second station looked 27–39, done, a latch at 40, lost) and s02va `final` 1
  (6.4 m off, survey from step 35 after thirty steps of wandering, two stations given up, lost). **Both
  lost.** s02vc `final` 3, the cell lost four of four flights before with no survey, started its survey at
  step 2 this time and never left the line (the step-0 waypoint-behind artefact did not fire: the drone went
  straight; won at 30). s02va `dynamic` 1, R55's other no-survey loss, surveyed from step 4 and won in 60.
  s02c `final` 3 had no survey (11.5 m off the line, never back within 2.5 m) and was won by the route at
  60 steps with a latch at 11.
- **s02 19/24.** The survey started in 23 of 24 runs, 22 by step 8. s02a 6/6 (`a93` R58 4/6, R54 4/6, R53 4/6:
  this agent family's first clean sweep of the a site on 3 seeds): `dynamic` seeds 1 and 3 through from the
  second station at 53 and 39. Losses: s02c `dynamic` 3 (first station given up at 23, second done at 35),
  s02c `final` 1 (above), s02va `dynamic` 2 (both stations given up by 19, latch 29), s02va `final` 1
  (above), s02vc `dynamic` 1 (second station done at 21). **Two won runs latched before crossing** (s02c
  `final` 3 at 11, crossed 52; s02va `dynamic` 1 at 31, crossed 51; `a93` R58: one).
- **s03 3/6.** `dynamic` 1 read the shut door at 14, latched at 19, across at 41, goal at 45; `dynamic` 2
  read at 35, latched at 44, not through; `dynamic` 3 read at 26, latched at 31, out, not through in time;
  `final` 1 read at 26, latched at 35, lost; `final` 2 by the open tine at 26; `final` 3 read at 13, latched
  at 23, across at 49, goal at 52. Gaps 5, 9, 5, 9, 10 (`a93`'s latch, unchanged; R58: 5 and 33). **No survey
  started in any s03 run** (0 of 6).
- **Walls in flight:** missed 18.8% (148/789), phantom 11.5% (670/5811), **s03 phantom 17.4%** (R58: 20.2 /
  10.5 / 12.7): the s03 phantom rate is 4.7 points above the reference's, outside the 4 allowed; the other two
  within 1.3. Longest turn-around streak 3.
- **Goal reports:** 237 in 30 runs; 30 with no line of sight (1.0 a run), 7 dropped (23%); 3 of 207 made with
  a line of sight dropped (1.4%). The 23 blind reports kept raised a tag each, taken 23 times.
- **Labels** (`labels.csv`, Claude review): 22 success, 8 replan_failure. No tags.

**Manipulation check.** Every `run.json` carries `a95`, `f4cb70320370`, git `755a89d`, `:8006`; every
`godot.log` names `NVIDIA H100 PCIe`: held.
- A survey in every s02 run whose trail came back within 2.5 m of the line with a closed door read square:
  held (2 of 2), and in at least 23 of 24 s02 runs (23): held.
- No survey in any s03 run: held (0).
- Unbroken: a route on at least 95% of steps (30 of 30 at 100%): held. Walls within 4 points of R58's: **not
  held on s03 phantom (17.4 against 12.7)**, held on missed and phantom. The latch in the shut s03 tine within
  5 steps of R58's per run: not comparable run by run (different trails); gaps 5–10 against R58's 5 and 33.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, lanes 5–8 of twelve (`~/asep-r56-l5..8`)
on a copy of `:8004` on GPU 3 (`:8006`), four lanes to the instance, beside R56 on `:8004` and R58 on
`:8007`; Godot on GPU 5 (`GODOT_VK=nvidia`); `Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at
`755a89d` on 2026-11-07, 02:52–03:37 UTC, by Claude alone overnight (OVERNIGHT_PROMPT.md). Shakedown 4/4 won
at `c403f7b` (s02vc `final` 1 at 48, s02va `dynamic` 1 at 32, s02a `final` 1 at 22, each with a survey from
step 2–4; s03 `dynamic` 1 lost with no survey). **30/30 valid**, no attempt beyond the first. Labels: Claude
review, not yet confirmed by the operator. Frames stay on the host.

**Reading.** Two above the reference, inside the draw band and inside the flight-to-flight spread of this
family (4). The rule is sound (it started surveys exactly where it was meant to and nowhere in s03) but
rare: the drone left the line and came back in 2 of 24 runs, and those two were lost on the survey's
stations, not for want of one. The s02a sweep that made the two runs happened in runs where the rule was
not exercised. Not carried on its own; cheap and safe, so it rides in the next batch's combination with
`a94`'s latch (R59), where the question is whether the two changes add.
