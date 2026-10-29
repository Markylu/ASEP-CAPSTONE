# R19 / R19K: s02 final and dynamic failures

Written 2026-10-29 by a Claude subagent as a read-only analysis of the recorded `decisions.jsonl` of
R19 (`a35`) and R19K (`a36` = `a35` + `c01`). No model calls were made. Truth comes from R11's
`analysis/geo.py`. The scripts were throwaway, kept under `/tmp/s02a`. Alongside them ran
`eval/r21_along_probe.py items` and `eval/r22_floor_ends_probe.py` on both rounds.

**Count correction.** On s02 final and dynamic, R19 solved **1/8** (s02c/dynamic) and R19K solved
**3/8** (s02a/final, s02c/final, s02c/dynamic). That is **12 failures**, not 10. R19's "final 2,
dynamic 2" also counts s01 and s03.

**Conventions.**
- `dD` is the distance to the open door's centre (0, ±9).
- "Wrong side" means steps with x > 0.5 and |y| > 1.5 on the side of the closed door.
- "Mouth" means within 3 m of the open door, on the near side.
- "Divider" is the first step at x < 2.5.
- `sN` is the step.

## 1. Per-run table

| Run | End dg | At divider | Wrong side | Min dD | Primary mode | Chain (key steps) | R20 | R21 | R22 |
|---|---|---|---|---|---|---|---|---|---|
| R19 s02a/final | 2.2 | s6 | 0 | 1.6 | **K → J** | At door A's mouth s19 (dD 2.7); the toward move clips the inner jamb at s20. Detours `unexplored_2`, then `back_to_step_16` (wall face), pull it south s20–32. Real `doorway_E` (−0.2, 10.4) is picked at s44 and "closed" at s45 by an oblique look. Through at s52–53, about 1 step short. | no | plausible (1 step short; R21 changes the path from s6) | no |
| R19 s02a/dynamic | 16.6 | s6 | 34 | 6.9 | **B** | False walled at s2 (ignored). After `back_to_step_3`, side-toward sharp rights curve it down the C side. False doorways D/F on the C-side face; never above y = 1.7 after s4. | no | plausible (A-side item listed at s6) | no |
| R19 s02c/final | 18.6 | s6 | 31 | 5.2 | **B** | Explore at s6. A-side false `doorway_C` at s12. Reaches the closed A end (0.45, 10.0) at s36, then `unexplored_2` (1.3, −0.4) takes it back to B. On the C side only at s53–59. | no | plausible (C-side item at s6, s28, s44; "other way" after s36) | no |
| R19 s02va/final | 13.0 | s17 | 21 | 2.8 | **B (+C)** | B / C-side dither s18–45 (16 steps by B). At s53–55, 2.8 m from door A, a false `doorway_H` (0.5, 0.6) at closed B pulls it back. | partial (H may be refused) | partial: at s18 only the C side is listed (wrong first), late start | no |
| R19 s02va/dynamic | 14.2 | s11 | 0 | 1.7 | **K** | 20 steps within 3.5 m of door A (s24–38, s51–59). A through-door move exists on 2 of them. The toward move clips the inner jamb. Wall-face frontiers (−0.4, 8.1), (0.4, 7.2), (−0.4, 4.7) and the real `doorway_F` (−0.6, 10.4), closed at s46, churn it. | no | partial (A-side items lead along; crossing is luck) | no |
| R19 s02vc/final | 8.5 | s16 | 11 | 0.8 | **J** | False walled at x = 14.9 (s3); `back_to_step_14` at s16; false `doorway_H` at B s24–26; explore loop s37–45. Real `doorway_J` (0.8, −8.7) at s52 takes it through at s57, 3 steps from the end. | partial (H) | **risk**: q08 rule 4 takes an along item over `doorway_J` at s52 | no |
| R19 s02vc/dynamic | 16.2 | s11 | 31 | 4.6 | **B (+C)** | At s16 it is 4.6 m from door C. The detour `unexplored_1` (0.4, −0.4), at B, stalls, and side-toward circles it to the A side for 40 steps. | no | plausible (C-side item at s11, s14) | no |
| R19K s02a/dynamic | 14.6 | s6 | 33 | 6.9 | **B** | Side-toward sharp rights take it down the C side (s8–19). Explore and wall-face cells at closed C s20–46. Back to B at s56. | no | plausible (A-side item at s6) | no |
| R19K s02va/final | 13.0 | s11 | 22 | 0.9 | **K + D** | In door A's mouth s22–26 with line of sight at s23–25. The toward move goes 0.5 m into the jamb, then a turn-around. At s26 (0.54, 8.33), dD 0.9, a **stall** ask returns `back_to_step_20`. After that, C side. | no | partial (the stall call's only item ends at (0.0, 9.7), in the gap) | no |
| R19K s02va/dynamic | 14.2 | s20 | 35 | 4.3 | **F + B** | False walled at x = 16.6 and 14.9 with the goal in view (s2–3). `unexplored_1` (19.1, 0.4) sends it back east, 8 steps lost. Then the C side, s21–49. | no | partial: B yes, F no | no |
| R19K s02vc/final | 16.9 | s13 | 33 | 5.3 | **B (+C)** | False `doorway_H` at B three times (s15–17). The A side to the closed end (0.45, 9.6) s23–28, then A-side loops to the end. | partial | plausible (C-side item at s15–18, s33–52) | no |
| R19K s02vc/dynamic | 19.1 | s11 | 2 | 1.3 | **K** | 11 mouth steps. At s45 straight (open_far, doorway) ran through door C, but "toward" was sharp right into the jamb, and it was picked. The real `doorway_J` (−0.4, −9.5) was overshot south s47–49; `detour_stalled` at s52; `unexplored_2` took it away. | no | **no / risk**: mouth items at s46 run along or through the wall, none through the gap; q08 drops `doorway_J` | no |

Totals over the 12 failures:
- **Steps:** 253 wrong side, 142 within 2.5 m of closed B, 45 in the mouth (none on the inner side
  crossed), 143 turn-arounds.
- **Detour calls (122):** explore 45, unexplored 45, doorway 25 (4 at a real door), back 7.
- **Walled asks:** 90, of which 11 were false walled (> 3 m free toward the goal).

## 2. Failure modes

| Mode | Primary in | What happens |
|---|---|---|
| **B** wrong side / no along-wall search | 7 (R19 s02a/d, s02c/f, s02va/f, s02vc/d; R19K s02a/d, s02va/d, s02vc/f) | When the goal is behind, side-toward (sharp left or right) chooses the side by the sign of a ~180° bearing. Detours are wall-face cells at B or false doorways. |
| **K** new: cannot cross at the open door | 4 (R19 s02a/f→J, s02va/d; R19K s02va/f, s02vc/d) | The goal line from the inner side (between B and the door) clips the inner jamb. A sharp turn is 43.5° and a move 1.7 m, so a drone running parallel to the wall cannot turn square into the gap in one step. |
| D (stall / detour turns it away at the door) | with K in R19K s02va/f s26, R19K s02vc/d s52 | The stall ask and `detour_stalled` fire exactly where moves along the wall gain nothing toward the goal. |
| J through too late | 2 (R19 s02a/f, s02vc/f) | Early steps lost to F, backtracks and false B doorways. |
| F false walled far from the wall | contributing (R19K s02va/d primary with B) | 11 walled asks with more than 3 m free. |
| Real doorway closed on approach | R19 s02a/f s45, R19 s02va/d s46 | The estimate sits on the jamb (y = 10.4). A look along the wall sees floor end short, so `_close_openings` closes it. |

Mode A (turn-around on "searched") is not a factor on s02:
- There were 24 turn-arounds against a forward "toward" move across the 12 failures.
- Most of them were the side-toward circling away from the wall.

**K in numbers.** All s02 final and dynamic runs of R15, R15N, R16K, R17, R17K, R19 and R19K have
268 steps within 4 m of the open door, on the near side.
- The straight line to the goal passes through the gap on **5/202 inner-side steps (2%)** and on
  **39/66 outer-side steps (59%)** (door to corner).
- A forward move geometrically through the door exists on only 74/268 steps. It was taken on 38.
  Of the 36 missed:
  - "toward" was on the through move 9 times;
  - the perceiver said open doorway on its strip 11 times.

## 3. The successes

R19 has 1 success and R19K has 3. Every crossing came from the outer side, or from a doorway target
placed beyond the wall:

- **R19 s02c/dynamic.** `doorway_E` (0.5, −8.3) at s23 drew the drone to (3.84, −9.32), outer side.
  The goal diagonal from (2.63, −9.0) and (0.95, −9.29) passed through at s32–33.
- **R19K s02a/final.** It overshot north to the corner (2.05, 11.24) at s37 and turned around.
  "Toward" from (1.28, 9.73) went through at s39–40 (line of sight; c01 kept the goal reports).
- **R19K s02c/final.** At (3.72, −11.05), outer side, 3.7 m off the wall, at s48: line of sight, and
  the goal diagonal went straight through at s49–51.
- **R19K s02c/dynamic.** `doorway_E` (−0.8, −9.7), an opening placed *beyond* the door, picked at s13;
  through at s15.

In all four the crossing came from luck (an overshoot or a far-placed doorway). Nothing the agent
does lines up a crossing on purpose.

## 4. Coverage by R20–R22

**R20 (`d01`).**
- It removes false doorway items: in the R15 probe it refused 61%. That helps only where a false
  doorway pulled the drone off (R19 s02va/f s55, R19 s02vc/f s24, R19K s02vc/f s15–17).
- It fixes no run outright: 25 doorway picks in the failures, 4 real.
- **Two side effects:**
  - The navigator tag `doorway (seen now)` is written for any truthy lane doorway
    (`spatial.project`, `if lane.get("doorway")`). Strips the perceiver itself calls `closed` are
    therefore tagged as doorways: 362 of 1188 tags in R19/R19K. `d01`'s `closed` verdicts (118 of
    its 221 refusals in the R15 probe) keep the tag too.
  - A truly open door is still closed by an oblique look.

**R21 (along items + `q08`).**
- `r21_along_probe items` on R19/R19K: 101/97 calls; at the divider the items follow the divider
  90–93% of the time; 49% lead toward the open door; ends are clear in truth 72%/68%.
- At the first divider call of all 7 B runs, an item toward the open door was listed. The other side
  was listed too in 6 of them, so the side is a coin flip, and following to the end costs about 25
  steps when wrong. **B is plausibly fixed in 5–6 of 7**; tight for the va/vc runs, which reach the
  divider at s11–20.
- **K is not addressed.**
  - An along leg runs parallel to the wall. `along_way_open` needs the goal within 60° of the
    heading, about 125° off when running along the divider.
  - It crosses only if the leg ends on the outer side, where 59% of goal lines pass.
  - At the mouth, the items run along the wall or through solid wall, none through the gap (R19K
    s02vc/d s46).
- **Regression risk.** q08 rule 4 ("doorway … only when no along item is listed") would replace the
  doorway picks behind 2 of the 5 crossings in these rounds: R19 s02vc/f s52 `doorway_J`, and R19K
  s02c/d s13 `doorway_E`, a success. Along items were listed at both calls.

**R22 (`a17b`).**
- `r22_floor_ends_probe` on R19/R19K: toward + searched 356 → 96, and no-forward-new 40% → 22%.
- In the 12 s02 failures, 18 of 24 turn-arounds against "toward" would read "new ground". None is
  primary.
- It also lists along items on a few calls that were empty with `a17`. No s02 run is plausibly fixed
  by R22 alone.

**Unfixed after R22.**
- **K**: R19 s02va/d, R19K s02va/f (partly), R19K s02vc/d, and the late crossings in R19 s02a/f and
  R19 s02vc/f.
- The **stall / detour hand-back at the door**.
- **F**: false walled with the goal in view at x ≥ 8.
- **q08 versus confirmed doorways.**

## 5. Proposals for R23 (ranked)

### 1. Through-the-doorway detour (code geometry, VLM door)

**Change.**
- When `d01` has confirmed an opening twice, intersect its strip rays with the axis of the wall that
  blocked the drone (`planner.wall_axis`). That gives the gap's position on the wall, not 5 m down
  the ray.
- Offer `through_<label>` first on the detour menu. It is two waypoints: 1.5 m in front of the gap
  on the wall normal, then 2 m beyond.
- It hands back to the goal once a trail segment crosses the wall line. It is not closed by an
  oblique look.
- `q09` = `q08` with rule 4 replaced: "an opening confirmed in this wall comes first; then along the
  wall".

**Evidence.**
- K is primary in 4 of 12 failures, plus 2 late crossings.
- Inner-side goal lines pass the gap 5/202 times.
- All 4 successes crossed from the outer side or from a doorway placed beyond the wall.
- Real doorway estimates on the jamb were closed on approach twice.
- On the R15 `d01` answers, an `open` strip ray meets the divider within 1.2 m of an open door 43/87
  times (within 10 m), against 1/57 for `closed` and 1/18 for `none`. Median error is about 1.0 m.

**Offline gate (no model).** Replay the R15 `d01` answers through `spatial.rebuild`, then do the same
on R20 once flown.
- Of the `through` items built from two confirmed sightings, at least 70% have the gap within
  1.2 m of an open door.
- For those, the two-segment path is clear in `geo` at least 80% of the time.
- On the 202 inner-side near-door steps, an item exists at least 50% of the time.

### 2. Doorway wording to the navigator (prompt and tag fix)

**Change.**
- Tag `open doorway (seen now)` only for `doorway == "open"` after `d01`; tag `closed door` for
  closed strips.
- `p18` adds one line: "A move through an open doorway in the wall between you and the goal goes
  first, straight through; 'toward your target' cuts across the door frame there."

**Evidence.**
- 362/1188 doorway tags in R19/R19K sat on strips the perceiver called closed.
- 36 through-door moves were missed near the door (R19/R19K 10/20). 11 had an open doorway on the
  strip.
- R19K s02vc/d s45: the drone took toward (sharp right) into the jamb when straight ran through door C.

**Offline gate (live probe on recorded frames, like `r19_nav_probe`).**
- p17 against p18 on the 74 near-door steps where a through move exists: taken at least 70% (now
  38/74).
- About 150 steps away from any open door that carry a doorway tag: the doorway move taken at most
  the baseline plus 5 points.
- No-model count of tags removed by the fix.

(Not ranked: suppress the stall ask and `detour_stalled` within 2 m of a confirmed opening. That is
R19K s02va/f s26 and R19K s02vc/d s52, and proposal 1's hand-back largely covers it.)
