# Prior work for the next round: spatial memory and prompting

Written 2026-10-29, after R25D (14/18) and R26/R26N. A literature scan, read against the agent
on `phase2/r13-verify` (orchestrated agent, code-written memory `a17b`, navigator `p17`, door
confirmer `d01`). Phase 2 rules apply to every idea here: the model (`Qwen3-VL-30B-A3B`, temperature
0) and its weights stay fixed, and the memory is built from pose and perceiver readings only.

Sources were read as abstracts and summaries, not full papers. Check numbers in the paper before
citing them in a write-up.

## Where we are (what the ideas below aim at)

| Problem | Evidence |
|---|---|
| Run-to-run noise: the same step-0 frame is read differently at temperature 0; the `a17b` family expects 11.3 ± 1.4 | `R25D/.../why_14.md` §4 |
| s02: the door, once near. Within 3 m of the open door, 57% get through (`a17b`) | `why_14.md` §2 |
| s03: stuck in the shut tine for 34–46 steps. The way out was listed on 25 of 33 dead-end calls and picked 0 times. R26's "other way" menu item scored 9/18 | `R22K/.../s03_tines_analysis.md`, R26 README |
| Extra machinery costs runs: along-wall items, "other way" and the goal confirmer all failed to carry | `why_14.md` §3 |

## 1. What the literature says about our design

**Code doing the spatial reasoning is the right call.** CogEval (Momennejad et al., NeurIPS 2023)
found that LLMs handed a cognitive map in text still plan badly over it: they make up invalid paths
and get stuck in loops. VSI-Bench (Yang et al., CVPR 2025) names spatial reasoning as the main
bottleneck for MLLMs. SayPlan (Rana et al., CoRL 2023) gives path-finding to a classical planner so
the LLM plans over a shorter horizon. Our R6/R7 finding (the model never compared two positions)
matches all three. Phase 2's `spatial.py` approach (code judges, the model sees verdicts tied to
actions) is the pattern the field converged on.

**Explicit cognitive maps help, but the big gains needed training.** VSI-Bench: when a model
writes out a cognitive map before answering, its distance judgements improve. MindCube (Wang et al.,
ICLR 2026): "map then reason" was the best of the approaches tested. Most of its gain (37.8% → ~58%)
came with fine-tuning, which Phase 2 does not allow. Expect a small effect at most from asking our
frozen model to draw a map.

**Frontiers are first-class objects in the systems that work.** VLFM (Yokoyama et al., 2023) and
3D-Mem (Yang et al., CVPR 2025) both keep a list of frontiers (unexplored edges) and pick one to
explore, with code driving the motion. 3D-Mem shows the VLM an image per frontier ("frontier
snapshots") and lets it choose between exploring and answering. MapGPT (Chen et al., ACL 2024) turns
a topological map into the prompt as text and adds explicit backtracking, so a zero-shot GPT-4
agent explores globally and does not stay local.

**Memory has to forget in a changing world.** DynaMem (Liu et al., 2024) adds and removes map
points as objects move or disappear, and reports more than twice the success of static-memory
systems on moving objects. Newer benchmarks (LiSoNav-Eval, arXiv 2610.10125; EvoNav-Bench, arXiv
2609.08292) test exactly that: memory that was right goes stale, and the agent has to notice on a
revisit. Our `dynamic` arm is a door that slams, the same problem in small.

## 2. What the literature says about prompting

| Finding | Source | What it means for us |
|---|---|---|
| Chain-of-thought, self-consistency and tree-of-thoughts did not improve spatial QA | VSI-Bench | More reasoning text in the navigator is unlikely to help on its own |
| CoT can hurt visual recognition (o1-preview up to −36 pts vs GPT-4o) | Liu et al., "Mind Your Step", ICML 2025 | Keep the perceiver a pure reader: no "explain first" before it classifies strips |
| Strict JSON formats hurt reasoning but can help classification | Tam et al., "Let Me Speak Freely?", EMNLP 2024 | Constrained JSON suits the perceiver. For the strategist, let it write freely first and then extract the answer |
| Option order and labels move answers: 13–75 pt swings; models favour some option IDs | Zheng et al., ICLR 2024; Pezeshkpour & Hruschka, NAACL Findings 2024 | Our menus (strategist targets, navigator actions) may carry position bias. s03's tie always went to `along_left` |
| One irrelevant sentence sharply lowers accuracy. "Ignore irrelevant info" and self-consistency help | Shi et al., ICML 2023 (GSM-IC) | Fits "fewer moving parts". Each added menu item or note can cost runs |
| Marking candidates on the image (numbered marks, arrows) turns spatial choice into visual QA | PIVOT (Nasiriany et al., ICML 2024); VLMnav (Goetting et al., 2024); egocentric disjoint-frames study (arXiv 2505.24257): open-source models gain more from marks | Draw the memory's verdicts onto the navigator frame, not only into text |
| VLMs confuse left and right and front and back; some lean toward "right" | arXiv 2606.15200; arXiv 2603.15624 | A left/right lean in the perceiver would bias s02 side choice and s03 tine choice |

## 3. The noise problem has a known cause

Thinking Machines Lab ("Defeating Nondeterminism in LLM Inference", He, Sept 2025) showed that
temperature 0 does not give identical outputs on a shared server. A request's numbers depend on
which other requests share its batch (RMSNorm, matmul and attention kernels change their reduction
order with batch size). On Qwen3-235B at temperature 0, they got 80 different completions out of
1000. With batch-invariant kernels all 1000 were the same. Our 8 lanes on one vLLM is the textbook
case for this.

vLLM now has `VLLM_BATCH_INVARIANT=1` (docs: `docs.vllm.ai/.../features/batch_invariance/`). It needs
NVIDIA compute capability ≥ 8.0, which H100 meets. The docs' examples are dense models. **I found no
statement that Qwen3 MoE (our 30B-A3B) is supported.** Expect it to run slower: reports range from
about 25–60% lower throughput.

**This is the operator's call.** It means restarting the shared vLLM on sctsvr6, which would change
the host every earlier round flew on. That is a phase-level decision, not a round.

## 4. What the code does today (a49, read from `phase2/r13-verify`)

Read before the candidates below. Several of them change shape once the code is known.

| Topic | Today | Where |
|---|---|---|
| Strategist | a49 uses q03, asked only when the goal way is walled or blocked, or on a stall. Menu: frontiers (code score) → doorways (creation order) → `back_to_step_N` → `explore`. IDs are semantic (`unexplored_1`, `doorway_A`), not letters | `planner.route` L128, `planner.search_menu` L560, `planner.detour_situation` L418 |
| Navigator list | Fixed by angle: `[0]` turn around first, then sharp left → sharp right. Up to 3 tags per action | `prompt.render_orchestrated` L1444, `spatial.project` L1222 |
| Schemas | Every stage writes `reason` first: perceiver g05 (describes each strip's floor end before classifying), strategist, navigator. Sent as strict `json_schema` | `schema.py` L28/L182/L266, `vlm.call_structured` L886 |
| Doorways | Newest reading wins, both ways (open re-opens, closed or short floor closes). Listed only once seen twice; dropped after 10 steps unseen | `spatial._add_opening` L699, `_close_openings` L712, `listed_openings` L762 |
| Other records | Seen ("searched") cells and blocks **only accumulate**. A later successful move never clears a block. Stop-walls clear only on a visit | `spatial.py` L591–602, L692 |
| Regions | No notion of a region or a side of the fork. The only "nothing left" check (`ask = "exhausted"`) belongs to the staged policies a17–a24, not a49 | `planner.py` L719 |
| Frame marks | Godot draws the fan lines and numbered discs. No memory element (doorway, target, frontier) is drawn. The server passes `frame_b64` through untouched | `first-project/common/vlmnav/action_overlay.gd` |

What changes as a result:
- **E** is not about doorways. Doorways already update newest-first. The question is the blocks and "searched" cells that never expire.
- **A**: the navigator's order is geometry, so position and angle are confounded there. The strategist menu is where order can be permuted cleanly (text only).
- **B** can reuse the staged policies' `exhausted` logic as a starting point.
- **D** must be drawn server-side on `frame_b64`, or in `action_overlay.gd`.
- Every stage reasons first under strict JSON, so "Mind Your Step" and "Let Me Speak Freely" are both directly testable.

## 5. Candidate next rounds, ranked

Each is one change, as the Phase 2 rules require. Costs are against the 4-H100 limit (shared vLLM
on :8004, 8 lanes).

### A. Offline first, no GPU: menu position bias
Count, over every recorded strategist and navigator call (R9 onward), how often each list position
is picked, against how often it is the "toward"/best item. Also count left versus right picks when
items tie (s03 crossbar). If position or left/right bias shows up, the fix is cheap: order items by
code rank, or shuffle them and check that picks follow content. No flight needed to learn
whether this matters. *Lit: Zheng 2024, Pezeshkpour 2024.*

### B. Frontier exhaustion handled by code (s03)
The model saw the way out on 25 of 33 calls and never took it. R26 put it in the menu again and
lost. The systems that work (VLFM, 3D-Mem, classical frontier exploration) do not ask: when a region
has no open frontier left, code moves the target to the best remaining frontier elsewhere. Proposal:
once `search_frontiers` finds no unreached frontier on the drone's side of the fork (or within N m),
code sets the target to the nearest frontier across the crossbar. This follows R11's "goal by
default, detours on demand", which already gives target choice to code. Probe on the five s03
tine-failure runs by replay: does the rule fire within 5 steps of reaching the exit wall, and
never in `initial`? *Lit: VLFM, 3D-Mem, MapGPT backtracking, CogEval loops.*

### C. Perceiver read twice: mirrored frame (noise, s02 side choice)
Temperature is locked at 0, so sampling more answers is not an option. Test-time augmentation is.
Read the clean frame and its left-right mirror, swap the mirror's strip labels back, and keep
readings the two agree on. Mark disagreeing strips "unsure". This attacks both the step-0 lottery and
any left/right lean. Costs a second perceiver call per step (about +1.5 s per step at the P1 fit, and
more load on the shared vLLM). Probe: on recorded frames with ground truth, agreement rate and
accuracy of agreed readings against single reads. *Lit: self-consistency (Wang et al. 2022; Shi 2023
for its effect against distraction), egocentric left/right studies.*

### D. Doorway drawn on the navigator frame (s02 last 3 m)
Within 3 m of the open door, 43% still fail. Project the memory's open-doorway position onto the
navigator's annotated frame as a marked target, so "go through" is a visible mark and not only a
note. Probe: R20–R26N s02 calls within 3 m of the open door, rate of picking the through move. *Lit:
PIVOT, VLMnav, Set-of-Mark; open-source models gain most from marks.*

### E. Stale blocks and "searched" cells (`dynamic`)
Doorways already update newest-first (§4). Blocks and seen cells never expire. After a door
switch, an action toward the newly opened door can still carry "blocked here before" or "searched
already this way". Count how often that happens first (no model). It becomes a round only if it is
common. *Lit: DynaMem, LiSoNav, EvoNav.*

### F. Perceiver without reasoning first (prompt format)
g05 writes `reason` before it classifies strips. "Mind Your Step" predicts a pure reader does as
well or better on visual classification. Probe it on the same frames as C. *Lit: Liu 2025, Tam 2024.*

Probes for every candidate: [probe-plan.md](probe-plan.md).

### Not recommended now
- **Asking the model to draw a map** (VoT, MindCube style): the gains needed training. Our code map
  already does the job.
- **More reasoning in the navigator**: VSI-Bench saw no gain, and "Mind Your Step" shows losses on
  visual tasks.
- **Calibrated stopping** (Explore until Confident, Ren et al. RSS 2024): built for question
  answering, and our confirmers already showed no consistent effect.

## Sources

- Momennejad et al., CogEval, NeurIPS 2023: https://arxiv.org/pdf/2309.15129
- Yang et al., Thinking in Space (VSI-Bench), CVPR 2025: https://arxiv.org/html/2412.14171v1
- Wang et al., MindCube, ICLR 2026: https://arxiv.org/abs/2506.21458v1
- Rana et al., SayPlan, CoRL 2023: https://proceedings.mlr.press/v229/rana23a.html
- Yokoyama et al., VLFM: https://arxiv.org/pdf/2312.03275
- Yang et al., 3D-Mem, CVPR 2025: https://arxiv.org/pdf/2411.17735
- Chen et al., MapGPT, ACL 2024: https://arxiv.org/pdf/2401.07314
- Liu et al., DynaMem: https://huggingface.co/papers/2411.04999
- LiSoNav: https://arxiv.org/html/2610.10125v1 · EvoNav-Bench: https://arxiv.org/html/2609.08292v2
- Goetting et al., VLMnav: https://arxiv.org/pdf/2411.05755
- Nasiriany et al., PIVOT, ICML 2024: https://huggingface.co/papers/2402.07872
- Egocentric reasoning across disjoint frames: https://arxiv.org/pdf/2505.24257
- Left/right confusion: https://arxiv.org/pdf/2606.15200, https://arxiv.org/pdf/2603.15624
- Liu et al., Mind Your Step, ICML 2025: https://arxiv.org/abs/2410.21333v4
- Tam et al., Let Me Speak Freely?, EMNLP 2024: https://themoonlight.io/review/let-me-speak-freely-a-study-on-the-impact-of-format-restrictions-on-performance-of-large-language-models
- Zheng et al., LLMs Are Not Robust Multiple Choice Selectors, ICLR 2024: https://mlanthology.org/iclr/2024/zheng2024iclr-large
- Pezeshkpour & Hruschka, option order sensitivity: https://arxiv.org/pdf/2308.11483
- Shi et al., GSM-IC, ICML 2023: https://arxiv.org/pdf/2302.00093
- Ren et al., Explore until Confident, RSS 2024: https://arxiv.org/pdf/2403.15941
- Nondeterminism and batch invariance: https://www.spheron.network/blog/vllm-batch-invariance-why-temperature-0-isnt-deterministic/ ;
  vLLM docs: https://docs.vllm.ai/en/v0.32.0/features/batch_invariance/
