# Probe a72: one look is soft, and route commitment, replayed on R30's records

Run 2026-11-04, no model, CPU only, on the 18 R30 runs in the repo (`decisions.jsonl`; frames
stay on the host). Open loop: the drone flew `a66`'s route, so every readout says what `a72`'s
memory and planner would have said from where `a66` stood, not where `a72` goes. Scripts:
`eval/probes/a72_replay.py` (1–3), `a72_replay2.py` (4–5), `a72_replay3.py` (6), `a72_replay4.py`
(7, measurement only, no agent). Outputs: `replay.txt`, `replay2.txt`, `replay3.txt`, `replay4.txt`.

Gates registered in the R31 README before the run: (a) phantom free cells in the s02 divider under
`a17h` at most half of `a17f`'s on the same steps; (b) the true gap no less passable; (c) route
flips in R30 s03 `dynamic` and s02vc `final` halved; (d) R30's solved runs keep their routes.

## Readouts

| | a17f (`a66`) | a17h (`a72`) |
|---|---|---|
| 1. s02 divider wall cells claimed as floor, per step (strong; soft) | 7.39 | 7.24; soft 0.13 |
| 2. true gap passable, share of steps | 85% | 84% |
| 3. s03 stem mouth sealed, steps | 0/60, 0/28, 0/58 | same |
| 4. of (1), claimed by an open-doorway's rays (`free_near`) | 4.40 | 1.66 |
| 5. openings confirmed at the run's end (a17h, two poses ≥ 1 m): phantom / true | | 20 / 4 |

| route flips (> 90°), 626 steps | a66 recorded | a17h, no commit | a72 |
|---|---|---|---|
| all runs | 34 | 44 | 35 |
| s03 `dynamic` | 8 | 11 | 7 |
| s02vc `final` | 5 | 8 | 7 |

6. Where the route crosses the divider, s02 `final`/`dynamic`, 305 near-side steps with a route:

| config | through the true gap | through phantom floor | flips |
|---|---|---|---|
| a66 recorded | 29 (10%) | 276 | 19 |
| a72 (a17h + commit) | 20 (7%) | 285 | 23 |
| a72 on weak far floor (near_free_m 2.5, far_free_cost 1.6) | 21 (7%) | 284 | 26 |
| a17g alone (a67's memory, a65's planner) | 38 (12%) | 267 | 22 |

7. A wall halo (a nose-on wall run extended along its line over far floor, never over a visit,
near floor or a confirmed door), on weak far floor with a17h and commit:

| halo cells | through the true gap | phantom | true gap impassable, steps | flips |
|---|---|---|---|---|
| 1 (today's) | 21 (7%) | 284 | 88/358 | 26 |
| 3 | 22 (7%) | 283 | 88/358 | 41 |
| 5 | 57 (19%) | 248 | 94/358 | 46 |

## Reading

- **Gate (a) fails as registered** (7.24 against 7.39) and **holds on the door-ray part alone**
  (1.66 against 4.40, row 4). The doorway rule does what it was built to do and it does not
  matter: the divider's phantom floor is painted by ordinary `open_far` rays from 3–4 m out
  (4 m reach), and a wall is written only when the drone reads `no_floor` within 1 m of it.
  Under `a17f` every free cell is strong, so taking a doorway's rays away leaves the floor.
- **Two poses do not separate phantom doorways from real ones** (row 5: 20 to 4). The perceiver
  reports the same dark panel as a doorway from everywhere. Only the kill rule (two strong
  closes) and the nose-on veto would, and they fire only in closed loop.
- **The route goes through phantom floor on 90% of near-side steps in every variant** (6). The
  best open-loop figure, 19%, needs a 5-cell halo that doubles the flips and seals the real door
  on 26% of steps. `a72` itself is a little worse than `a66` here (7% against 10%): its single-read
  walls are popped by later far floor, as `a17b`'s were, and the real door's rays are soft until
  the second pose, so the true gap is routed through less, not more.
- **Commitment returns the flips to `a66`'s count** (35 against 34; the memory change alone had
  raised them to 44), not below. In open loop the drone leaves a kept route it did not fly, so
  the readout understates it; it cannot say by how much.
- Gate (b) holds (84% against 85%); (c) fails (s03 `dynamic` 8 → 7, s02vc `final` 5 → 7); (d) not
  scored: with (a) and (c) failed the round does not fly on this probe.
- Row 3 cannot test the stem-mouth case: a71's runs are on the host, not in the repo, and `a66`'s
  R30 run never sealed the mouth.

What the record says instead: the s02 divider is unknown to the map until the drone is within 1 m
of it, and nothing in the memory or the planner can route through the real door while the map holds
7 phantom floor cells per step on the wall. `a17b`'s win (R22, R25D) was exactly not writing walls
at `open_near` ends because that sealed real doors; the pathfinder probe's second run found
`bottom` near walls seal a true route on 11% of steps. The lever is the reading at 2–4 m, not the
map, as the R30 verdict said.
