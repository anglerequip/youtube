# ===================================================================== v3 characters in the shed (appended after the set)
# Native motion capture through the NLA (same skeleton, no retargeting), lip sync on the mouth primitives, blinks,
# brow raises on stressed words, a clean three-camera test of lines 6-8 of "The Lure Avalanche".
for a_, loc_, yaw_ in ((nils, (0.5, 0.22, 0), -48), (theo, (-0.42, -0.36, 0), 66)):
    a_.rotation_mode = 'XYZ'; a_.location = loc_; a_.rotation_euler = (0, 0, math.radians(yaw_))
bpy.context.view_layer.update()
def head_pos(a_):
    return a_.matrix_world @ a_.data.bones['Head'].head_local + Vector((0, 0, 0.12))
H_N, H_T = head_pos(nils), head_pos(theo)
for o_ in list(bpy.data.objects):                                    # the old character lights aimed at old head heights
    if o_.name.startswith(('char_key', 'char_rim')): bpy.data.objects.remove(o_)
kit.area('char_key', (-0.9, -1.3, 2.3), tuple((H_N + H_T) / 2), color='#ffcf9a', power=110, size=0.8)
kit.area('char_rim', (0.9, 1.05, 2.2), tuple(H_N), color='#7fc4e0', power=500, size=0.5)
kit.area('char_rim2', (-1.3, 0.9, 2.1), tuple(H_T), color='#7fc4e0', power=450, size=0.5)

for g_ in ('UAL1_Standard.glb', 'UAL2_Standard.glb'):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=kit.asset('D:\\CounterPhysical\\assets-cc0\\anim\\' + g_))
    for o_ in [o_ for o_ in bpy.data.objects if o_ not in before]: bpy.data.objects.remove(o_)

TL = json.load(open(arg('--timeline'))); T0, T1 = float(arg('--t0', '13.1')), float(arg('--t1', '20.0'))
FPS = 24; N = int(round((T1 - T0) * FPS)); sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, N
lines = [dict(l, start=l['start'] - T0) for l in TL['lines'] if T0 - 0.2 <= l['start'] < T1]
def F(t): return int(round(t * FPS)) + 1
def talking_spans(who):
    return [(l['start'] - 0.15, l['start'] + l['dur'] + 0.25) for l in lines if l['who'] == who]

def nla(arm_, who, off):
    """Bottom track: the idle loop under everything (full influence, never a gap, never the T-pose).
    Top track: a talking strip per line, cross-fading in and out over 8 frames."""
    arm_.animation_data_create(); arm_.animation_data.action = None
    base, top = arm_.animation_data.nla_tracks.new(), arm_.animation_data.nla_tracks.new()
    def strip(track, name, f0, f1, off_s, blend):
        ac = bpy.data.actions[name]; L_ = ac.frame_range[1] - ac.frame_range[0]
        st = track.strips.new(f'{name}_{f0}', f0, ac)
        st.action_frame_start = ac.frame_range[0] + (off_s * 30.0) % max(1.0, L_); st.action_frame_end = ac.frame_range[1]
        st.scale = FPS / 30.0
        st.repeat = max(1.0, (f1 - f0) / max(1.0, (st.action_frame_end - st.action_frame_start) * st.scale))
        st.blend_in = st.blend_out = blend
        try: st.action_slot = ac.slots[0]
        except Exception: pass
        return st
    b_ = strip(base, 'Idle_Loop', -30, N + 30, off, 0); b_.extrapolation = 'HOLD'
    for (a0, a1) in talking_spans(who):
        strip(top, 'Idle_Talking_Loop', F(a0) - 4, F(a1) + 4, a0 + off, 8).extrapolation = 'NOTHING'
nla(nils, 'nils', 0.0); nla(theo, 'theo', 1.3)

# ------------------------------------------------------------------ eye contact: heads turn to each other on top of the mocap
def look_at(arm_, target, infl=0.7):
    m3 = arm_.data.bones['Head'].matrix_local.to_3x3().inverted()
    face = m3 @ Vector((0, -1, 0))                                    # the face looks along world -Y at rest
    ax = max((('X', face.x), ('Y', face.y), ('Z', face.z)), key=lambda q: abs(q[1]))
    track = ('TRACK_' if ax[1] > 0 else 'TRACK_NEGATIVE_') + ax[0]
    e_ = bpy.data.objects.new(arm_.name + '_look', None); kit.link(e_); e_.location = target
    for bn, k_ in (('neck_01', 0.35), ('Head', infl)):
        c_ = arm_.pose.bones[bn].constraints.new('DAMPED_TRACK'); c_.target = e_; c_.track_axis = track; c_.influence = k_
    return e_
look_at(nils, H_T + Vector((0, 0, -0.05))); look_at(theo, H_N + Vector((0, 0, -0.05)))

# ------------------------------------------------------------------ faces: lip sync, blinks, brows
import lipsync
R_ = random.Random(7)
for who, arm_ in (('nils', nils), ('theo', theo)):
    ws = [dict(w=w['w'], s=w['s'] + l['start'], e=w['e'] + l['start']) for l in lines if l['who'] == who for w in l['words']]
    VIS = lipsync.visemes(ws, N, FPS)
    mouth = bpy.data.objects[f'{who}_mouth']; lo = bpy.data.objects[f'{who}_lip_lower']; up = bpy.data.objects[f'{who}_lip_upper']
    m0, lo0, up0 = mouth.scale.copy(), lo.location.copy(), up.scale.copy()
    lids = [bpy.data.objects[f'{who}_lid_{s}'] for s in 'LR']; l0 = [o_.rotation_euler.copy() for o_ in lids]
    brows = [bpy.data.objects[f'{who}_brow_{s}'] for s in 'LR']; b0 = [o_.location.copy() for o_ in brows]
    blinks = []; t = R_.uniform(0.4, 1.2)
    while t < T1 - T0: blinks.append(F(t)); t += R_.uniform(2.0, 3.8)
    accents = [F(w['s']) for w in ws if len(w['w'].strip('.,?!')) >= 6]
    # parented to the Head bone: local axes follow the bone (bone Y = up the head); measure the mouth's open direction
    hb = arm_.data.bones['Head'].matrix_local.to_3x3().inverted()
    down = (hb @ Vector((0, 0, -1))).normalized(); up_v = -down
    for f in range(1, N + 1):
        v = VIS[f - 1]; jaw = sum(VIS[max(0, min(N - 1, f - 1 + k))]['jaw'] * wk for k, wk in ((-1, 0.25), (0, 0.5), (1, 0.25)))
        ee, oo = v['vis'].get('EE', 0), v['vis'].get('OO', 0)
        mouth.scale = (m0.x * (1 + 0.25 * ee - 0.3 * oo), m0.y, m0.z * (1 + 7.0 * jaw)); mouth.keyframe_insert('scale', frame=f)
        lo.location = lo0 + down * (0.022 * jaw); lo.keyframe_insert('location', frame=f)
        up.scale = (up0.x * (1 + 0.15 * ee - 0.2 * oo), up0.y, up0.z); up.keyframe_insert('scale', frame=f)
        bl = 1.0 if any(0 <= f - b < 3 for b in blinks) else 0.0
        for o_, r0 in zip(lids, l0):
            o_.rotation_euler = (r0.x + math.radians(55) * bl, r0.y, r0.z); o_.keyframe_insert('rotation_euler', frame=f)
        br = sum(math.sin(math.pi * (f - a) / 10.0) ** 2 for a in accents if 0 <= f - a < 10)
        for o_, p0 in zip(brows, b0):
            o_.location = p0 + up_v * (0.008 * min(1.0, br)); o_.keyframe_insert('location', frame=f)

# ------------------------------------------------------------------ cameras: two-shot, Nils close, Theo close
def cam_at(name, loc, tgt, lens, fs, f0, f1, creep=0.06):
    c = kit.camera(name, tuple(loc), tuple(tgt), lens=lens, fstop=fs, focus=(Vector(tgt) - Vector(loc)).length)
    for f in range(f0, f1 + 1, 2):
        u = (f - f0) / max(1, f1 - f0); c.location = Vector(loc) + (Vector(tgt) - Vector(loc)) * creep * u * u * (3 - 2 * u); c.keyframe_insert('location', frame=f)
    m = sc.timeline_markers.new(name, frame=f0); m.camera = c; return c
starts = [l['start'] for l in lines]
cA = cam_at('two', (-0.35, -2.0, 1.55), ((H_N + H_T) / 2 + Vector((0.05, 0, -0.3))), 30, 6.0, 1, F(starts[1]) - 3)   # favours Nils, who speaks
_d = (H_N - H_T); _d.z = 0; _d.normalize()
_p = Vector((_d.y, -_d.x, 0))                                       # sideways, toward the camera side
if _p.y > 0: _p = -_p
cB = cam_at('theo', H_T + _d * 1.45 + _p * 0.55 + Vector((0, 0, 0.0)), H_T + Vector((0, 0, -0.15)), 60, 3.5, F(starts[1]) - 2, F(starts[2]) - 3)
cC = cam_at('nils', H_N + Vector((-0.8, -1.05, -0.05)), H_N + Vector((0, 0, -0.12)), 45, 3.5, F(starts[2]) - 2, N, 0.1)
sc.camera = cA
fdir = os.path.join(OUT, 'frames'); os.makedirs(fdir, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'v3_shed.blend'))
if arg('--still'):
    for s_f in arg('--still').split(','):
        sc.frame_set(int(s_f)); sc.render.filepath = os.path.join(OUT, f'still_{s_f}.png'); bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = os.path.join(fdir, 'f'); bpy.ops.render.render(animation=True)
print('V3SHED', N)
