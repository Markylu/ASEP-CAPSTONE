# Probe PG: does the map's own geometry mark the s03 dead end, early, and not the s02 door wall?

**Script:** `eval/probes/pg.py` · **Model calls:** none (offline, CPU) · **Status:** gate set
2026-11-02 before the run, run the same day, **refuted**

Follows [probe DE](../de/README.md): the closed-door sign fires on 72% of s02 detour calls and the
dwell sign fires too late (4–22 steps left, 28 needed). This probe tries the cue DE named and did
not test: the shape of the known floor around the drone.

## Belief

In the shut tine the memory's known floor forms a pocket: the cells a path reaches within a few
metres leave that neighbourhood in one direction only (back toward the crossbar), and the goal
lies through the wall on another side. Along s02's door wall the known floor leaves the
neighbourhood in two or three directions (both ways along the wall, and back), so the same test
fails there. Read from the map at every step, not only at strategist calls, the pocket should show
soon after the drone enters the tine, with enough steps left to come back out.

## Method

Inputs: every step of every `a49` run in R25D, R29N and R29S (54 runs). The memory is rebuilt as
the agent had it at that step (`spatial.rebuild`, a49's config), then:
- `reach` = `mem.reach(here)`: path metres to every known-floor cell a path reaches.
- **local**: the reached cells within R = 5 m of path.
- **exits**: local cells with a reached neighbour beyond 5 m. Their bearings from the drone are
  clustered (a new cluster when the gap exceeds 60°); `n_exits` is the number of clusters.
- **goal walled**: a wall or stop-wall cell within 3 m of the drone, within ±30° of the bearing to
  the goal.
- **pocket** = at least 15 local cells, `n_exits` ≤ 1, goal walled, and the goal bearing not
  within ±45° of the exit cluster (the way out is not toward the goal).
- `closed_perc` and `closed_d01` as in DE (a closed door reported / confirmed in the last 5 steps).

Rules: **P** pocket; **PC** pocket and `closed_perc`; **PD** pocket and `closed_d01`.

Places, per step: `s03_dead` (shut tine: `final` L, `dynamic` the tine first entered), `s03_open`
(the other tine; the s03 `initial` runs' tines, both doors open), `s03_else`, `s02`, `s01`.

## Gate (set before the run)

A rule **passes** if all hold:
1. in ≥ 4 of the 5 failed s03 runs it fires at a step with ≥ 28 steps left, inside the shut tine;
2. it fires on ≤ 5% of s02 steps, and in no s02 run on more than 5 steps;
3. it fires on ≤ 10% of `s03_open` steps (the open tine must not read as a dead end);
4. it fires on ≤ 5% of s01 steps.

If a rule passes: round `a63` = `a49` + the rule in code (`planner.route`: when it fires, the target
is the far frontier out of the pocket, held until reached), on-policy check before 18 runs, as
R28's README laid out. If none passes, the geometry does not separate the two sites either, and
the s03 dead end stays with the crossbar coin.

## Run

2026-11-02, locally, on the committed `a49` records of R25D, R29N and R29S: 54 runs, 1,986 steps,
the memory rebuilt at each (8 s). Output: [score.txt](score.txt), per step [steps.jsonl](steps.jsonl).

## Result

**Refuted. No rule passes.**

| Rule | shut tine (136 steps) | first fire, steps left (5 runs) | s02 (1,305 steps) | s03 open tine (66) | s01 (208) |
|---|---|---|---|---|---|
| P pocket | 64 | 18, 22, 14, 26, 30 → ≥ 28 on 1/5 | **322 (24.7%)**, 18 runs over 5 fires | 6 (9%) | **33 (16%)** |
| PC pocket and closed door seen | 55 | same five | **237 (18.2%)**, 15 runs over 5 | 3 | 0 |
| PD pocket and `d01` closed | 21 | –, 22, –, 20, 22 → 0/5 | **148 (11.3%)**, 12 runs over 5 | 3 | 0 |

- **The map does not know the s02 wall is long.** The memory holds the floor the drone has walked
  and seen; along the door wall that is a strip a few cells wide, bounded by the wall on one side
  and unknown ground on the other, with one known way out behind. To `reach` that is a pocket as
  much as the tine is. A quarter of all s02 steps read as pocket, and on 18 of 20 s02 `final`/`dynamic`
  runs the rule would have fired more than five times. Gating on the closed door (PC, PD) halves
  that and no more, for the same reason DE found: door B is in view along that wall.
- **In the tine the cue is right but late.** Pocket reads true on 64 of 136 shut-tine steps and
  almost never in the open tine (6 of 66). But the first fire comes with 14–30 steps left; the
  way out needs about 28.
- **Where the budget goes is the crossbar, not the tine.** Crossbar arrival (x < 8) against tine
  entry, per s03 run:

  | run | crossbar | tine | at the crossbar |
  |---|---|---|---|
  | R25D `dynamic` | 8 | 36 | 28 steps |
  | R29N `dynamic` | 9 | 42 | 33 |
  | R29S `dynamic` | 9 | 24 | 15 |
  | R25D `final` | 31 (lobby first) | 37 | 6 |
  | R29S `final` | 31 (lobby first) | 46 | 15 |
  | R29N `final` | 8 | 25 | 17 |
  | `initial` (3 runs, all won) | 8 | 14–23 | 6–15 |

  In `dynamic` the drone reaches the crossbar by step 9 and then spends 15–33 steps there: the
  goal line points at the x = 5 wall, `goal_way` reads walled or blocked, `q03` is asked every 2–5
  steps and answers `explore` or a frontier a cell or two away ([DE's listing](../de/score.txt)
  and R29N `dynamic` steps 10–37 in the R29 records). In two `final` runs the lobby costs 31 steps
  before that. A run that enters a tine by step 12, meets the shut door at about step 18, and turns
  back at once reaches the other door by about step 44. The dead end is survivable; the crossbar
  dithering is what makes it fatal.

**Where this leaves the belief.** Refuted for the pocket cue: the map's geometry is the drone's
own trail, and a wall-side strip and a tine look the same in it. The s03 finding that survives
both probes is about time, not recognition: 15–33 steps lost at the crossbar before either tine
is tried. The candidate that follows (not probed here): at the crossbar, when the goal line is
walled and the two tine mouths are the listed frontiers, code picks one at once and holds it to
the tine's end; on a `d01`-confirmed closed door in that tine, code turns to the other mouth. Its
offline check is on the same records: how many steps the rule would save at the crossbar, and
whether its trigger (walled, two frontiers ±90° off the goal line, none nearer the goal) ever
fires on s02.
