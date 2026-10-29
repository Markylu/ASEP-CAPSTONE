> Written by a Claude subagent on 2026-10-16 from the 810 R5 decisions (with R1 and R4 for comparison), read-only. Headline numbers were spot-checked against the data for [summary.md](summary.md), which uses its own counts where they differ (the analysis counts some rates over post-change steps only).

# R5 (a06) reasoning analysis: goal identifier + sighting line

Read-only analysis of `eval/phase2/R5_goal_identifier/runs/*/*/seed1` against R1 (`a01`) and R4 (`a04`).
Ground truth is `manifest.goal` and `true_goal()` from `eval/agent_evidence.py`. Helper scripts are in this
scratchpad: `analyse.py`, `dump2.py`, `metrics.py`, `memuse.py`, `infer.py`, `turns.py`, `geom.py`, `ident.py`, `mapping.py`.
"Post-change" means every step in `final`, and steps after the `events.jsonl` change step in `dynamic`.

## 0. Headline

1. **The identifier works, and the navigator obeys it.** It saw the goal in 114 of 114 in-view frames. It had
   10 "false positives" in 696 out-of-view frames, and none of them is a real error (§3). The navigator's
   side matches the identifier's side in 115 of 124 decisions. All 9 mismatches are marker-number slips.
   Its reason places the goal in view in 1 of the 686 decisions where the identifier says not visible
   (R4: 342 of 781). Phantoms are gone.
2. **Final and dynamic fail because the drone turns around in place over and over (ping-pong), not
   because it misses the change.** Post-change, `a06` turns around in 41% of `final` decisions and 78%
   of `dynamic` decisions (R1: 8% / 14%; R4: 23% / 28%). Back-to-back turn-arounds make up 26% / 65% of
   decisions (R1: 0% / 1%).
   - In `dynamic`, 211 of 360 decisions sit in streaks of 4 or more turn-arounds (R1: 4; R4: 43). The
     longest streaks are 26, 36, 7, 21, 22 and 18.
   - The drone barely moves after the change. Its path is 10–34 m over 56 steps, against R1's 65–86 m.
3. **The sighting line causes part of the loop in `dynamic`.** It does this through two arguments that
   alternate:
   - Facing the old sighting heading (net turn 0): "the closed door/wall ahead blocks it, turn around".
   - Facing away (net turn 180): "the goal is behind me, turn around to face where it was seen".

   Of 92 reasons that infer "the goal is behind", 83 pick turn-around. When the inference follows the
   log, the geometry is correct (76 of 77 match ground truth). Acting on it points the drone back at
   the closed door, so the line behaves like the goal-bearing hint that failed in Phase 1.
4. **The ping-pong also happens without any sighting.** In the `final` runs of s01, s02a and s02vc the
   goal was never seen, yet turn-around streaks reach 15, 9 and 12. The justification there is "facing a
   wall, turning around is the safest way to reorient". Of the turn-arounds justified by a wall in
   s01/s02, 54% had at least 5 m of free floor ahead by ray-cast (median 6.3 m). Of `a06`'s reasons
   that note the drone keeps turning around, 84% (183 of 217) pick turn-around again.
5. **The successes come from the identifier and from the move log, not from the sighting line.**
   - With the goal in view there are no turn-arounds (R1: 6 of 164; R4: 11 of 179). That is why
     s02va/s02vc `initial` take 19 steps where R1 took 55.
   - At the s03 T-junction the move log stopped R1's shuttle: "Turning around … would retrace the path
     already taken" (s03 `initial`, step 14).
   - s03 `final` succeeded without any sighting until step 47.

## 1. Results in context

| Cell | R1 | R4 | R5 |
|---|---|---|---|
| initial | 5/6 | 2/6 | **6/6** (s01 14, s02a 14, s02c 14, s02va 19, s02vc 19, s03 41) |
| final | 2/6 (s02c, s02vc) | 2/6 (s02a, s02va) | 2/6 (s03 54, s02va 35) |
| dynamic | 1/6 (s02a) | 1/6 (s02va) | 0/6 |

**Some runs are near-duplicates. Read `initial` as 4 independent tests, not 6.**
- s02a and s02c `initial` are byte-identical: 14 of 14 picks, poses and reasons. s02va and s02vc
  `initial` share 19 of 19 poses and 16 of 19 reasons. R1 shows the same pairing.
- s01 `initial` is a different run that happens to also take 14 steps.
- s02a and s02c `dynamic` are identical through step 18. Their first different pick is at step 19,
  when the open door first enters the frame.
- s03 `initial` and `final` are identical through step 21. s03 `dynamic` matches them through step 25.

## 2. Q1: why `final` and `dynamic` fail

### 2.1 Behaviour per arm (R5 post-change, with R1 and R4)

| Metric | R5 initial | R5 final | R5 dynamic | R1 final / dyn | R4 final / dyn |
|---|---|---|---|---|---|
| decisions | 121 | 329 | 313 | 298 / 295 | 304 / 320 |
| turn-around pick | 7% | **41%** | **78%** | 8% / 14% | 23% / 28% |
| turn-around right after a turn-around | 1% | 26% | **65%** | 0% / 1% | 10% / 16% |
| steps in turn-around streaks ≥ 4 (of the arm's decisions) | 0 | 70 / 329 | **211 / 360** | 0 / 4 | 20 / 43 |
| revisit (within 1 m of a pose ≥ 5 steps earlier) | 2% | 41% | 65% | 28% / 35% | 19% / 36% |
| distinct 1.7 m cells, summed over runs | 106 | 127 | **59** | 174 / 161 | 162 / 132 |
| reason cites the sighting ("last seen/sighting") | 62% | 33% | **90%** | – | – |
| reason cites net turn / degrees | 31% | 14% | **83%** | – | – |
| "behind" | 4% | 10% | 34% | 0% / 1% | 1% / 5% |
| wall | 20% | 65% | 55% | 65% / 65% | 63% / 65% |
| explore | 24% | 80% | 62% | 86% / 82% | 76% / 64% |
| open door / doorway / opening | 30% | 28% | 22% | 35% / 37% | 31% / 24% |
| closed door (explicit) | 0% | 1% | 12% | 4% / 6% | 0% / 4% |
| notes the loop ("turning around repeatedly", "loop") | – | 217 of final+dyn, 183 then pick 0 | | 0 | 150, 85 then pick 0 |

The longest turn-around streaks in failed runs:

| Run | Streak |
|---|---|
| s01 `final` | 15 |
| s02a `final` | 9 |
| s02c `final` | 3 (this run grinds on collisions instead) |
| s02vc `final` | 12 |
| s01 `dynamic` | 26 |
| s02a `dynamic` | 36 |
| s02c `dynamic` | 7 |
| s02va `dynamic` | 21 |
| s02vc `dynamic` | 22 |
| s03 `dynamic` | 18 |

Over the 56 post-change steps, R5 `dynamic` moves 10, 14, 26, 24 and 34 m on s01, s02a, s02c, s02va and
s02vc. R1 moves 65, 83, 86, 85 and 81 m. The farthest the drone gets back toward spawn on s02a/s02c
`dynamic` is x = 10.3 (R1: 20.9 and 21.2).

### 2.2 It does notice the change

The labeller acknowledges the change within 5 steps in all 10 failures. Examples:
- s02a `dynamic`, step 4: "The current image shows a closed door directly ahead, which blocks the path."
- s03 `dynamic`, step 26: "The drone is facing a closed door, which is a wall."

**Misconceptions about turning around.**
- s02a `dynamic`, step 4 (already facing the closed door): "To proceed, I need to turn around to face the
  door and then move through it."
- s01: the risen cube is never called a cube or box (0 mentions in `final` or `dynamic`). It is "a large
  wall directly ahead" (s01 `final`, step 0, 10 m away). The agent never tries the 7.75 m side gaps.

### 2.3 It usually finds the open route, and then fails to execute

- **`final`, s02 family: the right side is chosen at step 0–1 in 4 of 4 runs.**
  - s02a: "two closed and one open on the right".
  - s02va: "the rightmost door (marker 5) is open".
  - s02vc: "Marker 1 leads toward the open left doorway".
  - s02c went left "because it is more open", which is weak reasoning but the right side.

  Only s02va succeeded. The other three failed for these reasons:
  - **s02a `final`: stuck at the doorway.** It reaches the mouth of door A at step 7 (3.2, −7.5) and
    then spends 32 steps within 3 m of the opening.
    - At step 8, facing −X at z = −7.6, it is 0.2 m off the jamb line.
    - It says "a wall on the left and an open space to the right", then picks turn-around.
    - It ping-pongs at (1.5, −7.6) on steps 12–17 and at (0.9, −7.5) on steps 35–43.
  - **s02c `final`: grinds into the jamb.** It sees the goal through door C (identifier left/ahead at
    steps 16, 17, 30) but sits at z ≈ 11, outside the opening (z 7.8–10.2). It flies "straight" into the
    divider and jamb 23 times between steps 10 and 59.
    - The frame is all black at step 41.
    - The reason at step 41 says "the lack of visible obstacles suggests an open corridor … continue
      straight".
    - The log said "flew straight" each time, and 23 of 37 reasons after a collision claim the drone
      "has been moving forward".
  - **s02vc `final`: false wall, then ping-pong.** At step 1, after turning toward door C, it says
    "currently facing a wall" with 16 m of free floor ahead. It turns around, then ping-pongs near the
    north wall (8.6, 11.5) on steps 19–23 and 33–44.
- **`dynamic`, where the new door is in view at the change (s02va, s02vc):**
  - s02va steps 4–5 go forward, then pick 5: "move forward toward the open doorway on the right
    (marker 5)". At step 6 the sighting arithmetic pulls it off: "The open door is visible ahead … Given
    the recent rightward turn, the goal may now be to the left … turning around (marker 0)". It
    eventually reaches the doorway at a bad angle. It collides with the jamb at steps 19 and 38, then
    ping-pongs at (0.7, −7.4) for 21 steps (steps 39–59). The frame is filled by the orange architrave.
  - s02vc at step 4: "Given that the goal was ahead and is now not visible, the most likely explanation
    is that the drone has passed the point … The only way to reorient … is to turn around." R1 and R4
    both picked 1 (toward door C) at this step.
- **`dynamic`, s02a/s02c (new door off-frame):** the drone never gets more than 5 m back from the closed
  door. The open door enters view at step 19–20 ("one closed on the left and one open on the right",
  s02a, step 20) and the drone heads toward it on steps 20–22.
  - At step 23 it turns away: "Given the net turn of 40 degrees to the right since the last sighting,
    the goal is likely to the left … turning slightly left (action 1)".
  - That points it back at the wall. It then ping-pongs for 36 steps at (3.5, −4.6).
- **s03 `dynamic`:** it commits to tine L, and the door closes at step 25. It turns around once, then
  ping-pongs for 34 steps. Facing back down an open 9 m corridor, it says "a narrow corridor with a wall
  directly ahead and no visible path forward" (frame f000030).

**When it mentions an open door or doorway, it still turns around.** Post-change on s02/s03, R5 picks
turn-around in 30 of 95 such decisions (32%). R1: 1 of 106 (1%). R4: 8 of 87 (9%).

### 2.4 What it says it is doing when it turns around (379 post-change turn-arounds)

- **Reorient / re-evaluate / check / safe / conservative:** 350 of 379. "Reorient" alone appears in 89%
  of R5's `final`/`dynamic` turn-arounds (R1: 61%). "Safe/avoid collision" appears in 44%.
- **Facing a wall / blocked / dead end / closed door:** 229.
  - s01/s02 ray-cast check of the 187 such claims: median free distance ahead 6.3 m; ≥ 5 m in 101
    (54%); < 2.5 m in 46.
  - R1 has the same misperception (64% have ≥ 5 m free), but acts on it in only 47 decisions.
- **"Goal behind / opposite direction / face where it was last seen":** 246.

Typical alternating pair (s02a `dynamic`, steps 28 and 29):
- Net turn 0: "the drone is currently facing a wall (marker 0)" → turn around.
- Net turn 180: "it is now facing the opposite direction from when the goal was last seen … likely
  behind the drone" → turn around.

## 3. Q2: how the navigator uses the memory

- **The sighting line is cited constantly.** It appears in 75 of 121 `initial` reasons, 108 of 329 `final`
  and 290 of 360 `dynamic`. The net turn or degrees appear in 40, 50 and 272.
- **The move log is cited to avoid retracing or to count turn-arounds.** "Turning around would retrace
  the path already taken", s03 `initial`, step 14, is the step that got s03 off the T-junction.
- **Confabulated sightings.** In 16 of 325 decisions whose log said "No goal sighting yet", the reason
  names a sighting step anyway. Examples: "The last time the goal was seen was at step 0" (s02vc
  `final`, step 20) and "The last sighting of the goal was at step 26" (s01 `final`, step 27).

**Inference correctness.** These are the goal-direction claims in frames where the identifier says not
visible and the log has a sighting (n = 124). They are scored against the direction implied by the log
and against ground-truth bearing.

| Claim | Matches the log, GT right | Matches the log, GT wrong | Does not match the log, GT wrong | Does not match the log, GT right |
|---|---|---|---|---|
| behind | 55 | 1 | 29 | 2 |
| left | 16 | 0 | 12 | 0 |
| right | 4 | 0 | 3 | 0 |
| ahead | 2 | 0 | 0 | 0 |

- **When it follows the arithmetic, it is correct: 76 of 77.** For example, s02a `dynamic`, steps 9–59:
  "net turn of 180 … goal behind" with ground-truth bearing −161 to −177.
- **The 44 wrong claims mostly argue from absence.** With net turn 0, "not visible ⇒ behind": s02c
  `final`, step 20, "Given that the goal was seen ahead and the drone has continued forward, it is likely
  that the goal is behind the drone" (bearing −33).
- **There are sign slips too.** s01 `dynamic`, step 20: "the net left turn, the goal is likely to the left"
  (truly right, −46).
- **Action given the inference:**
  - "behind" → turn-around 83 of 92.
  - "left" → left 14, turn-around 12, straight 2.
  - "right" → right 4, turn-around 3.

  So even a correct side often becomes a turn-around. s01 `dynamic`, step 44: "it is likely that the
  goal is now to the right … The most logical action is to turn around (0)."
- **Correct inference does not mean a good route.** In every s01/s02 `dynamic` run, the correctly
  inferred direction points through the closed door or the cube. The line turns the navigator into a
  goal-bearing follower:
  - re-aligning left toward the wall (s02a `dynamic`, step 23; s02va `dynamic`, steps 9–10);
  - turning around to "face the direction where the goal was last seen" (s02a `dynamic`, steps 9, 18
    and so on).

## 4. Q3: identifier against navigator

**Identifier accuracy in flight** (rows: ground truth; columns: identifier):

| GT \ identifier | ahead | left | right | not_visible |
|---|---|---|---|---|
| ahead | 95 | 0 | 0 | 0 |
| left | 5 | 5 | 0 | 0 |
| right | 2 | 0 | 7 | 0 |
| not_visible | 4 | 0 | 6 | 686 |

- **Seen when visible: 114 of 114.** The direction is exact in 107. The 7 misses are off-centre goals
  called "ahead".
- **None of the 10 "false positives" is a real error:**
  - 6 are "right" at bearing −44 to −53 with line of sight, the sphere on the FOV edge (43.5°).
  - 4 are "ahead" at `dynamic` step 3 (s02a, s02c, s02va, s02vc). The manifest has
    `line_of_sight: false` there, but the clean frame (s02a `c000003.png`) shows the sphere through door
    B. This is a ground-truth timing artifact: line of sight is recorded after the step-3 trigger,
    while the frame is captured before it.
  - The auto-labeller's `phantom: 1` on s02c, s02va and s02vc `dynamic` and on s03 `final` comes from
    these cases.
- **The navigator follows the identifier.**
  - When the identifier says left, it picks left 5 of 5; right, right 13 of 13; ahead, ahead 97 of 106.
  - All 9 "ahead → left" cases are marker-mapping slips, for example "[1], which corresponds to flying
    straight" (s02a/s02c `initial`, step 11).
  - No reason argues against the identifier. Only 1 of 686 not-visible decisions has `claims_goal()`
    true.
- **Approach quality when the goal is truly in view:**
  - Nearest-bearing pick 96 of 114 (84%; R1 82%, R4 73%).
  - Turn-around 0 of 114 (R1 6, R4 11).
  - Sight lost on the next step 15 times. These come from sharp 1/5 picks when 2/4 fit, as in the
    zig-zag in s02va `final` steps 26–34, and from mapping slips.

**Marker-mapping slips (reason says straight, pick ≠ 3), confirmed by reading:**
- R5: about 10 (s01 `initial` 1; s02a/s02c `initial` 11; s03 `initial` 31; s02a `final` 56; s03
  `final` 47 and 50; s01 `dynamic` 1; s02va `dynamic` 13; s02vc `dynamic` 49).
- R4: about 9. R1: 1.
- s02va `dynamic`, step 12: "The marker for turning left is likely 1, as it is the first available
  action after 0."

## 5. Q4: what made the 8 successes work

- **s01, s02a, s02c, s02va, s02vc `initial` (14/14/14/19/19 steps).** The goal is in view almost
  throughout. The identifier gives a discrete side, the navigator follows it, and it never turns around
  with the goal in view.
  - R1's s02va/s02vc `initial` took 55 steps for one reason. At step 17, 3.4 m from a goal 25° left,
    it said "the drone is currently facing away from the sphere, so … turn around". It then flew away
    for about 10 steps and turned around 3 more times.
  - R5's only wobble on s02va `initial` is a slip at step 11 (pick 1 while saying "continue flying
    straight"). The identifier said "right" at step 12 and pick 5 re-centred it.
- **s03 `initial` (41; first ever).** Four things carried it:
  1. At the T-junction (step 14, x = 7.7) the move log stopped the R1-style shuttle (R1 never got past
     x = 7.41): "Turning around (0) would reverse … this would retrace the path already taken … turn
     slightly to the left (action 1)".
  2. It goes down tine L, sees the doorway at steps 22–24 ("Marker 4 is aligned with the doorway"), and
     goes through.
  3. The identifier picks up the goal at step 28 (right → 5).
  4. A slip at step 31 loses the goal on steps 32–37. The identifier re-acquires it at step 38, and the
     drone arrives at step 40.
- **s03 `final` (54; first ever).** Identical to `initial` through step 21. Then:
  - It sees "a closed door on the right" (step 27) and ping-pongs on steps 22–33. These 12 steps were
    wasted.
  - It backs out of tine L (steps 33–35), crosses the crossbar (steps 36–38) and goes down R (steps
    39–46).
  - It sees the goal at step 47 and arrives at step 53, after two more slips (steps 47 and 50).
  - There was no sighting in the log before step 47, so the sighting line played no part. The 12
    ping-pong steps and 3 slips put it 6 steps from timeout.
- **s02va `final` (35).** It identifies the open door at steps 0–1, wanders with 6 turn-arounds
  (steps 5–17), and goes through door A at step 24. The identifier then guides the approach
  (steps 26–34), with a left/right zig-zag from sharp picks.

## 6. Q5: divergence from R1 and R4 on the same cells

- **s02a `dynamic`: R1 succeeds at 60, R5 fails.**
  - Both see the closed door at step 4.
  - R1 tries both sides (picks 1, 5), turns around once (step 6), then flies straight back for 13 steps
    to the spawn wall (x = 20.9, step 20). From there it sees the s02va-like view: "three doors ahead.
    The left and center doors are closed; the rightmost door is open" (step 21). It flies through A and
    reaches the goal.
  - R5 never goes beyond x = 10.3. At net turn 180 the sighting line says "goal is behind → turn
    around", so it can never commit to flying away from the closed door. Its post-change path is 14 m
    (R1: 83 m).
- **s02va `dynamic`: R4 succeeds at 40, R5 fails.**
  - Both pick 5 toward open door A at step 5.
  - R4's phantom "goal still reported as ahead" kept it flying forward (steps 6–8). It reached the
    doorway by step 12 and passed through around step 21.
  - R5 turned around at step 6 ("the goal may now be to the left … turning around"). It re-aligned
    left on steps 9–10 ("Given the net turn of 20 degrees to the right overall … turn slightly left").
    It reached the doorway obliquely at step 19 and collided with the jamb at steps 19 and 38, then
    ping-ponged for 21 steps at (0.7, −7.4).
- **First post-change picks** (`dynamic`, next 10 picks):

  | Site | R1 | R4 | R5 |
  |---|---|---|---|
  | s01 | 0301103031 | 3313133330 | 0000033100 |
  | s02a | 1503330033 | 0333333433 | 0300300000 |
  | s02c | 3033012334 | 0343331313 | 0300300000 |
  | s02va | 5332333333 | 3533313530 | 3500321411 |
  | s02vc | 1333343234 | 1333432313 | 0333004012 |

  R5's first post-change pick is a turn-around in 4 of 5 s01/s02 runs (R1: 1 of 5; R4: 2 of 5).

## 7. Q6: failure modes the rubric does not capture

All 10 failures are labelled `replan_failure` with no tags. Underneath that label:

| Mode | Runs | Evidence |
|---|---|---|
| **Turn-around ping-pong** (in-place dithering, no displacement) | 9 of 10 (all but s02c `final`) | 281 decisions in streaks of 4 or more. Not `ignore_change`, not `collision`, not `timeout`. |
| **Stuck at the threshold** (reached the open doorway, never threaded it) | s02a `final`, s02c `final`, s02va `dynamic` | 32 / 49 / 32 steps within 3 m of the open doorway mouth, closest 0.3 / 0.7 / 1.6 m. "Never passes the newly opened door" makes this look like a failure to find the route, which it is not. |
| **Blind wall-grinding with a log that says progress** | s02c `final` (23 collisions), s02vc `final` (7) | 23 of 37 post-collision reasons claim the drone "has been moving forward". The log records the command, not the outcome. |
| **Sighting anchor** (re-aligning to the old goal heading, into the obstacle) | s01, s02a, s02c, s02va, s02vc `dynamic` | 83 "behind → turn-around"; re-alignment examples in §3 |
| **False "wall ahead"** | All arms | 54% of wall-justified turn-arounds have ≥ 5 m free. |
| **Marker-mapping slip** | 5 successes, 5 failures | About 10 slips, each followed by loss of sight or a detour. |
| **Ground-truth timing artifact** | s02a/s02c/s02va/s02vc `dynamic` step 3 | `line_of_sight` false while the frame shows the goal; it inflates the phantom facet by 1. |
| **Confabulated sighting** | 16 decisions | Cites "last seen at step N" when the log says no sighting. |

## 8. Q7: ranked next-step options (one change each)

`a06` met its drop criterion, so each option is stated against the agent it would modify. Every option
keeps the goal identifier (`g02` on the clean frame). It is the clean win of this round:
- 114 of 114 sightings;
- no turn-arounds with the goal in view;
- phantoms gone;
- `initial` 6/6, including the first s03.

### 1. Do not offer [0] on the step right after a turn-around (`a06` + one feature flag)

**What changes.** The agent omits `[0]` from "Available actions" and from the schema enum when the
previous executed move was a turn-around. Godot's fan is untouched, so this is an agent-side feature.
The operator should confirm it does not count as changing the fixed "action fan".

**Evidence.**
- Back-to-back turn-arounds are 26% of `final` and 65% of `dynamic` decisions; 281 decisions sit in
  streaks of 4 or more.
- The model cannot reason its way out: 183 of 217 reasons that note "turning around repeatedly" turn
  around again.
- The loop drives 9 of 10 failures in both arms, with or without a sighting.
- R1, which flew long straight legs, won s02a `dynamic` by retreating to x = 20.9.

**Prediction.**
- Back-to-back turn-arounds go to 0 by construction.
- Post-change turn-around rate ≤ 30% on both arms (R5: 41% / 78%).
- Post-change path length per `dynamic` run ≥ 50 m (R5: 10–34 m).
- Distinct cells ≥ R4's.
- `final` + `dynamic` ≥ 4/12, with `initial` held at ≥ 5/6. `initial` used no back-to-back
  turn-arounds except one pair on s03.

**Risk.** It may become a longer shuttle, as R1 did on s03. Watch revisits.

### 2. Remove the "Last goal sighting … net turn" line (`a06` minus the sighting line; keep the identifier's current-image answer and the move-only log)

**Evidence.**
- 83 of 92 "goal behind" inferences become turn-arounds.
- The line is cited in 90% of `dynamic` decisions.
- It pulled s02va `dynamic` off a correct door approach (steps 6, 9, 10) and s02a `dynamic` off door A
  (step 23).
- It produced the step-4 turn-around in s02vc `dynamic`, where R1 and R4 went for the open door.
- Every s01/s02 `dynamic` drone stays within 5 m of the closed obstacle.
- No success depended on it: s03 `final` had no sighting until step 47, and in `initial` the identifier
  alone drives the approach.

**Prediction.**
- `dynamic` turn-around ≤ 30% (R5: 78%).
- First post-change pick is not [0] in at least 4 of 5 s01/s02 runs.
- `dynamic` ≥ 2/6.
- `initial` unchanged (6/6 or 5/6).

**Limit.** It does not touch the `final` ping-pong, where there is no sighting (s01, s02a, s02vc).

### 3. Make the log state outcomes, not commands (`a06` + an outcome-aware log)

**What changes.**
- A move that did not displace the drone is logged as "flew straight: blocked, did not move".
- A run of in-place turn-arounds collapses to one line: "steps 24–59: turned around 36 times in place,
  position unchanged".

This is the README's own fallback candidate ("collision feedback in the log").

**Evidence.**
- s02c `final`: 23 collisions.
- 23 of 37 post-collision reasons claim progress, for example "has been moving forward in a straight
  line" (s02c `final`, step 41, black frame).
- The ping-pong is invisible as a non-move in the current log.

**Prediction.**
- Repeat-the-colliding-pick rate after a collision ≤ 20% (R5: 16 of 37; R4: 73 of 99).
- Collisions ≤ 15 in the round (R5: 37).
- s02c `final` gets through door C.

**Limit.** It is weaker on the loop than option 1, because the model already sees the loop and keeps
going.

### 4. Name the marker directions in the action list (`[1] sharp left … [3] straight … [5] sharp right`)

**Evidence.**
- About 10 confirmed slips ("[1], which corresponds to flying straight") against 1 in R1.
- 3 slips in the s03 `final` endgame, which finished 6 steps from timeout.
- Each slip is followed by loss of sight or a detour.

**Prediction.**
- Mapping slips ≤ 2.
- Sight lost on the next step ≤ 8 of the visible decisions (R5: 15 of 114).
- s03 `final` steps-to-goal ≤ 48.

**Limit.** This is an efficiency fix. It will not flip the `dynamic` failures by itself.

### 5. Wording on turning around and walls

Drop "Turning around is a normal move when the way ahead is blocked." Say instead: "Only turn around if
no floor is visible ahead; a wall with floor in front of it is not blocking you."

**Evidence.**
- 54% of wall-justified turn-arounds have ≥ 5 m free ahead.
- "Reorient" appears in 89% of R5's turn-arounds.
- R1 (`p03`), which lacks the sentence and the log, turns around 8–14% of the time.

**Prediction.** Post-change turn-around rate ≤ 20%.

**Limit.** This is the least certain option. Prompt-only behaviour changes have been fragile (R2–R4),
and R4 had the same sentence and turned around only 23–28% of the time.

**Not recommended.** Turning the sighting into an explicit "goal is now behind / to your right" hint.
§3 shows the navigator already infers this correctly (76 of 77) and it still steers into the closed
door. That is Phase 1's bearing-follower failure.

**Instrumentation.** Fix the step-3 `line_of_sight` timing, or give `true_goal()` a few degrees of edge
tolerance, before the next labelling pass. Consider tags for ping-pong (for example, ≥ 8 consecutive
turn-arounds) and for stuck-at-threshold (≥ 10 steps within 3 m of the open opening without passing).
Under the no-retroactive-relabel rule, these would apply from the next round only.
