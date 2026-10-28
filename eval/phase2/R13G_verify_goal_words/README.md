# R13G: R13 with goal truth in the search menu (a21)

**Agent:** `a21` (`97790ec7c54e`) · **Navigator prompt:** `p14` (`31a9f28eaf94`) ·
**Perceiver:** `g05` (`133ed83db46b`) · **Strategist:** `q05` (`86e1f4104ac0`, new) ·
**Stage machine:** as `a20` (`planner_a17` `6eb22517c3e0`, `planner_a20` `2ff7c48cdc16`) ·
**Status:** pre-registered 2026-10-28, not flown. Probe gate passed with R13's.

`a21` is `a20` (R13) with the goal's true position in the strategist's text alone
(`goal_truth: strategist`). The operator's second candidate, flown beside R13 at the same SHA
(operator, 2026-10-28: "can we test both since they can be parallelised"). Not a control.

Everything else (change, evidence, predictions, gate, host) is in
[R13's README](../R13_verify/README.md), "Two agents" and on.

## Change against `a20`

- `q05` = `q04` with one paragraph: the system says where the goal truly is and how much nearer
  the goal each place lies; a place nearer the goal is worth more only when it also leads
  somewhere new.
- The strategist's situation adds "The goal's position is known: …" and each place's "about N m
  nearer/farther the goal than you are" (`a16`'s wording, `planner.gain_words`).
- The menu is `a20`'s, reachable places only. The stages, map, perceiver and navigator see no goal
  truth: the manifest reaches them without its goal block, as for `a20`.

## Outcome

Not flown.
