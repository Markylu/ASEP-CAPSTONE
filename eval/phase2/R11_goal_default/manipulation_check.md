# R11 manipulation check: a16 against R11C (a14)

From `python eval/spatial_replay.py manip` and `audit` on both rounds' runs, and the recorded
`decisions.jsonl` (`target`, `strategist`, `tags`, `hidden`, `navigator_text`). R11: 706 decided
steps; R11C: 721.

## Did a16 do what it was built to do

| Part | Check | R11C (`a14`) | R11 (`a16`) |
|---|---|---|---|
| Route planner | steps with the goal as standing target | 235 (33%) | **329 (47%)** |
| | steps on unexplored ground, backtrack or none | 312 (43%) | **376 (53%)**, all unexplored ground |
| | target changes | 156 | 60 |
| `q03` | strategist calls | 226 (31% of steps) | **38 (5%)** |
| | asked because: walled / blocked / no progress | | 16 / 16 / 6 |
| | detour chosen: unexplored ground / doorway / explore | | 37 / 1 / 0 |
| | goal listed on the strategist's menu | 226 of 226 | 0 of 38 (by design) |
| | "goal is not in the current image" / "within 2 m" lines | 167 / 47 | 0 / 0 |
| Wall-aware toward | "toward your target" on an action with a wall, blocked or stopped-short note | 40 (picked 13, 7 stopped short) | **0** |
| Block note | picks carrying "blocked here before" / "stopped short here before" | 1 / 0 | 0 / 1 (stopped short) |
| | steps with a block note on every forward move | | 1 |
| | near-repeat collisions (audit definition), with no note | 6, 5 with no note | 16, **15 with no note** |
| Turn rule | steps with [0] not offered / picks naming it | | 94 / 0 |
| Role views | navigator texts wording the goal's distance and direction | 0 | 0 |

**Every part ran as built.** The goal stood more, the strategist was asked a sixth as often and
never saw the goal on its menu or the two dropped lines, and "toward" never sat on a walled move.

## Where it went wrong

- **The goal-side detours went nowhere and hit walls.** Standing on unexplored ground gained
  **0.01 m a step** toward the goal (standing on the goal 1.13 m; R11C: goal 0.97, doorway 0.87,
  unexplored ground 0.01). Forward moves made while standing on unexplored ground stopped short
  **36 of 283 times (13%)**; R11C's 4 of 176 (2%). Under the goal they stopped short 20 of 309
  (6%; R11C 8 of 215). `a16` offers each unexplored edge at its cell nearest the goal: in a
  walled situation that cell lies against the wall between the drone and the goal, so the
  detour leads back into it.
- **The detours stood long.** 376 steps on 37 detours: about 10 steps each, up to the 12-step
  limit (in the probe's smoke run, "too long" was the commonest hand-back, 16 of 35). Doorways were never
  chosen (1 of 38); R11C's strategist chose a doorway 78 times and doorway targets gained 0.87 m a
  step.
- **Collisions 58** (R11C 24, R10 36), 56 stopped-short moves (R11C 20). By arm: `dynamic` 28,
  `final` 23, `initial` 5. By site: s02c 16 (R11C 1), s03 19 (11), s02va 8 (2), s02vc 8 (6), s02a 5
  (3), s01 2 (1).
- **The block note did not warn about the repeats.** 15 of 16 near-repeat collisions carried no
  blocked or stopped-short note. The narrow window (15° after a full block, 25° after a short
  stop) leaves the next move out unwarned; the wide one (a15) warned every move. Neither found
  the case the navigator needed.
- **More turn-arounds:** 13.6% of picks (R11C 7.5%, R10 8.6%), loop-score steps 60 (R11C 12). The
  turn rule kept them from running two in a row ([0] hidden 94 times, never picked).
- **Revisits:** revisit rate up to 0.40 on the failing `final`/`dynamic` runs (s02c `final`,
  s02va `dynamic`), 0 on every `initial` run.

## Unchanged

Perceiver: goal bearing median error 5.0° (142 sightings); range classes still wrong (`near`
median 18.9 m true). Mean step 2.9 s (R11C 3.1 s). No failed perceiver or model call.
