# Phase 2 Todo

Phase 1 is complete: 90/90 citable runs are valid, plus 18/18 for the shakedown. `initial`
succeeded 5/5 everywhere except s03. `final` and `dynamic` failed 0/5 everywhere. Failure
modes for each site are in `eval/phase1/<mini-phase>/summary.md`.

**Round design:** 6 sites × 3 arms (`initial`, `final`, `dynamic`) × seed 1 = 18 runs per round.
This is screening and is not citable. The final round flies the full Phase 1 protocol: 6 × 3 × 5 = 90 runs, citable.

---

## 0. Close Phase 1

- [x] Move uncommitted demo work to branch `media/demo-videos`
  - [x] `first-project/tools/broll.gd` + `.uid`
  - [x] `eval/make_bonk_grid.py`, `eval/make_site_demo.py`
  - [x] Decide on `eval/phase1/1A_s01/run_grid.png` (commit or ignore)
- [x] Confirm `phase1-shakedown` tree is clean
- [x] Review and confirm labels myself (reviewer is currently Claude)
  - [x] 1A `labels.csv`
  - [x] 1Ba `labels.csv`
  - [x] 1Bc `labels.csv`
  - [x] 1Ca `labels.csv`
  - [x] 1Cc `labels.csv`
  - [x] 1D `labels.csv`
- [x] Build aggregation script → `eval/phase1/results/` (test plan §12, unchecked)
  - [x] §11 main table per layout + pooled row
  - [x] Fisher contrasts a–d
  - [x] Reuse `eval/runlib/stats.py`
  - [x] Regenerates identically twice
- [x] Add `.github/pull_request_template.md` (clean tree, lock matches, n valid, labels reviewed, summary written)
- [x] PR `phase1-shakedown` → `main`
- [x] Merge PR
- [x] Tag `phase1-complete`
- [x] Leave `linux-headless` unmerged

## 1. Phase 2 setup (branch `phase2/setup`)

- [ ] Create GitHub milestone "Phase 2"
- [x] Add `.github/ISSUE_TEMPLATE/round.md` (blank fields: change, why, expected outcome, drop criterion)
- [x] Write `docs/phase2-test-plan.md`
  - [x] Frozen config: model, temp 0, frame, action fan, 60 steps, no collision cap, Phase 1 site versions
  - [x] Round protocol: 6 sites × 3 arms, seed 1 (18 runs)
  - [x] Final round protocol: full 90 runs
  - [x] Validity rules (reuse Phase 1 §10)
  - [x] Changelog section
- [x] Add agent identity
  - [x] `agent_version` + `agent_sha` (prompt text + feature flags)
  - [x] Record in `run.json` / `metrics.json`
  - [x] Lock check rejects a mismatched agent
  - [x] Rule: never edit an old version
- [x] Create `eval/phase2/` tree (`README.md` index, `R<N>_<slug>/` per round)
- [x] Generalise `eval/phase1.py` to take phase root + round definition
- [x] Reuse `eval/phase1_label.py` rubric unchanged
- [x] R0 baseline: Phase 1 seed-1 runs, all 3 arms (no new flying)
- [ ] Shakedown round `P2.0` with fake decider: 18/18 valid, agent fields recorded, replay exact
- [ ] PR → `main`, merge, tag `p2-setup`

## 2. Per round (repeat for R1, R2, …)

- [ ] Open Issue from `round.md` template, assign to "Phase 2" milestone
- [ ] Create branch `phase2/r<N>-<slug>`
- [ ] Commit 1: implement change as a new agent version
- [ ] Preflight: clean tree, tunnel up, lock matches
- [ ] Fly 18 runs (one SHA for the whole round)
- [ ] All 18 valid per §10; rerun invalid ones only
- [ ] Replay every run
- [ ] Label: auto pre-label + manual review
- [ ] Write `summary.md`
- [ ] Commit 2: runs + labels + summary
- [ ] PR closes Issue; body has round table + delta vs best so far
- [ ] Merge (even if the round didn't help)
- [ ] Tag `p2-r<N>`
- [ ] Decide whether the change carries into the next round

## 3. Final round

- [ ] Freeze chosen agent in new `config.lock.json`
- [ ] Fly full 90 runs under `eval/phase2/final/`
- [ ] Validate, replay, label all runs
- [ ] Results: §11 table + Phase 1 vs Phase 2 per cell
- [ ] PR → `main`, merge, tag `phase2-complete`

## Housekeeping

- [ ] Rename roadmap phases in `notes/PLAN.md` §11 (its "Phase 2" ≠ proposal Phase 2)
- [ ] Tunnel down mid-round → stop and tell operator (never restart it)
