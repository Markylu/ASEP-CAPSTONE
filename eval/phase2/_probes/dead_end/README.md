# Probe dead_end: what could trigger a dead-end latch, and probe DE

For R38 ([round write-up](../../R38_dead_end_latch/README.md)). Two parts: a readout on the
recorded runs with no model, done; and probe DE, which asks the model, not yet run.

## 1. Closed-door reads as a trigger (no model)

`python eval/probes/dead_end_trigger.py` on the 120 change-arm runs of `eval/phase2/final`,
R32P and R35. The reads are the ones recorded in flight (`doorway` per strip, after `d01`).
Table in [trigger.txt](trigger.txt). Three candidate triggers:

- **asked:** a closed door read in the centre three strips. The steps `a78`'s confirmer is
  asked on.
- **strict:** the centre strip reads a closed door within 5 m, the goal within 35° of the
  heading, and the same no more than 3 steps before.
- **trail:** an asked step at the end of a straight run of 5 m or more begun at a turn of 60°
  or more.

| Group | Runs | Strict fired before the crossing | Trail fired before the crossing | Asked steps per run |
|---|---|---|---|---|
| s02 `dynamic` lost | 20 | 17 | 20 | 10–20 |
| s02 `dynamic` won | 29 | 17 | 13 | 0–16 |
| s02 `final` lost | 25 | 20 | 25 | 12–22 |
| s02 `final` won | 24 | 13 | 15 | 0–15 |
| s03 `dynamic` lost | 11 | 2 | 9 | 5–10 |
| s03 `final` lost | 2 | 2 | 2 | 7–12 |
| s03 `final` won | 9 | 1 | 1 | 0–5 |

- Neither rule separates the shut tine from the s02 hall: strict fires in 67 of 98 s02 runs
  and 2 of 11 s03 `dynamic` runs, trail in 73 and 9. The strict rule's goal condition cuts the
  tine itself, where the goal lies about 30° off the corridor.
- Asked steps by where the drone stood: 90 in the shut tine facing its door, 24 elsewhere in
  s03, 1126 in s02. Whatever answers on those steps has to say no about twelve times for every
  yes.
- The trigger is not late. All 11 s03 `dynamic` losses have an asked step in the shut tine
  facing its door, first at step 23 (median), 9 of them with 25 or more steps left. The two
  without: the door shut at steps 32 and 35.
- A closed door is sometimes read before any door has shut (R32P seed 2 at step 4, R35 seed 3
  at step 3, both in the lobby).

## 2. Probe DE: the dead-end confirmer (run 2026-11-05)

`eval/probes/dead_end.py`. Prompts `e01` ("is the drone in a dead-end corridor that ends at
that closed door?") and `e02` ("is turning back the only way on from here?"), each on the clean
frame of the 1240 asked steps: 2480 calls, one at a time, alone on sctsvr6's `:8004`
(`Qwen3-VL-30B-A3B`, remote profile, temperature 0), from a checkout of `bfd0cf6` in the
`asep-phase1` image, on the operator's instruction ("Run probe DE"). No failed call; median 927
and 768 ms. Sample, calls and [score.txt](score.txt) are here; the frames stay on the host. The
gate was set in the round write-up before any call.

| Readout | Gate | `e01` | `e02` |
|---|---|---|---|
| Yes on steps in the shut tine facing its door | at least 80% | 85/90 (94%) | **15/90 (17%)** |
| Yes on s02 steps | at most 5% | **420/1126 (37%)** | 15/1126 (1%) |
| Yes elsewhere in s03 (no gate) | | 20/24 | 4/24 |
| s03 `dynamic` runs the rule fires in with 25 or more steps left | at least 7 of 11 | 8 | **3** |
| s02 runs the rule fires in before the crossing | at most 5 of 88 | **65** (21 of them won) | 0 |
| Asked steps answered | all | 1240 | 1240 |
| **Gate** | | **fail** | **fail** |

**Neither prompt passes.** `e01` knows the tine and calls the hall a corridor one time in
three; `e02` almost never says yes anywhere. By the rule set beforehand R38 is not flown and
`a78` is dropped.

What the answers look like ([breakdown.txt](breakdown.txt), `dead_end.py breakdown`, read
after the gate, so a description and not a test):

| s02 steps | `e01` yes | | s02 steps | `e01` yes |
|---|---|---|---|---|
| 8 m or more from the divider | 6/427 (1%) | | within 30° of square to it | 88/666 (13%) |
| 4–8 m | 65/236 (28%) | | 30–60° off square | 122/152 (80%) |
| 2–4 m | 159/230 (69%) | | 60° or more | 210/308 (68%) |
| under 2 m | 189/225 (84%) | | | |

- `e01`'s false yes is the look along a wall from close to it, the look probe
  [door_read](../door_read/README.md) found behind the phantom doorways. Its reasons say so:
  "the walls on the left and right are close to the drone and run away from the camera,
  forming a narrow passage" at (4.2, −11.5), heading 125°, in the s02a hall. Far from the wall
  and square to it the hall is read as a hall (1%).
- The out-of-view sites draw more of it (s02a 49%, s02c 50%) than the in-view ones (s02va 26%,
  s02vc 30%). A step with two or three closed doors in the centre strips is rarely called a
  corridor (12% and 8%); one closed door, half the time.
- In the shut tine `e01` says yes at every range (84% inside 2 m of the door wall, 100% from
  4 m out).
- `e02` says no in the tine for a reason that is wrong about the image: "to the left of the
  door ... the floor continues along a wall ... the drone can fly past the door on either
  side".
  Asked about ways on, the model counts the floor beside the door as one.
- Yes from both prompts on the same step: 13/90 in the shut tine, 10/1126 in s02. `e02` alone
  has a yes before the crossing in 15 of 88 s02 runs and in 8 of 11 s03 `dynamic` runs (one
  of the eight in the lobby at step 3, before any door shut).

Where this leaves the question a69 ended on: asked directly, the model can tell the tine from
the hall only from where the hall looks like a hall. Close to the divider and along it, where
the s02 runs spend their steps, one frame is not enough, for this question as for doorways.
Every call here saw one frame and nothing else, so this says nothing about a model that also
holds a record of its earlier steps.
