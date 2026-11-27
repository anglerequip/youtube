"""OMEGA Milestone 5: a silent 6 s acting test on the dock set (24 fps, 144 frames).

Beat (from the Nils brief, 'animate a decision in parts'): the float on the desk rolls three centimetres. His eyes
find it in 3 frames, the head follows 5 frames later over 10 frames with a small overshoot and settle, then a long
hold: the silence between noticing evidence and deciding what to do about it. One brow lifts. Eyes return to camera
first, the head follows. Blinks, a breathing layer and a slow camera push keep it alive. Nothing moves at once
without a reason: eyes lead, head follows, the float on his strap lags the head turn.

Called from calib_m3.py --shot anim (needs --nils)."""
import math
import bpy
from mathutils import Vector, Matrix, Euler

FPS, END = 24, 144


def key(o, f, rot=None, loc=None, scale=None, interp='BEZIER'):
    if rot is not None:
        o.rotation_euler = rot; o.keyframe_insert('rotation_euler', frame=f)
    if loc is not None:
        o.location = loc; o.keyframe_insert('location', frame=f)
    if scale is not None:
        o.scale = scale; o.keyframe_insert('scale', frame=f)


def ease_all(o):
    ad = o.animation_data
    if not ad or not ad.action: return
    for fc in _fcurves(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'; kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'


def _fcurves(action):
    try:
        return list(action.fcurves)
    except AttributeError:                       # Blender 5 layered actions
        out = []
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out += list(cb.fcurves)
        return out


def yaw_pitch(frm, to):
    d = (to - frm)
    yaw = math.atan2(d.x, -d.y)                  # + towards +X (his left, viewer's right)
    pitch = math.atan2(-d.z, math.hypot(d.x, d.y))  # + looks down
    return yaw, pitch


def build(sc, DESK, kit):
    sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, END
    body = bpy.data.objects['nils_tsg']
    bpy.context.view_layer.update()
    # ------------------------------------------------------------ neck pivot carries the head and the face parts
    neck = bpy.data.objects.new('neck', None); kit.link(neck)
    neck.location = body.matrix_world @ Vector((0.0, -0.03, 1.42))
    neck.parent = body; neck.matrix_parent_inverse = body.matrix_world.inverted()
    bpy.context.view_layer.update()
    for o in list(bpy.data.objects):
        if o.parent == body and o.name.startswith(('nils_head', 'eye_', 'lid_', 'brow_', 'sideburn_')):
            mw = o.matrix_world.copy(); o.parent = neck; o.matrix_world = mw
    bpy.context.view_layer.update()

    eyes = [bpy.data.objects[n] for n in ('eye_L', 'eye_R')]
    lids = [bpy.data.objects[n] for n in ('lid_L', 'lid_R')]
    browL = bpy.data.objects['brow_L']
    hang = bpy.data.objects.get('float_hang')
    flt = bpy.data.objects['float']
    cam_target = None

    # targets (world)
    eye_c = sum((e.matrix_world.translation for e in eyes), Vector()) / 2
    float_end = flt.location + Vector((0.03, -0.004, 0))
    # ------------------------------------------------------------ camera: medium, eye level, slow push
    cpos = Vector((DESK.x + 0.36, DESK.y - 0.66, 1.43)); ctgt = Vector((DESK.x + 0.14, DESK.y + 0.3, 1.22))
    cam = kit.camera('cam', tuple(cpos), tuple(ctgt), lens=36, fstop=3.5, focus=(eye_c - cpos).length)
    key(cam, 1, loc=cpos); key(cam, END, loc=cpos + (ctgt - cpos).normalized() * 0.07)
    look_cam = cpos.copy()

    # ------------------------------------------------------------ the float on the desk rolls 3 cm, rocks back
    r0 = flt.rotation_euler.copy(); l0 = flt.location.copy()
    key(flt, 1, loc=l0, rot=r0); key(flt, 20, loc=l0, rot=r0)
    r1 = r0.copy(); r1.rotate_axis('Z', math.radians(70))
    key(flt, 32, loc=l0 + Vector((0.032, -0.004, 0)), rot=r1)
    r2 = r0.copy(); r2.rotate_axis('Z', math.radians(62))
    key(flt, 37, loc=l0 + Vector((0.029, -0.0036, 0)), rot=r2)
    key(flt, 41, loc=l0 + Vector((0.03, -0.004, 0)), rot=r1)

    # ------------------------------------------------------------ head (neck) and eyes
    hy_c, hp_c = yaw_pitch(neck.matrix_world.translation + Vector((0, 0, 0.13)), look_cam)
    hy_f, hp_f = yaw_pitch(neck.matrix_world.translation + Vector((0, 0, 0.13)), float_end)
    ey_c, ep_c = yaw_pitch(eye_c, look_cam)
    ey_f, ep_f = yaw_pitch(eye_c, float_end)
    head_share = 0.6                                   # the head turns 60 % of the way; the eyes do the rest
    H = lambda share_y, share_p, yb, pb: Euler((pb * share_p, 0, yb * share_y))
    head_cam = Euler((hp_c * 0.35 - math.radians(4), 0, hy_c * 0.35))   # the brief: head tips up slightly
    head_flt = Euler((hp_f * head_share, 0, hy_f * head_share))
    def eye_rel(head, y, p):
        return Euler((p - head.x, 0, y - head.z))
    for f, h in ((1, head_cam), (42, head_cam), (52, Euler((head_flt.x * 1.06, 0, head_flt.z * 1.06))), (58, head_flt),
                 (100, head_flt), (112, Euler((head_cam.x - math.radians(1.2), 0, head_cam.z * 0.9))), (120, head_cam)):
        key(neck, f, rot=h)
    for e in eyes:
        for f, (h, y, p) in ((1, (head_cam, ey_c, ep_c)), (34, (head_cam, ey_c, ep_c)), (37, (head_cam, ey_f, ep_f)),
                             (42, (head_cam, ey_f, ep_f)), (52, (head_flt, ey_f, ep_f)), (92, (head_flt, ey_f, ep_f)),
                             (95, (head_flt, ey_c, ep_c)), (100, (head_flt, ey_c, ep_c)), (112, (head_cam, ey_c, ep_c))):
            key(e, f, rot=eye_rel(h, y, p))
    # ------------------------------------------------------------ lids: follow the gaze down a little, blink twice
    base = [l.rotation_euler.copy() for l in lids]
    for l, b in zip(lids, base):
        def lid(f, extra):
            key(l, f, rot=Euler((b.x + math.radians(extra), b.y, b.z)))
        lid(1, 0); lid(9, 0); lid(11, 50); lid(12, 50); lid(15, 0)                    # blink
        lid(34, 0); lid(37, 9); lid(92, 9); lid(95, 0)                                  # look down: lids drop
        lid(66, 9); lid(68, 55); lid(69, 55); lid(72, 9)                                # blink during the hold
        lid(126, 0); lid(128, 50); lid(129, 50); lid(132, 0)
    # ------------------------------------------------------------ one brow lifts while he decides
    bl = browL.location.copy()
    key(browL, 1, loc=bl); key(browL, 80, loc=bl); key(browL, 88, loc=bl + Vector((0, 0, 0.005)))
    key(browL, 120, loc=bl + Vector((0, 0, 0.004))); key(browL, 144, loc=bl + Vector((0, 0, 0.001)))
    # ------------------------------------------------------------ breathing and the hanging float lagging the head
    s0 = body.scale.copy()
    for f in range(1, END + 1, 21):
        key(body, f, scale=(s0.x, s0.y, s0.z)); key(body, min(END, f + 10), scale=(s0.x * 1.002, s0.y * 1.004, s0.z * 1.003))
    if hang:
        h0 = hang.rotation_euler.copy()
        for f, dz in ((1, 0), (46, 0), (56, 6), (62, -3), (68, 1.5), (74, 0), (104, 0), (114, -5), (120, 2.5), (126, 0)):
            key(hang, f, rot=Euler((h0.x, h0.y + math.radians(dz), h0.z)))
    for o in [neck, browL, body, flt, cam] + eyes + lids + ([hang] if hang else []):
        ease_all(o)
    print('ANIM', dict(head_cam=tuple(round(math.degrees(a), 1) for a in head_cam), head_float=tuple(round(math.degrees(a), 1) for a in head_flt)))
