# R30 Code route planner (A* over the memory) under a49: summary

**14/18, equal to R25D's 14. The total holds and gains nothing; `a66` is not better than
`a49`, and not worse.** R30 (`a66`) against R25D (`a49`), the best round so far:
- `initial`: 6/6 (R25D 6/6). s03 took 58 steps (R25D 50), 37 of them in the lobby.
- `final`: **4/6** (R25D 3/6). It won s02c and s03 and lost s02vc.
- `dynamic`: 4/6 (R25D 5/6). It lost s02a and s03 (R25D lost s03 too).

What changed:
- **The planner ran as built.** A route on 100% of steps (`fallback: none`), stall rule on 3–7
  steps per long run, walls missed 18.5% and phantom 11.1% in flight (R25D 17.3% / 12.7%),
  longest turn-around streak 3.
- **The navigator followed the route most of the time.** "Toward your target" taken on 82% of
  forward offers and 70% of marker-0 offers. The marker-0 refusals cost 37 lobby steps in s03
  `initial`; the a70 fix (shakedown, 77/77) is not in `a66`.
- **s03 2/3 (R25D 1/3).** In `final` d01 read the left tine's door `closed` from the crossbar at
  s15, the route went right, 0 steps in the shut tine, goal at s28: the case the planner was
  built for, taken. In `dynamic` it entered the right tine, read the door `closed` at s24 and spent
  31 steps there as the route alternated between the shut door and the way out
  ([labels.csv](labels.csv): `replan_failure`): the same case, lost.
- **s02 9/12 (R25D 10/12).** Three `replan_failure`s at the divider without crossing: s02a
  `dynamic` (a nose-on read of the newly shut door B became a firm wall and the route went the
  wrong side, then came back to door A's position and did not cross), s02vc `final` (doors read
  `closed` both sides, the route chose the wrong side for 48 steps), s02va `final` (the
  family-hard cell, lost in both rounds). The nine others crossed the open door's gap, five of
  them on the route's "toward your target", one on a navigator pick the route did not carry.
- **Luck or mechanism** (README, cell by cell): 8 of the 14 are baseline cells solved in both
  rounds at the same steps; 4 are the planner's (two resting on an early perception read or
  the step budget); 2 are the draw's (s03 `initial` at 58 of 60, s02c `dynamic` crossed by the
  navigator against the route). Against R25D the planner gained s02c `final` and s03 `final` and
  lost s02a `dynamic` and s02vc `final`. The step-0 perceiver read differs from R25D's at the same
  pose and frame in 16 of 18 cells, on a lane alone on `:8004`: every run is a fresh draw from
  step 0, batching or not. On the `a17b` family's 11.3 ± 1.4, 14 is R25D's draw again.

Why it did not fly as registered: the offline probe gate failed (README, Probe gate), the
operator made the on-policy shakedown the gate, and none of seven versions (a63, a64, a66, a67,
a68, a70, a71; 42 unscored `dynamic` runs) met its s03 shut-tine check. Each planner-side fix
moved s03's failure between three perceiver limits: phantom `open` doorways in s02's divider,
nose-on `no_floor` reads into a 3 m corridor, the shut tine's side walls. The operator flew
R30 on `a66`, the best measured (4/6), against that rule. What the shakedown settled: the
navigator leak is closed by a70's sentence and critic, and an obedient navigator then follows
the route into phantom doors (a70 2/6, a71 3/6); the next lever is the perceiver's doorway and
corridor reads.

**Not citable.** Agent `a66` (`de7f23d07186`): navigator `p17` (`cb3578251cfe`), perceiver `g05`
(`133ed83db46b`), door confirmer `d01` (`95c80a5ef984`), route planner `planner.pathfind` with
`agent.PATHFINDER_A65` (local mobility), memory `a17f` (door walls, suspects, free wins, near
walls from the side strips, firm walls); no strategist, no critic; `Qwen3-VL-30B-A3B`, remote
profile, temperature 0.
- Host: sctsvr6, one lane (`~/r30_shake`, `~/round_lane.sh 1 1`), alone on `:8004` (R25D: four
  lanes beside R25; R29N/R29S, the host-setting rounds, are unflown).
- Flown at `2f9c171` on 2026-11-03, 22:46–23:51 UTC. **18/18 valid.** Frames stay on the host.
- Labels: Claude review, not yet confirmed by the operator.
- Probe gate: failed as registered; shakedown gate not met; flown on the operator's
  instruction ([README](README.md#probe-gate)).

Design and evidence: [docs/research/pathfinder-plan.md](../../../docs/research/pathfinder-plan.md).
Shakedown record, all seven versions: [README](README.md).
