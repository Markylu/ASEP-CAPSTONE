# R45: a84 with the survey lining up on the door, contested cells

**Agent:** `a85` (`a43435111dff`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A85` ·
**Status:** laid out 2026-11-06 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason) while R44 was in flight; shakedown flown 2026-11-06 (four of
four solved, gate passed); **round flown 2026-11-06: 23/30 against `a84`'s 18/30 and `a66`'s
15/30, carried** ([summary](summary.md))

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R32P (`a66`, 15/30) and R44 (`a84`, in flight as this is written).
The bundle is R43's and R44's (the wall survey for s02, the dead-end latch for s03); this
round changes the survey's last stretch only.

## Change

Against `a84` (R44), three settings of the survey (`agent.SURVEY_A85`, read in
`planner.wall_survey`); the latch and everything else are `a84`'s.

| Setting | `a84` | `a85` | Why (R44's shakedown, s02vc `final` seed 1) |
|---|---|---|---|
| `through_deg` | a doorway read counts within 40° of the approach axis, always | within 65° once a doorway is being flown at (40° still starts it) | the door was read at 21° off the axis at step 8 and flown at; at steps 9–11 it was read in the left strips, 42–58° off, and those reads, which pointed at the door's centre to within 0.3 m, were dropped; the aim stayed on the first ray, 1.5 m short of the jamb |
| `lineup` | stopped by the wall in the through phase: a check of three steps, then the next station | with the doorway's reads in hand, the wall is 1 m ahead of where the drone was stopped, the door's line is where the newest ray meets it, and the waypoint is 2.5 m out from the wall on that line, then through it square; twice at most | the drone stood nose-on to the wall 3.3 m from the door's centre, turned about, and spent twelve steps along the wall in the look phase. This is `a76`'s approach pose with the two things it lacked, the wall's range and the door's line |
| `through_adv_m` | five steps without a read: back to the look | 5 m farther on than the last read with nothing in the way: through, the survey is done | in s02c `dynamic` the drone was through at step 15 and the survey went back to the look for six steps beyond the wall |

## Evidence

- **R44's shakedown** (`a84`, [R44 Outcome](../R44_survey_latch_fixed/README.md#outcome)):
  the trace in the table. The reads the 40° cone dropped were right: from (5.9, −4.1) at 221°,
  from (4.3, −4.7) at 229° (the middle of two strips) and from (2.7, −5.3) at 237°, they meet
  the wall at y = −9.0, −9.3 and −8.9; the door is centred at −9.0.
- **Probe door_read** (`docs/research/round-f-analysis.md` §9): a look 40–60° off square read
  the open door on 67 of 92 looks and a blank wall strip as open on 33 of 346; beyond 60°, 112
  of 231 and 76 of 393. That is why 40° starts the flight at a door; once one is being flown
  at, a second read to its side is a correction, and a phantom costs a line-up that ends at
  the wall (two at most).
- **`a76` and `a77`** (R36, R37): the approach pose failed because the doorway's position was
  written short of its wall and the wall's line was not known
  (`docs/research/round-f-analysis.md` §8, §11). Here the wall is where the drone was stopped
  and the line is the approach axis's.

## Hypothesis

With the door's later reads kept and a square line-up when the wall stops it, the survey gets
through the doors it now reaches and misses; `a85` scores at least as well as `a84` on s02
and at least 18/30.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a85` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 8–10 |
| s02 `dynamic` ×4 | 6/12 | 8–10 |
| s03 `final` | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 1–2 |
| **total** | **15/30** | **18–24** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule), against `a66` and against `a84`.

## Manipulation check

R44's, and: in s02 runs where the drone is stopped by the wall in the through phase, a
line-up (`survey.lined` ≥ 1) and, after it, the drone within 1 m of the open door's centre
line at the wall in at least half; no look phase begun after the drone has crossed.

## Drop criterion

Not carried forward below 15/30, or with fewer s02 wins than `a84` in R44 by 3 or more.
Carried as the base of the next round at 18/30 or more and no fewer s02 wins than `a84`.

## Probe gate

**No model probe** (no call added, nothing the model perceives or reports changes).

- **Closed loop, no model** (`eval/probes/a80_sim.py --agent a85 --far 20`,
  `eval/phase2/_probes/a85/`): truthful perceiver 32/32 on the change arms (`initial` 16/16);
  doorways and walls misread with 20% random moves 67/96 (`a84` 59, `a83` 65, `a80` 48, `a66`
  48). Gate: all on the first row, no worse than `a84` on the second. Passed.
- `python -m pytest server/decider/tests -q`: 71 pass. `VLM_AGENT=a85 python
  eval/probes/a63_smoke.py`: 627/627. Earlier agents keep their shas (`a84` `58e76b4b2054`).

**Shakedown gate** (on-policy, seed 1, slot 5 as a fifth client beside R44's lanes): s02vc
`final` (the run above), s02vc `dynamic`, s02va `dynamic`, s02c `final`. Passes if the s02vc
`final` run crosses, or its drone stands within 1.5 m of the door's centre line when it is
stopped at the wall or lines up; no survey step holds the waypoint more than five steps after
a crossing; a route is on at least 95% of steps. Wins are not required.

## Builds on

`a84` (R44). Branch `phase2/r45-survey-lineup` from `phase2/r44-survey-latch-fixed` (`eb80c0f`).

## Notes for the operator

- **Preflight:** `python -m server.decider --profile remote --agent a85`; `/health` should
  report `a43435111dff`.

## Outcome

**Flown 2026-11-06, 06:17–07:02 UTC, 30/30 valid: 23/30 against `a84`'s 18/30 (R44) and
`a66`'s 15/30 (R32P). The hypothesis held; `a85` is carried forward and is the bar.** s02
19/24 (R44 13/24): s02va 6/6, s02a 6/6, s02c `dynamic` 3/3, s02vc 3/6; 17 of the 19 s02 wins
crossed on the survey, at a median of step 15. s03 4/6 (`final` 3/3, `dynamic` 1/3). The gain
is the wider cone of reads, not the line-up: of five line-ups at the near wall two crossed,
and three s02 losses were stopped beside the jamb, lined up and did not get through. Details:
[summary.md](summary.md).

**Shakedown (2026-11-06, 05:39–05:58 UTC): four unscored runs, slot 5 (port 8105) as a fifth
client beside R44's four lanes, sctsvr6 `~/asep-r33-shake` at `7031eb4`, log
`~/r45_shake_a85.log`. All valid, all four solved. Gate passed.** (`eval/probes/a80_check.py`.)

| Cell (seed 1) | `a85` | `a84` | R32P `a66` | Survey | Crossed |
|---|---|---|---|---|---|
| s02vc `final` | **solved, 30** | lost (R44 shakedown) | lost | from step 4; the door flown at from 6, re-aimed on reads 21–58° off the axis at steps 7–12 (the waypoint's y from −2.9 to −8.8, the door at −9) | 14 |
| s02vc `dynamic` | **solved, 46** | — | solved | from step 4; through phase 5–10, then ended 5 m on from its last read, still short of the wall; the route crossed | 37 |
| s02va `dynamic` | **solved, 25** | — | solved | from step 4; flown at the door for 13 steps | 14 |
| s02c `final` | solved, 41 | solved, 23 (R43 shakedown) | lost | from step 2 on a read from far; ended at 7, 5 m on, short of the wall; a latch in the hall at 12; the route crossed | 32 |

- **Gate:** the s02vc `final` run crosses: held (step 14). No survey step more than five steps
  after a crossing: held (five, in that run). A route on at least 95% of steps: held (40/41 at
  the lowest).
- **One fault, not in the gate:** `through_adv_m` calls the drone through when it is 5 m past
  its last read with nothing in the way, and a door read from far leaves it 5 m on and still
  in the hall. The survey ended early in two of the four runs (steps 7 and 10); both were
  solved by the route afterwards, 9 and 18 steps later than a survey that had held on. Noted
  for the version after; this round flies `a85` as laid out.
