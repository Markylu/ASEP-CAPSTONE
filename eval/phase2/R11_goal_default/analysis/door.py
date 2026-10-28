from tl import *
from geo import *
import collections
for rnd in ['R11','R11C']:
  print('==',rnd)
  for s in ['s02a','s02c','s02va','s02vc']:
    for a in ['final','dynamic']:
      rows,met,G=load(rnd,s,a)
      yd=S02_DOORS['A' if s in ('s02a','s02va') else 'C']
      near=[r for r in rows if r['step']>=4 and 0.3<r['x']<3.0 and abs(r['y']-yd)<2.6]
      passed=next((r['step'] for r in rows if r['x']<-0.5),None)
      mind=min(math.dist((r['x'],r['y']),(0.5,yd)) for r in rows if r['step']>=4)
      ev=[(r['step'],round(r['y'],1),r['target'],r['word'],'gb%.0f'%r['gbear'],'L' if r['los'] else '') for r in near]
      print(f"  {s}/{a}: {'reached' if met['goal_reached'] else 'fail'} passed_wall_step={passed} min_dist_to_door_mouth={mind:.1f} near-door steps={len(near)} {ev[:8]}")
