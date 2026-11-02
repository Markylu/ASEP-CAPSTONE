# Plan: a63 "pathfinder", a code route planner under the a49 agent

Written 2026-11-02 by Claude for the operator, on branch `m/vlm-drone-agent-design-57d971`
(reset to the tip of `phase2/r29n-host-noise`, `822f1d7`). Nothing here has been built, probed
or flown. Engineering mode: the aim is the best agent for the final 90, read against `a49`
(R25D, 14/18, family 11.3 ± 1.4).

## 1. The diagnosis, in one page

`a49` already knows where the goal is (`goal_truth: planner`) and where the drone is (pose in
every manifest). What it does not have is a route. Its planner (`planner.route`) asks one local
question, "is a forward move within 55° of the goal open on the map?", and when the answer is
no, hands a menu of detours to a text-only strategist (`q03`). Every recorded failure of the
`a17b` family is that machinery failing, not the perceiver:

| Failure | Where | Evidence | What a route planner does instead |
|---|---|---|---|
| Dead-end tine, 34–46 steps, 0 in the other tine | s03 `final`/`dynamic` | `R22K…/s03_tines_analysis.md`; R25D s03 `final` s43–59 (§6: 17 steps bouncing at x ≈ −5.5, 12 turn-arounds); probe B0: `planner.way` reads `open` on 78% of shut-tine decisions because a goal behind the drone counts as open | The exit wall is on the map (a17b writes it; B0 and the tines analysis confirm). A path search cannot go through it and routes back along the trail, across the crossbar, into unknown cells of the other tine. R26 tried this with one target 11 m behind and a strategist; the stall hand-back killed it. A path gives waypoints, so there is nothing to stall. |
| Lobby wandering before the stem | s03 all arms | R25D s03 `final` s2–31: 30 steps in the lobby, out to z = −11 and back, before entering the stem at s26; `initial` took 50 steps; R17's "lobby wall pattern" | The planner prefers the shortest path through unknown cells; the stem mouth lies on the goal line, so the waypoint points at it from the first wall contact. |
| Door wall walk, cannot cross at the open door (modes B and K) | s02 `final`/`dynamic` | `R19…/s02_failure_analysis.md`: the goal line clips the inner jamb on 197/202 inner-side steps; the wrong-side search is a coin flip; R25D s02c/s02va `final` (12.8 m, 17.8 m, 22–24 `d01` calls each) | Walls at the divider seal as the drone looks at them; the door becomes the only free gap on the map once looked through; the waypoint is the farthest path point in line of sight, so the "toward" bearing goes through the gap, not along the goal line. |
| Strategist picks and hand-backs | all | R11: 47% of steps on detours that gained nothing; R26: the right pick, then a hand-back after 4 steps; A1: the strategist's picks re-roll under any text change | No strategist call. Fewer model calls per step (perceiver, `d01` when needed, navigator). |

What stays the same: the perceiver `g05`, the door confirmer `d01`, the memory `a17b`, the
navigator `p17`, the tags, the turn rule, goal truth on the planner side only. Seven attempts on
the perceiver found no better reader (R27, R28, LD); the host rounds R29N/R29S may still move it,
and this design does not care which host setting wins.

## 2. The agent: a63

`Agent("a63", "p17", {"orchestrator": {..., "target_policy": "pathfinder", "pathfinder": PATHFINDER_A63}})`,
built on `a49`'s features. One new stage replaces `route`; everything else is `a49`'s code.

### 2.1 Cost map (code, `spatial.py` additions, read by the planner only)

Built from the same memory `a17b` builds today; nothing new is read from Godot.

| Cell class | Source | Planner cost |
|---|---|---|
| visited | trail | 1.0, always passable |
| free | a look's cone (as today) | 1.0 |
| unknown | nothing seen there | `unknown_cost` (2.0) |
| unknown next to a wall (4-neighbour) | derived | impassable: a wall the perceiver saw ends in a wall, not a gap. A free cell is never sealed, so a door the drone has looked through stays open |
| wall (perceiver `no_floor`, a17b rule) | as today | impassable |
| stop wall (a move stopped short) | as today | impassable, plus 1 cell each side across the move's heading (a collision is a wide thing: cube face, door leaf, wall) |
| closed door, confirmed by `d01`, strip end within 2.5 m | new: `floor_end` in {`no_floor`, `bottom`} | impassable across the strip and its two neighbours at that range (a door is 2.4 m ≈ 3 cells) |
| suspected wall: strip end `lower` / `middle` at 3 m / 5 m, closed door farther than 2.5 m | new, soft | `suspect_cost` (4.0): not a wall, a reason to prefer another way. Erased like `wall` by a later look that sees floor there |

Phantom walls (12.7% of open strips in R25D) therefore cost a detour attempt, not a trap: a
perceiver wall is erased by the next look that sees floor there or by a visit (today's rule),
and `wall` cells are never written on visited cells.

### 2.2 Planner (code, `planner.py`, new function `pathfind`)

Every step:

1. A* from the drone's cell to the goal's cell on the cost map, 8-connected. Unknown cells are
   passable at `unknown_cost`, so there is always a plan unless the drone is sealed in; then
   the search repeats with perceiver walls (not stop walls) made soft at `suspect_cost`, and
   if that fails too, the target is the nearest frontier (today's `search_frontiers`).
2. The waypoint is the farthest path point within `lookahead_m` (4.0) reachable in a straight
   line over passable cells from the drone (string pulling). Near a door this is the point
   beyond the gap, so the bearing runs through it.
3. The target is `Target("path", "path", wx, wy, "the next point on the planned route", step)`.
   `spatial.project` tags "toward your target" as today (nearest open action within 55°, or
   marker 0 when the waypoint is behind, or the sharpest open move on its side).
4. Stall rule (replaces `detour_stall`): if the drone has not come `stall_gain_m` (1.0) nearer
   the goal along the path in `stall_steps` (5) decisions and the last move was not blocked, the
   two cells ahead of the last chosen heading become stop walls and the plan is rebuilt. This
   is the only way a repeatedly ignored or repeatedly clipped move changes the map.
5. The record keeps `planner: {path_m, path_cells, waypoint, unknown_on_path, replanned, stall}`
   and the memory snapshot adds the cost-map counts, so `eval/spatial_replay.py` reproduces the
   plan from `decisions.jsonl` and the manipulation check can read it.

The plan line to the navigator stays `WORDS_A14["plan_goal"]` ("head for the goal (approach)"),
so `p17` is unchanged and its sha stays. Parameters and the one new label are
`agent.PATHFINDER_A63`, hashed into the sha.

### 2.3 What is deliberately not in a63

- No strategist, no menus, no detour kinds, no along-the-wall or other-way items, no goal
  confirmer `c01` (why_14 §3: no consistent effect in seven pairs).
- No change to `g05`, `d01`, `a17b`'s floor rules, `p17`, the turn rule. One change: the planner.
- No new reads from Godot: pose and the perceiver only, as the memory contract says.

## 3. Open question that changes the design: who picks the action

Today the VLM navigator picks; code only tags. In R11 the navigator ignored "toward your
target" on marker 0 on 76% of offers; `p16`/`p17` brought that down but not to zero. With a
real route, every ignored tag is a wasted step.

Options, cheapest first:
- **A (default here):** the VLM navigator picks, as `a49`. The manipulation check measures how
  often it follows the tag.
- **B:** the VLM navigator picks, but when it picks a move the map calls blocked, stopped short
  or wall-seen while an open "toward" move exists, code asks once more with the critic note
  (`critic: retry` exists from a13). Cheap, still the VLM's choice.
- **C:** code picks the "toward" action; the VLM is the perceiver only. This is the ceiling of
  the perception plus planner, and the cleanest number for "what the model can and cannot
  see". It changes what the thesis calls a VLM navigator.

Proposal: build A; fly C only as an unscored diagnostic in the shakedown (§5 step 4, six runs,
30 min) so the gap between A and C is known before the round. Whether C may ever be a round or
the final agent is the operator's call (question 1 below).

## 4. Hypothesis, predictions, checks (draft for the R30 README)

**Hypothesis.** With a path search over the memory in place of the local goal-way test and the
detour strategist, `a63` leaves the s03 dead end and crosses the s02 open door more often than
`a49`, and scores at least 14/18.

| Arm | R25D (`a49`) | Predicted `a63` | Where it changes |
|---|---|---|---|
| initial | 6 | 6 | s03 `initial` in fewer steps (50 → ~30) |
| final | 3 | 4 or 5 | s03 `final` (tine recovery; the first tine is a coin flip), s02c/s02va `final` (door crossing) |
| dynamic | 5 | 4 to 6 | s03 `dynamic` (recovery needs ~44 of 60 steps: tight), s02 at risk of a lucky draw not repeating (why_14) |

**Manipulation check** (code only, from `decisions.jsonl` and geo truth):
- s03 `final`/`dynamic`: steps spent in the shut tine after the first confirmed closed door ≤ 8
  (R25D `final`: 17; R22K: 34–46); steps in the open tine > 0 (R20–R25D: 0).
- s03, all arms: steps in the lobby ≤ 12 (R25D `final` 30).
- The navigator follows "toward your target" on ≥ 70% of steps where it is offered on a forward
  move, and on ≥ 50% where it is on marker 0.
- Planner: a path exists on ≥ 95% of steps; the soft fallback fires on ≤ 5%.

**Drop criterion.** Below 14/18, or the s03 check fails in both `final` and `dynamic` (then the
planner did not do the one thing it was built for, whatever the total).

## 5. How to get there (order of work)

1. **Code** (about a day): `spatial.cost_map`, `planner.pathfind`, the stage in
   `orchestrator.pipeline` (`target_policy: pathfinder`), `agent.PATHFINDER_A63`, `a63` and
   `a64` (= a63 with the code navigator, for the diagnostic only). Unit tests on a hand-drawn
   map: the sealed exit wall, the open door gap, string pulling through a 3-cell gap, the
   soft fallback.
2. **Offline replay probe, no model, CPU only** (can run beside R29 on the host, or locally):
   `eval/probes/pathfinder.py`. For every recorded step of R20–R29 (memory rebuilt with `a17b`
   as `spatial_replay` does), run the planner and score against geo truth:
   - s03 shut-tine steps (x < −3 in the shut tine, after the closed door's first confirmation):
     waypoint bearing leads out of the tine (+x) on ≥ 80%;
   - s03 lobby steps: waypoint within 2 m of the stem mouth line on ≥ 70%;
   - s02 steps within 4 m of the open door, near side: the first straight-line segment of the
     path crosses x = 0 inside the door opening on ≥ 60% (R19: the goal line did on 2% of
     inner-side steps);
   - sealing harm: share of steps where a perceiver wall plus inflation closes a true passage on
     the true shortest path (counted per site; gate ≤ 5% outside s03's tines);
   - "toward" agreement with the recorded navigator pick on R25D's solved runs ≥ R25D's own
     toward-follow rate, so `initial` is not put at risk.
   Gate numbers are committed before the script runs. Parameters may be tuned on R20–R26 and are
   then frozen; R27 and R29 steps are the held-out check.
3. **Smoke** (no model): `a63` on R25D's 627 recorded manifests with stub replies, 0 failed steps.
4. **On-policy shakedown** (model, needs a quiet instance: after R29, or a copy on a free GPU):
   one unscored `dynamic` run per site, s03 first, for `a63` and for `a64`; scored by
   `r28_flight.py` and the manipulation check above. Fails if s03's tine check fails or any run
   shows a turn-around streak ≥ 10.
5. **R30** (`a63`, 18 runs), README committed before flight, on the host setting R29 decides.
6. If R30 holds: ablation only if there is time (soft suspects off; stall rule off); otherwise
   straight to the final 90 on `a63`.

Time: code and offline probe 1.5 days; shakedown and round 2 hours of host time plus labelling.

## 6. Evidence used

- R25D s03 `final` trace (`eval/phase2/R25D_door_confirmer_open_near_unwalled/runs/s03/final/seed1/decisions.jsonl`):
  lobby s2–31 (reached z = −11.5 at s10), stem s26–31, tine L s37–42, closed door confirmed by
  `d01` at s38 (9 m out), s42, s47; exit wall at s43; s43–59 at x ∈ [−6, −5] with 12
  turn-arounds; `planner.way` open on 49 of 60 steps.
- R25D per-run counts (this session): s02c `final` 60 steps, 12.8 m, 22 `d01` calls; s02va
  `final` 60 steps, 17.8 m, 24 `d01` calls; s03 `dynamic` 60 steps, 8.2 m, 19 turn-arounds.
  Step latency median 5.0 s, p95 13.4 s (the wall clock allows 15 s per step).
- `docs/research/what-we-learned.md`, `eval/phase2/_probes/b0/README.md`,
  `eval/phase2/_probes/e0/README.md`, `eval/phase2/R26_other_way/README.md` (Outcome: "hand it to
  the planner as waypoints back along the trail"), `eval/phase2/R19_searched_defined/s02_failure_analysis.md`.
- Site geometry: `first-project/sites/*/site.json` (s03 divider 7 m thick, tines 3 m wide, doors
  2.4 m; s02 divider 1 m thick; s01 cube 8 m, side gaps 7.75 m).

## 7. Questions for the operator (answers change the plan)

1. May code pick the action (option C) in a flown round or the final, or must the VLM navigator
   always choose? If never, a64 is a diagnostic only.
2. Is `goal_truth: planner` (the goal's true position on the planner side, as `a49`) acceptable
   for the final 90? Phase 1's `a00` had distance and bearing in its prompt, so this seems
   within the design, but it is the operator's line to draw.
3. Which round is flying now (R29N, R29S, both), on which host layout, and when does `:8004`
   free up? The offline probe needs no model; the shakedown does.
4. Deadline: how many host sessions remain before the final 90 must fly? That sets whether an
   ablation round happens at all.
5. Branching: cut `phase2/r30-pathfinder` from `phase2/r29n-host-noise`'s tip now, or wait for
   R29's data commit so the chain stays linear?
6. The lane layout for R30: whatever R29 decides, or shared `:8004` as every round so far?
