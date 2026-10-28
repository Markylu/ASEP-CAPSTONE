from tl import *
from geo import *
import collections
C=collections.Counter()
for s in ['s02a','s02c','s02va','s02vc']:
  for a in ['final','dynamic']:
    rows,met,G=load('R11',s,a)
    yd=S02_DOORS['A' if s in ('s02a','s02va') else 'C']
    picks=[]
    for r in rows:
      if not r['strat']: continue
      ops=(r['raw'].get('spatial') or {}).get('openings') or []
      near=[o for o in ops if abs(o['y']-yd)<3.5 and o['x']>-1 and o['x']<4]
      menu=[m['id'] for m in r['strat'].get('menu') or []]
      listed=[o for o in near if 'doorway_'+o['label'] in menu]
      pk=(r['strat'].get('result') or {}).get('target')
      tm=[m for m in r['strat'].get('menu') or [] if m['id']==pk][0]
      rep=(tm['x'],tm['y']) in picks; picks.append((tm['x'],tm['y']))
      C['calls']+=1; C['repeat_target']+=rep
      C['true_door_in_memory']+=bool(near); C['true_door_listed']+=bool(listed)
      print(s,a,r['step'],'near-door openings in memory:',[(o['label'],o['x'],o['y'],o['seen'],o['last_seen'],o['closed'],o['passed']) for o in near],'listed:',[o['label'] for o in listed],'pick',pk,'repeat' if rep else '')
print(C)
