"""a95's survey start on flown records: the line test on where the drone is
now, not on every position of its trail. No model.

An approximation of planner.survey_start from the records (the centre strip's
closed read from the perceiver, the heading within goal_deg of the direct
line, run_m along it, the position within line_m of it; the station guard is
not replayed): per run, the step the survey started at (old, from the planner
records) and the step the position-now test first passes (new). Prints the
runs where they differ. eval/phase2/R57_survey_line_now/README.md.

    python eval/probes/a95_survey_start.py R44,R45,R46,R47,R49,R51,R52,R53,R54,R55
"""
import json, math, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from server.decider import spatial, agent as agents
GOAL=(-12.0,0.0)
c = agents.get("a93").features["orchestrator"]["pathfinder"]["survey"]
folders = sys.argv[1].split(",")
newstart=0; same=0; none_both=0; rows_out=[]
for folder in folders:
    for f in sorted((REPO/"eval"/"phase2").glob(folder+"*/runs/*/*/*/decisions.jsonl")):
        site, arm, seed = f.parts[-4], f.parts[-3], f.parts[-2]
        rows=[json.loads(l) for l in open(f)]
        met=json.loads((f.parent/"metrics.json").read_text()); won=bool(met.get("goal_reached"))
        old=None
        for r in rows:
            sv=(r.get("planner") or {}).get("survey")
            if sv: old=sv.get("step"); break
        spawn=None; trail=[]; new=None; new_left=None
        for r in rows:
            here=spatial.pose_xyh((r.get("manifest") or {}).get("pose"))
            if here is None: continue
            if spawn is None: spawn=here[:2]
            trail.append(here)
            if (r.get("planner") or {}).get("latch"): break   # latched: the survey does not run
            lanes=((r.get("perceiver") or {}).get("result") or {}).get("lanes") or []
            centre_closed=any(l.get("strip")=="centre" and l.get("doorway")=="closed" for l in lanes)
            if not centre_closed: continue
            axis=spatial.bearing(spawn,GOAL)
            if abs(spatial.wrap(here[2]-axis))>c["goal_deg"]: continue
            rad=math.radians(axis); dx=here[0]-spawn[0]; dy=here[1]-spawn[1]
            along=dx*math.cos(rad)+dy*math.sin(rad); left=-dx*math.sin(rad)+dy*math.cos(rad)
            if along < c["run_m"]: continue
            if abs(left) > c["line_m"]: continue
            new=r["step"]; new_left=left; break
        tag = "same" if (old is not None and new==old) else ("NEW" if (old is None and new is not None) else ("none" if old is None and new is None else "DIFF old %s new %s"%(old,new)))
        if tag=="NEW" or tag.startswith("DIFF") or site=="s03" and new is not None:
            rows_out.append("%-4s %-5s %-7s %s %s old %-4s new %-4s left %s"%(folder.split("_")[0], site, arm, seed, "W" if won else "L", old, new, None if new_left is None else round(new_left,1)))
        if tag=="same": same+=1
        elif tag=="NEW": newstart+=1
        elif tag=="none": none_both+=1
print("same", same, "new starts", newstart, "none either way", none_both)
print("\n".join(rows_out))
