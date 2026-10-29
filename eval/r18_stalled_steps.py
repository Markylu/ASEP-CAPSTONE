"""R18: steps spent on a detour that is not getting nearer (from the records).

A step counts when the standing target is not the goal, has stood for the last
4 steps, and those 4 moves brought the drone under 0.5 m nearer it while it is
still over 1.5 m away. Printed per round: the count, by target kind, the runs
with most, and a histogram of the distance to the target (m).

    python3 eval/r18_stalled_steps.py eval/phase2/R11_goal_default/runs ...
"""
import json, glob, math, sys, collections
def pos(r):
    p=r["manifest"]["pose"]["position"]; return (p[0], -p[2])
for root in sys.argv[1:]:
    tot=stall=runs=0; D=[]; per=collections.Counter(); kinds=collections.Counter()
    for f in sorted(glob.glob(root+"/*/*/seed1/decisions.jsonl")):
        rows=[json.loads(l) for l in open(f)]
        runs+=1
        for i,r in enumerate(rows):
            t=r.get("target"); tot+=1
            if not isinstance(t,dict) or i<4: continue
            prev=rows[i-4].get("target")
            if not isinstance(prev,dict) or (prev.get("x"),prev.get("y"),prev.get("id"))!=(t.get("x"),t.get("y"),t.get("id")): continue
            if t.get("kind")=="goal": continue
            d0=math.dist(pos(rows[i-4]),(t["x"],t["y"])); d1=math.dist(pos(r),(t["x"],t["y"]))
            if d0-d1<0.5 and d1>1.5:
                stall+=1; D.append(round(d1)); per[f.split("/")[-4]+"/"+f.split("/")[-3]]+=1; kinds[t.get("kind")]+=1
    print(root.split("/")[-2] if "phase2" in root else root[-20:], "runs",runs,"steps",tot,"stalled-on-detour",stall, dict(kinds), per.most_common(4), sorted(collections.Counter(D).items()))
