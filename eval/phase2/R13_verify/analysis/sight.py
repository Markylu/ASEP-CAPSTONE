"""Q2 support: goal reports per round (genuine / stale / hallucinated), misses (goal in frame with LOS, not
reported), and steps spent in goal/verify stages that rest on hallucinated sightings (R13/R13G)."""
import sys, collections
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa
from r12_probe import in_view, los  # noqa

HALF = spatial.FOV_DEG / 2.0
for rnd in sys.argv[1:] or ['R11', 'R12', 'R13', 'R13G']:
    c = collections.Counter()
    for arm in ARMS:
        for site in SITES:
            rows, met = load(rnd, site, arm)
            sw = next((e['step'] for e in met['events'] if e['name'] in ('doors_switched', 'occluder_deployed')), None)
            for r in rows:
                rep = pgoal(r) in STRIPS
                iv = in_view(r, HALF)
                if rep:
                    k = 'gen' if in_view(r) else ('stale' if r['step'] == sw else 'hall')
                    c[k] += 1
                    c[(arm, k)] += 1
                elif iv:
                    c['miss'] += 1
                c['inview'] += iv
                if stage(r) in ('verify',):
                    c['verify_steps'] += 1
    tot = c['gen'] + c['stale'] + c['hall']
    print(f"{rnd:4s} reports {tot}: genuine {c['gen']}, stale {c['stale']}, hallucinated {c['hall']} "
          f"(final {c[('final','hall')]}, dynamic {c[('dynamic','hall')]}, initial {c[('initial','hall')]}); "
          f"goal in frame+LOS {c['inview']} looks, missed {c['miss']}; verify steps {c['verify_steps']}")
