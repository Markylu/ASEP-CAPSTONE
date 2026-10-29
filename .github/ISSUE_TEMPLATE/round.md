---
name: Phase 2 round
about: One change to the agent, flown as one screening round (docs/phase2-test-plan.md §4)
title: "R<N>: "
labels: []
milestone: Phase 2
---

<!-- The full write-up lives in eval/phase2/R<N>_<slug>/README.md, committed before flying
     (docs/phase2-test-plan.md §4.1). Keep this issue short and link it. -->

Write-up: `eval/phase2/R<N>_<slug>/README.md`
Branch: `phase2/r<N>-<slug>` (from the previous round's tip). PR: never merged; close this issue by hand.

## Change

<!-- What this round changes in the agent. One change per round. -->

## Why

<!-- Which Phase 1 / earlier-round evidence points at this. Link runs or summaries. -->

## Expected outcome

<!-- Which arms and sites should move, and how. -->

## Drop criterion

<!-- What result means this change is not carried forward. -->

## Identity

- Agent version: `a<NN>` (prompt `p<NN>`, features: …)
- Agent sha: <!-- from `python -c "from server.decider import agent; print(agent.describe('a<NN>'))"` -->
- Builds on: <!-- previous agent this round extends -->
