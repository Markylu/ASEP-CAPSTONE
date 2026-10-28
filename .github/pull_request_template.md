<!-- Phase 2 round PRs are never merged (docs/phase2-test-plan.md §4.2). Base = the previous
     round's branch, so the diff is this round only. Leave the PR open as the iteration record. -->

## What this PR does

<!-- One or two sentences. For a round: what changed in the agent, and the result. -->

## Results

<!-- Paste the round or mini-phase table, plus the change vs the best result so far. Delete for code-only PRs. -->

## Checklist

- [ ] Round `README.md` (hypothesis, predictions) committed before the first run; Outcome line filled
- [ ] Tree clean at the flown SHA (`git_dirty: false` in every `run.json`)
- [ ] `config.lock.json` matches the spec; prompt / agent sha matches
- [ ] Every planned run valid (§10); invalid attempts kept in `_attempts/`
- [ ] Every valid run replayed exactly (`replay.json`)
- [ ] `labels.csv` complete and reviewed by the operator
- [ ] `summary.md` written; `phase.json` status `complete`
- [ ] Spec changelog updated if anything in the spec changed
