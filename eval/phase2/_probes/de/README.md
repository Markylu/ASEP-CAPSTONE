# Probe DE: is the s03 dead end recognisable from the record, and is a way out on the menu?

**Script:** `eval/probes/de.py` · **Model calls:** none (offline, CPU) · **Status:** gate set
2026-11-02 before the run, run the same day, **refuted**

Comes from [R29S](../../R29S_host_noise_solo/summary.md): `a49`'s s03 `final`/`dynamic` cells are
decided by the side choice at the crossbar (R29S and R25D pose-identical to step 33, then tine R
or tine L). Every a49 s03 failure (R25D, R29N, R29S: 5 of 6 `final`/`dynamic` runs) is the shut
tine: in, 25–40 steps there, never out
([s03_tines_analysis.md](../../R22K_open_near_unwalled_goal_confirmer/s03_tines_analysis.md)
found the same on the a43 line). The plan's next lever (plan §3): a code rule on the `q03` line
that recognises the dead end and takes the way out, instead of a new menu item for the strategist
to ignore (R26: new items are not picked).

## Belief

In the shut tine the record already carries the two signs of a dead end, and the recorded menu
already lists a way out:
1. the perceiver reports a closed door in the last few steps (the tines analysis: closed-door
   strips on 9–15 steps per run), confirmed or not by `d01`;
2. the drone dwells: most of its last 10 poses lie within 4 m of where it stands.
And the search menu (`planner.search_menu`) lists a frontier back in the crossbar or lobby, or in
the other tine, which `q03` never picks (it picks a local frontier or `explore`).

If that holds on the recorded `a49` calls and almost never on s02, a code rule
("dead end → take the far frontier, hold it") can be built and flown as a round. If the signs are
as common on s02 (the shut door B is in view along the door wall), the rule would send s02 runs
back toward the spawn, and it is dropped or needs a different cue.

## Method

Inputs: every recorded strategist call (`planner.ask` set) in the `a49` rounds R25D, R29N and R29S:
18 runs each, all sites. No model calls; poses from the manifests, readings from the records.

Per call:
- **place:** `s03_dead` (s03, `final`/`dynamic`, in a tine: x < 5, |y| ≥ 3); `s03_else`; `s02`
  (any s02 site); `s01`.
- **closed_perc:** a perceiver strip read `closed` on any of the last 5 steps, this one included.
- **closed_d01:** `d01` said `closed` on any of the last 5 steps (`planner.closed_door_line`'s
  rule with `recent_steps` 5).
- **dwell:** of the last 10 poses, how many lie within 4 m of the drone now.
- **far item:** the menu item (frontier, doorway or backtrack) farthest from the drone by straight
  line, if it is at least 6 m away. **good** when, on `s03_dead`, it lies in the crossbar or lobby
  (x ≥ 3) or in the other tine (|y| ≥ 3.5, opposite side) on free floor (`geo.world`); on s02,
  when it is at least 0.5 m nearer an open door than the drone (R26's `good`).
- **steps left** at the first `s03_dead` call of each run.
- **recorded pick**, and whether it was the far item.

Rules scored, each a dead-end trigger:

| Rule | Fires when |
|---|---|
| A | `closed_perc` |
| B | `closed_d01` |
| C | `closed_perc` and `dwell` ≥ 7 |
| D | `dwell` ≥ 7 |

## Gate (set before the run)

A rule **passes** if all three hold:
1. it fires on ≥ 80% of the `s03_dead` calls (pooled over the 5 failed runs, and on every run at
   least once);
2. when it fires there, a far item exists and is good on ≥ 90% of those calls;
3. it fires on ≤ 10% of s02 calls and ≤ 10% of s01 calls.

If a rule passes, a round is laid out: `a63` = `a49` + the rule in code (`planner.route`: when the
rule fires, the target is the far item, held until reached or `other_way`-style `max_steps`), with
its own on-policy check before 18 runs. The budget check must also hold: steps left at the first
dead-end fire ≥ 28 on at least 4 of the 5 failed runs (the way back to the crossbar, down the other
tine and on to the goal is about 42 m, 26–28 steps).

If no rule passes, the dead end is not readable from these signs on this line, and the next
candidate cue is the map's own geometry (a pocket: the reachable free cells around the drone are
bounded on three sides), not tried here.

## Run

2026-11-02, locally, on the committed `a49` run records of R25D, R29N and R29S (54 runs, 228
strategist calls). After the first pass two things were added before any reading was drawn: the
shut tine is told from the open one (`final`: L; `dynamic`: the tine first entered, whose door
slams), so R29S's s03 `final` win in tine R is not counted as a dead end; and rules E–G gate on
"no open doorway on the menu", since the s03 tine menus list none and the s02 divider menus often
do. Output: [score.txt](score.txt), per call [calls.jsonl](calls.jsonl).

## Result

**Refuted. No rule passes.** 22 dead-end calls in the 5 failed runs; 144 s02 calls.

| Rule | Dead-end fires | Far item good on fires | s02 fires | Verdict |
|---|---|---|---|---|
| A closed door seen (perceiver, last 5 steps) | 20/22, 5/5 runs | 18/20 | **103/144 (72%)** | fail (3) |
| B closed door confirmed by `d01` | 8/22, 3/5 runs | 7/8 | 70/144 (49%) | fail (1, 2, 3) |
| C A and dwell ≥ 7 of last 10 poses within 4 m | 13/22 | 12/13 | 13/144 (9%) | fail (1) |
| D dwell ≥ 7 | 15/22 | 14/15 | 16/144 (11%) | fail (1, 3) |
| E A and no open doorway listed | 19/22, 5/5 runs | 17/19 | 70/144 (49%) | fail (2, 3) |
| F E and dwell ≥ 4 | 15/22 | 14/15 | 23/144 (16%) | fail (1, 3) |
| G B and no open doorway listed | 8/22 | 7/8 | 47/144 (33%) | fail (1, 2, 3) |

- **The way out is on the menu and never taken.** A far item (≥ 6 m) exists on 22 of 22 dead-end
  calls and is good (crossbar, lobby or the other tine, on free floor) on 20; `q03` picked it 0
  times. It picks a local frontier inside the tine or `explore` every time. That part of the belief
  holds and matches the tines analysis on the a43 line (25 of 33 listed, 0 picked).
- **The closed-door sign does not separate s03 from s02.** The perceiver reports a closed door
  within 5 steps of 72% of s02 strategist calls (door B stands in the same wall as the open door),
  and on 49% of them no open doorway is on the menu either. A rule on that sign would turn half
  the s02 detour calls into "take the far frontier", and on s02 the far item is good on only 30 of
  103 such calls: it is mostly the way back toward the spawn.
- **Dwell is clean but late.** Dwell ≥ 7 fires on 9–11% of s02 calls, within the gate, but on
  s03 only once the drone has already spent 7 of 10 steps in the pocket: at the first fire the runs
  have 4, 10, 11, 21 and 22 steps left, against the 28 the way out needs. Any rule here fires
  with ≥ 28 steps left on at most 2 of the 5 runs (A: R29N `final` 30, R29S `dynamic` 28).
- **Budget is the binding constraint, not the cue.** The first dead-end strategist call comes at
  steps 30–48; the first closed-door sighting at steps 25–46. From inside the tine the way out is
  about 33–42 m, 20–28 steps. Even a perfect trigger at the first sighting fits the budget on 3 of
  5 runs. The cheap place to decide is the crossbar at steps 32–34, where nothing in the record
  says which door is shut: the two tine mouths are listed as equal frontiers and the pick is a
  coin (R29S vs R25D s03 `final`).

**Where this leaves the belief.** Signs 1 and 2 hold on s03 but sign 1 holds on s02 as well,
and sign 2 comes too late to use. No `a63`. Candidates not tried here, each a new probe:
- a map-geometry cue (a pocket: the reachable free cells around the drone bounded on three sides,
  with the goal line through the closed side), which s02's long open wall should not show;
- deciding at the crossbar by looking: a step into each tine mouth is 11 m from its door, beyond
  `d01`'s reach, so this needs the perceiver to read a closed door at 11 m, which the record
  does not show it doing;
- a cheaper way out once in: at the first `d01`-confirmed closed door, turn back at once (budget
  fits on 3 of 5), gated by something that is not the closed door itself.
