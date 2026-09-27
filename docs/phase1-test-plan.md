# Phase 1 Test Plan: VLM Navigation Under Mid-Episode Change

**Owner:** Markus Lu · **Status:** draft, frozen before the first citable run · **Created:** 2026-09-27
**Source:** ASEP Capstone Proposal, "Phase 1; Experimental Design"; `notes/PLAN.md`; `notes/DEVLOG.md`

This is the spec sheet for Phase 1. Every parameter a run depends on is pinned here. A number can
only go in the paper if it comes from a run flown under this spec. If the spec has to change after
runs have started, the affected mini-phase (§7) restarts and the change goes in the changelog (§15).

---

## 1. Purpose and research question

**Diagnostic question (proposal):** *When an environment changes mid-episode, how does a VLM
navigating it adapt, succeed or fail?*

**H1:** Success rate (SR) drops significantly when the layout changes mid-episode. The dominant
failure mode is **ignoring the change** rather than trying to replan and failing. The reasoning is
that a frozen VLM conditions each decision on a single frame and has no memory of what the scene
looked like one step earlier.

Phase 1 measures that gap. Phase 2 (not covered here) tries to close it with external, non-training
changes such as memory and prompting. Phase 1's failure-mode table is Phase 2's input.

## 2. Deviations from the proposal

| Proposal | This spec | Why |
|---|---|---|
| 2 conditions: unchanged vs changed | **3 arms:** `initial`, `final`, `dynamic` (§5) | "Unchanged" can mean two things. Holding the *initial* layout shows whether the task is solvable at all. Holding the *final* layout from step 0 separates "the change hurt" from "the post-change layout is just hard". Running both makes the causal claim clean. |
| 3 layouts | **4 layout families, 6 sites.** Door Switch is split into out-of-view (2a) and in-view (2b), each with A/C mirror arms | On s02a/c the new door is off-screen when it opens, so a failure could mean "never saw it" or "saw it and didn't replan". s02va/vc puts the new door in frame and removes the search component. Mirror arms catch left/right bias. |
| 30 episodes (3 × 2 × 5) | **90 episodes** (6 sites × 3 arms × 5 seeds) | Follows from the two rows above. |
| 5 runs per cell, sampling unspecified | **Temperature 0 + seeded spawn jitter** (§7.3) | At temperature 0 the model is (near-)deterministic, so 5 identical spawns would give 5 copies of one run. Jitter makes the runs differ in input while keeping decoding fixed. |

## 3. Frozen configuration

Recorded per run in `run.json` / `metrics.json`, and once per phase in `eval/phase1/config.lock.json`.
A run whose recorded values differ from this table is **invalid**.

| Parameter | Value | Where it comes from |
|---|---|---|
| Model | `Qwen3-VL-30B-A3B` (served name; weights `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8`) | `REMOTE_VLM_MODEL` |
| Provider | `remote` profile: vLLM container on sctsvr6, `:8004` over `ssh -N -L 8004:127.0.0.1:8004 sctsvr6` | `server/README.md` |
| Inference mode | non-thinking | proposal (latency) |
| Temperature | `0` | `VLM_TEMPERATURE` |
| Prompt | `p02`, sha `26260774b60e` | `server/decider/prompt.py` |
| Goal information | distance + signed bearing + arrival radius as text, every step (PointNav) | `prompt.py` |
| Output contract | `json_schema` strict, `reason` before `action`, action enum = indices drawn on this frame | `server/decider/vlm.py` |
| Frame | 768 × 768, HUD and panel hidden | `run_session.gd`, `capture_decision_frame()` |
| Camera | FOV 87° horizontal (`KEEP_WIDTH`), pitch 0, 1.75 m altitude | `vlmnav_config` |
| Action fan | 5 actions + index 0 turn-around, `fan_spread 1.0`, `action_dist 1.7 m`, `annotation_distance 6.0 m` | `vlmnav_config` |
| Navigability filter | **none** (collisions allowed and recorded) | proposal, DEVLOG 2026-09-12 |
| `freeze_world` | `true` (world paused while the model decides) | `decision_client.gd` |
| `--speed` | `1.0` | `run_session.gd` |
| Physics | 60 ticks/s, Jolt, Godot 4.7.2-stable | `project.godot` |
| Execution | **sequential**: one Godot run at a time, one decider | §7 |
| Git | clean tree; `git_dirty` must be `false` in every `run.json`. Recorded data (`eval/runs/`, `eval/phase1/`) does not count as dirty | recorder, `config.git_dirty()` |

Site versions frozen for Phase 1: `s01_occluder_dropin@v1`, `s02a_doors_open_a@v2`,
`s02c_doors_open_c@v2`, `s02va_doors_visible_a@v1`, `s02vc_doors_visible_c@v1`,
`s03_fork_deadend@v2`.

## 4. Layouts

All sites share one shell (48 × 23.5 m, 12 m walls, greybox), one goal `(-12, 1, 0)` with a 1.0 m
arrival radius and a 6 m beam, and spawn facing −X. Full geometry is in each site's `site.json` and
`README.md`.

| Layout | Site | Spawn (x) | Goal dist / LOS at spawn | Change | Trigger → switch step | Straight-line collision | Post-change route |
|---|---|---|---|---|---|---|---|
| 1 Object Appearance | `s01_occluder_dropin` | 12 | 24.0 m / yes | 8 m cube rises at x = −2, blocking path and sightline | x = 6.5 → step 3; first occluded frame 4 | step 6, x = 2.2 | around either side (7.75 m side gaps) |
| 2a Door Switch, out of view | `s02a_doors_open_a` / `s02c_doors_open_c` | 12 | 24.0 m / yes (through B) | B closes; A (−z, right) or C (+z, left) opens | x = 6.5 → step 3; first switched frame 4 | step 7, x = 0.45 | new door **56.3° off-axis** (outside 43.5° half-FOV); ≈ 26.5 m |
| 2b Door Switch, in view | `s02va_doors_visible_a` / `s02vc_doors_visible_c` | 20 | 32.0 m / yes (through B) | same switch as 2a | x = 14.5 → step 3; first switched frame 4 | step 12, x = 0.45 | new door **in frame** (far edge 39.7°); ≈ 32.4 m ≈ 19 steps |
| 3 Split Path | `s03_fork_deadend` | 21 | 33.0 m / no | whichever tine is entered first has its exit door slam shut; the other bank disarms | mid-tine x = 0, step depends on the agent | ≈ 4 steps after the switch | back out, cross crossbar, take other tine; scripted recovery = 43 steps |

## 5. Arms

| Arm | Meaning | s01 | s02a / s02va | s02c / s02vc | s03 |
|---|---|---|---|---|---|
| `initial` | pre-change layout held for the whole run | occluder never deploys | B open, A/C closed, all run | same | both exits open, all run |
| `final` | post-change layout present from step 0; nothing changes | cube deployed at load | B closed, **A** open at load | B closed, **C** open at load | one exit closed at load: **L on odd seeds, R on even seeds** |
| `dynamic` | change fires mid-episode (site as built) | cube rises at trigger | B→closed, A→open | B→closed, C→open | committed tine's exit closes |

`initial` is what `--static-doors=1` already does for door sites. `final` and the s01 `initial` arm
need the `--world` flag (§12).

## 6. Episode protocol

| Rule | Value |
|---|---|
| Success | `goal_reached`: agent within 1.0 m planar distance of the goal |
| `max_steps` | **60**. Covers the slowest known recovery (s03, 43 steps) with ~1.4× headroom. Same for every site. |
| `max_collisions` | **none** (`--max-collisions=-1`). Collisions are measured and never end a run, so every failure runs the full 60 steps and post-change behaviour is fully observed. |
| `stop_on_goal` | `true` |
| Wall clock | 900 s. Safety net only; 60 steps × p95 ≈ 8 s ≈ 480 s. |
| Valid end reasons | `goal_reached`, `max_steps` |
| Invalid end reasons | `wall_clock_limit`, `decision_error: …` → rerun (§10) |

Launch (once §12 lands; flag names are provisional until implemented):

```bash
godot --path first-project res://sites/<site>/site.tscn -- \
    --run-id=<run_id> --decider-url=http://127.0.0.1:8000 \
    --max-steps=60 --max-collisions=-1 --frame-size=768x768 \
    --world=<initial|final|dynamic> --spawn-seed=<1..5>
```

## 7. Mini-phases

Phase 1 is split by map into self-contained **mini-phases**. A mini-phase is the smallest unit that
can be rerun wholesale. If something goes wrong in 1C, only 1C is rerun.

| Mini-phase | Folder | Sites | Runs | Citable |
|---|---|---|---|---|
| 1.0 Shakedown | `1.0_shakedown/` | all 6, **fake decider**, seed 1, one run per arm | 18 | **no** |
| 1A Object Appearance | `1A_s01/` | s01 | 15 | yes |
| 1B Door Switch, out of view | `1B_s02/` | s02a, s02c | 30 | yes |
| 1C Door Switch, in view | `1C_s02v/` | s02va, s02vc | 30 | yes |
| 1D Split Path | `1D_s03/` | s03 | 15 | yes |

### 7.1 Rules

- Every run in a mini-phase shares **one git SHA and one config lock**. If either has to change
  mid-phase, the whole mini-phase restarts (old runs move to `_attempts/`, `phase.json` status →
  `superseded`).
- A single invalid run is rerun on its own, with the same seed and the next attempt number (`a02`, …).
- Mini-phases can run in any order and in separate sessions. Within one, runs go in the fixed order
  in §7.4.
- **Strictly sequential.** One Godot instance at a time. Parallel runs would inflate decision
  latency, which is a dependent variable.
- 1.0 must pass before any citable mini-phase starts. It proves the flags, run-dir layout, replay
  and labeling scripts end to end without spending H100 time.

### 7.2 Per mini-phase procedure

1. **Preflight**
   - [ ] `git status` clean; record SHA in `phase.json`
   - [ ] Tunnel up; `curl localhost:8000/health` reports profile `remote`, model `Qwen3-VL-30B-A3B`
   - [ ] `config.lock.json` matches §3; the prompt sha printed by the decider matches
   - [ ] Sites in this mini-phase are `status: active` at the frozen version
   - [ ] One scripted straight-ahead probe per site reproduces the expected trigger and collision steps (§4)
2. **Run:** `eval/phase1.py --mini-phase <id>` flies `order.txt`, skipping runs already `valid`.
3. **Validity gate:** every run passes §10; failures get rerun.
4. **Replay:** every valid run is replayed; `replay.json` saved.
5. **Label:** auto pre-label, then manual review (§9).
6. **Sign-off:**
   - [ ] 15 or 30 valid runs, one per (site, arm, seed)
   - [ ] `labels.csv` complete, no blank manual labels
   - [ ] `summary.md` written (table + notes)
   - [ ] `phase.json` status → `complete`, committed

### 7.3 Replicates: spawn jitter

At temperature 0, runs differ only through their input. Each run applies a seeded offset to the spawn:

- lateral (z) offset uniform in **±0.5 m**, yaw offset uniform in **±5°**
- seeds **1–5**, reused unchanged across every site and arm, so the three arms of a site see the
  same five starting poses (paired design)
- the offset actually applied is written to `run.json` (`spawn_seed`, `spawn_offset`)
- jitter never moves spawn across a trigger. All triggers are ≥ 5.5 m ahead of spawn.

Known limitation: vLLM batching can make temperature-0 outputs not bit-exact across sessions. Trajectories stay exactly
replayable from the recorded index list regardless.

### 7.4 Run order (fixed)

Generated once with `random.Random("phase1-<mp>")` over (site, arm, seed). Format `site/arm/seed`.

**1A:** s01/final/1, s01/initial/4, s01/dynamic/4, s01/final/4, s01/final/3, s01/initial/1,
s01/final/2, s01/initial/2, s01/dynamic/1, s01/dynamic/5, s01/initial/5, s01/final/5,
s01/dynamic/2, s01/initial/3, s01/dynamic/3

**1B:** s02a/dynamic/5, s02c/final/2, s02a/final/3, s02c/initial/2, s02c/final/1, s02a/final/5,
s02a/final/4, s02a/final/1, s02a/initial/3, s02c/initial/4, s02a/final/2, s02a/dynamic/1,
s02a/dynamic/4, s02c/dynamic/4, s02a/initial/1, s02a/dynamic/2, s02c/dynamic/3, s02a/dynamic/3,
s02c/final/3, s02c/initial/3, s02c/initial/1, s02c/dynamic/1, s02c/dynamic/2, s02c/dynamic/5,
s02c/initial/5, s02a/initial/4, s02a/initial/5, s02c/final/5, s02a/initial/2, s02c/final/4

**1C:** s02va/dynamic/5, s02vc/initial/5, s02va/dynamic/3, s02vc/dynamic/4, s02vc/initial/4,
s02va/dynamic/1, s02va/dynamic/2, s02vc/initial/3, s02vc/dynamic/1, s02vc/final/5,
s02va/initial/4, s02va/dynamic/4, s02vc/final/2, s02vc/dynamic/2, s02vc/final/4,
s02vc/dynamic/5, s02va/final/4, s02vc/initial/2, s02va/final/1, s02vc/dynamic/3,
s02va/initial/1, s02va/final/3, s02vc/final/3, s02va/initial/2, s02va/final/2, s02va/final/5,
s02vc/final/1, s02va/initial/3, s02va/initial/5, s02vc/initial/1

**1D:** s03/final/2, s03/dynamic/4, s03/initial/4, s03/initial/2, s03/dynamic/5, s03/final/3,
s03/initial/3, s03/dynamic/2, s03/final/4, s03/initial/1, s03/dynamic/1, s03/initial/5,
s03/final/1, s03/final/5, s03/dynamic/3

## 8. Dependent variables

| Variable | Definition | Source |
|---|---|---|
| **SR** | successes / runs per cell, with Wilson 95% CI | `metrics.json: goal_reached` |
| **ΔSR** | SR(dynamic) − SR(initial), SR(dynamic) − SR(final) | derived |
| Failure mode | one terminal label per run (§9) | `labels.csv` |
| Collisions pre/post | collided steps before vs after the change step | `steps.jsonl`, `events.jsonl` |
| `steps_to_reacquire` | steps from goal hidden to goal visible again; `null` if never | `metrics.json` |
| Acknowledgement step | first step after the change whose `reason` refers to it (§9) | `decisions.jsonl` + manual |
| Progress | goal distance per step; final distance | `steps.jsonl` |
| Steps to goal | successful runs only | `metrics.json: steps` |
| Decision latency | p50 / p95 per run, also split pre/post change; network vs compute breakdown | `metrics.json: latency_ms`, `latency_breakdown_ms` |
| Output rung | `rungs_used` | `metrics.json` |

For the `initial` and `final` arms, where nothing changes, "pre/post" is split at the step the
`dynamic` arm's trigger would fire (step 3 for s01/s02/s02v; for s03, the step the agent crosses x = 0
in a tine).

## 9. Failure-mode rubric

Each run gets **one terminal label**. The labels come from the proposal's driver analogy. Apply them
in this order; the first match wins:

| # | Label | Definition (operational) |
|---|---|---|
| 0 | `success` | `goal_reached = true` |
| 1 | `pre_change_failure` | *dynamic arm only:* the change never fired (agent never reached the trigger) |
| 2 | `ignore_change` | after the change, **no** `reason` in the next 5 decisions refers to the new obstacle / closed door / blocked route, **and** the agent keeps heading toward the goal bearing (≥ 3 of those 5 actions within ±30° of bearing) |
| 3 | `replan_failure` | change acknowledged in `reason`, but the agent never gets through the new route: never passes the newly opened door (s02/s02v), never gets past the cube's x (s01), never enters the other tine (s03) |
| 4 | `collision` | change acknowledged and a route attempted, but **≥ 50%** of post-change steps are collisions: stuck grinding on geometry |
| 5 | `timeout` | got through the new route but did not reach the goal within 60 steps |

For `initial` / `final` arms, labels 1–2 do not apply. Use `collision`, `timeout`, or
`replan_failure` (the agent never found the available route).

**Secondary tags** (CapNav, multi-select, optional): `path_hallucination`, `obstacle_hallucination`,
`dimension_neglect`, `ability_hallucination` (e.g. assumes it can open a door).

**Labeling procedure (two passes):**
1. **Auto pre-label** by script: keyword match on post-change `reason` text (`closed`, `blocked`,
   `wall`, `obstacle`, `door`, `box`, `no longer`, `dead end`, …) plus geometric checks from
   `steps.jsonl`.
2. **Manual review** of every run: read post-change reasons and watch the replay. Confirm or override,
   with a note on every override.

`labels.csv` columns: `run_id, site, arm, seed, auto_label, label, ack_step, tags, override_note, reviewer, date`

Thresholds above (5 decisions, ±30°, 50%) are fixed **before** 1A starts. Changing them later
means relabeling every mini-phase.

## 10. Validity checks and rerun policy

A run is **valid** only if all of these hold:

- [ ] end reason ∈ {`goal_reached`, `max_steps`}
- [ ] no `decision_error`; `rungs_used` is ≥ 90% `json_schema`
- [ ] `run.json` matches `config.lock.json` (model, prompt sha, frame, config, site version, `git_dirty: false`)
- [ ] `dynamic` arm: change event present in `events.jsonl` at the expected step (s01/s02/s02v: step 3),
      or absent only if the agent never reached the trigger (→ `pre_change_failure`)
- [ ] `initial` / `final` arm: **no** change event in `events.jsonl`
- [ ] `eval/replay.py` reproduces the trajectory with drift < 1e-3 m, matching collisions and events

**Invalid → rerun** with the same seed and the next attempt number. The old attempt moves to
`_attempts/` with a reason in `matrix.csv`. **A valid failure is never rerun or dropped.** Doing so
would bias SR upward.

## 11. Analysis plan

**Main table** (one per layout, plus a pooled row):

| Site | Arm | n | SR | 95% CI | success | ignore | replan | collision | timeout | pre-change | latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|

**Planned contrasts** (fixed now, before data):

| # | Contrast | Question |
|---|---|---|
| a | dynamic vs initial | Cost of the change (H1) |
| b | dynamic vs final | Is it the change, or is the final layout just hard? |
| c | 2b vs 2a, dynamic arm | Cost of search: new door in view vs out of view |
| d | A vs C mirrors (s02a/c, s02va/vc); s03 L vs R | Side bias |

Test: Fisher's exact test on success counts per contrast. **Caveat, stated up front:** n = 5 per site
cell (10 per 2a/2b family) is underpowered. Only very large gaps (e.g. 5/5 vs 0/5) reach p < 0.05.
Results are reported as effect sizes with CIs; significance is secondary. Failure-mode distribution is
the main qualitative result for Phase 2.

**Qualitative:** one annotated case study per observed failure mode (frames before and after the
change, reasons, trajectory plot).

## 12. Prerequisites (not built yet)

Phase 1 cannot start until these exist and 1.0 has passed.

- [x] `--spawn-seed=<n>`: seeded jitter (§7.3), offset recorded in `run.json`
- [x] `--world=initial|final|dynamic`, generalising `--static-doors`:
  - [x] `TriggeredOccluder`: disarm (s01 `initial`) and deploy-at-load (s01 `final`)
  - [x] `TriggeredDoorBank`: apply post-trigger state at load, then disarm (`final`)
  - [x] s03 `final`: pick the closed side from the seed parity
  - [x] `world` recorded in `run.json` / `metrics.json`
- [x] Decider run-dir override (`--run-dir=`) so runs land in `eval/phase1/<mp>/runs/<site>/<arm>/seed<N>/`
      (today `recorder.py` writes `config.RUNS_DIR / run_id`)
- [x] `eval/phase1.py run --mini-phase <id> [--only site/arm/seed]`: reads `matrix.csv`, flies
      `order.txt` sequentially, skips valid runs, assigns attempt numbers, moves superseded attempts to
      `_attempts/`, runs validity checks and replay
- [x] Labeling script (`eval/phase1_label.py`)
- [ ] Aggregation script (`results/`)
- [x] `.gitignore` rules for `eval/phase1/**` (§14)
- [x] Sites promoted `draft → active` at the frozen versions
- [ ] Rubric thresholds (§9) confirmed
- [ ] Network access to sctsvr6 (school Wi-Fi blocks SSH; proposal "Things I will Need")
- [ ] All of the above committed; clean tree

## 13. Pilot data (not citable)

Runs in `eval/runs/` from 2026-09-20 to 2026-09-27 were flown with the p01/p02 prompts, no seeds, varying budgets
(30–50 steps, collision cap 3 or none) and `git_dirty: true`. They are **pilots**. They informed this
spec and are never cited.

What they suggest:
- Every `dynamic` pilot on s01, s02a, s02c and s03 failed. With no cap, the agent spent ~29–41 of
  40–50 steps colliding (e.g. `run_2026-09-26_1150_s02a_p02`: 34 collisions / 40 steps, final
  distance 12.45 m).
- `run_2026-09-26_1133_s02a_staticdoors` (initial arm) reached the goal in 14 steps with 0 collisions.
- Remote latency with p02: p50 ≈ 1.6 s, p95 ≈ 8.1 s per decision.

These results are consistent with H1 but prove nothing yet.

## 14. Data layout

Phase 1 data is real data and lives in its own tree, separate from the flat `eval/runs/`.

```
eval/phase1/
├── README.md                 ← index: mini-phase status table, links to summaries
├── config.lock.json          ← frozen §3 config: model, prompt sha, frame, fan, budgets, seeds, site versions
├── matrix.csv                ← all 90 planned runs + 18 shakedown
├── 1.0_shakedown/            ← same shape as below; marked not citable in phase.json
├── 1A_s01/
│   ├── phase.json            ← status, git_sha, started/finished, operator, notes
│   ├── order.txt             ← §7.4 order for this mini-phase
│   ├── runs/
│   │   └── <site>/<arm>/seed<N>/
│   │       ├── run.json
│   │       ├── decisions.jsonl
│   │       ├── steps.jsonl
│   │       ├── events.jsonl
│   │       ├── metrics.json
│   │       ├── replay.json   ← replay verdict: drift, collisions/events match
│   │       └── frames/
│   ├── labels.csv            ← §9
│   ├── summary.md            ← mini-phase table + notes
│   └── _attempts/<site>/<arm>/seed<N>/a<NN>/   ← invalid or superseded attempts, never deleted
├── 1B_s02/
├── 1C_s02v/
├── 1D_s03/
└── results/                  ← aggregate tables + figures, built only from `complete` mini-phases
```

**Naming**
- Run ID: `p1_<mp>_<site>_<arm>_seed<N>_a<NN>`, e.g. `p1_1A_s01_dynamic_seed3_a01`
- Arms: exactly `initial`, `final`, `dynamic`
- `phase.json` status: `planned` | `running` | `complete` | `superseded`
- `matrix.csv` columns: `mini_phase, site, site_version, arm, seed, run_id, attempt, status, end_reason, invalid_reason`
  (`status` ∈ `planned` | `valid` | `invalid`)

**Git**
- Committed: `README.md`, `config.lock.json`, `matrix.csv`, `phase.json`, `order.txt`, `labels.csv`,
  `summary.md`, and per run `run.json`, `metrics.json`, `decisions.jsonl`, `events.jsonl`, `replay.json`
- Ignored: `frames/`, `steps.jsonl` (regenerable by `eval/replay.py`)
- `decisions.jsonl` is committed because the model's reasoning is the one thing a rerun does not reproduce.

**Timeline:** ~90 runs × ~2 min ≈ 3–4 h of sequential compute (~30–60 min per mini-phase), plus
labeling. Fits the proposal's weeks 6–9 block (layout edge-case testing, then all Phase 1 episodes).

## 15. Changelog

| Date | Change |
|---|---|
| 2026-09-27 | Initial spec. 3 arms, 6 sites, 90 episodes, temperature 0 + spawn jitter, max 60 steps, no collision cap, mini-phases 1.0/1A–1D. |
| 2026-09-27 | §12 prerequisites built (`d100948`). `git_dirty` ignores recorded data trees (§3). Godot takes `--run-dir=`; replays of nested runs go to `<run>/replay/`; `godot.log` per run, git-ignored (§14). 1.0 shakedown complete, 18/18 valid; rubric questions open in `eval/phase1/1.0_shakedown/summary.md`. |
