from tl import *
from geo import *
from val import wfun
import collections
C=collections.Counter()
for s in SITES:
  for a in ARMS:
    rows,met,G=load('R11',s,a)
    for r in rows:
      p=r['planner'] or {}
      if not p.get('ask'): continue
      f=wfun('R11',s,a,r['step'])
      want=spatial.bearing((r['x'],r['y']),G)
      cands=[]
      for k,act in r['acts'].items():
        if act.get('turn_around'): continue
        h=spatial.action_heading(act,r['h'])
        if abs(spatial.wrap(h-want))<=55:
          d=ray(f,r['x'],r['y'],h)
          cands.append((k,round(d,1)))
      truly_open=[c for c in cands if c[1]-0.2>=1.65]
      # also: would a 1.7 m move toward goal reduce distance? whether goal side reachable at all is separate
      C[(p['ask'], 'true_open_move_existed' if truly_open else 'truly_shut')]+=1
      print(s,a,r['step'],p['ask'],'cands',cands,'lanes',r['lanes'])
print(C)
