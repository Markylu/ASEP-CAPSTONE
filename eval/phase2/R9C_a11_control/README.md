# R9C: a11 control on the R9 host

**Agent:** `a11` (`3859d0345560`) · **Prompt:** `p12` (`f24e2855bfbe`) · **Identifier prompt:**
`g02` (`bf175c973dfb`) · **Status:** flown (18/18 valid)

Written before flying. Spec: `docs/phase2-test-plan.md`.

## Change

None. This is `a11`, the agent R8 flew and carried forward, flown again unchanged on sctsvr6 at
R9's SHA, right after R9. It is the control R9 is read against, not a round of its own.

## Evidence

R9 (`a13`) is a bundle round, read against a control on the same host at the same SHA (R9 README,
"Attribution rule"). R8 found `a11` not dropped (1 of 4 drop conditions).

## Hypothesis

None to test. The decider is deterministic on this host (R8 probe: `a10` rerun 80/80) and this
branch's changes leave `a11`'s prompt renders byte-identical, so R9C is expected to reproduce R8.

## Predictions

| Arm | R8 `a11` | Predicted R9C |
|---|---|---|
| initial | 5/6 | 5/6 |
| final | 1/6 | 1/6 |
| dynamic | 0/6 | 0/6 |

Any cell that differs from R8 is reported with its first divergent step; a difference means the
host or the decider is less deterministic than the R8 probe showed.

## Manipulation check

Not applicable (no change). The renderer line in `godot.log` must read Vulkan, Forward+ and
llvmpipe, and every run's captured frame size must be 768x768 (checked by validation).

## Drop criterion

None. Used only to read R9 against.

## Outcome

Flown 2026-10-23 on sctsvr6 at `756345b`, right after R9, 18/18 valid. 6/18 (initial 5/6, final
1/6, dynamic 0/6), the same as R8 in every cell; 16 of 18 pick sequences identical to R8.
[summary.md](summary.md).
