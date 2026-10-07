# Phase 2 Todo

Phase 1 is complete: 90/90 citable runs are valid, plus 18/18 for the shakedown. `initial`
succeeded 5/5 everywhere except s03. `final` and `dynamic` failed 0/5 everywhere. Failure
modes for each site are in `eval/phase1/<mini-phase>/summary.md`.

**Round design:** 6 sites × `dynamic` × seed 1 = 6 runs per round. This is screening and is
not citable. The final round flies the full Phase 1 protocol: 6 × 3 × 5 = 90 runs, citable.

---

## 0. Close Phase 1

- [ ] Move uncommitted demo work to branch `media/demo-videos`
  - [ ] `first-project/tools/broll.gd` + `.uid`
  - [ ] `eval/make_bonk_grid.py`, `eval/make_site_demo.py`
  - [ ] Decide on `eval/phase1/1A_s01/run_grid.png` (commit or ignore)
- [ ] Confirm `phase1-shakedown` tree is clean
- [ ] Review and confirm labels myself (reviewer is currently Claude)
  - [ ] 1A `labels.csv`
  - [ ] 1Ba `labels.csv`
  - [ ] 1Bc `labels.csv`
  - [ ] 1Ca `labels.csv`
  - [ ] 1Cc `labels.csv`
  - [ ] 1D `labels.csv`
- [ ] Build aggregation script → `eval/phase1/results/` (test plan §12, unchecked)
  - [ ] §11 main table per layout + pooled row
  - [ ] Fisher contrasts a–d
  - [ ] Reuse `eval/runlib/stats.py`
  - [ ] Regenerates identically twice
- [ ] Add `.github/pull_request_template.md` (clean tree, lock matches, n valid, labels reviewed, summary written)
- [ ] PR `phase1-shakedown` → `main`
- [ ] Merge PR
- [ ] Tag `phase1-complete`
- [ ] Leave `linux-headless` unmerged

## 1. Phase 2 setup (branch `phase2/setup`)

- [ ] Create GitHub milestone "Phase 2"
- [ ] Add `.github/ISSUE_TEMPLATE/round.md` (blank fields: change, why, expected outcome, drop criterion)
- [ ] Write `docs/phase2-test-plan.md`
  - [ ] Frozen config: model, temp 0, frame, action fan, 60 steps, no collision cap, Phase 1 site versions
  - [ ] Round protocol: 6 sites, `dynamic`, seed 1
  - [ ] Final round protocol: full 90 runs
  - [ ] Validity rules (reuse Phase 1 §10)
  - [ ] Changelog section
- [ ] Add agent identity
  - [ ] `agent_version` + `agent_sha` (prompt text + feature flags)
  - [ ] Record in `run.json` / `metrics.json`
  - [ ] Lock check rejects a mismatched agent
  - [ ] Rule: never edit an old version
- [ ] Create `eval/phase2/` tree (`README.md` index, `R<N>_<slug>/` per round)
- [ ] Generalise `eval/phase1.py` to take phase root + round definition
- [ ] Reuse `eval/phase1_label.py` rubric unchanged
- [ ] R0 baseline: link Phase 1 `dynamic` seed-1 runs (no new flying)
- [ ] Shakedown round with fake decider: 6/6 valid, agent fields recorded, replay exact
- [ ] PR → `main`, merge, tag `p2-setup`

## 2. Per round (repeat for R1, R2, …)

- [ ] Open Issue from `round.md` template, assign to "Phase 2" milestone
- [ ] Create branch `phase2/r<N>-<slug>`
- [ ] Commit 1: implement change as a new agent version
- [ ] Preflight: clean tree, tunnel up, lock matches
- [ ] Fly 6 runs (one SHA for the whole round)
- [ ] All 6 valid per §10; rerun invalid ones only
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
