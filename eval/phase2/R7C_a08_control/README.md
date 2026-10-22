# R7C: a08 control on the R7 host

**Agent:** `a08` (`e8c66be05bd3`) · **Prompt:** `p09` (`7642a3e1056d`) · **Status:** flown (18/18 valid)

Written before flying. Spec: `docs/phase2-test-plan.md`.

## Change

None. This is `a08`, the agent R6 flew, flown again unchanged on sctsvr6 (headless Linux, Mesa
lavapipe CPU Vulkan, Docker) instead of the Mac. It is a control for R7, not a round of its own.

## Evidence

R6 was flown on the Mac (Metal). R7 (`a10`) is flown on sctsvr6. Frames rendered by lavapipe are
not the pixels Metal renders (`eval/docker/README.md`), so a host change is a config change and
R7 against R6 mixes the prompt change with the renderer change. Flying `a08` on the R7 host
separates them: R7 against R7C is the prompt change alone; R7C against R6 is the host alone.

## Hypothesis

None to test. If the host does not matter, R7C reproduces R6's 5/18 (initial 3/6, final 2/6,
dynamic 0/6) within the noise of 18 runs.

## Predictions

| Arm | R6 (Mac) | Predicted R7C |
|---|---|---|
| initial | 3/6 | 2–4/6 |
| final | 2/6 | 1–3/6 |
| dynamic | 0/6 | 0–1/6 |

## Manipulation check

Not applicable (no change). The renderer line in `godot.log` must read Vulkan, Forward+ and
llvmpipe, and every run's captured frame size must be 768x768 (checked by validation).

## Drop criterion

None. Used only to read R7 against.

## Probe gate

Not needed: `a08` was probed in R6, and re-probed on sctsvr6 this round (78 of 80 identical picks
against the Mac, spin turn-around 6/40 both times).

## Builds on

R6 and agent `a08`, unchanged.

## Outcome

The host, or noise, changed `a08`'s result: 8/18 against R6's 5/18 on the Mac, with 100 collisions
against 143. One seed cannot separate the two. [summary.md](summary.md).
