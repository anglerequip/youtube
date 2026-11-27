"""The fishing shed: Nils and Theo pick lures by reading the weather and the time (Caesar, 27 Nov).

  blender -b -P tools/blender/omega/shed.py -- --nils <nils_rig.blend> --theo <theo_rig.blend> --timeline <timeline.json>
        --out <dir> [--pct 50] [--samples 32] [--still F]

Set: a small timber shed among trees, warm and friendly (Caesar: the dusk dock read as 'weird, kinda scary'):
vertical pine boards, a window full of green daylight, a workbench with tackle boxes, a pegboard of lures, a rod rack,
a wall clock and a brass barometer (the two things the script is about), a hanging lamp.
Acting (Caesar: 'weird body movements'): one head attitude per phrase, a nod on stressed words, small overshoot,
quiet listeners, no hip sway; see act() below."""
import json, math, os, random, sys
import bpy, bmesh
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import kit, lipsync
from kit import hexc
from anim_skit import set_bone, look_angles

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
OUT = arg('--out'); os.makedirs(OUT, exist_ok=True)
FPS = 24
sc = kit.reset(); kit.eevee_quality(sc, int(arg('--samples', '32'))); kit.output(sc, pct=int(arg('--pct', '50')))
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
sc.view_settings.exposure = -0.4
R = random.Random(5)

# ----------------------------------------------------------------------------------------------- materials
M = dict(
    board=kit.painted('board', ['#8e5e34', '#a06c3c', '#b47c46'], rough=0.7, scale=4.0, stripes=(14.0, 0.55), grain_axis='Z'),
    board_dk=kit.painted('board_dk', ['#5a3a22', '#6e4a2c', '#835a37'], rough=0.75, scale=1.0, stripes=(9.0, 0.5)),
    beam=kit.painted('beam', ['#4a301c', '#5c3d24', '#6e4a2c'], rough=0.8, scale=1.5, stripes=(7.0, 0.5)),
    bench=kit.painted('bench', ['#6b4426', '#82552f', '#996639'], rough=0.55, scale=1.3, stripes=(12.0, 0.4), grain_axis='X'),
    peg=kit.painted('peg', ['#b89a6c', '#c9ab7c', '#d8bb8c'], rough=0.8, scale=4.0, cavity=0.3),
    box_g=kit.painted('box_g', ['#2f5a3a', '#3a6d46', '#4a8254'], rough=0.35, scale=6.0),
    box_r=kit.painted('box_r', ['#7a1f18', '#962a20', '#ad3626'], rough=0.35, scale=6.0),
    tray=kit.painted('tray', ['#c9b98f', '#d8caa2', '#e6dab6'], rough=0.4, scale=8.0),
    brass=kit.painted('brass_s', ['#6e5422', '#a07c3a', '#d0ad60'], rough=0.22, metal=1.0, scale=6.0, cavity=0.6),
    steel=kit.painted('steel_s', ['#4a4e52', '#6e7378', '#959a9f'], rough=0.3, metal=1.0, scale=6.0),
    dial=kit.painted('dial', ['#e8e0cc', '#f0e9d8', '#f7f2e6'], rough=0.5, scale=10.0, cavity=0.2),
    ink=kit.flat('ink_s', '#1e1a18', rough=0.6),
    red=kit.flat('red_s', '#b02a1e', rough=0.5),
    cork=kit.painted('cork_s', ['#8a6a40', '#a5824f', '#bd9a62'], rough=0.85, scale=20.0),
    blank=kit.painted('blank', ['#1d2a24', '#26372f', '#30453a'], rough=0.3, scale=10.0),
    glass=kit.flat('glass_s', '#ffffff', rough=0.05, transmission=1.0, ior=1.2),
    bulb=kit.flat('bulb', '#ffd9a0', emit='#ffcf8a', emit_strength=25.0),
    net=kit.painted('net', ['#6f6250', '#887760', '#9c8a70'], rough=0.9, scale=30.0),
    rubber=kit.painted('rubber', ['#22302a', '#2c3c34', '#38493f'], rough=0.4, scale=6.0),
)
LURE_COLS = ['#d43a2a', '#f0c23a', '#e8e4d6', '#3a8a4a', '#2c6fb0', '#e07a2a', '#8a3ab0', '#c8c8c8', '#2a2a2a', '#9ad04a']
LURES = [kit.painted(f'lure{i}', [c, c, '#ffffff'], rough=0.2, scale=30.0, cavity=0.3) for i, c in enumerate(LURE_COLS)]

# ----------------------------------------------------------------------------------------------- the shed (inside: x -1.6..1.6, y -1.4..1.2)
W0, W1, D0, D1, HGT = -1.6, 1.6, -1.6, 1.2, 2.45
for k in range(int((W1 - W0) / 0.16)):                         # back wall, vertical boards with a window cut
    x = W0 + 0.08 + k * 0.16
    if -0.55 < x < 0.55:
        kit.box('bw_lo', (0.155, 0.03, 0.95), (x, D1, 0.475), mat=M['board'], bev=0.006, jitter=0.003, seed=k)
        kit.box('bw_hi', (0.155, 0.03, 0.5), (x, D1, 2.2), mat=M['board'], bev=0.006, jitter=0.003, seed=k + 50)
    else:
        kit.box('bw', (0.155, 0.03, HGT), (x, D1, HGT / 2), mat=M['board'], bev=0.006, jitter=0.003, seed=k)
for side in (-1, 1):                                            # side walls
    for k in range(int((D1 - D0) / 0.16)):
        y = D0 + 0.08 + k * 0.16
        kit.box('sw', (0.03, 0.155, HGT), (side * W1, y, HGT / 2), mat=M['board'], bev=0.006, jitter=0.003, seed=200 + k * (side + 2))
for k in range(int((W1 - W0) / 0.2)):                           # floor planks
    kit.box('fl', (0.195, D1 - D0, 0.04), (W0 + 0.1 + k * 0.2, (D0 + D1) / 2, -0.02), mat=M['board_dk'], bev=0.005, jitter=0.002, seed=300 + k)
for y in (D0 + 0.3, -0.3, 0.7):                                 # ceiling beams + ceiling
    kit.box('beam', (W1 - W0, 0.12, 0.14), (0, y, HGT - 0.07), mat=M['beam'], bev=0.01)
kit.box('ceil', (W1 - W0, D1 - D0, 0.03), (0, (D0 + D1) / 2, HGT + 0.015), mat=M['board_dk'], bev=0)
# window frame + panes + outside greenery
for (sx, sz, x, z) in ((1.14, 0.07, 0, 1.95), (1.14, 0.07, 0, 0.98), (0.07, 1.0, -0.57, 1.465), (0.07, 1.0, 0.57, 1.465),
                       (0.04, 0.95, 0, 1.465), (1.1, 0.04, 0, 1.465)):
    kit.box('wf', (sx, 0.08, sz), (x, D1, z), mat=M['beam'], bev=0.006)
kit.box('pane', (1.1, 0.004, 0.95), (0, D1 + 0.02, 1.465), mat=M['glass'], bev=0)
LEAF = [kit.painted(f'leaf{i}', c, rough=0.8, scale=0.6, cavity=0.0) for i, c in enumerate(
    (['#4f7a2e', '#5f8f36', '#72a442'], ['#3f6a2a', '#4e7d32', '#5f913c'], ['#6a8f34', '#7ba43e', '#8cb84a']))]
for i in range(26):                                              # bright trees right outside the window
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=R.uniform(0.6, 1.3))
    o = kit.from_bm('bush', bm, LEAF[i % 3], smooth_angle=None)
    o.location = (R.uniform(-4, 4), D1 + R.uniform(1.5, 6), R.uniform(0.5, 3.2)); o.scale = (1, 1, R.uniform(0.8, 1.2))
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, D1 + 20.3, -0.05)); g = bpy.context.active_object
g.data.materials.append(kit.painted('grass_out', ['#5c8a32', '#6c9c3a', '#7eae46'], rough=0.9, scale=0.3, cavity=0))

# workbench under the window, with tackle boxes, a reel and lures laid out
BX, BY, BZ = 0.0, D1 - 0.33, 0.9
kit.box('bench_top', (1.7, 0.6, 0.06), (BX, BY, BZ - 0.03), mat=M['bench'], bev=0.01, segs=2, jitter=0.002)
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.box('bench_leg', (0.07, 0.07, BZ - 0.06), (BX + sx * 0.78, BY + sy * 0.25, (BZ - 0.06) / 2), mat=M['bench'], bev=0.008)
kit.box('shelf', (1.6, 0.5, 0.03), (BX, BY, 0.25), mat=M['bench'], bev=0.006)
def tackle_box(loc, mat, open_=True):
    x, y, z = loc
    kit.box('tb_body', (0.36, 0.2, 0.12), (x, y, z + 0.06), mat=mat, bev=0.01, segs=2)
    if open_:
        kit.box('tb_tray', (0.33, 0.18, 0.012), (x, y, z + 0.125), mat=M['tray'], bev=0.003)
        for i in range(6):
            kit.box('tb_div', (0.004, 0.17, 0.02), (x - 0.15 + i * 0.06, y, z + 0.14), mat=M['tray'], bev=0)
            l = kit.box('lure_s', (0.035, 0.012, 0.012), (x - 0.12 + i * 0.06, y + R.uniform(-0.04, 0.04), z + 0.14),
                        (0, 0, R.uniform(-0.6, 0.6)), mat=LURES[R.randrange(len(LURES))], bev=0.004)
        lid = kit.box('tb_lid', (0.36, 0.012, 0.2), (x, y + 0.11, z + 0.22), mat=mat, bev=0.008)
        lid.rotation_euler = (math.radians(-12), 0, 0)
    else:
        kit.box('tb_lidc', (0.37, 0.21, 0.03), (x, y, z + 0.135), mat=mat, bev=0.01)
        kit.box('tb_handle', (0.12, 0.02, 0.02), (x, y, z + 0.16), mat=M['steel'], bev=0.006)
tackle_box((BX - 0.45, BY - 0.02, BZ), M['box_g'], True)
tackle_box((BX + 0.48, BY + 0.05, BZ), M['box_r'], False)
tackle_box((BX + 0.4, BY, 0.27), M['box_g'], False)
kit.cyl('reel_body', 0.035, 0.04, (BX + 0.05, BY - 0.12, BZ + 0.035), (0, math.radians(90), 0), seg=24, mat=M['steel'], bev=0.004)
kit.cyl('reel_spool', 0.028, 0.03, (BX + 0.09, BY - 0.12, BZ + 0.035), (0, math.radians(90), 0), seg=24, mat=M['brass'], bev=0.003)

# pegboard of lures on the left wall ("all of these")
PX = W0 + 0.02
kit.box('pegboard', (0.02, 1.2, 0.9), (PX + 0.01, -0.1, 1.55), mat=M['peg'], bev=0.004)
for r in range(4):
    for c in range(6):
        y = -0.6 + c * 0.2; z = 1.9 - r * 0.21
        kit.cyl('pin', 0.004, 0.03, (PX + 0.035, y, z + 0.06), (0, math.radians(90), 0), seg=8, mat=M['steel'], bev=0)
        col = LURES[(r * 6 + c) % len(LURES)]
        body = kit.lathe('lure', [(0, 0), (0.012, 0.01), (0.016, 0.04), (0.011, 0.075), (0, 0.09)], seg=16,
                         loc=(PX + 0.045, y, z - 0.03), rot=(0, 0, 0), mat=col, angle=20)
        body.scale = (1, 0.6, 1)
        kit.box('lip', (0.022, 0.004, 0.012), (PX + 0.05, y, z - 0.035), mat=M['glass'], bev=0.002)
        kit.cyl('hook', 0.0015, 0.03, (PX + 0.045, y, z - 0.05), seg=6, mat=M['steel'], bev=0)
# rod rack on the right wall: five rods with cork handles and reels
for i in range(5):
    y = -0.9 + i * 0.16; x = W1 - 0.06
    kit.cyl('rod', 0.006 if True else 0, 1.9, (x, y, 1.15), (0, math.radians(-3), 0), seg=10, mat=M['blank'], bev=0, r2=0.0025)
    kit.cyl('handle', 0.014, 0.3, (x + 0.02, y, 0.3), (0, math.radians(-3), 0), seg=12, mat=M['cork'], bev=0.003)
    kit.cyl('rreel', 0.028, 0.03, (x - 0.01, y, 0.5), (0, math.radians(90), 0), seg=16, mat=M['steel'], bev=0.003)
kit.box('rack', (0.06, 0.9, 0.06), (W1 - 0.05, -0.58, 0.12), mat=M['beam'], bev=0.006)
kit.box('rack2', (0.06, 0.9, 0.04), (W1 - 0.05, -0.58, 2.0), mat=M['beam'], bev=0.006)
# the clock and the barometer, on the back wall beside the window (insert targets)
CLOCK = Vector((0.92, D1 - 0.03, 1.75)); BARO = Vector((-0.92, D1 - 0.03, 1.72))
for (c, ring, face) in ((CLOCK, M['beam'], M['dial']), (BARO, M['brass'], M['dial'])):
    kit.cyl('ring', 0.13, 0.04, tuple(c), (math.radians(90), 0, 0), seg=40, mat=ring, bev=0.01)
    kit.cyl('face', 0.112, 0.045, tuple(c + Vector((0, -0.003, 0))), (math.radians(90), 0, 0), seg=40, mat=face, bev=0)
    for k in range(12):
        a = k * math.pi / 6
        kit.box('tick', (0.006, 0.004, 0.02), tuple(c + Vector((0.095 * math.sin(a), -0.027, 0.095 * math.cos(a)))), (0, a, 0), mat=M['ink'], bev=0)
hands = {}
for name, L_, w, a in (('hour', 0.055, 0.008, 2.3), ('minute', 0.085, 0.005, 0.0)):
    h = kit.box('clock_' + name, (w, 0.003, L_), tuple(CLOCK + Vector((0, -0.03, 0))), mat=M['ink'], bev=0)
    for v in h.data.vertices: v.co.z += L_ / 2
    h.rotation_euler = (0, a, 0); hands[name] = h
needle = kit.box('baro_needle', (0.005, 0.003, 0.09), tuple(BARO + Vector((0, -0.03, 0))), mat=M['red'], bev=0)
for v in needle.data.vertices: v.co.z += 0.045
needle.rotation_euler = (0, math.radians(-35), 0)                 # "change" side: the weather is turning
for t, a in (('RAIN', -55), ('CHANGE', 0), ('FAIR', 55)):
    tx = kit.text_mesh('baro_' + t, t, 0.016, tuple(BARO + Vector((0.07 * math.sin(math.radians(a)), -0.028, 0.07 * math.cos(math.radians(a))))),
                       (math.radians(90), math.radians(a), 0), M['ink'])
# hanging lamp, net, boots by the door
kit.cyl('cord', 0.004, 0.5, (0.2, -0.2, HGT - 0.25), seg=6, mat=M['ink'], bev=0)
kit.lathe('shade', [(0.0, 0.0), (0.16, 0.0), (0.1, 0.09), (0.025, 0.13), (0.0, 0.13)], seg=32, loc=(0.2, -0.2, HGT - 0.62), mat=M['box_g'], angle=25)
kit.lathe('bulbm', [(0, 0), (0.035, 0.02), (0.03, 0.05), (0, 0.06)], seg=16, loc=(0.2, -0.2, HGT - 0.64), mat=M['bulb'], angle=60)
kit.point('lamp', (0.2, -0.2, HGT - 0.67), color='#ffc98a', power=90, radius=0.05)
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=12, y_segments=12, size=0.4)
net = kit.from_bm('net', bm, M['net'], smooth_angle=None); net.location = (W1 - 0.04, 0.55, 1.6); net.rotation_euler = (0, math.radians(90), 0)
wf = net.modifiers.new('wire', 'WIREFRAME'); wf.thickness = 0.004
for i, x in enumerate((-1.25, -1.1)):
    kit.box('boot', (0.11, 0.26, 0.05), (x, D0 + 0.4, 0.025), mat=M['rubber'], bev=0.015)
    kit.box('bootleg', (0.11, 0.12, 0.38), (x, D0 + 0.47, 0.22), mat=M['rubber'], bev=0.02)

# ----------------------------------------------------------------------------------------------- light: bright, warm, friendly
w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = hexc('#cfe3f2'); bg.inputs['Strength'].default_value = 1.0
s_ = kit.sun('sun', (55, 0, 200), color='#fff0d6', strength=4.0, angle=2.0)      # sun through the window
kit.area('window_fill', (0, D1 - 0.15, 1.5), (0, -0.5, 1.2), color='#e6f0ff', power=120, size=1.1, shape='SQUARE')
kit.area('room_fill', (0.0, D0 + 0.3, 2.2), (0, 0.2, 1.2), color='#ffe2c0', power=90, size=2.0)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.2, 1.2)); hz = bpy.context.active_object; hz.scale = (3.1, 2.7, 2.35)
hm = bpy.data.materials.new('dust'); hm.use_nodes = True; hnt = hm.node_tree; hnt.nodes.remove(hnt.nodes['Principled BSDF'])
vv = hnt.nodes.new('ShaderNodeVolumePrincipled'); vv.inputs['Density'].default_value = 0.012; vv.inputs['Color'].default_value = hexc('#fff3e0')
vv.inputs['Anisotropy'].default_value = 0.5
hnt.links.new(vv.outputs['Volume'], hnt.nodes['Material Output'].inputs['Volume']); hz.data.materials.append(hm)

# ----------------------------------------------------------------------------------------------- characters
def load(path):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects: kit.link(o)
load(arg('--nils')); load(arg('--theo'))
nils = bpy.data.objects['nils_rig']; theo = bpy.data.objects['theo_rig']
nils.location = (0.55, 0.25, 0); nils.rotation_euler = (0, 0, math.radians(-42))   # by the bench, turned to Theo
theo.location = (-0.45, -0.35, 0); theo.rotation_euler = (0, 0, math.radians(100))
bpy.context.view_layer.update()
H_N = nils.matrix_world @ Vector((0, -0.03, 1.56)); H_T = theo.matrix_world @ Vector((0, -0.03, 1.56))

# ----------------------------------------------------------------------------------------------- cameras + cuts
TL = json.load(open(arg('--timeline'))); N = int(math.ceil(TL['total'] * FPS))
sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, N
# Camera language from One Bold Chemist (v1/v5/v6/v8 overviews): every shot creeps slowly (dolly in a few %),
# punchlines get a fast push-in (zoom over ~0.3 s, ease-out, then hold), inserts pull focus onto the prop.
def F(t): return int(round(t * FPS))
TPL = {}
def tpl(name, loc, tgt, lens, fstop=3.5):
    TPL[name] = (Vector(loc), Vector(tgt), lens, fstop)
tpl('two', (0.1, -2.0, 1.48), (0.05, 0.0, 1.22), 30, 6.0)
tpl('nils', tuple(H_T + Vector((-0.42, -0.78, 0.06))), tuple(H_N + Vector((0, 0, -0.12))), 48)
tpl('theo', tuple(H_N + Vector((0.42, -0.72, 0.04))), tuple(H_T + Vector((0, 0, -0.12))), 46)
tpl('wall', (-0.8, 0.6, 1.55), (PX, -0.15, 1.6), 32, 2.8)
tpl('clock', tuple(CLOCK + Vector((-0.12, -0.7, -0.05))), tuple(CLOCK), 45, 2.8)
tpl('baro', tuple(BARO + Vector((0.12, -0.7, -0.05))), tuple(BARO), 45, 2.8)
lines = {l['i']: l for l in TL['lines']}
def ts(i): return lines[i]['start']
def word_t(i, word):
    for w in lines[i]['words']:
        if w['w'].strip('.,?!').lower().startswith(word.lower()): return lines[i]['start'] + w['s']
    return lines[i]['start']
# (start, template, move); moves: ('creep', frac) | ('punch', time, lens_factor) | ('rack', near_m)
cuts = [(0.0, 'two', ('creep', 0.06)), (ts(2) - 0.05, 'nils', ('punch', word_t(2, 'weather') - 0.1, 1.45)),
        (ts(3) - 0.05, 'theo', ('creep', 0.05)), (ts(4) - 0.05, 'nils', ('creep', 0.05)), (ts(5) - 0.05, 'theo', ('creep', 0.06)),
        (ts(6) - 0.05, 'nils', ('punch', word_t(6, 'wrong') - 0.05, 1.8)), (ts(7) + 1.4, 'clock', ('rack', 0.25)),
        (ts(7) + 2.9, 'baro', ('rack', 0.25)), (ts(7) + 4.6, 'nils', ('creep', 0.08)), (ts(8) - 0.05, 'wall', ('creep', 0.12)),
        (ts(8) + 1.0, 'theo', ('punch', word_t(8, 'these') - 0.1, 1.35)), (ts(9) - 0.05, 'nils', ('punch', word_t(9, 'one') - 0.1, 1.5))]
def ease_out(u):
    u = min(1.0, max(0.0, u)); return 1 - (1 - u) ** 3
cams = {}
for k, (t0, name, mv) in enumerate(cuts):
    t1 = cuts[k + 1][0] if k + 1 < len(cuts) else TL['total']
    loc, tgt, lens, fs = TPL[name]
    c = kit.camera(f'cut{k:02d}_{name}', tuple(loc), tuple(tgt), lens=lens, fstop=fs, focus=(tgt - loc).length)
    cams[f'cut{k}'] = c; cams.setdefault(name, c)
    f0, f1 = F(t0) + 1, F(t1) + 1
    if mv[0] == 'creep':
        d = (tgt - loc) * mv[1]
        for f in range(f0, f1 + 1, 2):
            u = (f - f0) / max(1, f1 - f0); c.location = loc + d * (u * u * (3 - 2 * u)); c.keyframe_insert('location', frame=f)
    elif mv[0] == 'punch':
        fp = F(mv[1]) + 1
        for f in range(f0, f1 + 1):
            u = (f - fp) / 7.0                                  # ~0.3 s push, ease-out, then a slow drift
            z = 1.0 if f < fp else 1.0 + (mv[2] - 1.0) * ease_out(u) + 0.0015 * max(0, f - fp - 7)
            c.data.lens = lens * z; c.data.keyframe_insert('lens', frame=f)
    elif mv[0] == 'rack':
        dist = (tgt - loc).length
        for f in range(f0, f1 + 1):
            u = (f - f0) / 10.0
            c.data.dof.focus_distance = mv[1] + (dist - mv[1]) * ease_out(u); c.data.keyframe_insert('dof.focus_distance', frame=f)
            c.location = loc + (tgt - loc) * 0.06 * min(1.0, (f - f0) / max(1, f1 - f0)); c.keyframe_insert('location', frame=f)
    m = sc.timeline_markers.new(name, frame=f0); m.camera = c
sc.camera = cams['cut0']

# ----------------------------------------------------------------------------------------------- acting
import anim_skit
anim_skit.OVER = 0.6
from anim_skit import Chan
def ease_soft(u):
    u = min(1.0, max(0.0, u)); c1 = 0.6; c3 = c1 + 1
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2
anim_skit.ease_back = ease_soft                                     # smaller overshoot than the dock test
rig = {'nils': nils, 'theo': theo}; other = {'nils': 'theo', 'theo': 'nils'}
CH = {w: {b: {a: Chan(0.0) for a in 'pyr'} for b in ('neck', 'chest', 'spine', 'shoulder.L', 'shoulder.R')} for w in rig}
NOD = {w: [] for w in rig}                                          # (frame, amplitude) accents
def pose(who, f, d, T=5):
    for b, axes in d.items():
        for a, v in axes.items(): CH[who][b][a].key(f, v, T)
def F(t): return int(round(t * FPS))

pose('nils', 0, {'neck': {'p': 6, 'y': 0}, 'chest': {'p': 3}}); pose('theo', 0, {'neck': {'p': 2}, 'chest': {'p': 4}})
speaking = []
for L in TL['lines']:
    who = L['who']; t0 = L['start']
    ws = [dict(w=w['w'], s=w['s'] + t0, e=w['e'] + t0) for w in L['words']]
    speaking.append((who, t0, t0 + L['dur'], ws))
    # phrases: split at punctuation; one attitude per phrase (a turn and a tilt that it keeps)
    phrase = []; phrases = []
    for w in ws:
        phrase.append(w)
        if w['w'][-1:] in ',.?!': phrases.append(phrase); phrase = []
    if phrase: phrases.append(phrase)
    side = R.choice((-1, 1))
    for k, ph in enumerate(phrases):
        side = -side
        q = ph[-1]['w'].endswith('?') or L['text'].strip().endswith('?') and k == len(phrases) - 1
        amp = 1.25 if who == 'theo' else 1.0
        pose(who, F(ph[0]['s']) - 3, {'neck': {'y': side * R.uniform(3, 6) * amp, 'r': side * R.uniform(2.5, 5) * amp,
                                               'p': (-5 if q else R.uniform(0, 4)) * amp},
                                      'chest': {'y': side * 2.0 * amp}}, T=6)
        for i, w in enumerate(ph):                                   # nods on stressed words (long words, phrase heads)
            core = w['w'].strip('.,?!-')
            if len(core) >= 5 or i == 0:
                NOD[who].append((F(w['s']) - 2, (5.5 if len(core) >= 7 else 4.0) * amp))
    fe = F(t0 + L['dur'])
    pose(who, fe + 2, {'neck': {'y': 0, 'r': 0, 'p': 3}, 'chest': {'y': 0}}, T=8)
    NOD[other[who]].append((fe - 3, 4.5))                              # the listener acknowledges
# listeners: rare, small re-poses
for who in rig:
    t = 1.0
    while t < TL['total']:
        if not any(s - 0.2 <= t <= e + 0.2 for (w, s, e, _) in speaking if w == who):
            pose(who, F(t), {'neck': {'y': R.uniform(-2.5, 2.5), 'r': R.uniform(-2, 2)}}, T=8)
        t += R.uniform(1.6, 2.6)
# beats from the script
pose('theo', F(ts(3)), {'shoulder.L': {'r': -9}, 'shoulder.R': {'r': 9}, 'neck': {'r': 7}}, T=5)            # unsure shrug
pose('theo', F(ts(3) + 1.0), {'shoulder.L': {'r': 0}, 'shoulder.R': {'r': 0}}, T=7)
pose('theo', F(ts(5)), {'neck': {'p': -4, 'r': -5}, 'chest': {'p': -3}}, T=5)                                 # proud
pose('nils', F(ts(6)), {'neck': {'p': 9, 'r': 0, 'y': 0}, 'chest': {'p': 5}}, T=5)                            # 'wrong answer'
pose('nils', F(ts(6) + 1.1), {'neck': {'p': 3}, 'chest': {'p': 2}}, T=8)
pose('nils', F(ts(7) + 0.2), {'spine': {'p': 6}}, T=8); pose('nils', F(ts(8) - 0.2), {'spine': {'p': 0}}, T=8)
pose('theo', F(ts(8)), {'neck': {'y': -25, 'p': -3}, 'chest': {'y': -8}}, T=6)                                # looks at the lure wall
pose('theo', F(ts(8) + 1.4), {'neck': {'y': 0, 'p': 2}, 'chest': {'y': 0}}, T=7)
pose('nils', F(ts(9) + 1.15), {'neck': {'y': -6, 'p': -2}, 'chest': {'y': -3}}, T=7)                            # to camera for the CTA

GAZE = {'nils': [(0, 'other'), (ts(7) + 1.3, 'clock'), (ts(7) + 4.5, 'other'), (ts(9) + 1.1, 'cam')],
        'theo': [(0, 'other'), (ts(8) - 0.1, 'wall'), (ts(8) + 1.3, 'other')]}
def gaze(who, t):
    g = [x for (tt, x) in GAZE[who] if tt <= t][-1]
    return {'other': H_T if who == 'nils' else H_N, 'clock': (CLOCK + BARO) / 2, 'wall': Vector((PX, -0.1, 1.55)),
            'cam': cams['cut11'].location}[g]
BLINK = {w: [] for w in rig}
for who in rig:
    t = R.uniform(0.6, 1.5)
    while t < TL['total']:
        BLINK[who].append(F(t)); t += R.uniform(2.2, 4.2)
VIS = {who: lipsync.visemes([w for (wh, s, e, ws) in speaking if wh == who for w in ws], N, FPS) for who in rig}

def nod(who, f):
    v = 0.0
    for (f0, a) in NOD[who]:
        d = f - f0
        if 0 <= d < 12: v += a * (math.sin(math.pi * min(1, d / 3.0) / 2) if d < 3 else math.exp(-(d - 3) / 3.0))
    return v

P_ = {'nils': 'nils_', 'theo': 'theo_'}
eyes = {'nils': ['eye_L', 'eye_R'], 'theo': ['theo_eye_L', 'theo_eye_R']}
lids = {'nils': ['lid_L', 'lid_R'], 'theo': ['theo_lid_L', 'theo_lid_R']}
e0 = {w: [bpy.data.objects[n].rotation_euler.copy() for n in eyes[w]] for w in rig}
l0 = {w: [bpy.data.objects[n].rotation_euler.copy() for n in lids[w]] for w in rig}
for f in range(1, N + 1):
    t = (f - 1) / FPS
    sc.frame_set(f)
    for who, arm in rig.items():
        c = CH[who]; br = math.sin(t * 2 * math.pi / 4.0 + (0 if who == 'nils' else 1.7))
        nk = {a: c['neck'][a].at(f) for a in 'pyr'}; lag = {a: c['neck'][a].at(f - 3) for a in 'pyr'}
        nd = nod(who, f)
        set_bone(arm, 'neck', nk['p'] + nd + 0.4 * math.sin(t * 0.8), nk['y'] + 0.6 * math.sin(t * 0.37 + 1), nk['r'])
        set_bone(arm, 'chest', c['chest']['p'].at(f) + 0.3 * lag['p'] + 0.25 * nd + 0.7 * br, c['chest']['y'].at(f) + 0.3 * lag['y'],
                 0.3 * lag['r'])
        set_bone(arm, 'spine', c['spine']['p'].at(f) + 0.3 * br, 0, 0)
        set_bone(arm, 'shoulder.L', 0, 0, c['shoulder.L']['r'].at(f) - 0.8 * br)
        set_bone(arm, 'shoulder.R', 0, 0, c['shoulder.R']['r'].at(f) + 0.8 * br)
        v = VIS[who][f - 1]; vis = v['vis']; jaw = v['jaw'] * (0.55 if who == 'nils' else 0.65)
        set_bone(arm, 'jaw', 13 * jaw, 0, 0)
        for b in ('neck', 'chest', 'spine', 'shoulder.L', 'shoulder.R', 'jaw'):
            arm.pose.bones[b].keyframe_insert('rotation_quaternion', frame=f)
        hd = bpy.data.objects[P_[who] + 'head'].data.shape_keys.key_blocks
        hd['jaw_open'].value = jaw; hd['wide'].value = vis.get('EE', 0) * 0.8; hd['round'].value = vis.get('OO', 0)
        for k in ('jaw_open', 'wide', 'round'): hd[k].keyframe_insert('value', frame=f)
        mo = bpy.data.objects[P_[who] + 'mouth']
        mo.scale = (1.0 + 0.2 * vis.get('EE', 0) - 0.25 * vis.get('OO', 0), 1.0, 0.05 + 1.6 * jaw); mo.keyframe_insert('scale', frame=f)
        for lipn in ('lip_upper', 'lip_lower'):
            lo = bpy.data.objects[P_[who] + lipn]
            lo.scale = (1.0 + 0.12 * vis.get('EE', 0) - 0.18 * vis.get('OO', 0), 1.0, 1.0); lo.keyframe_insert('scale', frame=f)
        bpy.context.view_layer.update()
        hp = arm.matrix_world @ arm.pose.bones['neck'].tail
        yy, pp = look_angles(arm, hp, gaze(who, t))
        ey = max(-30, min(30, yy - nk['y'] - c['chest']['y'].at(f))); ep = max(-20, min(22, pp - nk['p'] - nd - c['chest']['p'].at(f)))
        for n, r0 in zip(eyes[who], e0[who]):
            o = bpy.data.objects[n]; o.rotation_euler = (r0.x + math.radians(ep), r0.y, r0.z + math.radians(ey)); o.keyframe_insert('rotation_euler', frame=f)
        bl = 40 if any(0 <= f - b < 3 for b in BLINK[who]) else 0
        for n, r0 in zip(lids[who], l0[who]):
            o = bpy.data.objects[n]; o.rotation_euler = (r0.x + math.radians(bl + 0.3 * max(0, ep)), r0.y, r0.z); o.keyframe_insert('rotation_euler', frame=f)
    # the clock's minute hand creeps (time is half the topic)
    hands['minute'].rotation_euler = (0, math.radians(6 * t), 0); hands['minute'].keyframe_insert('rotation_euler', frame=f)

if arg('--frames'):                                                 # a short clip for the improvement cycles
    a_, b_ = (int(x) for x in arg('--frames').split(','))
    sc.frame_start, sc.frame_end = a_, b_
fdir = os.path.join(OUT, 'frames'); os.makedirs(fdir, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'shed.blend'))
if arg('--still'):
    for s_f in arg('--still').split(','):
        sc.frame_set(int(s_f)); sc.render.filepath = os.path.join(OUT, f'still_{s_f}.png'); bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = os.path.join(fdir, 'f'); bpy.ops.render.render(animation=True)
print('SHED', N, 'frames')
