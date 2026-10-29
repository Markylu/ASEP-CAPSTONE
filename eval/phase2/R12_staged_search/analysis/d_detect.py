"""D_detect: how far away the g03 perceiver reliably reports the goal sphere.

Read-only, from recorded decisions.jsonl (manifest goal truth is evaluation only).
In view = line of sight and |bearing| within half the 87 deg field of view.
Run from the repo root: python3 eval/phase2/R12_staged_search/analysis/d_detect.py
"""
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
ROUNDS = ['R9_hail_mary', 'R10C_a13_control', 'R10_goal_planner',
          'R11C_a14_control', 'R11_goal_default']
HALF_FOV = 43.5
BINS = [0, 2, 4, 6, 8, 10, 12, 15, 18, 22, 30]


def records():
    for rnd in ROUNDS:
        for f in sorted((REPO / 'eval/phase2' / rnd / 'runs').glob('*/*/seed1/decisions.jsonl')):
            for line in open(f):
                if not line.strip():
                    continue
                r = json.loads(line)
                if 'step' not in r or not r.get('perceiver'):
                    continue
                res = (r['perceiver'] or {}).get('result') or {}
                yield rnd, r['manifest']['goal'], res


def bin_of(d):
    for lo, hi in zip(BINS, BINS[1:]):
        if lo <= d < hi:
            return '{0:>2}-{1:<2}'.format(lo, hi)
    return '30+  '


def main():
    seen = defaultdict(lambda: [0, 0])      # bin -> [reported, in view]
    rng = defaultdict(lambda: defaultdict(int))  # bin -> range class -> n
    false_pos = [0, 0]                       # reported while out of view, out-of-view frames
    for _rnd, g, res in records():
        reported = res.get('goal') not in (None, 'none', 'not_visible', '')
        in_view = g.get('line_of_sight') and abs(g.get('bearing_deg', 180.0)) <= HALF_FOV
        if in_view:
            b = bin_of(g['distance'])
            seen[b][1] += 1
            if reported:
                seen[b][0] += 1
                rng[b][res.get('goal_range')] += 1
        else:
            false_pos[1] += 1
            false_pos[0] += reported
    print('true distance  reported/in view  rate   range classes when reported')
    for b in sorted(seen, key=lambda s: int(s.split('-')[0].strip().rstrip('+'))):
        k, n = seen[b]
        cls = ', '.join('{0} {1}'.format(c, v) for c, v in sorted(rng[b].items(), key=lambda t: -t[1]))
        print('{0} m      {1:4d}/{2:<4d}      {3:5.0%}  {4}'.format(b, k, n, k / n if n else 0, cls))
    print('reported while out of view: {0}/{1} ({2:.1%})'.format(
        false_pos[0], false_pos[1], false_pos[0] / max(1, false_pos[1])))


if __name__ == '__main__':
    main()
