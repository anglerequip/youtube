# ----------------------------------------------------------------------------------------------- "The Lure Avalanche"
# (Caesar 27 Nov: "bring in interesting elements ... creative scripts ... 30 seconds"). New pieces: a giant tackle box
# whose lid bursts off, a few hundred lures pouring over Nils's boots (our own little ballistic sim), Nils's coffee mug,
# a phone, a weather change outside the window, the barometer needle falling, one lure that rises and glows.
ACT = False
TL = json.load(open(arg('--timeline'))); N = int(math.ceil(TL['total'] * FPS))
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
theo.location = (-0.58, -0.46, 0); bpy.context.view_layer.update()           # close enough to reach the box
H_T = theo.matrix_world @ Vector((0, -0.03, 1.56))
def clean_regions(name, iters=4):
    """Mode filter on the painted clothing regions: a face takes the material most of its neighbours have, so
    stray patches (yellow flecks on a grey sleeve, blue blots on the bib) disappear and borders stop being ragged."""
    o = bpy.data.objects.get(name)
    if not o: return
    bm_ = bmesh.new(); bm_.from_mesh(o.data); bm_.faces.ensure_lookup_table()
    nb = [[g.index for e in f.edges for g in e.link_faces if g.index != f.index] for f in bm_.faces]
    mi = [f.material_index for f in bm_.faces]; changed = 0
    for _ in range(iters):
        new = mi[:]
        for i, ns in enumerate(nb):
            if not ns: continue
            cnt = {}
            for j in ns: cnt[mi[j]] = cnt.get(mi[j], 0) + 1
            top = max(cnt, key=cnt.get)
            if top != mi[i] and cnt[top] >= max(2, len(ns) * 0.6): new[i] = top; changed += 1
        mi = new
    for f, m_ in zip(bm_.faces, mi): f.material_index = m_
    bm_.to_mesh(o.data); bm_.free(); print('CLEAN', name, changed)
clean_regions('nils_tsg'); clean_regions('theo_tsg')
# the image-to-3D body kept its hands at the thighs; once the arms were rebuilt, those lumps hung off Theo's jeans
# like a black box (Caesar's screenshot). Flatten them back onto the thigh.
_tb = bpy.data.objects.get('theo_tsg')
if _tb:
    for v_ in _tb.data.vertices:
        if 0.5 < v_.co.z < 1.0 and abs(v_.co.x) > 0.245: v_.co.x = math.copysign(0.245, v_.co.x)
BOXP = Vector((0.06, -0.1, 0.0))
ANK0 = {w_: min((a_.matrix_world @ a_.data.bones[b_].tail_local).z for b_ in ('shin.L', 'shin.R')) for w_, a_ in (('nils', nils), ('theo', theo))}
TBM = kit.painted('tb_giant', ['#b8481a', '#d25a22', '#e46e30'], rough=0.7, scale=5.0, cavity=0.5)
BW, BD, BH = 0.6, 0.4, 0.3
kit.box('gt_body', (BW, BD, BH), (BOXP.x, BOXP.y, BH / 2), mat=TBM, bev=0.02, segs=2)
kit.box('gt_rim', (BW + 0.02, BD + 0.02, 0.03), (BOXP.x, BOXP.y, BH - 0.015), mat=M['steel'], bev=0.006)
kit.box('gt_tray', (BW - 0.04, BD - 0.04, 0.01), (BOXP.x, BOXP.y, BH - 0.06), mat=M['tray'], bev=0.003)
for sx in (-1, 1):
    kit.box('gt_latch', (0.05, 0.02, 0.07), (BOXP.x + sx * 0.18, BOXP.y - BD / 2 - 0.012, BH - 0.04), mat=M['steel'], bev=0.005)
LID = bpy.data.objects.new('gt_lid_root', None); kit.link(LID); LID.location = (BOXP.x, BOXP.y, BH + 0.03)
_l = kit.box('gt_lid', (BW + 0.03, BD + 0.03, 0.06), (0, 0, 0), mat=TBM, bev=0.02, segs=2); _l.parent = LID
_h = kit.box('gt_handle', (0.2, 0.035, 0.035), (0, 0, 0.045), mat=M['steel'], bev=0.01); _h.parent = LID

# lures: one shared mesh per colour, linked copies
LURE_PROFILE = [(0, 0), (0.009, 0.008), (0.013, 0.03), (0.009, 0.058), (0, 0.07)]
_base = []
for k, mat_ in enumerate(LURES):
    o = kit.lathe('lure_base', LURE_PROFILE, seg=12, loc=(0, 0, -5), mat=mat_, angle=20)
    o.scale = (1.7, 1.2, 1.7); _base.append(o)
RL = random.Random(11)
NL = int(arg('--lures', '330'))
GRAV, DT = -9.8, 1.0 / (FPS * 4)
NF_ = nils.matrix_world @ Vector((0, 0, 0))                                 # Nils's feet
FEET = [a_.matrix_world @ a_.data.bones[b_].tail_local for a_ in (nils, theo) for b_ in ('shin.L', 'shin.R')]   # ankles
CELL = 0.045; HF = {}
def hf(x, y):
    k = (int(math.floor(x / CELL)), int(math.floor(y / CELL)))
    if k not in HF:
        h = 0.0
        if abs(x - BOXP.x) < BW / 2 and abs(y - BOXP.y) < BD / 2: h = BH - 0.05
        HF[k] = h
    return k
def sim_lure(p, v, t0, spin):
    """Positions + rotations per frame (frame index from 1) for one lure launched at t0 from p with velocity v."""
    out = {}; t = 0.0; p = p.copy(); v = v.copy(); rest = False; landed = 0
    rot = Vector((RL.uniform(0, 6.28), RL.uniform(0, 6.28), RL.uniform(0, 6.28))); flat = None; yaw = RL.uniform(0, 6.28)
    nfr = N
    for f in range(1, nfr + 1):
        tf = (f - 1) / FPS
        if tf >= t0 and not rest:
            for _ in range(4):
                v.z += GRAV * DT; p += v * DT
                if landed == 0: rot += spin * DT
                for fp in FEET:                                              # boots are solid: slide the lure off
                    d_ = Vector((p.x - fp.x, p.y - fp.y))
                    if d_.length < 0.13 and p.z < 0.16:
                        d_ = d_.normalized() if d_.length > 1e-4 else Vector((1, 0)); p.x, p.y = fp.x + d_.x * 0.13, fp.y + d_.y * 0.13
                        v.x, v.y = 0.4 * d_.x * max(0.2, v.xy.length), 0.4 * d_.y * max(0.2, v.xy.length)
                k = hf(p.x, p.y); floor = HF[k] + 0.011
                if p.z < floor:
                    p.z = floor
                    if landed == 0 and flat is None: flat = (math.radians(90 + RL.uniform(-12, 12)), RL.uniform(-0.3, 0.3), yaw)
                    landed += 1
                    if abs(v.z) > 0.6 and landed < 3: v.z = -v.z * 0.28; v.x *= 0.55; v.y *= 0.55
                    else:
                        v.z = 0; v.x *= 0.82; v.y *= 0.82
                        if v.xy.length < 0.05:
                            rest = True; HF[k] += 0.012; break
        if flat is not None:
            r_ = Vector(flat)
            rot = rot.lerp(r_, 0.35)
        out[f] = (p.copy(), rot.copy())
    return out
LURE_TRACKS = []
for i in range(NL):
    o = _base[i % len(_base)].copy(); kit.link(o); o.name = 'lure_av'
    p = Vector((BOXP.x + RL.uniform(-0.24, 0.24), BOXP.y + RL.uniform(-0.15, 0.15), BH - 0.04 + RL.uniform(-0.02, 0.06)))
    t0 = 0.34 + 1.5 * (i / NL) ** 1.6 + RL.uniform(0, 0.08)                 # a burst, then a pour
    ang = math.radians(RL.gauss(40, 38))                                     # mostly toward Nils (+x +y)
    sp = RL.uniform(0.5, 1.7) * (1.25 if i < NL * 0.3 else 0.8)
    v = Vector((sp * math.cos(ang), sp * math.sin(ang), RL.uniform(1.6, 3.1) * (1.0 if i < NL * 0.3 else 0.7)))
    spin = Vector((RL.uniform(-18, 18), RL.uniform(-18, 18), RL.uniform(-10, 10)))
    LURE_TRACKS.append((o, sim_lure(p, v, t0, spin)))
for o, tr in LURE_TRACKS:
    last = None
    for f, (p, r) in tr.items():
        key = (tuple(round(c, 4) for c in p), tuple(round(c, 3) for c in r))
        if key == last and f > 2: continue
        o.location = p; o.rotation_euler = r
        o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_euler', frame=f); last = key
PILE = sum((tr[N][0] for o, tr in LURE_TRACKS), Vector()) / max(1, NL)
for o in _base: bpy.data.objects.remove(o)

# the lid: bursts up and away from Theo, tumbles, lands behind the box
lp = Vector(LID.location); lv = Vector((0.35, 0.9, 3.3)); lr = Vector((0, 0, 0)); lw = Vector((7.5, 2.0, 1.2)); landed_ = False
for f in range(1, N + 1):
    tf = (f - 1) / FPS
    if tf >= 0.32 and not landed_:
        for _ in range(4):
            lv.z += GRAV * DT; lp += lv * DT; lr += lw * DT
            if lp.z < 0.03 and lv.z < 0:
                lp.z = 0.03; landed_ = True; lr = Vector((round(lr.x / math.pi) * math.pi, 0, lr.z)); break
    LID.location = lp; LID.rotation_euler = lr
    LID.keyframe_insert('location', frame=f); LID.keyframe_insert('rotation_euler', frame=f)
    if landed_ and tf > 2.0: break

# the hero lure: chartreuse (matches the phone's pick), lands at the front of the pile, later rises and glows
HERO_M = bpy.data.materials.new('hero_lure'); HERO_M.use_nodes = True; _hb = HERO_M.node_tree.nodes['Principled BSDF']
_hb.inputs['Base Color'].default_value = hexc('#c8e030'); _hb.inputs['Roughness'].default_value = 0.5
_hb.inputs['Emission Color'].default_value = hexc('#e8ff60'); _hb.inputs['Emission Strength'].default_value = 0.0
HERO = kit.lathe('hero_lure', [(0, 0), (0.012, 0.01), (0.018, 0.04), (0.012, 0.08), (0, 0.095)], seg=20, loc=(0, 0, 0), mat=HERO_M, angle=20)
HERO.scale = (2.0, 1.4, 2.0)
HERO_START = Vector((0.33, 0.02, 0.022))
HERO_HALO = kit.point('hero_glow', (0, 0, -5), color='#e8ff60', power=0.0, radius=0.02)

# Nils's coffee mug and phone, Theo's two lures (moved onto the hands every frame in the main loop)
MUG = bpy.data.objects.new('mug_root', None); kit.link(MUG)
_m1 = kit.cyl('mug', 0.038, 0.095, (0, 0, 0.0475), seg=24, mat=kit.painted('mug_s', ['#2c5a8a', '#336a9e', '#3d7ab0'], rough=0.7, scale=10.0), bev=0.006)
_m2 = kit.cyl('coffee', 0.033, 0.004, (0, 0, 0.088), seg=24, mat=kit.flat('coffee_s', '#3a2216', rough=0.3), bev=0)
_m3 = kit.box('mug_handle', (0.012, 0.03, 0.05), (0, 0.048, 0.05), mat=bpy.data.materials['mug_s'], bev=0.005)
for o in (_m1, _m2, _m3): o.parent = MUG
SCREEN_IMG = kit.asset(r'D:\CounterPhysical\research\omega\lure30\phone_screen.png')
def make_phone(name):
    root = bpy.data.objects.new(name, None); kit.link(root)
    b_ = kit.box(name + '_body', (0.075, 0.009, 0.15), (0, 0, 0), mat=kit.flat('phone_s', '#1a1c20', rough=0.5), bev=0.006); b_.parent = root
    sm = bpy.data.materials.get('screen_s')
    if not sm:
        sm = bpy.data.materials.new('screen_s'); sm.use_nodes = True; nt_ = sm.node_tree; bb = nt_.nodes['Principled BSDF']
        ti = nt_.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(SCREEN_IMG, check_existing=True)
        nt_.links.new(ti.outputs['Color'], bb.inputs['Base Color']); nt_.links.new(ti.outputs['Color'], bb.inputs['Emission Color'])
        bb.inputs['Emission Strength'].default_value = 0.8; bb.inputs['Roughness'].default_value = 0.35
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -0.0052, 0), rotation=(math.radians(90), 0, 0))
    s_ = bpy.context.active_object; s_.name = name + '_screen'; s_.scale = (0.068, 0.136, 1); s_.data.materials.append(sm); s_.parent = root
    return root
PHONE = make_phone('phone')
PHONE_HERO = make_phone('phone_hero')
bpy.ops.mesh.primitive_torus_add(major_radius=0.008, minor_radius=0.0009, major_segments=32, minor_segments=6, location=(0, 0, -5))
PULSE = bpy.context.active_object; PULSE.name = 'pin_pulse'; PULSE.data.materials.append(kit.flat('pulse_s', '#ffd060', emit='#ffd060', emit_strength=6.0))
HL = [kit.lathe('held_lure', LURE_PROFILE, seg=12, loc=(0, 0, -5), mat=LURES[c], angle=20) for c in (1, 4)]
for o in HL: o.scale = (2.4, 1.7, 2.4)

# outside: a sky that clouds over, trees that start to bend in the wind
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, D1 + 7.5, 2.5), rotation=(math.radians(90), 0, 0))
SKY = bpy.context.active_object; SKY.name = 'sky_out'; SKY.scale = (30, 12, 1)
SKM = bpy.data.materials.new('sky_out'); SKM.use_nodes = True; snt = SKM.node_tree; sb = snt.nodes['Principled BSDF']
stc = snt.nodes.new('ShaderNodeTexCoord'); smp = snt.nodes.new('ShaderNodeMapping'); snz = snt.nodes.new('ShaderNodeTexNoise')
snz.inputs['Scale'].default_value = 2.2; snz.inputs['Detail'].default_value = 6.0
snt.links.new(stc.outputs['Object'], smp.inputs['Vector']); snt.links.new(smp.outputs['Vector'], snz.inputs['Vector'])
scr = snt.nodes.new('ShaderNodeValToRGB'); scr.color_ramp.elements[0].position = 0.45; scr.color_ramp.elements[1].position = 0.7
scr.color_ramp.elements[0].color = hexc('#8fc4e8'); scr.color_ramp.elements[1].color = hexc('#f4f4f0')
snt.links.new(snz.outputs['Fac'], scr.inputs['Fac'])
sgrey = snt.nodes.new('ShaderNodeMix'); sgrey.data_type = 'RGBA'; sgrey.inputs['B'].default_value = hexc('#6e7680')
snt.links.new(scr.outputs['Color'], sgrey.inputs['A'])
snt.links.new(sgrey.outputs['Result'], sb.inputs['Base Color']); snt.links.new(sgrey.outputs['Result'], sb.inputs['Emission Color'])
sb.inputs['Emission Strength'].default_value = 1.0
SKY.data.materials.append(SKM)
for o in [o for o in bpy.data.objects if o.name.startswith('pane')]: bpy.data.objects.remove(o)   # the glass rendered black (no raytracing): an open window
SKY.visible_shadow = False; SKY.visible_diffuse = False                      # it must not shade the sunlit garden
for o in [o for o in bpy.data.objects if o.name.startswith(('jar', 'lidj')) and o.location.x < -0.5 and o.location.z > 1.5]:
    bpy.data.objects.remove(o)                                               # top-left jars hid the barometer
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.4         # the whip-pan and the avalanche smear
BUSHES = [o for o in bpy.data.objects if o.name.startswith('bush')]
for o in BUSHES: o['r0'] = tuple(o.rotation_euler); o['l0'] = tuple(o.location)
SUN = bpy.data.objects['sun']; WFILL = bpy.data.objects['window_fill']
