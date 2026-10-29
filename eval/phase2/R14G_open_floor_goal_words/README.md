# R14G: R14 with goal truth in the search menu (a23)

**Agent:** `a23` (`5bbb755c939f`) · **Navigator prompt:** `p14` (`31a9f28eaf94`) ·
**Perceiver:** `g05` · **Strategist:** `q05` · **Stage machine:** as `a22` ·
**Status:** pre-registered 2026-10-29, not flown. Probe gate passed with R14's.

`a23` is `a21` (R13G: goal truth in the strategist's text alone, `goal_truth: strategist`) with
`a22`'s two changes: `a18`'s floor map (g05's `bottom` read `open_near`, not a wall) and a verify
step limit that grows with the distance back. Flown beside R14 at the same SHA.

Change, evidence, predictions, gate and host: [R14's README](../R14_open_floor/README.md).

## Outcome

Flown 2026-10-29 03:05–04:00 UTC, 4 lanes, 18/18 valid. **7/18**: `initial` 4/6 (s02va, s03
failed), `final` 2/6 (s01 in 54 steps, s02c), `dynamic` 1/6 (s02vc). R13G 5/18, R14 7/18, R11
11/18.

Per run: [manipulation.txt](manipulation.txt). Median `blocked_near` 10% (R13G 44%), turn-arounds
8.5 (19.5), max distance from start 19.5 m (14.7 m). The floor fix took here as in R14; the goal
words in the search menu bought one more `final` and lost one `initial` against R14. Same score
as R14: the goal's position in the strategist's text alone does not make the no-truth search an
agent that reaches R11.
