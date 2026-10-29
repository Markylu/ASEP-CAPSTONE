"""Q2: every goal_lost episode: sightings genuine?, vantage reached?, ending, check look truth, ping-pong."""
import sys, math, collections
sys.path.insert(0, 'eval/phase2/R13_verify/analysis')
from common import *  # noqa
from r12_probe import in_view, los  # noqa

HALF = spatial.FOV_DEG / 2.0
END = ('verify_failed', 'verify_timeout', 'verify_unreachable', 'reacquired', 'reacquired_moved')


SWITCH = {}


def gen(r):
    # 's': stale. The frame of the switch step still shows the pre-switch scene (geo.SWITCH_STEP note);
    # the manifest's line of sight is already post-switch. Counted genuine.
    if r['step'] == SWITCH.get('step') and not los(r):
        return 's'
    return 'G' if in_view(r, HALF) else ('g' if in_view(r) else ('l' if los(r) else 'h'))


tot = collections.Counter()
for rnd in sys.argv[1:] or ['R13', 'R13G']:
    print('==', rnd, ' sighting codes: G in frame+LOS, g LOS within 60deg, l LOS outside view, h no LOS (hallucinated)')
    for arm in ARMS:
        for site in SITES:
            rows, met = load(rnd, site, arm)
            SWITCH['step'] = next((e['step'] for e in met['events'] if e['name'] in ('doors_switched', 'occluder_deployed')), None)
            by = {r['step']: r for r in rows}
            for k, r in enumerate(rows):
                if 'goal_lost' not in events(r):
                    continue
                vx, vy, vh, vs = r['stage']['vantage']
                # sightings in the goal stage leading up to the loss
                j = k - 1
                while j >= 0 and stage(rows[j]) == 'goal':
                    j -= 1
                sight = [x for x in rows[j + 1:k] if pgoal(x) in STRIPS]
                codes = ''.join(gen(x) for x in sight)
                vrow = by[int(vs)]
                # episode: from k until stage leaves verify
                end, endstep, reach, maxta, cur, check = 'run_end', None, None, 0, 0, None
                for x in rows[k:]:
                    p = xyh(x)
                    d = math.dist(p[:2], (vx, vy))
                    if reach is None and d < 1.5:
                        reach = x['step']
                    e = [e for e in events(x) if e in END]
                    if x['step'] > r['step'] and e:
                        end, endstep = e[0], x['step']
                        check = x
                        break
                    cur = cur + 1 if is_ta(x) else 0
                    maxta = max(maxta, cur)
                tot[(rnd, end)] += 1
                tot[(rnd, 'orig_' + gen(vrow))] += 1
                d0 = math.dist(xyh(r)[:2], (vx, vy))
                line = (f"{site:5s} {arm:7s} lost@{r['step']:2d} vantage@{int(vs):2d} orig={gen(vrow)} goal-stage sightings={codes or '-'} "
                        f"back {d0:4.1f}m reach@{reach}({'' if reach is None else reach - r['step']}st) end={end}@{endstep} TArun={maxta}")
                if check is not None and end == 'verify_failed':
                    ch = check
                    line += (f" | check: LOS={los(ch)} inview={in_view(ch, HALF)} gb={ch['manifest']['goal']['bearing_deg']:.0f} "
                             f"perc={pgoal(ch)}")
                    tot[(rnd, 'failed_los' if los(ch) else 'failed_nolos')] += 1
                if check is not None and end.startswith('reacq'):
                    line += f" | reacq sighting={gen(check)}"
                print(line)
for k in sorted(tot):
    print(k, tot[k])
