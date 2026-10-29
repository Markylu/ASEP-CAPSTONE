# R15 (a25) and R15N (a26) failure analysis

Written 2026-10-29 by a Claude subagent as a read-only analysis of the recorded
`runs/<site>/<arm>/seed1/decisions.jsonl` of R15 (`a25`, 9/18), R15N (`a26`, 10/18), and R11 (`a16`,
11/18). No model calls were made and no labels were changed. The scripts were throwaway and are not
in the repo. Each number below is defined well enough to recompute it.

**Conventions.**
- Steps are the 0-based `step` of `decisions.jsonl`.
- Map coordinates are the memory's: x = world x, y = −world z. The goal is at (−12, 0).
- `dg` is the true distance to the goal and `gb` the goal's true bearing (left positive).
- "TA" is a turn-around (marker 0).
- `[F/n/X][D]` are the perceiver's five strips, far_left to far_right: open_far, open_near,
  blocked_near, with D marking a doorway flag.

**Ground truth and proxies.**
- Ground truth is `eval/phase2/R11_goal_default/analysis/geo.py`, with the s03 arms corrected from
  each `run.json`:
  - `initial`: both exit doors open (`static_doors`).
  - `final`: door L (y < 0) closed from step 0.
  - `dynamic`: the door of the first tine crossed at x = 0 slams.
- R15 runs have no `steps.jsonl`. "Short move" stands in for a collision: a forward move under 1.4 m
  between consecutive poses.
- "Toward" kinds:
  - **true**: on a forward action within 55° of the target.
  - **side**: a17's fallback, the sharpest open move on the target's side when nothing points at it.
  - **back**: on marker 0.

---

## 0. The short version

1. **Turning around against "toward your target".** a17's coverage note "searched already this way"
   is the main new cost.
   - Steps where no forward move says "new ground": R11 105/706 (15%), R15 348/827 (42%), R15N
     317/786 (40%).
   - The navigator turns around on 39–42% of those steps, against 1–2% when a forward move offers new
     ground. 134 of R15's 140 turn-arounds are on such steps.
   - Turn-arounds with "toward" on a forward move: R11 3, R15 50, R15N 50. The toward move had over
     2.2 m of true free floor in 44 (R15) and 35 (R15N) of them.
   - The navigator's stated reason is nearly verbatim each time: "all forward directions … marked as
     'searched already this way', meaning those paths have been explored and did not lead to the
     goal".
   - This lost s03 in every failing run, and R15 `s01/dynamic` at step 17, where the goal was in line
     of sight.
   - p14 and p16 never define this note.
2. **No way to search along a wall.**
   - In the 10 failed s02 runs the drone reached the divider by step 6–15 (step 31 once) and then
     spent 29–54 steps without passing it.
   - It spent 148 steps within 2.5 m of the closed door B.
   - In 4 runs it never visited the open door's side.
   - The open door was on a q03 menu in 2 of the 10.
   - Walled calls ended in "explore" 28/61 (R15) and 29/72 (R15N) times, because the menu had nothing
     useful.
   - R11 won s01 final/dynamic, s02a final and s03 final by accident. A goal-side phantom held for
     10–13 steps made the drone slide along the wall. a25's reachable targets are reached in 3–5
     steps (`detour_reached` 36 and 42 times), so nothing carries the drone along the wall any more.
3. **Detours still do not pay.**
   - Frontier, doorway and backtrack spans: R15 267 steps for a net −1.8 m toward the goal; R15N 227
     steps for −29.8 m. R11's phantoms gained +6.6 m over 377 steps.
   - Reachability did remove most targets beyond a wall: strictly beyond or inside a wall, R15 4 and
     R15N 11 picks (R11: 34/37). But 12 and 14 picks are frontier cells on the divider face, at the
     closed door B.
4. **Doorways on the menu are mostly false.**
   - Openings at a truly open door: R15 4/54, R15N 5/52.
   - Doorway picks: 18 and 17, of which 1 each was real.
   - The queued q07 ("a doorway first") would act on 44 and 37 menus that list a doorway. Only 3 and 5
     of those menus list a real one.
5. p16 raised how often "toward" on a forward move is followed: true-toward 65% → 80% (290/444 →
   359/449). It did not change the turn-arounds in item 1 (50 and 50). The outcome difference, 10 vs
   9, is 5 cells won against 4 lost, which is noise.

---

## Q1. Failed runs: causal chains

Summary (distance at the end; R11 in the same cell):

| Run | End dg | Steps lost mainly to | R11 same cell |
|---|---|---|---|
| R15 s01/final | 14.8 | 9 TAs against toward, orbit s12–24, never past x = 2.2 | ✔ 29 steps |
| R15 s01/dynamic | 12.7 | TA at s17 beside the cube with line of sight; detours pull back east | ✔ 29 |
| R15 s02a/final | 19.4 | wrong side (C) for 48 steps; wall-face detours at B and C | ✔ 26 |
| R15 s02c/final | 16.7 | pressing at closed B (28 steps); detour pulls it away 4.4 m from door C | ✗ |
| R15 s02c/dynamic | 16.7 | 13-step detour loop away; detour turns it back 2.6 m from door C; then A side | ✗ |
| R15 s02va/final | 14.9 | 13-step detour loop (false walled); detour held at door A s48–50 | ✔ 34 |
| R15 s02vc/dynamic | 12.5 | wrong side (A) 44 steps; 5 false-doorway picks | ✗ |
| R15 s03/final | 27.3 | TA at stem mouth s4 (9.2 m free); 54 of 60 steps in the lobby | ✔ 39 |
| R15 s03/dynamic | 19.4 | TAs at s4, s26, s35 in stem/crossbar; tines never on menu | ✗ |
| R15N s02a/final | 13.5 | wrong side (C) 41 steps; 4 wall-face detours; TA ping-pong | ✔ 26 |
| R15N s02a/dynamic | 6.9 | 45 steps at B and C side; through door A at s56, out of steps | ✗ |
| R15N s02c/dynamic | 13.4 | wrong side (A) 46 steps; 21 explore steps; 3 TAs in a row | ✗ |
| R15N s02va/dynamic | 16.7 | 2.7 m from door A at s27, q03 picks a "3 m nearer" wall-face cell at B | ✗ |
| R15N s02vc/final | 15.1 | at door C at s34 (straight 12 m free), phantom doorway target behind, TA | ✗ |
| R15N s03/initial | 8.1 | TA in the lobby s1 (36 lobby steps); TA 1.2 m from the open exit at s52 | ✔ 39 |
| R15N s03/final | 7.2 | 29 crossbar steps; dead end at closed door L, picked as a doorway 3× | ✔ 39 |
| R15N s03/dynamic | 19.5 | TA at stem mouth s4; 23 crossbar steps, never into a tine | ✗ |

### R15 (a25)

**s01/final.** Cube present from step 0; ends 14.8 m away.
1. s1 at (10.3, 0.24), 8 m from the cube face: the perceiver reads `X X X X X`.
   - The planner calls it walled, but a ray along some action within 55° of the goal is free for 12 m.
   - q03 answers `explore`, and the navigator turns around twice (s1, s3).
2. s7, at (7.95, 1.87): TA. "Toward" was on straight with "searched already this way", 6.0 m free.
3. s12: stall, so q03 picks `unexplored_1` (8.9, −1.3), abeam.
   - Steps 12–24 are the orbit already found: five consecutive sharp rights at s12–16, then
     `detour_too_long` at s25.
   - dg went 22.8 → 20.3 m.
4. s27, s30, s33, s41, s45, s49, s53: TA against toward each time. 9 such TAs in the run, all with
   "searched" or "been there" notes.
5. s36 blocked at the cube face, then `back_to_step_31`. s45 stall, then `back_to_step_43`. s54
   walled, then `explore`.
6. The drone never went below x = 2.2, so it never got round the cube (side gaps at |y| > 4).
7. R11 succeeded here in 29 steps:
   - s6 blocked; a phantom `unexplored_1` (−2.1, 0.4) lay inside the cube.
   - It held 13 steps, during which every forward note was "new ground", and the drone flew round the
     left side to y = 11.5.
   - The goal came into view at s20.

**s01/dynamic.** Ends 12.7 m away.
1. s0–3: goal in view, straight ahead. s6: collision at the cube face. s7: blocked, then
   `unexplored_1` (3.8, 2.1), reached at s9, then `explore`.
2. s14–16: the drone flies past the cube's left side, to (−2.47, 7.67) at s17, 12.2 m from the goal
   with line of sight.
   - "Toward" was on sharp left (12 m free, 19° off the goal), noted "searched already this way".
   - The navigator turns around ("the only unexplored direction is behind").
3. s20: stall, then `unexplored_2` (−1.3, 5.5) pulls it back east.
4. s29 at (−3.80, 4.20), dg 9.2, the closest it came: walled.
   - q03 picks `unexplored_3` (−2.1, 3.0), which is inside the cube.
   - Reached at s31. Side-toward sharp rights at s31–35 take it back to (2.2, 0.5) at s36.
5. s41: walled, then `back_to_step_32`. s54: `detour_too_long`. It ends at the far wall at y = 10.9.
6. R11: same pattern as R11 s01/final, 29 steps.

**s02a/final.** Door A open throughout; ends 19.4 m away.
1. s6 walled at closed door B, then `explore`. s7: collision. s9: blocked, then `unexplored_2`
   (4.7, −1.3), on the C side.
2. s12–16: the goal is the target. Side-toward sharp rights curve the drone along the C side to
   (0.92, −7.08), at closed door C.
3. s17, s23, s26: walled, then `doorway_D` at (−0.4, −1.6) or (−0.0, −2.1) each time: the divider
   face beside closed B.
4. s33: stall, then `unexplored_3` (−0.4, −5.5), on the divider face.
   - s33–46: back and forth along x ≈ 0.7, with 5 TAs (s37, s41, s44, …).
5. s47: walled, then `unexplored_1` (0.4, −9.8), the face at closed C.
6. Overall: y > 1.5 (the A side) on 0 steps; 48 steps on the C side. No menu item was ever within
   3 m of door A.
7. R11: 26 steps. A phantom (−3.0, 4.7) beyond the divider on the A side held for s7–17; the drone
   slid north along the wall and went through door A at s17–18.

**s02c/final.** Door C open; ends 16.7 m away.
1. s5: false walled at (4.35, −1.87), 5.5 m free, then `explore`. s7: goal reported with no line of
   sight (far_right).
2. s9: walled, then `unexplored_1` (2.1, 1.3), on the A side.
3. s14: walled, then `unexplored_2` (3.0, 0.4).
   - The drone first went south to (2.78, −5.19) at s17, 4.4 m from door C.
   - The target then pulled it east and north: a loop to (5.28, 0.35) at s25.
4. s28–37: at closed door B, (0.45..0.53, −0.15..−1.0). Short moves at s32–33; three TAs in a row
   at s34–36.
5. s41 at (3.97, −6.33), 4.3 m from door C, the closest it came: TA against toward on slight right
   (5.4 m free, "searched already this way").
6. s44: stall, then `doorway_D` (−0.1, 0.5), at closed B. s46: blocked, then `unexplored_3`
   (−0.4, 0.4), at B.
7. R11 also failed here.

**s02c/dynamic.** C opens at s3; ends 16.7 m away.
1. s6: walled at B, then `explore`. s15: stall, then `unexplored_1` (8.1, −3.0).
2. s23: stall, then `unexplored_2` (5.5, −4.7).
   - At s26 the drone is at (2.63, −7.44), 2.6 m from door C. The target is behind, so "toward" is on
     marker 0 and the drone turns around.
   - The detour then loops out to (12.07, −5.65) until `detour_too_long` at s36: 13 steps, dg 19.0 →
     23.2.
3. s43–45: walled at B (2 short moves). s46: `unexplored_1` (0.4, 2.1). s48: `doorway_L` (0.2, 8.3),
   a false doorway beside closed A.
4. s50: goal reported with no line of sight, then `goal_in_view` hand-back.
5. It ends on the A side at (1.67, 9.62). R11 also failed.

**s02va/final.** Door A open; ends 14.9 m away.
1. s3 at x = 14.9 (`XD×5`, 14 m from the divider) and s8 at (6.85, 2.57): false walled, both with
   12 m free.
2. s8: `unexplored_1` (8.1, 3.8). It holds for 13 steps: a loop via (2.7, −0.3) back to
   (10.46, 1.11), dg 19.0 → 22.5, ending `detour_too_long` at s21.
3. s31: walled at B, then `explore`. s36–42: three reached detours around B: `unexplored_1`
   (1.3, 1.3), then `unexplored_2` (3.0, 2.1), then (3.0, 3.0).
4. s48–49: the drone is in door A's mouth, (0.96, 9.02), with line of sight.
   - The standing detour (3.0, 3.0) is behind, so "toward" is on sharp right.
   - No single fan move clears the jamb: sharp left has 1.6 m free.
   - At s50 it hits the north wall and turns around; s51–54 take it back south.
5. s55: `detour_too_long`, plus a goal report with no line of sight. Then walled, then `doorway_D`
   (3.4, 3.8), a false doorway. The menu at s55 and s58 did list an item within 3 m of door A; it
   was not picked.
6. R11: 34 steps. An early sharp right at s4 toward a doorway flagged on the right put it on the A
   side; `doorway_J` beyond door A was picked at s23, and it went through at s24.

**s02vc/dynamic.** C opens in view at s3; ends 12.5 m away.
1. s0–3: goal centred. s12: walled at B, then `explore`; s13–15: three short moves against the
   divider.
2. s15: `unexplored_1` (2.1, 3.0), on the A side. s17–22: side-toward takes the drone to the A-side
   wall at (5.12, 11.09).
3. Five doorway picks, all false: `doorway_K` (0.5, 6.5) at s27, `doorway_F` (4.6, 3.4) at s34,
   `doorway_H` (0.9, −0.2) at s52, and `doorway_G` (2.3, 1.2) at s54 and s59.
4. Overall: 44 steps on the A side, 0 on the C side. Door C was never within 8 m, and never on a
   menu. R11 also failed.

**s03/final.** Door L closed from step 0; ends 27.3 m away.
1. s4 at the stem mouth, (14.21, 0.44): TA.
   - "Toward" was on straight, noted "searched already this way", with 9.2 m free down the stem.
   - Reason: "all forward paths … 'searched already this way' … the only remaining option is to turn
     around".
2. s5–51 in the lobby.
   - Stall at s9 (explore), walled at s13 (`unexplored_1`), stall at s29 (`unexplored_3`), walled at
     s38, s42 and s48 against lobby walls.
   - 54 of 60 steps were at x ≥ 15.
3. s52–53: back into the stem to (12.35, −1.0). s54: TA again against straight (7.4 m free),
   `[X X n X X]`.
4. It never reached the crossbar.
5. R11: 39 steps, straight down the stem with "new ground" on every step.

**s03/dynamic.** Ends 19.4 m away.
1. s4: TA against straight at the stem mouth (9.2 m free). s5–22 in the lobby.
2. s23–25: down the stem to x = 8.54. s26: TA against straight (3.5 m free to the crossbar).
3. s33–34: to the crossbar (6.67, 0.23). s35: TA against slight left (2.5 m free).
4. s41: walled at the divider face (6.54, 1.19).
   - Every menu item is 8–18 m behind and "farther", so q03 answers `explore`.
   - The crossbar arms and tines were not on the menu: never in the field of view, so not known
     floor.
5. s48–50: two more TAs. s52: goal reported with no line of sight, then hand-back. s58: walled, then
   `unexplored_1` (5.5, −2.1).
6. It never entered a tine (min x 6.28). R11 also failed, after entering the dead-end tine.

### R15N (a26)

**s02a/final.** A open; ends 13.5 m away.
1. s6: walled at B, then `explore`. s10: `unexplored_2` (0.4, 0.4), the divider face at B.
2. s10–22: down the C side to (2.42, −8.25). `detour_too_long` at s23.
3. s29–34: ping-pong at (1.33, −4.88), with TAs at s29, s31 and s33 and walled-to-explore twice.
4. s38, s43, s47: walled, then frontier cells on the divider face, at (0.4, −4.7), (−0.4, −4.7) and
   (−0.4, −1.3).
5. s48–50: the drone reaches y = 3.1, 5.9 m from door A; s50 TA (the toward move was blocked,
   0.5 m). s51–59: back to the C side.
6. Overall: 41 C-side steps, 6 A-side. The open door was never on a menu. R11 succeeded (26 steps,
   see R15 s02a/final).

**s02a/dynamic.** A opens at s3; ends 6.9 m away.
1. s2 at x = 8.6 with the goal in view: false walled (`X X XD X XD`, 12 m free), then `explore` for 3
   steps.
2. s7–52 at B and on the C side.
   - s17 → `unexplored_1` (1.3, −7.2). Reached at s19, then `explore`: 4 straight moves east to
     (9.31, −5.54), dg 14 → 22.
   - s38 and s43: `doorway_E` (−1.0, −0.1), beyond closed B.
   - s42: goal reported with no line of sight, then hand-back.
3. s52: another report with no line of sight (far_r) hands back `unexplored_3`. The drone then went
   north, through door A at s56, and flew at the goal; it ran out of steps at 6.9 m.
4. R11 also failed.

**s02c/dynamic.** C opens at s3; ends 13.4 m away.
1. s9: `unexplored_1` (3.0, 3.0), on the A side.
2. Walled-to-explore at s12, s16, s23, s30 and s50: 21 explore steps in all. s21: `doorway_C`
   (1.0, 4.8), false.
3. s40, s54, s58: frontier cells on the divider face at (0.4, 3.8) and (0.4, 4.7). s41–43: three TAs
   in a row.
4. Overall: 46 A-side steps, 0 C-side. R11 also failed.

**s02va/dynamic.** A opens in view at s3; ends 16.7 m away.
1. s9: false walled at (4.86, 1.39), 6.2 m free, then `unexplored_1` (6.4, 3.0), "2 m farther".
   s10–16: seven consecutive sharp rights orbiting it.
2. s27: at (0.70, 6.29), 2.7 m from door A, walled. q03 picks `unexplored_2` (−0.4, 0.4), worded
   "about 3 m nearer the goal": the divider face at closed B.
   - s28: goal reported with no line of sight hands it back.
   - s29: re-picked, and the drone drives south to B (s32).
3. s32–38: six sharp rights to the C side. Then `doorway_L` (0.6, −7.8), at closed C, at s41;
   `unexplored_3` (−0.4, −7.2) at s44; `unexplored_2` (−0.4, −7.2) at s54.
4. R11 also failed; R15 solved this cell in 59 steps.

**s02vc/final.** C open; ends 15.1 m away.
1. s2: false walled at x = 16.6 (12 m free), then `explore`, with TAs at s2 and s4.
2. s15: walled at B, then `unexplored_1` (4.7, 1.3), behind. s21: `unexplored_1` (3.0, 2.1).
3. s27: walled at (1.44, −3.43), then `doorway_F` (1.1, −6.0), false. s28–33: loop east and south.
4. s34: at (1.09, −8.27), in the mouth of open door C.
   - Straight is 12.0 m free and 20° off the goal.
   - The target `doorway_F` lies behind-right, so "toward" is on sharp right (1.1 m free).
   - The navigator turns around.
5. s37–42: loop east to (7.57, −6.52). s43: `doorway_F` re-picked. s48 and s56: `unexplored_2`
   behind.
6. R11 also failed.

**s03/initial.** Both exits open; ends 8.1 m away.
1. s1 at (19.3, 0.24): TA against straight (`n×5`, "searched already this way", 12 m free).
2. s1–36: in the lobby, 35 steps.
   - s8–10: three sharp rights. s11: walled, then `explore`.
   - s16: `unexplored_2` (19.1, −3.0), behind, held for 13 steps.
   - s32–36: `doorway_B` (13.7, −0.4), false.
3. s37–51: down the stem and into tine L to (−4.76, −3.70).
4. s52, 1.2 m from the open L exit: TA.
   - "Toward" was on straight: 1.3 m free, hugging the divider-side wall.
   - Slight left was 12 m free through the door.
5. s56: stall, then `back_to_step_54`. It is heading back to the door when the steps run out.
6. R11 succeeded in 39 steps.

**s03/final.** L closed; ends 7.2 m away.
1. s7–44: 29 steps at the crossbar.
   - TAs against toward at s7, s19, s28, s32.
   - Walled-to-explore at s35 and s40.
   - `unexplored_2` (8.9, 2.1), behind, held 13 steps to `detour_too_long` at s30.
2. s45–50: into tine L, the one with the closed door.
3. s54–59: at the closed exit (−5.7, −3.7). q03 picks `doorway_G` (−5.7, −3.5), the closed door, at
   s54, s55 and s57, with `unexplored_1` (−5.5, −5.5) in between. It never backed out.
4. R11 succeeded (39 steps, R tine).

**s03/dynamic.** Ends 19.5 m away.
1. s4: TA against straight at the stem mouth (9.2 m free). s5–27: lobby, with
   `back_to_step_6` held for 10 steps.
2. s28–32: down the stem.
3. s33–59: at the crossbar.
   - Walled-to-explore at s33 and s39.
   - s45: `unexplored_3` (9.8, 2.1), behind, held 13 steps.
   - 23 crossbar steps in all, and only 2 steps west of x = 5. It never entered a tine.
4. R11 also failed.

---

## Q2. Failure modes, ranked

"P" means primary: the run plausibly succeeds without it. "c" means contributing. Steps are spans
read from the chains above; a step is counted under one mode only.

| # | Mode | Failed runs P (c) R15 / R15N | Steps (P spans) | Mechanism |
|---|---|---|---|---|
| A | TA against "toward" on "searched already this way" | 3 (2) / 2 (2) | ≈ 193 (+ ≈ 52 shared with H) | a17's coverage note read as "explored, dead end"; s03 stem and lobby, s01 at line of sight |
| B | No along-wall search at a blocking wall (s02) | 4 (1) / 3 (1) | ≈ 368 | goal pull back to closed B, wrong side 41–48 steps, explore on walled |
| C | Detours that do not pay (wall-face frontiers, false doorways, loops away) | 1 (8) / 1 (7) | detour steps: 231 / 189 | reachable but useless; net −1.8 m / −29.8 m over all spans |
| D | Standing detour turns the drone away at an open door | 1 (1) / 1 | 12 + 26 | target behind while the way to the goal is open |
| H | T-junction: no 90° turn, unseen arms not on menu (s03 crossbar) | 1 / 1 (1) | shared with A (≈ 52) | walled → all items "farther" → explore |
| I | Dead end: closed exit picked as a doorway, no back-out | – / 1 | 6–10 | |
| E | Orbit of a near target abeam (side toward) | – (1) / – (1) | 50 / 68 steps in ≥3 same sharp turns | the known s01 case; detour_stall targets it |
| F | False "walled" from a far wall read blocked_near | – (3) / – (3) | 13/61, 11/72 walled calls; each → 3 steps without a target | |
| G | Goal reported with no line of sight | – (2) / – (2) | 14 / 18 sightings, 3 / 4 hand-backs | one in R15N s02a/dyn helped |
| J | Through the door with too few steps left | – / 1 | – | R15N s02a/dyn, 6.9 m at the end |

By runs: B (7 primary) > A (5) > C (2 primary, 15 contributing) > D (2) ≈ H (2 with A) > I (1).

By steps: B ≈ 368 > A ≈ 193–245 > C 420 detour steps (overlaps B) > D 38 > I.

The two top modes, A and B, share one root: the agent has no move that keeps it beside a blocking
wall. Reached detours hand straight back to the goal, which points into the wall, and "searched"
notes turn the drone round.

**Mechanical step accounting** (failed runs, non-overlapping by target; TA and B-proximity counted
inside):

| | R15 failed (9 runs, 540 steps) | R15N failed (8, 480) | R11 failed (7, 420) |
|---|---|---|---|
| target = goal | 255 | 222 | 125 |
| detour, drone's side, free floor | 178 | 88 | 12 |
| detour at a wall face, inside solid, or beyond | 53 | 101 | 283 |
| no target (explore) | 54 | 69 | 0 |
| turn-arounds | 108 | 110 | 75 |
| TA with "toward" on a forward move | 40 | 35 | 3 |
| s02, within 2.5 m of closed B (x < 3.5, \|y\| < 2.5) | 72 | 76 | 93 |

**Detour picks** (all 36 runs per round):

| | R11 | R15 | R15N |
|---|---|---|---|
| q03 calls / `explore` answers | 38 / 0 | 96 / 32 | 97 / 34 |
| walled calls answered `explore` | 0 | 28 / 61 | 29 / 72 |
| target beyond or inside a wall (truth) | 34 / 37 (by line) | 4 / 64 | 11 / 63 |
| target on the divider face (x ∈ [−0.5, 0.5]) | – | 12 | 14 |
| straight line to the target crosses a wall | 34 / 38 | 18 / 64 | 25 / 63 |
| hand-backs: reached / closed / goal_in_view / too_long | 1 / 0 / 14 / 18 | 36 / 10 / 7 / 5 | 42 / 7 / 6 / 3 |
| doorway items at a truly open door | 1 / 1 listed | 4 / 54 | 5 / 52 |
| doorway picks / real | 1 / – | 18 / 1 | 17 / 1 |

R15's README predicted ≤ 5 picks behind or inside a wall. R15 met it at 4; R15N did not, at 11.
Counting the divider face, the figures are 16 and 25.

---

## Q3. Do the queued changes address these modes?

| Mode | c01 confirmer (R16K) | q07 (R17) | detour_stall (R18) |
|---|---|---|---|
| A, TA on "searched" | no | no (q07 is the strategist; the TA is the navigator's) | no |
| B, no along-wall search | no | partly at best: rule 2 ("most unexplored ground first") still lists only known-floor frontiers; no along-wall item exists | no; a handed-back detour returns the goal, which points at the same wall |
| C, detours that don't pay | no | partly: "nearer is straight-line only" would argue against R15N s02va/dyn s27; 20/64 and 17/63 picks were worded nearer. Rule 1 ("doorway first") works against this mode: doorway items are real 4/54 and 5/52 | partly: 68 (R15) and 43 (R15N) stalled-on-detour steps (`eval/r18_stalled_steps.py`); cuts the 13-step loops in R15 s02va/final s8–21 and s02c/dyn s23–35, and the blacklist stops re-picks (R15N s02vc/final `doorway_F` s27 and s43) |
| D, detour at the open door | no | no | no (fewer than 4 moves at the door) |
| H, T-junction | no | no | no |
| I, dead end | no | yes, rule 3 ("blocked on several sides → go back") fits R15N s03/final s54–59, but rule 1 pulls toward `doorway_G`, the closed door | partly: the blacklist would drop `doorway_G` if it stalled |
| E, orbit | no | no | yes: built for it (R15 s01/final s12–24; R15N s02va/dyn s10–16) |
| F, false walled | no | no | no |
| G, goal reported with no line of sight | yes; small: 14 and 18 such reports, 3 and 4 hand-backs (R11: 26 and 10) | – | – |

On q07 specifically: R17's README predicts "doorway picks when one is listed ≥ 40%". On R15's
menus that means 44 menus with a doorway, of which 3 list a real one. Unless the doorway list is
cleaned first (Q4 change 3), q07 will mostly send the drone to false doorways at closed B and C. A
cheap check before R17 flies is `eval/r17_strategist_probe.py run` on R15/R15N's 193 recorded calls
(text only, so no frames are needed), scoring each doorway pick against the geometry.

---

## Q4. Recommended next changes

### 1. Navigator: "searched already this way" stops turning the drone round

**Change.** A prompt change (p17 = p16 with one definition and one rule):
- Definition: '"searched already this way": the camera has looked that way; the drone has not flown
  it. It is not a dead end.'
- Rule: "Turn around only when 'toward your target' is on marker 0, or when every forward move is
  blocked before, stopped short or wall close."

The mechanical alternative is in the projector: for a known-goal agent, write "new ground" for an
unvisited landing, as R11 did, and keep a17's note for the search agents only.

**Evidence.**
- Steps with no forward "new ground": 15% (R11), 42% (R15), 40% (R15N).
- Turn-around rate on those steps: 39–42%, against 1–2% otherwise.
- Turn-arounds against forward "toward": 3 (R11), 50 (R15), 50 (R15N), with true free floor > 2.2 m
  in 44 and 35 of them.
- This mode is primary in all 5 s03 failures and in R15 s01/dynamic (Q1). p16 did not move it (50 →
  50).

**Offline tests.**
- No model: replay `spatial.project` with the note dropped over the recorded manifests (the R12/R15
  smoke harness). Count steps with no forward "new ground": 42% should fall to about 15%.
- Live, text plus frame, as in R15N's probe (`eval/r15_nav_probe.py`): re-ask p16 and p17 on three
  sets.
  - **Set 1:** the 100 recorded TA-against-toward steps, 79 of them clear in truth. Gate: ≥ 60% now
    take the toward move.
  - **Set 2:** the 21 whose toward move was truly blocked (≤ 2.2 m). Gate: no more than a third take
    the toward move.
  - **Set 3:** about 150 steps where toward was followed. Gate: ≥ 95% unchanged.

### 2. Along-the-wall detours

**Change.** Code builds two items on every walled or blocked q03 call; the strategist chooses
between them.
- **The items.** "Along the wall to your left" and "… to your right".
  - Each is a point up to 5 m along the blocking wall: perpendicular to the blocked heading, 1.2 m
    off it, on floor the map does not call wall, with a clear straight segment.
  - It is worded with how far that way has been followed already.
  - When one way ends at a wall, the item becomes "the other way along this wall".
- **Strategist wording (q08).** "A wall stands between the drone and the goal; its way round is
  along it. Follow it one way to its end before the other; an opening seen along it comes first."
- **Natural hand-back.** End the along-wall detour when the way toward the goal opens: `goal_way`
  open with the goal within the fan. This also covers mode D, since R15 s02va/final s49 and R15N
  s02vc/final s34 stood at an open way.

**Evidence.**
- Mode B is primary in 7 of the 17 failures and took about 368 steps.
- 148 failed-run steps were within 2.5 m of closed B.
- Walled calls ended in `explore` 28/61 and 29/72 times.
- R11's wins in s01 final/dynamic, s02a final and s03 final all came from a long-held goal-side
  phantom that made the drone slide along the wall:
  - R11 spans averaged 9.9 steps.
  - R15 target spans averaged 4.2 (267/64), mostly `detour_reached` within 3–5 steps.
- The same item fits all three sites:
  - **s02 divider:** door A or C is 9 m from B, about 6 moves; the wrong way first costs about 13
    more.
  - **s01 cube:** the side gaps begin 4 m off the centre line.
  - **s03 crossbar:** the tines are 3.5–6.5 m to either side, out of view, which is why R15 s03/dyn
    s41 had only items "behind".

**Offline tests.**
1. No model: build the two items at each of the recorded walled and blocked calls (spatial.rebuild
   of the records up to that step). Check with `geo.py` that each lies on free floor with a clear
   line. Today 18/64 and 25/63 picks cross a wall.
2. No model: on `geo.py`, from the first walled call of each failed s02 run, count the sweep moves
   to the open-door gap, the wrong way first. All should be under 25.
3. `eval/r17_strategist_probe.py` with the two items appended to the recorded menus: how often q08
   picks along-wall over wall-face frontiers and `explore`.

### 3. Doorway confirmer (d01), before q07's "doorway first" flies

**Change.** A second VLM look, like c01. When an opening is about to be listed (its second
sighting, `doorway_min_seen` 2), ask on the clean frame whether that strip shows:
- an open doorway with floor visible beyond it,
- a closed door or door leaf, or
- no doorway.

Only "open" lists the opening; "closed" marks it closed.

**Evidence.**
- Real openings on menus: 4/54 (R15) and 5/52 (R15N).
- Doorway picks: 18 and 17, with 1 real each.
- 35 of 52 s02 doorway items in R15 lay more than 2.5 m from any door.
- The closed L exit door was picked 3 times in R15N s03/final's dead end.
- In s02 success runs, the picks that led through a door were ones near the real door.

**Offline test.** `eval/r16_confirm_probe.py`, adapted. Run d01 on the clean frame at each listed
opening's first and second sighting (the `spatial.openings` records give the label and step), about
110 frames on the flight host. Score each against `geo.py`: within 2.5 m of a door open at that
step. Gate: keep ≥ 7 of 9 real, refuse ≥ 80% of false.

### Smaller mechanical items (not in the top 3)

- **False walled from a far wall** (13/61 and 11/72 calls; for example R15N s02a/dyn s2 with the
  goal in view): require a stop wall or `blocked_near` on two looks before asking.
- **Orbit:** already covered by detour_stall.

---

## Q5. Did p16 help?

**Behaviour: yes, on what it targets.** Toward followed, by kind:

| | R11 (p14) | R15 (p14) | R15N (p16) |
|---|---|---|---|
| toward on a forward move, within 55° of the target | 287/407 (71%) | 290/444 (65%) | 359/449 (80%) |
| side toward (a17 fallback) | – | 110/191 (58%) | 93/147 (63%) |
| toward on marker 0 | 43/228 (19%) | 46/75 (61%) | 39/57 (68%) |
| TA with toward on a forward move | 3 | 50 | 50 |
| turn-arounds / steps | 96/706 | 140/827 | 142/786 |
| collisions (metrics) | 58 | 35 | 26 |

- The forward-toward rise is large: z ≈ 4.9 at the step level, though steps within a run are not
  independent.
- The marker-0 change is within noise (n = 75 and 57).
- p16 was written for marker-0 toward. a17's projector puts toward on marker 0 rarely: 75 and 57
  offers, against 228 in R11. So the targeted behaviour had little reach.
- p16 did not touch the dominant turn-around mode A.

**Outcome: +1 is noise.**
- R15N won 5 cells R15 lost: s01 final, s01 dynamic, s02c final, s02va final, s02vc dynamic.
- R15 won 4 cells R15N lost: s03 initial, s02vc final, s02a dynamic, s02va dynamic.
- The two runs diverge at steps 0–10 in every differing cell, so each cell is a different
  trajectory. 5 against 4 discordant cells gives a sign test p ≈ 1.
- One win plausibly comes from p16's behaviour: R15N s01/dynamic s27 took a sharp left with
  "toward; new ground" past the cube. R15 s01/dynamic s17 turned around at the same kind of spot,
  but its note said "searched".

p16 does no visible harm: turn-arounds are the same and collisions fewer. The queued a28–a34 all use
p14. Mode A's fix (Q4 change 1) is better made on top of p16 than on p14.

---

## Appendix: definitions

- **Turn-around against toward:** the pick is marker 0 while "toward your target" is on a visible
  forward action. "Clear" means the `geo.ray` free distance along that action's heading exceeds
  2.2 m.
- **No forward new ground:** no forward action's notes contain "new ground".
- **Detour span:** from a q03 pick to the next q03 call or change of target. Gain is the drop in true
  distance to the goal over the span.
- **Wall face:** a target with x ∈ [−0.5, 0.5] on s02. "Beyond": x < −0.5 on s02, or x < −6 on s03.
  "Inside solid": `geo` not free.
- **Doorway item real:** an opening on a menu within 2.5 m of a door that is open at that step.
- **Distances to doors:** measured to the door centre (0.6, ±9).
