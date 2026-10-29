"""Q5: navigator vs "toward your target": followed when the tag is on a forward move vs on [0] (turn around).
Also: steps with no action tagged toward; forward-toward moves that also carry 'wall close'."""
import sys, collections
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa

for rnd in sys.argv[1:] or ['R11', 'R12', 'R13', 'R13G']:
    c = collections.Counter()
    for arm in ARMS:
        if arm == 'initial':
            pass
        for site in SITES:
            rows, met = load(rnd, site, arm)
            for r in rows:
                tags = {int(i): v for i, v in (r.get('tags') or {}).items()}
                tw = [i for i, v in tags.items() if any('toward your target' in t for t in v)]
                idx = r.get('index')
                grp = 'all' if arm == 'initial' else 'fd'
                for g in ('all', grp) if grp == 'fd' else ('all',):
                    if not tw:
                        c[(g, 'none')] += 1
                        c[(g, 'none_TA')] += is_ta(r)
                        continue
                    if 0 in tw:
                        c[(g, 'on0')] += 1
                        c[(g, 'on0_follow')] += idx == 0
                    else:
                        c[(g, 'fwd')] += 1
                        c[(g, 'fwd_follow')] += idx in tw
                        c[(g, 'fwd_TA')] += idx == 0
                        wc = any(any('wall close' in t for t in tags[i]) for i in tw)
                        c[(g, 'fwd_wall')] += wc
                        c[(g, 'fwd_wall_follow')] += wc and idx in tw
                        c[(g, 'fwd_clear')] += not wc
                        c[(g, 'fwd_clear_follow')] += (not wc) and idx in tw
    for g, nm in (('all', 'all arms'), ('fd', 'final+dynamic')):
        def p(a, b):
            return f"{c[(g, a)]}/{c[(g, b)]} ({c[(g, a)]/max(1, c[(g, b)]):.0%})"
        n = c[(g, 'none')] + c[(g, 'on0')] + c[(g, 'fwd')]
        print(f"{rnd:4s} {nm:13s} steps {n}: toward on forward {c[(g,'fwd')]} followed {p('fwd_follow','fwd')} "
              f"[clear {p('fwd_clear_follow','fwd_clear')}, 'wall close' {p('fwd_wall_follow','fwd_wall')}], turned around instead {c[(g,'fwd_TA')]}; "
              f"toward on [0] {c[(g,'on0')]} followed {p('on0_follow','on0')}; no toward tag {c[(g,'none')]} (TA there {c[(g,'none_TA')]})")
