"""Two-character skit on the dock set: Nils (veteran, behind the inspection desk) and Theo (the beginner).

Acting is built to the motion study (research/omega/motion/MOTION_STUDY.md, One Bold Chemist v3/v7/v8/v9):
- pose-to-pose: every change hits its new pose in 3-5 frames with a small overshoot, then a moving hold (slow drift),
  never a long eased glide; while talking the head re-poses on every stressed word (every 0.3-0.6 s);
- the body acts with the head: the chest follows 2 frames later at 30-40 %, shoulders shrug and drop, the spine leans;
- listeners stay alive: small re-poses every ~1 s, nods at the speaker's sentence ends, blinks, eyes on the speaker;
- locked cameras and hard cuts (~2.5-4 s per shot), not camera moves.
Every channel is baked per frame (no Bezier interpolation between sparse keys).

Called from calib_m3.py --shot skit --nils <nils_rig.blend> --theo <theo_rig.blend> --timeline <timeline.json>"""
import json, math, random, sys, os
import bpy
from mathutils import Vector, Euler, Quaternion, Matrix

FPS = 24
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import lipsync


# ------------------------------------------------------------------ channel engine
def ease_back(u, over=1.35):
    u = min(1.0, max(0.0, u)); c3 = over + 1
    return 1 + c3 * (u - 1) ** 3 + over * (u - 1) ** 2


class Chan:
    """Piecewise pose channel: keys (frame, value, transition_frames). Each key starts from wherever the previous
    segment is at that frame and snaps to its value with an overshoot (ease_back), then holds."""
    def __init__(self, v0=0.0):
        self.keys = [(-999, v0, 1)]
    def key(self, f, v, T=4):
        self.keys.append((f, v, T)); self.keys.sort(key=lambda k: k[0])
    @staticmethod
    def _ev(a, b, kf, T, f):
        u = (f - kf) / max(1, T)
        return b if u >= 1.0 else a + (b - a) * ease_back(u)
    def at(self, f):
        a = b = self.keys[0][1]; kf0, T0 = -999, 1
        for (kf, v, T) in self.keys[1:]:
            if kf > f: break
            a = self._ev(a, b, kf0, T0, kf); b, kf0, T0 = v, kf, T
        return self._ev(a, b, kf0, T0, f)


def chans(names, v0=0.0):
    return {n: Chan(v0) for n in names}


# ------------------------------------------------------------------ rig helpers
def set_bone(arm, name, pitch=0.0, yaw=0.0, roll=0.0):
    """Rotation given in the armature's axes (character space: X right, -Y forward, Z up), degrees.
    pitch + = nod forward/down, yaw + = turn to his left (+X), roll + = tilt to his left."""
    pb = arm.pose.bones[name]; pb.rotation_mode = 'QUATERNION'
    rest = pb.bone.matrix_local.to_quaternion()
    q = (Quaternion((0, 0, 1), math.radians(yaw)) @ Quaternion((1, 0, 0), math.radians(pitch)) @
         Quaternion((0, 1, 0), math.radians(roll)))
    pb.rotation_quaternion = rest.inverted() @ q @ rest


def look_angles(arm, head_world, target):
    """Yaw/pitch (deg, armature axes) from a head point to a world target."""
    mi = arm.matrix_world.inverted()
    a = mi @ head_world; b = mi @ target; d = b - a
    yaw = math.degrees(math.atan2(d.x, -d.y)); pitch = math.degrees(math.atan2(-d.z, math.hypot(d.x, d.y)))
    return yaw, pitch


# ------------------------------------------------------------------ build
def build(sc, DESK, kit, nils_path, theo_path, timeline_path):
    TL = json.load(open(timeline_path))
    N = int(math.ceil(TL['total'] * FPS))
    sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, N
    R = random.Random(11)

    # place the two rigs (calib_m3 already appended Nils at the desk)
    nils = bpy.data.objects['nils_rig']
    nils.location = (DESK.x + 0.05, DESK.y + 0.55, 0.0); nils.rotation_euler = (0, 0, math.radians(-22))
    with bpy.data.libraries.load(theo_path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects:
        kit.link(o)
    theo = bpy.data.objects['theo_rig']
    theo.location = (DESK.x - 0.80, DESK.y + 0.02, 0.0); theo.rotation_euler = (0, 0, math.radians(68))
    bpy.context.view_layer.update()

    def head_pt(arm):
        return arm.matrix_world @ arm.pose.bones['neck'].tail
    H_N = Vector((nils.location.x, nils.location.y, 1.56)); H_T = Vector((theo.location.x, theo.location.y, 1.62))

    kit.area('faceN', tuple(H_N + Vector((-0.9, -1.0, 0.6))), tuple(H_N), color='#ffe9d2', power=70, size=0.35)
    kit.area('faceT', tuple(H_T + Vector((0.95, -0.8, 0.55))), tuple(H_T), color='#ffe9d2', power=60, size=0.35)
    # ------------------------------------------------------------ cameras (locked) and the cut list
    cams = {}
    def cam(name, loc, tgt, lens, fstop=3.2):
        c = kit.camera(name, loc, tgt, lens=lens, fstop=fstop, focus=(Vector(tgt) - Vector(loc)).length)
        cams[name] = c; return c
    cam('camA', (DESK.x - 0.45, DESK.y - 2.15, 1.48), (DESK.x - 0.33, DESK.y + 0.6, 1.3), 30, 5.0)
    cam('camN', (DESK.x - 0.42, DESK.y - 0.62, 1.56), tuple(H_N + Vector((0, 0, -0.08))), 42)
    cam('camT', (DESK.x + 0.18, DESK.y - 0.92, 1.56), tuple(H_T + Vector((0, 0, -0.1))), 46)
    cuts = [(0.0, 'camA'), (2.05, 'camN'), (5.0, 'camT'), (6.65, 'camN'), (9.7, 'camA'), (12.9, 'camT'),
            (14.0, 'camN'), (16.9, 'camT'), (18.45, 'camN')]
    sc.timeline_markers.clear()
    for t, cn in cuts:
        m = sc.timeline_markers.new(cn, frame=max(1, int(round(t * FPS)) + 1)); m.camera = cams[cn]
    sc.camera = cams['camA']

    # ------------------------------------------------------------ per character channels
    BONES = ('neck', 'chest', 'spine', 'hips', 'shoulder.L', 'shoulder.R')
    C = {who: {b: chans(('p', 'y', 'r')) for b in BONES} for who in ('nils', 'theo')}
    EYE = {who: chans(('y', 'p')) for who in ('nils', 'theo')}
    LID = {who: Chan(0.0) for who in ('nils', 'theo')}
    other = {'nils': 'theo', 'theo': 'nils'}
    rig = {'nils': nils, 'theo': theo}

    def key_pose(who, f, pose, T=4):
        for b, d in pose.items():
            for ax, v in d.items():
                C[who][b][ax].key(f, v, T)

    # base attitudes
    key_pose('nils', 0, {'neck': {'p': 4, 'y': 0}, 'chest': {'p': 3}})
    key_pose('theo', 0, {'neck': {'p': 6}, 'chest': {'p': 10}, 'spine': {'p': 6}, 'shoulder.L': {'r': 0}})

    # gaze targets over time: (time, target name or point)
    gaze = {'nils': [(0.0, 'clip'), (3.2, 'other'), (14.9, 'hat'), (16.2, 'other'), (18.4, 'camN')],
            'theo': [(0.0, 'down'), (1.4, 'other'), (16.95, 'hat'), (17.5, 'other')]}
    clip = Vector((DESK.x - 0.13, DESK.y + 0.0, DESK.z))
    hatpt = H_T + Vector((0.0, 0.0, 0.16))

    # speaking: words -> stressed re-poses (head), chest follows; listener re-poses and nods
    speaking = []
    for L in TL['lines']:
        who = L['who']; t0 = L['start']
        ws = [dict(w=w['w'], s=w['s'] + t0, e=w['e'] + t0) for w in L['words']]
        speaking.append((who, t0, t0 + L['dur'], ws))
        prev = -1
        for i, w in enumerate(ws):
            f = int(w['s'] * FPS) - 2
            if len(w['w'].strip('.,?!-')) < 4 and i not in (0, len(ws) - 1): continue
            if f - prev < 5: continue                                    # re-pose at most every ~0.2 s
            prev = f
            amp = 2.4 if who == 'theo' else 1.7
            key_pose(who, f, {'neck': {'p': R.uniform(-4, 6) * amp, 'y': R.uniform(-6, 6) * amp, 'r': R.uniform(-4, 4) * amp}},
                     T=R.choice((3, 4, 4, 5)))
        # sentence end: settle, the listener nods
        fe = int((t0 + L['dur']) * FPS)
        key_pose(who, fe, {'neck': {'p': 3, 'y': 0, 'r': 0}}, T=6)
        lw = other[who]
        key_pose(lw, fe - 4, {'neck': {'p': 9}}, T=3); key_pose(lw, fe + 3, {'neck': {'p': 2}}, T=5)

    # listener idle re-poses (every 0.9-1.6 s when not speaking)
    for who in ('nils', 'theo'):
        t = 0.6
        while t < TL['total']:
            talking = any(s <= t <= e for (w, s, e, _) in speaking if w == who)
            if not talking:
                key_pose(who, int(t * FPS), {'neck': {'y': R.uniform(-5, 5), 'r': R.uniform(-4, 4), 'p': R.uniform(-2, 4)},
                                            'chest': {'y': R.uniform(-3, 3)}}, T=4)
            t += R.uniform(0.6, 1.1)

    # acting beats (from the script)
    def at(t): return int(t * FPS)
    # L1 Theo: slumped, shakes his head on "not a single bite"
    key_pose('theo', at(0.2), {'shoulder.L': {'r': -6}, 'shoulder.R': {'r': 6}, 'chest': {'p': 14}}, T=6)
    for k, yv in enumerate((-9, 8, -7, 5, 0)):
        key_pose('theo', at(1.05) + k * 4, {'neck': {'y': yv}}, T=3)
    # L2 Nils: reads the clipboard, eyes come up first (gaze list), head follows on "the middle is flat"
    key_pose('nils', at(2.2), {'neck': {'p': 16}, 'chest': {'p': 6}}, T=5)
    key_pose('nils', at(3.45), {'neck': {'p': 2, 'y': -10}}, T=5)
    # L3 Theo: shoulders shrug up, head tilts, palms-up feel without hands
    key_pose('theo', at(5.05), {'shoulder.L': {'r': -14}, 'shoulder.R': {'r': 14}, 'chest': {'p': -2}, 'neck': {'r': 9, 'p': -3}}, T=4)
    key_pose('theo', at(6.55), {'shoulder.L': {'r': -2}, 'shoulder.R': {'r': 2}, 'chest': {'p': 6}, 'neck': {'r': 0}}, T=6)
    # L4 Nils: leans in over the desk, confident
    key_pose('nils', at(6.75), {'spine': {'p': 9}, 'chest': {'p': 5}}, T=5)
    key_pose('nils', at(12.4), {'spine': {'p': 0}, 'chest': {'p': 2}}, T=6)
    # L5 Theo: head pushes forward, eyes wide (lids)
    key_pose('theo', at(12.95), {'chest': {'p': -4}, 'neck': {'p': -6, 'r': -5}}, T=3)
    # L6 Nils: dry, chin up a little on "unlike that hat"
    key_pose('nils', at(15.2), {'neck': {'p': -5, 'r': 6}}, T=4)
    # beat + L7 Theo: eyes up to the hat, then sheepish: head down, shoulders up
    key_pose('theo', at(16.95), {'neck': {'p': -10}}, T=5)
    key_pose('theo', at(17.35), {'neck': {'p': 12, 'r': 7}, 'shoulder.L': {'r': -10}, 'shoulder.R': {'r': 10}, 'chest': {'p': 10}}, T=4)
    # L8 Nils: turns to camera for the line
    key_pose('nils', at(18.4), {'neck': {'y': 18, 'p': -2}, 'chest': {'y': 6}}, T=5)

    # blinks
    for who in ('nils', 'theo'):
        t = R.uniform(0.8, 1.8)
        while t < TL['total']:
            f = at(t); LID[who].key(f, 42, 1); LID[who].key(f + 2, 42, 1); LID[who].key(f + 3, 0, 3)
            t += R.uniform(1.8, 3.8)

    # visemes per character
    mouth = {}
    for who in ('nils', 'theo'):
        words = [w for (wh, s, e, ws) in speaking if wh == who for w in ws]
        mouth[who] = lipsync.visemes(words, N, FPS)

    # ------------------------------------------------------------ bake
    heads = {'nils': bpy.data.objects['nils_head'], 'theo': bpy.data.objects['theo_head']}
    mobj = {'nils': bpy.data.objects['nils_mouth'], 'theo': bpy.data.objects['theo_mouth']}
    eyes = {'nils': [bpy.data.objects['eye_L'], bpy.data.objects['eye_R']],
            'theo': [bpy.data.objects['theo_eye_L'], bpy.data.objects['theo_eye_R']]}
    lids = {'nils': [bpy.data.objects['lid_L'], bpy.data.objects['lid_R']],
            'theo': [bpy.data.objects['theo_lid_L'], bpy.data.objects['theo_lid_R']]}
    lid0 = {w: [l.rotation_euler.copy() for l in lids[w]] for w in lids}
    eye0 = {w: [e.rotation_euler.copy() for e in eyes[w]] for w in eyes}
    gaze_now = {}
    def gaze_target(who, t):
        name = [g for (tt, g) in gaze[who] if tt <= t][-1]
        if name == 'other': return H_T if who == 'nils' else H_N
        if name == 'clip': return clip
        if name == 'hat': return hatpt
        if name == 'down': return H_T + Vector((0.6, -0.2, -1.0))
        return cams[name].location
    for f in range(1, N + 1):
        t = (f - 1) / FPS
        sc.frame_set(f)
        for who in ('nils', 'theo'):
            arm = rig[who]; ch = C[who]
            breath = math.sin(t * 2 * math.pi / 3.6 + (0 if who == 'nils' else 1.3))
            drift = lambda k: 0.8 * math.sin(t * (0.7 + 0.13 * k) + k * 1.7)
            neck = {a: ch['neck'][a].at(f) for a in 'pyr'}
            lag = {a: ch['neck'][a].at(f - 2) for a in 'pyr'}
            set_bone(arm, 'neck', neck['p'] + drift(1) * 0.6, neck['y'] + drift(2), neck['r'] + drift(3) * 0.6)
            set_bone(arm, 'chest', ch['chest']['p'].at(f) + 0.45 * lag['p'] + 0.8 * breath, ch['chest']['y'].at(f) + 0.5 * lag['y'],
                     ch['chest']['r'].at(f) + 0.45 * lag['r'])
            set_bone(arm, 'spine', ch['spine']['p'].at(f) + 0.4 * breath, ch['spine']['y'].at(f), ch['spine']['r'].at(f))
            set_bone(arm, 'hips', 0, 1.5 * math.sin(t * 0.9 + (0 if who == 'nils' else 2)), 1.2 * math.sin(t * 0.55))
            set_bone(arm, 'shoulder.L', 0, 0, ch['shoulder.L']['r'].at(f) - 1.2 * breath)
            set_bone(arm, 'shoulder.R', 0, 0, ch['shoulder.R']['r'].at(f) + 1.2 * breath)
            for b in ('neck', 'chest', 'spine', 'hips', 'shoulder.L', 'shoulder.R'):
                arm.pose.bones[b].keyframe_insert('rotation_quaternion', frame=f)
            # eyes: look at the gaze target, relative to the current head (saccades snap in 2 frames)
            bpy.context.view_layer.update()
            hp = head_pt(arm)
            yy, pp = look_angles(arm, hp, gaze_target(who, t))
            hy = neck['y'] + ch['chest']['y'].at(f); hpch = neck['p'] + ch['chest']['p'].at(f) + ch['spine']['p'].at(f)
            ey, ep = max(-28, min(28, yy - hy - (-22 if who == 'nils' else 68) * 0)), max(-20, min(25, pp - hpch))
            for e, r0 in zip(eyes[who], eye0[who]):
                e.rotation_euler = (r0.x + math.radians(ep), r0.y, r0.z + math.radians(ey)); e.keyframe_insert('rotation_euler', frame=f)
            for l, r0 in zip(lids[who], lid0[who]):
                l.rotation_euler = (r0.x + math.radians(LID[who].at(f) + 0.35 * max(0, ep)), r0.y, r0.z)
                l.keyframe_insert('rotation_euler', frame=f)
            v = mouth[who][f - 1]; vis = v['vis']
            kb = heads[who].data.shape_keys.key_blocks
            jaw = v['jaw'] * (1.0 if who == 'theo' else 0.85)
            kb['jaw_open'].value = jaw; kb['wide'].value = vis.get('EE', 0) + 0.5 * vis.get('CONS', 0)
            kb['round'].value = vis.get('OO', 0)
            for k in ('jaw_open', 'wide', 'round'): kb[k].keyframe_insert('value', frame=f)
            mo = mobj[who]
            mo.scale = (1.0 + 0.25 * vis.get('EE', 0) - 0.3 * vis.get('OO', 0), 1.0, 0.04 + 0.85 * jaw)
            mo.keyframe_insert('scale', frame=f)
    for o in bpy.data.objects:
        ad = o.animation_data
        if ad and ad.action:
            try:
                for fc in ad.action.fcurves:
                    for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
            except AttributeError:
                pass
    print('SKIT', N, 'frames,', len(cuts), 'shots')
    return N
