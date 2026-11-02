# R29S: a49, one lane per vLLM instance (every call alone)

**Agent:** `a49` (`83f7a6a19b01`) · **Prompt:** `p17` (`cb3578251cfe`) · **Status:**
pre-registered 2026-11-02, flown the same day, 18/18 valid

The second half of R29. Change, evidence, hypothesis, predictions, gate and operator notes are in
[R29N's README](../R29N_host_noise_shared/README.md): R29N flies `a49` on 4 lanes sharing `:8004`
as every round so far; this round flies the same agent with each lane on its own vLLM instance
(`:8004`, `:8006`, `:8007`, `:8008`), so no perceiver call shares a batch. Flown after R29N, never
beside it.

## Outcome

**14/18** (R29N 11, R25D 14); gate check 1 (missed walls ≤ 10%) failed at 14.9%, checks 2–5 held.
[summary.md](summary.md) has the gate table, the cells and what carries.
