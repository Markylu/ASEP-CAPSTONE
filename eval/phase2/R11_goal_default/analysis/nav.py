from tl import *
import re, collections
TOW='toward your target'
def has(tags,prefix): return any(t.startswith(prefix) for t in tags)
GOALVIS=re.compile(r"(?<!not )(?<!no )(goal|sphere) (is |appears |was )?(now |clearly |directly )?(visible|in view|seen)|i can see the (goal|red sphere)|the (red )?sphere (is )?(ahead|in the)", re.I)
NEGGOAL=re.compile(r"goal is not visible|not visible|no (visible )?goal|goal is not in", re.I)
CLEAR=re.compile(r"\b(clear path|path (ahead )?is (clear|open|unobstructed)|unobstructed|no (walls?|obstacles?)|open (floor|space|path))\b", re.I)
WALLMENTION=re.compile(r"wall", re.I)
def classify(rnd):
    C=collections.Counter(); ex=collections.defaultdict(list)
    for s in SITES:
      for a in ARMS:
        rows,met,G=load(rnd,s,a)
        for r in rows:
          if r['idx'] is None: continue
          R=r['reason'] or ''
          vis=[k for k in r['acts'] if not (r['hidden'] and k in r['hidden'])]
          tw=[k for k in r['toward'] if k in vis]
          pt=r['ptags']; ta=r['word']=='TA'
          short = (not ta) and r['moved'] is not None and r['moved']<1.5
          C['n']+=1
          cites_tow = bool(re.search(r"toward (your|the) target|toward the planner|towards? (the )?target", R, re.I))
          C['cites_toward']+=cites_tow
          if tw:
            C['toward_visible']+=1
            if r['idx'] in tw: C['picked_toward']+=1
            else:
              C['picked_not_toward']+=1
              if cites_tow:
                C['picked_not_toward_but_cites_toward']+=1; ex['misattr'].append((s,a,r['step']))
          else:
            C['no_toward_visible']+=1
            if cites_tow: C['no_toward_visible_but_cites_toward']+=1; ex['phantom_toward'].append((s,a,r['step']))
          # goal sighting claims
          if r['pgoal']=='not_visible' and GOALVIS.search(R) and not re.search(r"goal is not visible", R[:GOALVIS.search(R).start()+40], re.I):
            C['claims_goal_seen_perceiver_not']+=1; ex['goal_claim'].append((s,a,r['step']))
          # wall notes
          if has(pt,'wall close'): C['picked_wall_note']+=1; C['picked_wall_note_short']+=short
          if has(pt,'blocked here') or has(pt,'stopped short here'): C['picked_block_note']+=1; C['picked_block_note_short']+=short
          if not ta:
            C['fwd']+=1; C['fwd_short']+=short
            if short:
              C['short_no_wall_note']+= not has(pt,'wall close')
              if CLEAR.search(R): C['short_but_reason_says_clear']+=1; ex['clear_but_short'].append((s,a,r['step']))
            if CLEAR.search(R): C['reason_says_clear']+=1
          # notes chosen
          if has(pt,'been there'): C['picked_been_there']+=1
          if has(pt,'new ground'): C['picked_new_ground']+=1
          if has(pt,'doorway'): C['picked_doorway_note']+=1
          if has(pt,'goal this way') or has(pt,'goal about one'): C['picked_goal_note']+=1
          if any(has(r['tags'].get(k,[]),'goal this way') or has(r['tags'].get(k,[]),'goal about one') for k in vis): C['goal_note_offered']+=1
          if ta:
            C['TA']+=1
            if tw and tw[0]!=r['idx']: C['TA_against_fwd_toward']+=1
            allwall=all(has(r['tags'].get(k,[]),'wall close') or has(r['tags'].get(k,[]),'blocked') or has(r['tags'].get(k,[]),'stopped short') for k in vis if not r['acts'][k].get('turn_around'))
            C['TA_all_fwd_noted']+=allwall
    return C,ex
for rnd in ['R11','R11C']:
    C,ex=classify(rnd)
    print('==',rnd)
    for k,v in sorted(C.items()): print('  ',k,v)
    for k,v in ex.items(): print('  ex',k,len(v),v[:8])
