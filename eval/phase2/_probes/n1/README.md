# Probe N1: is the step-0 lottery caused by batching?

Plan: [docs/research/probe-plan.md](../../../../docs/research/probe-plan.md), section N. Script:
`eval/probes/n1.py`.

## Belief

Temperature 0 is not deterministic on a shared server, because batch composition changes kernel
reduction order (Thinking Machines, "Defeating Nondeterminism in LLM Inference", 2025). If that
holds, the same step-0 frame reads differently from round to round (`R25D/.../why_14.md` §4)
because of what else the server was running, not because of the agent.

## Method

- **Instance.** A fresh copy of the `:8004` vLLM: the same image (`vllm/vllm-openai:v0.23.0`), the
  same weights (`Qwen3-VL-30B-A3B-Instruct-FP8`) and the same flags. It runs on GPU 3 at `:8006`,
  and nothing else uses it during the probe. In total 4 GPUs are in use: Coder-Next on 0–1, `:8004`
  on 2, this copy on 3. The copy is stopped afterwards.
- **Frames.** The step-0 clean frames of R25D `s02a/final` and `s03/final`. Their md5 is also
  compared with every R22–R26N step-0 frame of the same site.
- **Call.** The a49 perceiver call: g05, its schema, a49's floor map, 768 max tokens.
- **Arm *alone*.** 20 calls per frame, one at a time.
- **Arm *loaded*.** 20 trials per frame. In each, the call runs alongside 7 other perceiver calls
  on other recorded clean frames (R25D, steps 5–40, fixed seed), all sent together.
- **Score, per frame and arm:**
  - distinct raw replies;
  - distinct readings (goal, goal range, and each strip's floor and doorway, with the reason
    ignored);
  - the share of strip fields that differ from the arm's most common reading.
- **Stand-in check.** Compare the copy's *alone* mode with `:8004`'s recorded step-0 readings of
  the same frame bytes (R22–R26N, g05 agents), against how well those recorded readings agree with
  each other.

## Gate (set before the first call)

| Result | Verdict |
|---|---|
| *alone* gives ≤ 2 distinct readings on both frames, and *loaded* gives ≥ 5 on at least one | **Holds**: the noise is batching |
| *alone* gives at least as many distinct readings as *loaded* on both frames | **Refuted**: the noise is not from batching, and a batch-invariant host would not help |
| Anything else | No call |

**Stand-in.** The copy counts as a stand-in for `:8004` if its *alone* mode agrees with the recorded
readings, on strip fields, at least as well as the recorded readings agree with each other, minus
5 pts. If it does not, A1 runs on `:8004` only.

**Feeds the later probes.** The *loaded* strip-field disagreement rate is the noise floor for C1 and
F1: an effect there counts only at ≥ 2× this rate.

## Result

Pending.
