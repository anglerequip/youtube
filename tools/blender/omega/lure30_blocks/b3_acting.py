# beats of "The Lure Avalanche"
pose('theo', F(ts(1)), {'neck': {'p': -4, 'r': -5}, 'chest': {'p': -3}}, T=5)                                  # proud of it
pose('nils', F(1.6), {'neck': {'p': 14, 'y': 0}, 'chest': {'p': 4}}, T=8)                                        # looks down at his boots
pose('nils', F(ts(2) + 0.6), {'neck': {'p': 4}, 'chest': {'p': 2}}, T=8)
pose('theo', F(ts(3)), {'shoulder.L': {'r': -9}, 'shoulder.R': {'r': 9}, 'neck': {'r': 7}}, T=5)               # panics
pose('theo', F(ts(3) + 1.2), {'shoulder.L': {'r': 0}, 'shoulder.R': {'r': 0}}, T=7)
pose('nils', F(ts(6)), {'neck': {'p': 7}, 'chest': {'p': 4}}, T=6)                                               # very serious
pose('nils', F(ts(6) + 2.2), {'neck': {'p': 3}, 'chest': {'p': 2}}, T=8)
pose('theo', F(ts(7)), {'neck': {'p': -6}, 'chest': {'p': -4}}, T=5)                                             # wide-eyed
pose('theo', F(ts(7) + 1.4), {'neck': {'p': 2}, 'chest': {'p': 0}}, T=8)

def turn_to(who, t0, t1, target, frac=0.7, T=7):
    """Head (and a little chest) turn toward a point between t0 and t1."""
    arm = rig[who]; hp = arm.matrix_world @ arm.pose.bones['neck'].tail
    yy, pp = look_angles(arm, hp, target)
    pose(who, F(t0), {'neck': {'y': max(-50, min(50, frac * yy)), 'p': max(-20, min(25, frac * pp))}, 'chest': {'y': max(-20, min(20, 0.3 * yy))}}, T=T)
    pose(who, F(t1), {'neck': {'y': 0, 'p': 3}, 'chest': {'y': 0}}, T=T + 2)
WIN = Vector((0.0, D1 + 0.5, 1.5))
turn_to('nils', word_t(4, 'look') - 0.2, ts(5) + 1.4, WIN)
turn_to('theo', word_t(4, 'outside'), ts(5) + 1.0, WIN)
turn_to('theo', ts(10) - 0.1, ts(10) + 1.2, PILE, 0.8)
turn_to('theo', 22.6, 24.4, HERO_START + Vector((0, 0, 0.4)), 0.6)
turn_to('nils', 22.6, 24.4, HERO_START + Vector((0, 0, 0.4)), 0.5)

# ------------------------------------------------------------------ gestures
def G(side, up_p=0, up_out=0, fo_p=0, ha_p=-18, ha_y=0):
    o = -1 if side == 'L' else 1
    return {f'upper_arm.{side}': {'p': up_p, 'r': o * up_out, 'y': 0}, f'forearm.{side}': {'p': fo_p, 'y': 0, 'r': 0},
            f'hand.{side}': {'p': ha_p, 'y': o * ha_y, 'r': 0}}
def gesture(who, t, name, side='R', T=7, hold=None):
    pose_ = {'rest': {**G('L'), **G('R')},
             'explain': G(side, -28, 8, -72, -12),
             'beat': G(side, -22, 6, -60, -8),
             'shrug': {**G('L', -12, 20, -68, 0, 35), **G('R', -12, 20, -68, 0, 35)},
             'point': G(side, -68, 6, -12, 0),
             'one': G(side, -30, 4, -95, -5),
             'chin': G(side, -48, -12, -138, -25)}[name]
    pose(who, F(t), pose_, T=T)
    if hold: pose(who, F(t + hold), {**G('L'), **G('R')}, T=9)
# arms that motion capture can't give us: blended over the captured arms in these windows (ovr below)
pose('nils', 0, G('L', -22, 6, -80, -5))                                                   # the mug, held at the belly
pose('theo', F(ts(3) - 0.4), {**G('L', -50, 18, -80, 0), **G('R', -50, 18, -80, 0)}, T=6)   # a lure in each hand
pose('nils', F(ts(8)), G('R', -40, 2, -105, -15), T=7)                                     # the phone
pose('nils', F(word_t(8, 'AnglerMind') - 0.1), G('R', -62, 10, -78, -10), T=6)             # ... held up to show Theo
pose('theo', F(22.4), G('L', -45, 12, -70, 20), T=8)                                       # open hand for the lure
pose('nils', F(ts(12)), G('R', -68, 6, -12, 0), T=6)                                       # the CTA point
ARMS = {s: (f'upper_arm.{s}', f'forearm.{s}', f'hand.{s}') for s in 'LR'}
OVR = {'nils': [(-1, 2.85, ARMS['L']), (4.1, 27.7, ARMS['L']), (28.95, 99, ARMS['L']),
                (ts(8), 24.75, ARMS['R']), (ts(12), 99, ARMS['R'])],
       'theo': [(ts(3) - 0.4, ts(3) + 1.9, ARMS['L'] + ARMS['R']), (22.4, 24.9, ARMS['L'])]}
def ovr(who, bone, t):
    w = 0.0
    for (a, b, bones) in OVR[who]:
        if bone in bones:
            u = min(1.0, max(0.0, (t - a) / 0.35), max(0.0, (b - t) / 0.35)); w = max(w, u * u * (3 - 2 * u))
    return w

GAZE = {'nils': [(0, 'box'), (1.6, 'pile'), (ts(2) + 0.6, 'other'), (word_t(4, 'look') - 0.2, 'window'), (ts(5) + 1.4, 'other'),
                 (ts(8) + 0.2, 'phone'), (word_t(8, 'AnglerMind'), 'other'), (22.6, 'float'), (24.4, 'other'), (ts(12), 'cam')],
        'theo': [(0, 'box'), (0.8, 'other'), (word_t(4, 'outside'), 'window'), (ts(5) + 1.0, 'other'), (word_t(8, 'AnglerMind'), 'phone'),
                 (ts(9) + 1.5, 'other'), (22.6, 'float'), (24.4, 'hand'), (ts(10) - 0.1, 'pile'), (ts(10) + 1.2, 'other')]}
def gaze(who, t):
    g = [x for (tt, x) in GAZE[who] if tt <= t][-1]
    return {'other': H_T if who == 'nils' else H_N, 'window': WIN, 'pile': PILE, 'box': BOXP + Vector((0, 0, 0.3)),
            'cam': cams['cut%d' % (len(cuts) - 1)].location, 'phone': PHONE.location, 'float': HERO.location,
            'hand': HERO.location}[g]
