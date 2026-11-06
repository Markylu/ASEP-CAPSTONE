"""Where a80's wall survey would start, on flown records. No model.

Open loop, up to the starting step only (before it a80 is a66): per run, the
first step planner.survey_start fires at, where the drone stood, and the
stations it would take. The survey must start early in the s02 change arms
and never in an initial arm, in s03 or in s01.

    python eval/probes/a80_start.py [folders, comma separated]
"""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "eval" / "probes"))
FOLDERS = sys.argv[1] if len(sys.argv) > 1 else "final,R32P_repeat_a66,R35_wall_turn_only,R30_pathfinder"
import dead_end_trigger as trigger
from a73_replay import load, metrics, xy
from common import spatial, switch_step
from server.decider import agent as agents, planner
P = agents.PATHFINDER_A80
cfg = spatial.config_for(agents.get("a66").features["orchestrator"])
tot = {}
for folder in FOLDERS.split(","):
    for run in trigger.run_dirs(folder):
        site, arm, seed = run.parts[-3], run.parts[-2], run.parts[-1]
        rows = [r for r in load(run) if "step" in r and r.get("manifest")]
        met = metrics(run)
        recs = []
        hit = None
        crossed = None
        for r in rows:
            man = r["manifest"]; here = xy(r)
            if here is None: continue
            if crossed is None and here[0] < (-7.0 if site == "s03" else 0.0): crossed = r["step"]
            mem = spatial.rebuild(recs, man, (r.get("perceiver") or {}).get("result"), cfg)
            recs.append(r)
            gp = (man.get("goal") or {}).get("position")
            if gp is None or hit is not None: continue
            g = spatial.pose_xyh({"position": gp, "yaw": 0.0})
            start = spatial.cell(here[:2])
            cm = spatial.CostMap(mem, planner.stall_cells_from(recs[:-1], r["step"]), P, include=(start, spatial.cell(g[:2])), start=start)
            sv = planner.survey_start(mem, cm, here, r["step"], (g[0], g[1]), recs[:-1], P["survey"])
            if sv is not None:
                hit = (r["step"], here, sv)
        key = ("s03" if site == "s03" else "s01" if site == "s01" else "s02", arm, "won" if met.get("goal_reached") else "lost")
        t = tot.setdefault(key, [0, 0, 0])
        t[0] += 1; t[1] += hit is not None; t[2] += hit is not None and (crossed is None or hit[0] < crossed)
        print("{:5s} {:6s} {:8s} {:6s} {:4s} sw {} crossed {} | {}".format(folder.split("_")[0], site, arm, seed, key[2], switch_step(met), crossed,
              "-" if hit is None else "start {} at ({:.1f},{:.1f}) h{:.0f} axis {} wall_m {} order {}".format(hit[0], hit[1][0], hit[1][1], hit[1][2], hit[2]["axis_deg"], hit[2]["wall"], hit[2]["order"])), flush=True)
for k in sorted(tot):
    print(k, "runs", tot[k][0], "started", tot[k][1], "before crossing", tot[k][2])
