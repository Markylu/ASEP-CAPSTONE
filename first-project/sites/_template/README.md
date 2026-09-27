# sNN — Title

**Hypothesis:** …
**Class:** geometry | lighting | subject | texture | composite · **Status:** draft · **Version:** 1

## The condition

What is being manipulated, and what the agent is expected to do about it.

## Build log

- v1 YYYY-MM-DD — initial greybox

## Known issues

-

## Results referencing this site

- _(none yet)_

---

## Build checklist (notes/PLAN.md §7)

A site is not `active` until every box is checked.

- [ ] Hypothesis written **before** any geometry exists
- [ ] Folder copied from `sites/_template/`
- [ ] `site.json` filled; `id` and `scene` updated — **a stale `scene` path files
      every run under the wrong ID**, which `SiteManifest` warns about at launch
- [ ] Scene built to the notes/PLAN.md §5.2 skeleton, greybox only
- [ ] Real-world scale verified
- [ ] `Spawn` placed and oriented; the rig snaps to it, so the marker is the
      authority on the start pose
- [ ] Goal placed; line of sight from spawn checked deliberately, not assumed
- [ ] Manual walkthrough — no leaks, no z-fighting, no unreachable goal
- [ ] Headless run clean end to end
- [ ] Replay determinism verified (`python eval/replay.py eval/runs/<id>`)
- [ ] Baseline run recorded and logged above
- [ ] `status: active`, version bumped, committed
