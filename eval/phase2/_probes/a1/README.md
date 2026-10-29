# Probe A1: does the strategist's pick follow the item or the list position?

Plan: [docs/research/probe-plan.md](../../../../docs/research/probe-plan.md), section A. Script:
`eval/probes/a1.py`. Builds on [A0](../a0/README.md): first-listed items are picked 49–57% of the
time, later ones 8–16%. Content is worth only +8/+9 pts, but code lists its best item first.

## Belief

The model picks partly by position (Zheng 2024; Pezeshkpour 2024). If so, reordering a menu
changes the pick even though every item, and every word about it, stays the same.

## Method

- **Sample.** 300 recorded q03 strategist calls with at least 2 menu items, so 3 or more options
  counting `explore`. Taken from R19–R26N (agents a35–a38, a48, a49): all of a49's calls first,
  then a fixed-seed sample of the rest.
- **Orders.** Each call is re-asked in four orders, using the recorded user text with only the menu
  lines moved. `explore` stays last. Item ids and wording are unchanged. The schema's target enum
  follows the new order, as code would build it.
  - *rec*: the recorded order;
  - *rec2*: the recorded order again (noise control);
  - *rev*: reversed;
  - *shuf*: a fixed shuffle, different from *rec* and *rev* where the menu allows.
- **Call.** q03 system prompt, strategist schema and validator, 512 max tokens, temperature 0. All
  four orders of one call go to the same instance. Calls are split between `:8004` and the `:8006`
  copy, if N1 accepts the copy as a stand-in. The instance is recorded on every call.
- **Score:**
  - *Nn*: the share of calls where *rec* and *rec2* pick the same id (the noise floor);
  - *No*: the mean of same-id rates, *rec* vs *rev* and *rec* vs *shuf*;
  - the first-listed pick rate in each order;
  - among calls where *rec* and *rev* differ, the share where *rev*'s pick sits at the same list
    position as *rec*'s pick (position-following);
  - *rec* vs the originally recorded pick (replay fidelity).

## Gate (set before the first call)

| Result | Verdict |
|---|---|
| *Nn* − *No* ≥ 15 pts | **Holds**: order moves picks beyond noise. Next step: a round with the menu ordered by code rank, best first, probed first |
| *Nn* − *No* ≤ 5 pts | **Refuted**: picks follow the items. A drops |
| Between | No call |

**Correction to the plan.** The plan's draft gate ("first-listed rate moves ≥ 15 pts") had the sign
of the evidence backwards: a model that follows position keeps a *steady* first-listed rate across
orders. The gate above replaces it before any call. Because the noise control *rec2* measures the
noise directly, the gate does not need N1's numbers.

## Result

Pending.
