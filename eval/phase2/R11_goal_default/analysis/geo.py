"""Approximate 2D ground truth for the phase-2 sites, in map coords (x, y=-z).
Evaluation only. Divider/exit walls treated as solid slabs; doors as gaps."""
import math

HALF_W = 11.75  # side walls inner face (|y|)
X_MAX, X_MIN = 23.75, -24.0
DOOR_HALF = 1.2
# s02 door centres in map y (y = -z): A z=-9 -> y=+9; B y=0; C z=+9 -> y=-9
S02_DOORS = {'A': 9.0, 'B': 0.0, 'C': -9.0}
SWITCH_STEP = 4  # first changed frame for s01/s02 dynamic


def open_doors(site, arm, step):
    new = 'A' if site in ('s02a', 's02va') else 'C'
    if arm == 'initial':
        return {'B'}
    if arm == 'final':
        return {new}
    return {'B'} if step < SWITCH_STEP else {new}


def free_s02(x, y, doors):
    if abs(y) > HALF_W or x > X_MAX or x < X_MIN:
        return False
    if -0.5 <= x <= 0.5:
        return any(abs(y - S02_DOORS[d]) < DOOR_HALF for d in doors)
    return True


def free_s01(x, y, cube):
    if abs(y) > HALF_W or x > X_MAX or x < X_MIN:
        return False
    if cube and -6.0 <= x <= 2.0 and abs(y) <= 4.0:
        return False
    return True


# s03 tuning fork (map y = -z; L tine z in [3.5,6.5] -> y in [-6.5,-3.5])
def free_s03(x, y, closed=()):
    if x > X_MAX or x < X_MIN or abs(y) > HALF_W:
        return False
    if x >= 15.0:
        return True  # lobby
    if 8.0 <= x < 15.0:
        return abs(y) <= 1.5  # stem
    if 5.0 <= x < 8.0:
        return abs(y) <= 6.5  # crossbar
    if -6.0 <= x < 5.0:
        return 3.5 <= abs(y) <= 6.5  # tines
    if -7.0 <= x < -6.0:  # exit wall with doors at |y|=5
        if abs(abs(y) - 5.0) < DOOR_HALF:
            side = 'L' if y < 0 else 'R'
            return side not in closed
        return False
    return True  # goal chamber


def world(site, arm, step, s03_closed_from=None, s03_side=None):
    if site.startswith('s02'):
        d = open_doors(site, arm, step)
        return lambda x, y: free_s02(x, y, d)
    if site == 's01':
        cube = arm == 'final' or (arm == 'dynamic' and step >= SWITCH_STEP)
        return lambda x, y: free_s01(x, y, cube)
    if site == 's03':
        closed = ()
        if s03_closed_from is not None and step > s03_closed_from:
            closed = (s03_side,)
        return lambda x, y: free_s03(x, y, closed)
    raise ValueError(site)


def ray(free, x, y, heading_deg, max_d=12.0, step=0.05):
    h = math.radians(heading_deg)
    d = 0.0
    while d < max_d:
        d += step
        if not free(x + d * math.cos(h), y + d * math.sin(h)):
            return d
    return max_d


def segment_clear(free, a, b, step=0.1):
    L = math.dist(a, b)
    n = max(1, int(L / step))
    for i in range(1, n + 1):
        t = i / n
        if not free(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t):
            return False
    return True
