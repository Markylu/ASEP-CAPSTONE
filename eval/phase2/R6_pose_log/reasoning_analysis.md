# R6 (a08) reasoning analysis: ground-truth pose in the log, no sighting line

Written by Claude from all 894 R6 decisions. R5's 810 decisions were run through the same scripts
for comparison. The scripts work on the poses recorded in each decision's manifest:
- a forward move counts as **blocked** if the drone moved < 0.85 m (half a step);
- a step counts as **stationary** if the drone moved < 0.85 m, turn-arounds included.

Quotes are trimmed; step numbers are the decision's step.

## 0. Headline

**The pose log ended the spin.** It did not make the model use its position.
- The model quotes its coordinates and heading in 63–76% of reasons (R5 10–13%).
- It almost never compares them. After a blocked move, 65% of reasons still claim progress.
- With the sighting line gone, nothing in the log says where the goal was. Three runs saw the
  goal, lost it, and never found it again.
- The heading numbers produced a new error: arithmetic that turns the drone away from a goal it
  can see.

## 1. The spin is gone

| | R5 `initial` / `final` / `dynamic` | R6 |
|---|---|---|
| turn-around pick | 7% / 41% / 70% | **5% / 7% / 10%** |
| two turn-arounds in a row | 1% / 26% / 58% | **0% / 0% / 2%** |
| stationary steps, all runs in the arm | 9 / 166 / 249 | 27 / 70 / 94 |
| path per `dynamic` run | 17–41 m | **61–84 m** |
| revisit | 2% / 41% / 57% | 7% / 19% / 25% |
| `spin_failure` | 9 of 10 failures | **1 of 13** (s01 `dynamic`, 5 in a row) |

- s02a `dynamic` was R5's worst loop (48 turn-arounds, 36 in a row). In R6 it turns around 5
  times, never twice in a row, and flies 81 m.
- Two `final` cells that R5 lost to the loop now succeed:
  - s02a `final`, 18 steps, 0 collisions;
  - s02vc `final`, 54 steps. It stood in place for steps 14–31, then left.

## 2. Failure A: it reads the pose but does not compare it

The log says "moved 0.0 m" under a move into a wall. The next reason rarely notices.

| After a blocked forward move | R5 | R6 |
|---|---|---|
| blocked forward moves | 36 | **123** |
| same pick again | 15 (42%) | 52 (42%) |
| reason notes it did not move | 7 (19%) | 38 (31%) |
| reason claims progress ("has been moving forward", "moving steadily") | 20 (56%) | **80 (65%)** |

- s01 `dynamic`, steps 29–37, stuck at (23.5, 11.5): "The drone is currently at position (23.5,
  11.6) facing 41 degrees … Given the pr[evious moves]…". It cites the same coordinates step after
  step and calls it progress.
- **s03, all three arms, identical:**
  - At step 8 it used the log well: "the last move (Step 7) did not advance the drone, indicating
    a possible wall", and it turned around.
  - From step 14 it pins at x = 15.2. It flies up and down a wall from y −11 to +11.5 and never
    gets further west.
  - 16 collisions, and "moving in a straight line along a corridor-like path" (step 20).
  - In R5 the same site succeeded on `initial` and `final` with the move log alone.
- **Collisions: 143** (R5 38). R5's failure was standing still. R6's is flying.

So the number reaches the reason as a quoted fact, not as a comparison. The model writes its
position down; it does not check it against the line above.

## 3. Failure B: arithmetic on the heading

96% of reasons cite a heading in degrees (855 / 894) (R5 dynamic 74%, initial 16%). The model now does
geometry with it, and mixes the map frame with the image frame.

- **Turn-around with the goal in view: 3 of 112** (R5 0 of 114). All three are heading
  arithmetic:
  - s02va / s02vc `initial`, step 12, goal right at 12.0 m: "the drone is currently facing 221
    degrees, which is toward the left side of the scene … turning around (0), which would
    reorient the drone to face 41 degrees (221 + 180) …". It turns around and never sees the goal
    again.
  - s02va `final`, step 45, goal right at 18.6 m: "(215 + 180 = 395 → 395 − 360 = 35)".
- **Compass words are right in 247 of 299 uses (83%).** Wrong examples:
  - "358 degrees, which is nearly due north" (s01 `dynamic`, step 31; it is east);
  - "85 degrees, which is roughly northeast" (probe and flight);
  - "330 degrees, which is toward the upper-left of the image" (an image direction given for a
    map heading).
- The heading is a map angle. The markers and the identifier are image-relative. The model
  translates between the two and gets it wrong.

## 4. Failure C: losing a goal it had seen

`a08` has no sighting line. Once the goal leaves the frame, the log holds nothing about it.

| Run | Seen | Then |
|---|---|---|
| s02va / s02vc `initial` | steps 0–12, from 32 m down to 12 m | step-12 turn-around (§3); never seen again; ends 34 m out |
| s02va `dynamic` | through the new door; steps 22–24, about 13 m (identifier left, right, left) | lost at step 25; never seen again; ends 16 m out (label: timeout) |

R5's sighting line caused the `dynamic` spin ("goal is behind, turn around"). It also kept the
direction of a goal that had just left the frame, and these three runs needed that. The probe
replayed only spin states, where the line did harm. It had no rows where a goal had just been
lost, where the line helps.

## 5. `dynamic`: moving, and still not through

- Every s02 run acknowledges the closed door by step 4. One exception: s02va names no closed
  door at all.
- Every s01/s02 run except s02va stays east of the dividing wall (min x 2.3–5.2) while flying
  61–84 m.
- The open door is not found by flying more. R1, the only round to win s02a `dynamic`, backed out
  to x = 20.9 and came round. R6 reaches x = 19.7 on s02a and does not turn it into a way round.
- s03 `dynamic` never reaches the trigger (`pre_change_failure`): it is the s03 run of §2.

## 6. What made the successes work

- **`initial` s01, s02a, s02c** (14 steps, identical): identifier ahead, straight flight, as in
  R5.
- **s02a `final`** (18 steps): it turns toward the open door early and keeps going. There is no
  loop for the log to break.
- **s02vc `final`** (54 steps): it stands in place for 17 steps (14–31), then flies out and down
  the open side. R5 stood still on 38 steps in this cell and never got through.

## 7. The probe against flight

| | Probe (one step, R5 states) | Flight |
|---|---|---|
| turn-around at a loop state | 6 / 40 (15%) | two in a row: 0–2% |
| turn-around with the goal in view | 0 / 20 | 3 / 112 |
| goal-placement replay | 0 / 40 | – |

- The probe predicted the loop's end correctly.
- It could not see that ending the loop costs collisions, or that the sighting line was holding
  up recovery after a goal is lost.
- Its "visible" control had no row of a goal off-centre near 12 m. That is the frame where the
  arithmetic struck.

## 8. Next-step options (one change each)

Each option is stated against `a08` or `a07`.

1. **Fly `a07` (pose log + sighting line).** It passed the probe as well (spin 17 / 40), and it
   keeps the line that would have recovered §4's three runs. Cheapest: it already exists, with
   its probe in hand.
   - Risk: R5's "goal behind, turn around" may come back in `dynamic`, as the probe's 42% at loop
     states hints.
2. **Give the outcome, not the raw pose.** Keep the position, but have code write the comparison
   the model skips: "did not move (blocked)" and "back at the place you were at step 14".
   - Targets §2's 80 progress claims and the s03 wall.
   - This is R5 analysis option 3, which the operator set aside for raw numbers.
3. **Drop the heading degrees, keep the position.** Or give the heading only as an image-relative
   change since the last step. Targets §3: three goal-in-view turn-arounds and the compass
   errors.
4. **Combine 2 and 3 on `a07`**, if the operator accepts two changes in one round, as in R5.
