## What this PR does

<!-- One or two sentences. For a round: what changed in the agent, and the result. -->

## Results

<!-- Paste the round or mini-phase table, plus the change vs the best result so far. Delete for code-only PRs. -->

## Checklist

- [ ] Tree clean at the flown SHA (`git_dirty: false` in every `run.json`)
- [ ] `config.lock.json` matches the spec; prompt / agent sha matches
- [ ] Every planned run valid (§10); invalid attempts kept in `_attempts/`
- [ ] Every valid run replayed exactly (`replay.json`)
- [ ] `labels.csv` complete and reviewed by the operator
- [ ] `summary.md` written; `phase.json` status `complete`
- [ ] Spec changelog updated if anything in the spec changed
