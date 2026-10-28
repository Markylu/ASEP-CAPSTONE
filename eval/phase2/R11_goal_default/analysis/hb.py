from tl import *
from geo import *
from val import wfun
import collections
# hand-backs, hallucinated goal_in_view, goal-behind episodes, toward picks
for rnd in ['R11','R11C']:
    C=collections.Counter(); away=[]
    for s in SITES:
      for a in ARMS:
        rows,met,G=load(rnd,s,a)
        for i,r in enumerate(rows):
          p=r['planner'] or {}
          if p.get('hand_back'):
            C['hb_'+p['hand_back']]+=1
            if p['hand_back']=='goal_in_view' and not r['los']:
              C['hb_goal_in_view_no_los']+=1
          if r['idx'] is None: continue
          vis=[k for k in r['acts'] if not (r['hidden'] and k in r['hidden'])]
          tw=[k for k in r['toward'] if k in vis]
          tw_hidden=[k for k in r['toward'] if r['hidden'] and k in r['hidden']]
          if tw_hidden: C['toward_on_hidden']+=1
          if not tw: C['no_visible_toward']+=1
          if tw:
            k=tw[0]
            kind='TA' if r['acts'][k].get('turn_around') else 'fwd'
            C['toward_'+kind]+=1
            C['toward_'+kind+'_picked']+= (r['idx']==k)
          if r['target']=='goal' and r['dg_next'] is not None:
            C['goal_steps']+=1
            behind=abs(r['gbear'])>90
            C['goal_behind' if behind else 'goal_front']+=1
            C['dg_sum_goal_'+('behind' if behind else 'front')]+= r['dg_next']-r['dg']
            if behind:
              C['goal_behind_picked_TA']+= (r['word']=='TA')
              C['goal_behind_TA_hidden']+= bool(r['hidden'])
          if r['dg_next'] is not None:
            C['dg_sum_all']+=r['dg_next']-r['dg']
          C['TA_picks']+= r['word']=='TA'
          C['picks']+=1
    print('==',rnd)
    for k,v in sorted(C.items()): print('  ',k, round(v,2) if isinstance(v,float) else v)
