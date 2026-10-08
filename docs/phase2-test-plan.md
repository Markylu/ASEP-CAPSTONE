# Phase 2 Test Plan: Closing the Gap Without Changing the Model

**Owner:** Markus Lu · **Status:** draft · **Created:** 2026-10-08
**Source:** ASEP Capstone Proposal, "Phase 2; iterative improvement"; `docs/phase1-test-plan.md`;
`eval/phase1/results/results.md`

This is the spec sheet for Phase 2. It inherits everything from the Phase 1 spec that it does not
override here: the sites, arms, episode protocol, rubric and validity checks. Section references
written as "P1 §n" point into `docs/phase1-test-plan.md`.

---

## 1. Purpose

Phase 1 measured the gap. With `Qwen3-VL-30B-A3B` at temperature 0 and prompt `p02`, success was
25/30 on `initial` and 0/30 on both `final` and `dynamic` (`eval/phase1/results/results.md`).

Phase 2 tries to close that gap by changing the **agent**: the prompt, what the model is shown,
what is kept between steps. It never changes the model or its weights (proposal). The stretch goal
is a success rate of at least 50% on every layout.

Each round tests one change. The operator chooses the change; this spec only says how a change
is identified, flown and compared.

## 2. What is fixed and what varies

**Fixed for all of Phase 2** (`eval/phase2/config.lock.json`): model, provider profile,
temperature 0, frame 768 × 768, camera and action fan, `max_steps` 60, no collision cap,
`freeze_world`, physics rate, Godot version, and the six sites at their Phase 1 versions (P1 §3).

**Varies per round:** the agent only. An agent version (`server/decider/agent.py`) names one prompt
version (`server/decider/prompt.py`) plus a set of feature flags. Each round's own
`config.lock.json` adds the agent's identity to the phase lock:

| Field | Meaning |
|---|---|
| `agent_version` | `a00`, `a01`, … |
| `agent_sha` | hash of the prompt's sha and the feature flags |
| `prompt_version`, `prompt_sha` | the prompt that agent uses |

Rules:
- Never edit an agent or prompt version once a round has used it. A new idea gets a new version.
  `eval/phase2.py init` refuses if a round's agent no longer matches its lock.
- `a00` is the Phase 1 agent (`p02`, no features), sha `fb65adbe3317`.
- A feature only exists once code reads it. Add the flag to the agent, then read it where it acts.

## 3. Rounds

| Round type | Sites | Arms | Seeds | Runs | Citable |
|---|---|---|---|---|---|
| Shakedown `P2.0` | all 6 | all 3 | 1 | 18 | no (fake decider) |
| Baseline `R0` | all 6 | all 3 | 1 | 18 | no; Phase 1's seed-1 runs, not flown again |
| Screening `R1`, `R2`, … | all 6 | all 3 | 1 | 18 | no |
| Final `F` | all 6 | all 3 | 1–5 | 90 | **yes** |

**Why all three arms each round.** `dynamic` is the condition being improved. `initial` checks that
a change has not broken the solvable case, and `final` separates "handles the change" from
"handles the post-change layout". In Phase 1 the two failing arms behaved the same (contrast b = 0
everywhere), so a round that lifts `final` but not `dynamic` is informative on its own.

**Why one seed.** At temperature 0 the five seeds were near-replicates in Phase 1 (P1 §7.3): the
outcome was the same on all five seeds in every cell. One seed per cell is therefore a cheap
screen. A screening round is never cited as an effect size; only the final round is.

**Time.** About 35–40 min of flying per screening round (P1 §7.5 fit: 7 s + 1.9 s per step; most
failing runs take 60 steps), plus preflight and labelling.

## 4. Procedure per round

1. **Define.** Open an Issue from the "Phase 2 round" template. Add the agent version (and prompt
   version if the wording changes), then add the round to `ROUNDS` in `eval/phase2.py`.
   Run `python eval/phase2.py init`. Commit.
2. **Preflight** (P1 §7.2 step 1): clean tree; tunnel up; decider started with
   `python -m server.decider --profile remote --agent <aNN>`; `/health` reports the round's
   agent sha and prompt sha.
3. **Fly:** `python eval/phase2.py run --round R<N>`. One SHA for the whole round (P1 §7.1).
4. **Validity gate:** P1 §10, plus `agent_version` and `agent_sha` in every `run.json` match the
   round lock. Invalid runs are rerun; valid failures never are.
5. **Label:** `python eval/phase1_label.py --round R<N>`, then manual review of every run (P1 §9).
6. **Summarise:** `summary.md` in the round folder; `phase.json` status `complete`;
   `python eval/phase2.py results`.
7. **Merge:** PR closes the Issue; merge commit (never squash: run records cite the flown SHAs);
   tag `p2-r<N>`.

## 5. Dependent variables and rubric

As P1 §8 and §9, unchanged, so labels compare across phases. The round comparison in
`eval/phase2/results/results.md` shows, per round: success by arm, and per cell either the steps
to goal or the failure label.

## 6. Final round

The agent chosen from the screening rounds is frozen and flown under the full Phase 1 design
(P1 §5–§7): 6 sites × 3 arms × 5 seeds. The results use P1 §11's tables and contrasts, and add a
Phase 1 vs Phase 2 comparison per cell. The final round's order is generated with
`random.Random("phase2-F")`.

## 7. Data layout

Mirrors P1 §14 under `eval/phase2/`:

```
eval/phase2/
├── README.md               ← index: round status table
├── config.lock.json        ← phase lock (§2)
├── matrix.csv              ← every planned run, column `round` instead of `mini_phase`
├── P2.0_shakedown/
├── R1_<slug>/
│   ├── config.lock.json    ← phase lock + this round's agent
│   ├── phase.json, order.txt, labels.csv, summary.md
│   ├── runs/<site>/<arm>/seed1/
│   └── _attempts/
└── results/                ← results.md, runs.csv
```

Run ID: `p2_<round>_<site>_<arm>_seed<N>_a<NN>`, e.g. `p2_R1_s01_dynamic_seed1_a01`.
Git: same committed and ignored files as P1 §14.

## 8. Changelog

| Date | Change |
|---|---|
| 2026-10-08 | Initial spec. Agent versions (`agent.py`, a00 = Phase 1 agent). Rounds are 6 sites × 3 arms × seed 1 = 18 runs; R0 is Phase 1's seed-1 runs; final round is the full 90-run design. Runner shared with Phase 1 (`eval/phaselib.py`). |
