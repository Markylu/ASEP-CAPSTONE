# R25: R20K without the wall at the end of an open_near strip

**Agent:** `a48` (`c000b721200f`) · **Prompt:** `p17` (`cb3578251cfe`) · **Memory:** `a17b` ·
**Status:** pre-registered 2026-10-29, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. Laid out after R21 flew, while R22 was in
the air. Second agent at the same SHA: **R25D**, `a49` (`83f7a6a19b01`) = `a37` (R20) on `a17b`
([R25D](../R25D_door_confirmer_open_near_unwalled/README.md)).

## Change

One against `a38` (R20K, 12/18, the best so far): memory `a17b`, R22's change (no wall written at
the end of an `open_near` strip; [R22's README](../R22_open_near_unwalled/README.md)). R22 put it
on top of R21's along-the-wall detours, which turned out mixed (R21 `dynamic` 4/6 but `final` 2/6
and s03 0/3; R21K 10/18 against R20K's 12/18). R25 puts it on the best agent alone, so the two
are read apart.

## Evidence

R22's: the replay of R15–R17K cuts s03 "toward" moves noted "searched already" 279 → 84 and steps
with no forward "new ground" 39% → 20%, with "new ground" on a truly blocked move 6.1% → 6.5%
([../R22_open_near_unwalled/probe/notes_replay.txt](../R22_open_near_unwalled/probe/notes_replay.txt)).
s03 analysis: [../R17_doorway_first/s03_analysis.md](../R17_doorway_first/s03_analysis.md).
Smoke (`smoke_run`, R20K's 707 manifests): `a48`, `a49` 0 failed steps.

## Hypothesis

R25 scores above R20K, through s03 (crossbar reached early) without losing s02.

## Predictions

| Arm | Baseline (R20K, `a38`) | Predicted |
|---|---|---|
| initial | 6 | 6 |
| final | 4 | 4 or 5 |
| dynamic | 2 | 2 or 3 |

Total ≥ 13/18. s03 crossbar reached by step 15 in at least 2 of 3 runs.

## Manipulation check

Turn-arounds with a forward "toward" move offered: under half of R20K's 20.

## Drop criterion

Not carried forward if the total does not beat R20K's 12/18.

## Probe gate

R22's (passed).

## Builds on

R20K (`a38`).

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
