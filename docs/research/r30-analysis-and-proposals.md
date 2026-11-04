# After R30: what the record says, and what to try next

Written 2026-11-04 by Claude for the operator, read-only, from the tip of `phase2/r30-pathfinder`
(`f895cdb`): `results.md`, every round README and summary from R19 on, `why_14.md`, the s02 and
s03 failure analyses, `what-we-learned.md`, the R30 shakedown record, and the a17d–a17g memory
and `planner.pathfind` code. No model calls, nothing flown. Engineering mode, as the project
notes say: the aim is the best agent for the final 90, read against `a49` (R25D) and `a66` (R30).

## 1. State of play

| | R25D `a49` | R30 `a66` | `a17b` family expectation |
|---|---|---|---|
| total | 14/18 | 14/18 | 11.3 ± 1.4 |
| initial / final / dynamic | 6 / 3 / 5 | 6 / 4 / 4 | |
| s03 | 1/3 | 2/3 | |
| s02 final+dynamic | 6/8 | 5/8 | |
| walls missed / phantom in flight | 17.3% / 12.7% | 18.5% / 11.1% | |
| host | 4 lanes shared | 1 lane alone | |

Two rounds at 14, both read as good draws of the same family. The planner moved *which* cells
are won (gained s02c `final`, s03 `final`; lost s02a `dynamic`, s02vc `final`), not how many.

## 2. Where the 18 cells stand (R19–R30, 14 rounds)

| cells | solved | reading |
|---|---|---|
| s01 ×3, s02 `initial` ×4 | 14/14 each | settled; not a lever, and not worth re-flying every round |
| s03 `initial` | 11/14 | settled when the lobby is not wasted (R30: 37 lobby steps, solved at 58 of 60) |
| s02c `dynamic` | 10/14 | mostly solved |
| s02a `final`, s02c `final`, s02va `dynamic` | 7/14 each | coin flips: right side first at the divider |
| s02vc `final` | 5/14 | coin flip plus the door-wall walk |
| s02vc `dynamic`, s02a `dynamic` | 4/14, 3/14 | hard: door B shuts in front of the drone, the map must relearn it |
| s02va `final` | 2/14 | "family-hard": 44 steps at the divider in both best rounds |
| s03 `final` | 5/14 | solved only when the first tine taken is the open one |
| s03 `dynamic` | **0/14, 0/41 over all of Phase 2** | never solved by any agent |

So the game is ten contested cells. Eight are decided at the s02 divider, two in the s03 tines.
Everything below is about those two places.

## 3. The failure chains, as the record has them

**s02 divider (8 contested cells).** Three mechanisms, all present in R30's three s02 losses:

1. *Phantom open doorway.* `g05` reports an open doorway in the divider where there is none,
   `d01` confirms it, and `spatial._observe_a17d` writes 6 m of **strong** free cells through the
   wall from that one look, popping any wall, door wall or suspect there (`open_door_reach_m`,
   `free_near`). The route trusts it; the drone noses into the divider; the next look re-opens it.
   Seen in a70 s02c (s14, s23), a70 s02a/s02va, a71 s02va (five steps), R30 s02vc `final`.
2. *Wrong side first.* After door B seals, the route pokes at whichever divider cell is unsealed
   and nearest the goal line; which side that is depends on the last few reads. Over 312 runs:
   right side first 37% solved, wrong side 13%. Nothing in the agent chooses a side on evidence.
3. *Relearning a door that shut.* `dynamic` s02a/s02vc: the drone stands at door B when it slams;
   the nose-on read becomes a firm wall (a17f, correct) but the map still holds B's earlier open-door
   free rays on the far side, and the route goes the wrong way round (R30 s02a `dynamic`, 49 steps
   within 4 m of the divider).

**s03 tines (2 contested cells).** One chain with three links, each exposed in turn by the
shakedown's seven versions:

1. *Lobby waste.* The navigator declines "toward your target" on marker 0 (R11 pattern): 18
   lobby steps in a63/a67/a68, 37 in R30 s03 `initial`. a70's route-behind sentence plus route
   critic closed it (marker-0 "toward" taken 77/77, lobby 4–11). **Not in `a66`.**
2. *Shut-tine oscillation.* At the closed door the route alternates every 2–3 steps between the
   door (unknown divider cells cost 2) and the 40 m way back, as each nose-on look seals one cell
   and the next look moves the route to the next unsealed one. `astar` replans from scratch every
   step with no memory of the last route. a70 s03 s29–59, R30 s03 `dynamic` s24–55.
3. *Corridor mouth read as a wall.* Looking down the 3 m stem, `g05` reads `no_floor` on all five
   strips; a17f makes that a firm wall erased only by a visit the wall now forbids (a71 s03: 60
   steps in the lobby). The same read at the shut tine's end is what a68's dead-end seal needed
   and could not ground (a69: 1/8, 0/8 walled trail points).

**Common root of s02-1, s02-3 and s03-3:** one perceiver look writes permanent, strong map
state (6 m of free cells, or a firm wall), and a single `g05`/`d01` read is wrong often enough
(phantom doorway; `no_floor` into a corridor) that the route follows the error. Everything the
shakedown fixed on one side broke on the other because firmness was granted from one read.

**Measurement.** The step-0 read differed from R25D's in 16 of 18 cells on a lane alone, so the
solo host did not make runs reproducible, and R30 alone missed 18.5% of walls (R29S's check 1
wanted ≤ 10%): the host-noise question is answered well enough without flying R29N/R29S.
One seed-1 round still cannot resolve ±1–2 runs.

## 4. Proposals, in the order I would build them

### P1. One look is soft: confirm doorways and firm walls from two poses

*Memory `a17h` (code only).* A `d01`-confirmed open doorway writes **soft** free cells (cost as
unknown, 2.0, not strong) until a second confirmed sighting of the same opening from a pose at
least 1 m away; then its rays become strong as today. A nose-on `no_floor` run at an opening's
location vetoes it (the opening is dropped, its soft rays erased). Symmetrically, a nose-on
wall run or closed-door wall is **firm** (a17f) only after two nose-on reads from poses ≥ 1 m
apart, or a bump; one read writes a17b-style walls that a later floor read can still pop.

- *Why:* every phantom-door loss in a70/a71/R30 came from one confirmed look; a71's stem-mouth
  loss came from one `no_floor` look made firm. The memory already keeps `openings` with a
  `seen` count and `doorway_min_seen` for *targets*; the free rays just do not wait for it.
- *Cost:* a day. Offline replay exists for most of it: rebuild a70, a71 and R30's `decisions.jsonl`
  under `a17h` (frames are on the host under `~/r30_shake_a7x_runs`) and count (a) phantom
  free cells written inside the s02 divider and (b) the s03 stem mouth sealed or not at a71's s4.
- *Gate before flying:* phantom free cells in the divider ≤ half of a17f's on a70/a71's s02
  runs; a71 s03 s4 stem mouth not firm; R30 s03 `final` and the nine crossed s02 runs keep
  their route through the real door on ≥ 90% of their crossing steps.
- *Risk:* real doors confirmed late (two looks instead of one). The s02 crossing steps show the
  open door is looked at 9–22 times per run, so the second sighting is cheap.

**Measured 2026-11-04 (a72 built, `eval/phase2/_probes/a72/README.md`).** The doorway rule cuts
door-ray phantom floor by 62% and it does not matter: the divider's phantom floor is painted by
ordinary `open_far` rays, which the memory holds as strong floor, and the route crosses through
phantom cells on 90% of near-side steps under every map variant tried. Two poses confirm 20
phantom openings for 4 real ones. Gate failed; R31 laid out, not flown.

### P2. Route commitment (hysteresis)

*Planner change, code only.* Keep the previous step's route unless (a) it is now impassable,
(b) a fresh route is ≥ 25% cheaper, or (c) the drone has left it by more than 2 cells. Record
`planner.kept` per step. Waypoint selection unchanged.

- *Why:* the s03 shut-tine oscillation and the s02 divider hopping are the route flipping between
  two near-equal options as single cells seal. R30 s03 `dynamic`: "alternated every two or three
  steps". With commitment the drone finishes one option (reaches the door, bumps, seals it) and
  the 40 m way out wins on the next replan instead of being re-lost two steps later.
- *Cost:* half a day. Offline readout on R30/a70 runs: route flips per run (bearing change > 90°
  between consecutive routes), before and after.
- *Gate:* flips in R30 s03 `dynamic` and s02vc `final` fall by half; routes on R30's solved runs
  unchanged on ≥ 95% of steps.
- *Risk:* commitment to a wrong side at the s02 divider lasts longer. That is why P1 comes first
  (fewer wrong routes to commit to) and why (b) stays at 25%, not higher.

**Measured 2026-11-04.** Commitment brings route flips back to a66's count (35 against 34 over
626 steps; a17h alone raised them to 44), not below. Open loop understates it and cannot say by
how much.

### P3. Carry a70's navigator (route-behind sentence + route critic), after P1

*`a66` + `NAVIGATOR_A70`.* No new work; the pieces are built and measured.

- *Why:* lobby waste cost R30 s03 `initial` 37 steps and every shakedown s03 run 18; a70 cut it to
  4–11 with marker-0 "toward" taken 77/77. s03 `dynamic` needs ~44 of 60 steps for the recovery
  (tines analysis), so the lobby is the budget.
- *Why after P1:* a70 and a71 lost s02 runs because an obedient navigator follows a route through
  a phantom door; `a66`'s 14 includes one cell its navigator won by ignoring the route (s02c
  `dynamic`). Obedience is only worth having once the map stops lying.
- *Gate:* shakedown, s03 first: lobby ≤ 12 in all arms; no s02 cell lost that `a66` won.

### P4. Closed-door halo instead of a corridor seal

*Planner cost map.* Unknown cells within 3 m of a confirmed closed door cost 10, not 2 (a closed
door sits in a wall, and walls continue). Nothing is sealed, so no corridor detection is needed.

- *Why:* a68's dead-end seal worked in flight (took the drone out of the tine) but a69 showed its
  trigger cannot be grounded in `g05`'s reads, and it boxed s02a/s02vc in the hall. A halo gives
  A* the same push with no trigger: at the shut tine's door the 40 m way back beats poking at
  cost-10 cells; at s02's door B it pushes the route along the divider toward A or C (9 m away,
  outside the halo).
- *Cost:* an afternoon; offline readout: from the shut-tine steps of R30/a70 s03 `dynamic`, does
  the route point out of the tine (+x)?
- *Gate:* shut-tine route points out on ≥ 80% of steps after the closed read (the registered
  offline gate's row, now with a map that has the door); no R30 solved run loses its route.

### P5. Screen on the contested cells, with repeats

*Protocol change, no agent change.* A screening round flies the ten contested cells (s02
`final`/`dynamic` ×4 sites, s03 `final`/`dynamic`) three times each = 30 runs, plus one `initial`
run per site in the shakedown as the "not broken" check. Same host time as 18 + 12.

- *Why:* eight cells are 14/14 and tell a round nothing; one seed cannot resolve ±1–2 (why_14,
  twice now). Three repeats give a per-cell rate, which is what distinguishes a mechanism (s03
  `final` won because d01 read the door early) from a draw.
- *Before the final 90:* a head-to-head of `a49` against the chosen candidate on these 30 runs,
  so the final's agent is chosen on a rate, not on two lucky 14s.
- *Cost:* a `ROUNDS` entry type with a cell list and `repeats`; the runner already takes a cell
  matrix. The test plan's §3 "why all three arms" argument moves to the shakedown.

**Flown 2026-11-04 as R32/R32P** (`eval/phase2/R32_repeat_a49/summary.md`): a66 15/30, a49 11/30, s03 `final` 3/3 against 1/3, s03 `dynamic` 0/6. The final 90 flies a66.

### P6. Calibrate the memory's range table from probe LD (no flight)

*Memory params only.* LD measured the eye at 1.48 m (prompt says 1.84) and the model's metres
off by ×2.5–3. The a17d ranges (`door_wall_m` 1.0, `suspect_m` 4.5/8.0, `open_door_reach_m` 6.0,
`FLOOR_RANGE_M`) were set from the prompt's geometry. LD's 1,680 renders with truth can give the
empirical range per `floor_end` class; write them as `PARAMS_A17H` ranges.

- *Why:* R30 s02vc `final`: d01 read doors closed on both sides at s9 (true) and the route still
  went to the closed side for 48 steps, which fits a door wall written at the wrong range. Cheap
  to check offline on that run.
- *Cost:* a probe script over LD's existing outputs, no model; a day.

### Not proposed (the record says no)

- Perceiver wording for walls: R27, five R28 readers and LD all failed; the trade is missed vs
  phantom walls and phantoms cost more. Leave `g05`.
- Host rounds R29N/R29S: R30 alone on `:8004` missed 18.5% of walls and read step 0 differently
  from R25D in 16 of 18 cells; the solo host is not the lever. Skip unless host time is free.
- More strategist items or hand-backs (R21, R22, R26 all cost `final` runs); goal confirmer `c01`
  (no effect in seven pairs); code picking the action (`a64` 2/6: the map, not the navigator, is
  the limit).

## 5. Suggested sequence and what to expect

1. **a72 = a66 + P1 + P2** (map and planner only; navigator as a66). Offline gates on the
   shakedown and R30 frames already on the host. Shakedown on the ten contested cells.
2. **a73 = a72 + a70's navigator** (P3). Shakedown again, s03 first.
3. **P4** only if a73's s03 `dynamic` still oscillates at the shut door.
4. **P5** as the protocol for 1–3, and for the a49-vs-candidate decision before the final 90.
5. **P6** in parallel, no host time.

Honest expectation: P1–P3 attack the three R30 s02 losses and the lobby waste directly, so the
likely gain is one to two s02 cells and a safer s03 `initial`, i.e. 14–15 with less variance,
not a jump. s03 `dynamic` stays the hardest cell in the design: the first tine is a coin flip,
and a wrong first tine leaves ~30 steps for a 26–28 step recovery after a closed read at ~s24.
P2+P4 make that recovery start at once instead of 31 steps later, which is the only way that
cell has ever been in reach.

## 6. Loose ends in the record

- R30 labels are "Claude review, not yet confirmed by the operator".
- R18/R18K, R23/R23K, R28, R29N/R29S are `planned`, 0/18, and R28/R29 Outcomes say not flown;
  the index could mark them `closed` so `results.md` stops listing them.
- `prompt.py`'s g05 note still says 1.84 m eye height (LD: 1.48 m). A wording fix is a new
  prompt version; P6 avoids touching it.
