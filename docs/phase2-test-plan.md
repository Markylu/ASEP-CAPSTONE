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
is identified, flown and compared. A bundle round (R9 on) changes several things at once by the
operator's decision; its README names every part, its result is credited to the bundle and not
to any part, and it flies beside a control on the same host (§8, 2026-10-22).

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

1. **Define.** Open an Issue from the "Phase 2 round" template. Create the round's branch (§4.2).
   Add the agent version (and prompt
   version if the wording changes), then add the round to `ROUNDS` in `eval/phase2.py`.
   Run `python eval/phase2.py init`, which writes a stub `README.md` in the round folder.
   **Write it up before flying** (§4.1). Commit the agent change and the write-up together.
2. **Probe** (required when the change touches what the model is asked to perceive or report,
   optional otherwise). The README's Probe gate is written and committed first. Then:
   `python eval/goal_probe.py sample <earlier rounds> --out <round>/probe`, `run --agent` for the
   new agent and for a calibration agent whose failure in flight is known, and `report`. The probe
   sends recorded frames with ground truth to the model, one call per frame and no Godot, at about
   5 min per agent. An agent with a log is also replayed with the log in place (`sample-replay`,
   `run-replay`): recorded decisions whose last sighting is 5–20 steps old, scored on whether the
   reason still places the goal around the drone (R4's phantoms needed a log, which step-0 frames
   lack). If the gate fails, the round does not fly: the README's Outcome records the
   probe, and the next idea is a new version. Commit `probe/` before flying.
3. **Preflight** (P1 §7.2 step 1): clean tree; tunnel up; decider started with
   `python -m server.decider --profile remote --agent <aNN>`; `/health` reports the round's
   agent sha and prompt sha.
4. **Fly:** `python eval/phase2.py run --round R<N>`. One SHA for the whole round (P1 §7.1).
5. **Validity gate:** P1 §10, plus `agent_version` and `agent_sha` in every `run.json` match the
   round lock. Invalid runs are rerun; valid failures never are.
6. **Label:** `python eval/phase1_label.py --round R<N>`, then manual review of every run (P1 §9).
7. **Summarise:** `summary.md` in the round folder, opening with whether the hypothesis held;
   run `python eval/agent_evidence.py eval/phase2/R<N>_<slug>` for the manipulation check; fill
   the README's Outcome line; `phase.json` status `complete`; `python eval/phase2.py results`.
8. **Open the PR, never merge it** (§4.2). Tag the branch tip `p2-r<N>`. Close the Issue by hand
   with a link to the PR.

### 4.1 Round write-up

Every round has a `README.md` in its folder, written and committed **before** the round flies, so
a later write-up can trace evidence → hypothesis → prediction → result for each round.
`eval/phase2.py init` creates the stub, once, and never for a round that has already flown.
Sections:

| Section | Content |
|---|---|
| Change | The one change, against the agent it builds on |
| Evidence | Past data that points at the change. Every claim cites a path: `results.md`, a `summary.md`, a run ID and step, or `evidence.md` |
| Hypothesis | One falsifiable sentence |
| Predictions | Per arm against R0 (and the best round so far), per site where it differs |
| Manipulation check | A measurable sign that the change took effect, independent of success |
| Drop criterion | The result that means the change is not carried forward |
| Probe gate | `eval/goal_probe.py` thresholds that must pass before flying (§4 step 2), or "Not needed" |
| Builds on | Previous round and agent |
| Outcome | After flying, the only edit: held or not, and a link to `summary.md` |

### 4.2 Branches and PRs: one per round, never merged

Phase 2 is an iteration record, so each round stays visible as its own branch and PR instead of
being folded into `main`.

- **Branch** `phase2/r<N>-<slug>`, cut from the tip of the previous round's branch. R1 is cut
  from `main` after `p2-setup`. The rounds form one chain, so the tip of the latest branch holds
  every agent version, every round's data, and the cross-round `results.md`.
- **PR** base is the previous round's branch (R1: `main`), so its diff is exactly that round:
  the agent change, the write-up, the runs, labels and summary. The body links the write-up and
  gives the round table and the delta against the best round so far.
- **Never merged**, including the final round. A PR stays open as the record of its iteration.
  Close the Issue by hand (closing keywords only fire on merge).
- **Never rebased, force-pushed or deleted.** `run.json` cites the SHA each run was flown at,
  and those commits exist only on the round branch. Deleting a base branch would also close
  every PR stacked on it.
- A round that does not build on the one before (its README's "Builds on" names an earlier
  agent) still branches from the latest tip. Agent versions are append-only, so the old agent
  is still there to build on.
- Process and tooling changes that every round needs (the runner, labeller, templates, this
  spec) are not round work. They go to `main` through an ordinary, merged PR. A round branch
  that needs them merges `main` in before its first flight, never after.

`evidence.md` beside it is generated by `python eval/agent_evidence.py <phase or round folder>
--out <round>/evidence.md`. It gives per site and arm what the reasons cite and how often the
pick is the action nearest the true goal bearing. It is regenerated, never edited.

## 5. Dependent variables and rubric

As P1 §8 and §9, unchanged, so labels compare across phases. The round comparison in
`eval/phase2/results/results.md` shows, per round: success by arm, and per cell either the steps
to goal or the failure label.

**Added secondary tag: `failed_goal_identification`.** It goes in the `tags` column only, so it
leaves the terminal labels, their order and the frozen thresholds untouched. Several tags in one
cell are separated by `;`. The tag applies to a failed run (not `success`) that meets any one of
three facets:

| Facet | Rule |
|---|---|
| phantom goal | ≥ 5 decisions report the goal while ground truth has it out of view |
| missed goal | ≥ 3 decisions report `not_visible` while the goal is in view, and that is ≥ 50% of the in-view decisions |
| lost at close range | closest approach ≤ 3.0 m (arrival radius 1.0 m) without arriving |

- Ground truth is `true_goal()` in `eval/agent_evidence.py`: line of sight, and a bearing inside
  the camera's field of view.
- The first two facets need a `goal` field in the reply (`a03` on). For an agent without one,
  the reviewer judges them from the reasons.
- `eval/phase1_label.py` writes the facet counts and the suggested tag to `auto_labels.json`
  (`goal_id`). The reviewer confirms the tag like any other.
- Added in R4, whose phantom sightings came from the log. R1–R3 keep their labels and tags as
  they were reviewed (operator, 2026-10-14). The rubric grew with the experiment, and the round
  where a tag first appears records when that failure mode was recognised. R3's missed goals
  (R3 summary) would have met the "missed goal" facet.

**Added secondary tag: `spin_failure`.** In the `tags` column like the tag above. It applies to a
failed run in which the agent picks turn-around in place on **≥ 5 consecutive decisions**: two
turn-arounds cancel, so the drone stands still while the run's steps run out.

- `eval/phase1_label.py` reads the chosen action's `turn_around` flag from each manifest and writes
  the longest streak, where it starts, the total number of turn-arounds and the suggested tag to
  `auto_labels.json` (`spin`). The reviewer confirms it like any other tag.
- The threshold sits above every successful run in R1–R5 (longest streak 4, R5 s03 `final`).
- Added in R5, whose failures turned around in place in streaks of 7–36 (operator, 2026-10-16).
  R1–R4 keep their labels and tags as reviewed. By the rule, 9 of R3's 18 failures and 6 of R4's 13
  would have met it.

## 6. Final round

The agent chosen from the screening rounds is frozen and flown under the full Phase 1 design
(P1 §5–§7): 6 sites × 3 arms × 5 seeds. The results use P1 §11's tables and contrasts, and add a
Phase 1 vs Phase 2 comparison per cell. The final round's order is generated with
`random.Random("phase2-F")`. It follows §4.2 like any round: branch `phase2/final` from the
latest round's tip, PR against that branch, never merged, tip tagged `phase2-complete`. The
citable Phase 2 results live on that branch and tag.

## 7. Data layout

Mirrors P1 §14 under `eval/phase2/`:

```
eval/phase2/
├── README.md               ← index: round status table
├── config.lock.json        ← phase lock (§2)
├── matrix.csv              ← every planned run, column `round` instead of `mini_phase`
├── P2.0_shakedown/
├── R1_<slug>/
│   ├── README.md           ← write-up, committed before flying (§4.1)
│   ├── evidence.md         ← eval/agent_evidence.py output the README cites
│   ├── probe/              ← eval/goal_probe.py set, answers and probe.md (§4 step 2)
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
| 2026-11-02 | Host rounds (R29N/R29S): a round may change how the vLLM is shared instead of the agent, with the same agent sha in every run; the host layout is recorded in `phase.json` "lanes". Probe LD showed the model deterministic when called alone with a warm prefix cache and two thirds of the flight-time missed walls to be the shared host's. Feature flag `reason_cap` (a62): a maxLength on the describe-first reason, off for every agent up to a61. |
| 2026-10-28 | R13 (operator's decisions): a verify stage on `a19` (`a20`, `target_policy: staged_verify`): the first look without the goal sends the drone back to where it last saw it from to look again; seen, goal resumes (old sightings dropped if the new one disagrees); not seen, no path back or 8 steps, the sighting is dropped and explore resumes. Its thresholds and words are hashed into `agent_sha` (`planner_a20`). A second agent may fly beside a round at the same SHA as a candidate, not a control (R13G, `a21`). `goal_truth: strategist`: the goal's position reaches the strategist's text only; every stage runs on the manifest without the goal block. Rounds are read against the best round so far and their base; controls only on request. Probe: `eval/r13_probe.py` (transitions, smoke, open-loop count). |
| 2026-10-28 | Goal truth dropped (operator's decision, for R12 on): no part of an agent with `goal_truth: none` sees the goal's true position. `orchestrator.decide` removes the manifest's `goal` block before any stage runs; the decision record keeps it for evaluation only. This reverses 2026-10-26 for such agents; `a14`–`a16` keep it as flown. A round with no goal truth is read against a control without it (`a13`), not against R10 or R11. Staged agents (`target_policy: staged_search`, `a17`): the stage machine's thresholds and its strategist sentences are hashed into `agent_sha` (`planner_a17`). Probe: `eval/r12_probe.py` (offline lines on recorded runs against R11's 2D site model, and `smoke`, the real step with and without the goal block). |
| 2026-10-26 | Goal truth (operator's decision, for R11 on): code on an orchestrated agent's planner side (target policy, detour scoring, progress monitor) may read the goal's true position, as well as the strategist's prompt. No navigator or perceiver text may carry it; the navigator gets the goal only as "toward your target". `eval/spatial_replay.py audit` reports note use, near-repeat collisions, the goal estimate and the strategist's choices for a round (R11 evidence, `eval/phase2/R11_goal_default/evidence.md`). |
| 2026-10-24 | R10 (`a14`, operator's decisions): the goal's true position may be given to an orchestrated agent's planner only (`goal_truth: planner`): the strategist's prompt and target list carry it, and no other part sees it (the navigator gets "head for the goal" and "toward your target", no distance or direction). Since R1 no agent had the goal's position; Phase 1's `a00` had its distance and bearing in the navigator prompt. An agent may leave an action off its list and out of its schema (`turn_rule: no_repeat_when_open`: no turn-around right after a turn-around while a move ahead is open); the frame still shows the marker, and the record carries `hidden`. The operator accepts the hidden action for R10, not as a lasting design. a14's added wording is hashed separately (`spatial.wording_sha_a14()`), so `a13` keeps its sha and flies as R10's control. Probe: `eval/r10_probe.py` (q02 on R9's 321 strategist calls; the navigator on R9's 25 turn-arounds a14 would not offer). |
| 2026-10-22 | Bundle round (R9, operator's decision): several changes in one agent, credited to the bundle, flown beside a control on the same host; an ablation round follows if it wins. Orchestrated agents (`a13` on, `server/decider/orchestrator.py`): one step is several calls of the frozen model with one job each (perceiver, strategist, navigator, and a critic's one retry), and every subagent prompt and the spatial memory's wording and parameters are part of `agent_sha`. Spatial memory (`server/decider/spatial.py`) is built only from the drone's pose and what the perceiver reads off the clean frame, never from site geometry, depth, the `collided` flag or goal ground truth, and is rebuilt from `decisions.jsonl` each step. Probe: `eval/r9_probe.py` (perceiver against ground truth, trap replay through the real step). Checks: `eval/spatial_replay.py` (memory against the R7 comparison lines, manipulation-check counts, top-down maps). |
| 2026-10-22 | Control rounds (R7C, R8N): a round with no change of its own, flown at the same SHA and on the same host as the round it controls, and listed in `ROUNDS` beside it. R7C re-flies the previous agent on a new host; R8N flies a no-op prompt edit (`a12`) to measure how far wording alone moves a round. A round flown with a no-op control states an attribution rule in its README before flying. `eval/agent_evidence.py` gains heading columns (degrees, compass word, heading arithmetic, turn-around with the goal in view). |
| 2026-10-16 | Secondary tag `spin_failure` (§5): a failed run with ≥ 5 consecutive turn-around picks, computed by `eval/phase1_label.py`. Tags only; applies from R5. |
| 2026-10-15 | Clean frames: an agent whose goal identifier reads the frame without annotations (`goal_identifier.frame: clean`, a06) gets it from Godot beside the annotated frame, saved as `frames/c<step>.png`. `eval/replay.py --save-clean-frames` recovers clean frames for recorded runs at their exact poses, and `goal_probe.py attach-clean` pairs them with probe frames. |
| 2026-10-15 | Replay probe (§4 step 2): `eval/goal_probe.py sample-replay` / `run-replay` send recorded frames with the log the agent had, scored by `claims_goal()` (`eval/agent_evidence.py`). Gates are per round (`report --gate`). Agents may carry a goal identifier, a second call per step whose prompt sha is part of `agent_sha` (R5). |
| 2026-10-14 | Secondary tag `failed_goal_identification` (§5): phantom goal, missed goal or lost at close range, computed by `eval/phase1_label.py`. Tags only; the rubric's terminal labels are unchanged. |
| 2026-10-14 | Probe step (§4 step 2) and a Probe gate section in the write-up: `eval/goal_probe.py` checks offline, on recorded frames, whether an agent sees the goal before a round flies. R3 flew 0/18 on an agent that had stopped seeing it. |
| 2026-10-08 | Round write-ups (§4.1): `README.md` per round before flying, `evidence.md` from `eval/agent_evidence.py`. Branches (§4.2): one branch and PR per round, stacked on the previous round, never merged; replaces "merge, never squash". |
| 2026-10-08 | Initial spec. Agent versions (`agent.py`, a00 = Phase 1 agent). Rounds are 6 sites × 3 arms × seed 1 = 18 runs; R0 is Phase 1's seed-1 runs; final round is the full 90-run design. Runner shared with Phase 1 (`eval/phaselib.py`). |
