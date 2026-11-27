"""GENERATED from shed.py (set) + v3_shed_blocks.py (v3 characters). Edit those, not this file.

The fishing shed: Nils and Theo pick lures by reading the weather and the time (Caesar, 27 Nov).

  blender -b -P tools/blender/omega/shed.py -- --nils <nils_rig.blend> --theo <theo_rig.blend> --timeline <timeline.json>
        --out <dir> [--pct 50] [--samples 32] [--still F]

Set: a small timber shed among trees, warm and friendly (Caesar: the dusk dock read as 'weird, kinda scary'):
vertical pine boards, a window full of green daylight, a workbench with tackle boxes, a pegboard of lures, a rod rack,
a wall clock and a brass barometer (the two things the script is about), a hanging lamp.
Acting (Caesar: 'weird body movements'): one head attitude per phrase, a nod on stressed words, small overshoot,
quiet listeners, no hip sway; see act() below."""
import json, math, os, random, sys
import bpy, bmesh
from mathutils import Vector, Euler, Quaternion, Matrix

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
try: sc.view_settings.look = 'AgX - Punchy'
except Exception: pass
sc.view_settings.exposure = -0.35
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
# cycle 3: textured game-style surfaces (CC0 ambientCG sets) on whole wall slabs instead of procedural boards
TEXW = kit.tex_material('tex_walls', 'Planks003_1K-JPG', scale=0.55, rough_add=0.3, normal=0.25, flat='#9a6a40', detail=0.8)
TEXF = kit.tex_material('tex_floor', 'Planks005_1K-JPG', scale=0.6, rough_add=0.3, normal=0.3, flat='#6a4a32', detail=0.9)
TEXB = kit.tex_material('tex_bench', 'Wood005_1K-JPG', scale=0.8, rough_add=0.25, normal=0.3, tint='#c08a5a')
TEXD = kit.tex_material('tex_beam', 'Wood013_1K-JPG', scale=0.8, rough_add=0.25, normal=0.3)
M['bench'] = TEXB; M['beam'] = TEXD
WX0, WX1, WZ0, WZ1 = -0.57, 0.57, 0.97, 1.96                     # window opening in the back wall
for (sx, sz, x, z) in (((W1 - W0), WZ0, 0, WZ0 / 2), ((W1 - W0), HGT - WZ1, 0, (WZ1 + HGT) / 2),
                       (WX0 - W0, WZ1 - WZ0, (W0 + WX0) / 2, (WZ0 + WZ1) / 2), (W1 - WX1, WZ1 - WZ0, (W1 + WX1) / 2, (WZ0 + WZ1) / 2)):
    kit.box('backwall', (sx, 0.04, sz), (x, D1, z), mat=TEXW, bev=0.003)
for side in (-1, 1):
    kit.box('sidewall', (0.04, D1 - D0, HGT), (side * W1, (D0 + D1) / 2, HGT / 2), mat=TEXW, bev=0.003)
kit.box('floor', (W1 - W0, D1 - D0, 0.04), (0, (D0 + D1) / 2, -0.02), mat=TEXF, bev=0.003)
for x in (W0 + 0.02, W1 - 0.02):                                   # corner posts
    kit.box('post', (0.09, 0.09, HGT), (x, D1 - 0.03, HGT / 2), mat=TEXD, bev=0.008)
for y in (D0 + 0.3, -0.3, 0.7):                                 # ceiling beams + ceiling
    kit.box('beam', (W1 - W0, 0.12, 0.14), (0, y, HGT - 0.07), mat=M['beam'], bev=0.01)
kit.box('ceil', (W1 - W0, D1 - D0, 0.03), (0, (D0 + D1) / 2, HGT + 0.015), mat=TEXW, bev=0)
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
kit.cyl('cord', 0.004, 0.2, (0.2, -0.2, HGT - 0.1), seg=6, mat=M['ink'], bev=0)
kit.lathe('shade', [(0.0, 0.0), (0.16, 0.0), (0.1, 0.09), (0.025, 0.13), (0.0, 0.13)], seg=32, loc=(0.2, -0.2, HGT - 0.33), mat=M['box_g'], angle=25)
kit.lathe('bulbm', [(0, 0), (0.035, 0.02), (0.03, 0.05), (0, 0.06)], seg=16, loc=(0.2, -0.2, HGT - 0.35), mat=M['bulb'], angle=60)
kit.point('lamp', (0.2, -0.2, HGT - 0.38), color='#ffc98a', power=90, radius=0.05)
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=12, y_segments=12, size=0.4)
net = kit.from_bm('net', bm, M['net'], smooth_angle=None); net.location = (W1 - 0.04, 0.55, 1.6); net.rotation_euler = (0, math.radians(90), 0)
wf = net.modifiers.new('wire', 'WIREFRAME'); wf.thickness = 0.004
for i, x in enumerate((-1.25, -1.1)):
    kit.box('boot', (0.11, 0.26, 0.05), (x, D0 + 0.4, 0.025), mat=M['rubber'], bev=0.015)
    kit.box('bootleg', (0.11, 0.12, 0.38), (x, D0 + 0.47, 0.22), mat=M['rubber'], bev=0.02)

# ----------------------------------------------------------------------------------------------- cycle 2: busier set
# shelves either side of the window with jars, cans and spools; string lights on the beam; a lake-map poster; floats
JAR = [kit.painted(f'jar{i}', c, rough=0.7, scale=10.0, cavity=0.3) for i, c in enumerate(
    (['#7a4a20', '#9a6230', '#b07a40'], ['#2a5a7a', '#36709a', '#4a86b0'], ['#8a2a20', '#a83a2a', '#c04a36'],
     ['#d0b060', '#e0c070', '#f0d488'], ['#3a6a3a', '#4a824a', '#5a9a5a']))]
for sx in (-1, 1):
    for lvl, z in enumerate((1.25, 1.62)):
        kit.box('shelf_b', (0.62, 0.22, 0.03), (sx * 1.02, D1 - 0.12, z), mat=M['bench'], bev=0.006)
        for k in range(5):
            x = sx * 1.02 - 0.24 + k * 0.12 + R.uniform(-0.02, 0.02)
            h = R.uniform(0.08, 0.16); r = R.uniform(0.03, 0.045)
            kit.cyl('jar', r, h, (x, D1 - 0.12 + R.uniform(-0.03, 0.03), z + 0.015 + h / 2), seg=16, mat=JAR[(k + lvl + sx) % 5], bev=0.006)
            kit.cyl('lidj', r * 1.05, 0.015, (x, D1 - 0.12, z + 0.02 + h), seg=16, mat=M['steel'], bev=0.003)
BULB_W = kit.flat('bulb_w', '#ffd28a', emit='#ffcf80', emit_strength=18.0)
for k in range(15):                                                 # string lights along the front beam (bokeh points)
    x = W0 + 0.2 + k * 0.2; z = HGT - 0.2 - 0.05 * math.sin(k * 0.9)
    kit.cyl('wire', 0.002, 0.2, (x, -0.3, z + 0.02), (0, math.radians(90), 0), seg=6, mat=M['ink'], bev=0)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.018)
    b = kit.from_bm('sbulb', bm, BULB_W, smooth_angle=89); b.location = (x, -0.3, z - 0.01)
for k in range(4):
    kit.point('string', (W0 + 0.5 + k * 0.75, -0.3, HGT - 0.25), color='#ffc77a', power=6, radius=0.02)
POST = bpy.data.materials.new('lakemap'); POST.use_nodes = True; pn = POST.node_tree; pb = pn.nodes['Principled BSDF']
tc = pn.nodes.new('ShaderNodeTexCoord'); wv = pn.nodes.new('ShaderNodeTexNoise')          # a depth chart: banded noise
wv.inputs['Scale'].default_value = 3.0; wv.inputs['Detail'].default_value = 3.0
pn.links.new(tc.outputs['Object'], wv.inputs['Vector'])
rp = pn.nodes.new('ShaderNodeValToRGB'); cr = rp.color_ramp; cr.interpolation = 'CONSTANT'
cr.elements[0].position, cr.elements[0].color = 0.0, hexc('#16466e'); cr.elements[1].position, cr.elements[1].color = 0.62, hexc('#6f9a4a')
for pos, col in ((0.36, '#245f8c'), (0.45, '#3f80ac'), (0.53, '#7fb4d2'), (0.58, '#d8cfa8')):
    e = cr.elements.new(pos); e.color = hexc(col)
pn.links.new(wv.outputs['Fac'], rp.inputs['Fac']); pn.links.new(rp.outputs['Color'], pb.inputs['Base Color']); pb.inputs['Roughness'].default_value = 0.85
kit.box('poster_frame', (0.02, 0.62, 0.46), (W1 - 0.04, 0.55, 1.62), mat=M['dial'], bev=0.004)
kit.box('poster', (0.01, 0.56, 0.4), (W1 - 0.055, 0.55, 1.62), mat=POST, bev=0)
FL_R = kit.painted('fl_red', ['#9a1e16', '#b8281c', '#cc3a26'], rough=0.7, scale=20.0)
FL_W = kit.painted('fl_wht', ['#d6ccb0', '#e6dcc2', '#f0e8d4'], rough=0.7, scale=20.0)
for k in range(5):                                                  # floats hanging on strings from the back beam
    x = -1.3 + k * 0.18; z = HGT - 0.45 - 0.08 * (k % 2)
    kit.cyl('fstr', 0.0012, 0.3, (x, 0.7, z + 0.17), seg=6, mat=M['ink'], bev=0)
    kit.lathe('fl_top', [(0, 0.0), (0.03, 0.0), (0.024, 0.03), (0, 0.045)], seg=16, loc=(x, 0.7, z), mat=FL_R, angle=20)
    kit.lathe('fl_bot', [(0, -0.045), (0.024, -0.03), (0.03, 0.0), (0, 0.0)], seg=16, loc=(x, 0.7, z), mat=FL_W, angle=20)

# cycle 5: a foreground layer (refs: something near the lens in most shots) and more gear on the floor
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=14, y_segments=10, size=0.35)
fgn = kit.from_bm('fg_net', bm, M['net'], smooth_angle=None); fgn.location = (-0.95, -1.35, 2.05); fgn.rotation_euler = (math.radians(80), 0, math.radians(20))
fgn.modifiers.new('wire', 'WIREFRAME').thickness = 0.005
for k in range(3):
    xx = -1.15 + k * 0.14
    kit.lathe('fg_ft', [(0, 0.0), (0.035, 0.0), (0.028, 0.035), (0, 0.05)], seg=16, loc=(xx, -1.2, 1.62 - 0.05 * k), mat=FL_R, angle=20)
    kit.lathe('fg_fb', [(0, -0.05), (0.028, -0.035), (0.035, 0.0), (0, 0.0)], seg=16, loc=(xx, -1.2, 1.62 - 0.05 * k), mat=FL_W, angle=20)
COOL = kit.painted('cooler', ['#2a5a8a', '#336a9e', '#3d7ab0'], rough=0.7, scale=6.0)
kit.box('cooler', (0.45, 0.3, 0.32), (1.15, -0.9, 0.16), mat=COOL, bev=0.02, segs=2)
kit.box('cooler_lid', (0.47, 0.32, 0.05), (1.15, -0.9, 0.34), mat=M['dial'], bev=0.015)
kit.box('crate', (0.4, 0.3, 0.28), (-1.25, 0.4, 0.14), mat=M['bench'], bev=0.01)
for k in range(3):
    kit.cyl('rope_c', 0.12 - k * 0.02, 0.03, (-1.25, 0.4, 0.3 + k * 0.03), seg=20, mat=kit.painted('rope_s', ['#8a7650', '#a08a60', '#b49c70'], rough=0.9, scale=20.0), bev=0.008)

# ----------------------------------------------------------------------------------------------- light: bright, warm, friendly
w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = hexc('#4f8a98'); bg.inputs['Strength'].default_value = 0.22
s_ = kit.sun('sun', (58, 0, 205), color='#ffd8a8', strength=4.5, angle=1.0)      # sun through the window
kit.area('window_fill', (0, D1 - 0.15, 1.5), (0, -0.5, 1.2), color='#9fcfff', power=70, size=1.1, shape='SQUARE')
kit.area('room_fill', (0.0, D0 + 0.3, 2.2), (0, 0.2, 1.2), color='#ffe2c0', power=18, size=2.0)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.2, 1.2)); hz = bpy.context.active_object; hz.scale = (3.1, 2.7, 2.35)
hm = bpy.data.materials.new('dust'); hm.use_nodes = True; hnt = hm.node_tree; hnt.nodes.remove(hnt.nodes['Principled BSDF'])
vv = hnt.nodes.new('ShaderNodeVolumePrincipled'); vv.inputs['Density'].default_value = 0.01; vv.inputs['Color'].default_value = hexc('#fff3e0')
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
theo.location = (-0.45, -0.35, 0); theo.rotation_euler = (0, 0, math.radians(72))
bpy.context.view_layer.update()
H_N = nils.matrix_world @ Vector((0, -0.03, 1.56)); H_T = theo.matrix_world @ Vector((0, -0.03, 1.56))

kit.area('char_key', (-0.9, -1.3, 2.2), tuple((H_N + H_T) / 2), color='#ffcf9a', power=190, size=0.4)
kit.area('char_rim', (0.9, 1.05, 2.1), tuple(H_N), color='#7fc4e0', power=620, size=0.5)
kit.area('char_rim2', (-1.3, 0.9, 2.0), tuple(H_T), color='#7fc4e0', power=560, size=0.5)


def dress_characters():
    """Cycle 2 audit: our clothes read as flat-colour papercraft; the references wear textured game clothing. Swap the
    region materials on both characters for CC0 cloth/knit/rubber/leather textures, tinted to the model sheet."""
    SW = {  # material name -> (texture set, tiles per metre, flat colour, texture detail 0..1, bump)
        'nils_shirt': ('Fabric023_1K-JPG', 2.0, '#3c4c60', 0.5, 0.08), 'nils_bib': ('Fabric028_1K-JPG', 1.5, '#6e6a30', 0.6, 0.08),
        'nils_cap': ('Fabric016_1K-JPG', 5.0, '#c9531c', 0.5, 0.3), 'nils_boot': ('Rubber004_1K-JPG', 2.0, '#3a3532', 0.4, 0.05),
        'nils_leather': ('Leather001_1K-JPG', 4.0, '#5a3820', 0.5, 0.08), 'nils_knit': ('Fabric016_1K-JPG', 5.0, '#6a4a32', 0.6, 0.1),
        'theo_shirt': ('Fabric035_1K-JPG', 2.0, '#f2c230', 0.15, 0.05), 'theo_bib': ('Fabric035_1K-JPG', 2.0, '#f2c230', 0.15, 0.05),
        'theo_jeans': ('Fabric022_1K-JPG', 2.0, '#3a5a80', 0.6, 0.08), 'theo_cap': ('Fabric017_1K-JPG', 5.0, '#3fa7a0', 0.7, 0.15),
        'theo_boot': ('Rubber004_1K-JPG', 2.0, '#2f6a40', 0.3, 0.05), 'theo_knit': ('Fabric022_1K-JPG', 4.0, '#2b3a4a', 0.5, 0.08),
    }
    made = {}
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        for slot in o.material_slots:
            m = slot.material
            if not m or m.name not in SW: continue
            if m.name not in made:
                t, sc_, flat, det, bump = SW[m.name]
                made[m.name] = kit.tex_material('tex_' + m.name, t, scale=sc_, flat=flat, detail=det, rough_add=0.35, normal=bump)
            slot.material = made[m.name]
    print('DRESSED', sorted(made))


dress_characters()


def sheet_painted_skin(mix=0.6):
    """Cycle 8: paint Nils's skin with the model sheet's own painted colour (projected onto the head as the 'paint'
    attribute when the mesh was generated): warm nose and cheeks, cooler jaw, painted creases, instead of one flat tone."""
    for name in ('nils_skin', 'nils_nose'):
        m = bpy.data.materials.get(name)
        if not m: continue
        nt = m.node_tree; b = nt.nodes['Principled BSDF']; bc = b.inputs['Base Color']
        if not bc.links: continue
        src = bc.links[0].from_socket
        at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'paint'
        hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 1.25; hs.inputs['Value'].default_value = 1.0
        nt.links.new(at.outputs['Color'], hs.inputs['Color'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['Factor'].default_value = mix
        nt.links.new(src, mx.inputs['A']); nt.links.new(hs.outputs['Color'], mx.inputs['B']); nt.links.new(mx.outputs['Result'], bc)


sheet_painted_skin(0.5)


SHEET_HEAD_IMG = 'D:/CounterPhysical/lake-committee/assets/characters/nils_brack/v002/source/nils_head_rgba.png'


def sheet_face():
    """Cycle 11 (drastic): texture Nils's whole head with the model sheet's own painted image, through the 'sheet' UV
    map kept from the image-to-3D projection: his approved face, brows, sideburns and knit cap, exactly as painted."""
    head = bpy.data.objects.get('nils_head')
    if not head or 'sheet' not in head.data.uv_layers: return False
    m = bpy.data.materials.new('sheetface'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'sheet'
    im = nt.nodes.new('ShaderNodeTexImage')
    im.image = bpy.data.images.load(kit.asset(SHEET_HEAD_IMG), check_existing=True)
    im.extension = 'EXTEND'
    mp_ = nt.nodes.new('ShaderNodeMapping')                         # align painted features to the 3D ones (nose tip)
    mp_.inputs['Location'].default_value = (float(arg('--uvdx', '0')), float(arg('--uvdy', '0')), 0)
    s_ = float(arg('--uvs', '1')); mp_.inputs['Scale'].default_value = (s_, s_, 1.0)
    nt.links.new(uv.outputs['UV'], mp_.inputs['Vector']); nt.links.new(mp_.outputs['Vector'], im.inputs['Vector'])
    # where the projection falls outside the painted figure (cap top, back of the head), fall back to painted colour
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 1.585
    nt.links.new(sep.outputs['Z'], gt.inputs[0])
    fb = nt.nodes.new('ShaderNodeMix'); fb.data_type = 'RGBA'
    fb.inputs['A'].default_value = kit.hexc('#b98468'); fb.inputs['B'].default_value = kit.hexc('#c9531c')
    nt.links.new(gt.outputs[0], fb.inputs['Factor'])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    geo = nt.nodes.new('ShaderNodeNewGeometry'); vt = nt.nodes.new('ShaderNodeVectorTransform')
    vt.vector_type = 'NORMAL'; vt.convert_from = 'WORLD'; vt.convert_to = 'OBJECT'; nt.links.new(geo.outputs['Normal'], vt.inputs['Vector'])
    sn = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(vt.outputs['Vector'], sn.inputs['Vector'])
    fr = nt.nodes.new('ShaderNodeMapRange'); fr.inputs['From Min'].default_value = -0.15; fr.inputs['From Max'].default_value = -0.55
    nt.links.new(sn.outputs['Y'], fr.inputs['Value'])                     # facing -Y (the painted view) -> 1, side-on -> 0
    am = nt.nodes.new('ShaderNodeMath'); am.operation = 'MULTIPLY'; nt.links.new(im.outputs['Alpha'], am.inputs[0]); nt.links.new(fr.outputs['Result'], am.inputs[1])
    nt.links.new(am.outputs[0], mx.inputs['Factor']); nt.links.new(fb.outputs['Result'], mx.inputs['A']); nt.links.new(im.outputs['Color'], mx.inputs['B'])
    nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.72
    try: b.inputs['Specular IOR Level'].default_value = 0.25
    except Exception: pass
    for i in range(len(head.data.materials)): head.data.materials[i] = m
    for n in ('eye_L', 'eye_R', 'lid_L', 'lid_R', 'brow_L', 'brow_R', 'sideburn_L', 'sideburn_R'):
        o = bpy.data.objects.get(n)
        if o:
            o.hide_render = True
            for c in o.children_recursive: c.hide_render = True
    return True


SHEETFACE = '--sheetface' in argv and sheet_face()


def sheet_body():
    """Cycle 12 (drastic): the body's clothes carry the model sheet's painted image too (folds, stains, stitching,
    buckles as painted), through the body's own 'sheet' UV map (projection from the full-body cut-out)."""
    body = bpy.data.objects.get('nils_tsg')
    if not body or 'sheet' not in body.data.uv_layers: return False
    m = bpy.data.materials.new('sheetbody'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'sheet'
    im = nt.nodes.new('ShaderNodeTexImage'); im.extension = 'EXTEND'
    im.image = bpy.data.images.load(kit.asset(SHEET_HEAD_IMG.replace('nils_head_rgba', 'nils_input_rgba')), check_existing=True)
    nt.links.new(uv.outputs['UV'], im.inputs['Vector'])
    old_bc = None
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['A'].default_value = kit.hexc('#3c4c60')
    nt.links.new(im.outputs['Alpha'], mx.inputs['Factor']); nt.links.new(im.outputs['Color'], mx.inputs['B'])
    nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.8
    try: b.inputs['Specular IOR Level'].default_value = 0.2
    except Exception: pass
    for i, mm in enumerate(body.data.materials):
        if mm and any(k in mm.name for k in ('shirt', 'bib', 'boot', 'knit', 'strap', 'brass')):
            body.data.materials[i] = m
    return True


SHEETBODY = '--sheetbody' in argv and sheet_body()


def matte_and_paint():
    """Cycle 1 audit: no glossy surfaces (refs: matte painted game textures; highlights only on metal/glass), and a
    painted detail layer at the scale a phone shows, on every material."""
    keep = ('tex_', 'skin', 'nose', 'lips', 'eye', 'iris', 'pupil', 'glass', 'lens', 'bulb', 'flame', 'sun_disc', 'drop', 'water', 'mouth_in', 'teeth')
    for m in bpy.data.materials:
        if not m.use_nodes or any(k in m.name for k in keep): continue
        nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
        if not b: continue
        metal = b.inputs['Metallic'].default_value > 0.5
        try: b.inputs['Specular IOR Level'].default_value = 0.35 if metal else 0.18
        except Exception: pass
        rin = b.inputs['Roughness']
        if rin.links:
            src = rin.links[0].from_node
            if src.type == 'MAP_RANGE':
                src.inputs['To Min'].default_value = max(src.inputs['To Min'].default_value, 0.45 if metal else 0.68)
                src.inputs['To Max'].default_value = max(src.inputs['To Max'].default_value, 0.55 if metal else 0.82)
        else:
            rin.default_value = max(rin.default_value, 0.45 if metal else 0.7)
        if 'Coat Weight' in b.inputs: b.inputs['Coat Weight'].default_value = 0.0
        bc = b.inputs['Base Color']
        if bc.links:
            fs = bc.links[0].from_socket
            tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise')
            nz.inputs['Scale'].default_value = 55.0; nz.inputs['Detail'].default_value = 5.0; nz.inputs['Roughness'].default_value = 0.6
            nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
            mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.8; mr.inputs['To Max'].default_value = 1.12
            nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
            mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
            nt.links.new(fs, mx.inputs['A']); nt.links.new(mr.outputs['Result'], mx.inputs['B'])
            nt.links.new(mx.outputs['Result'], bc)


matte_and_paint()
try: sc.eevee.use_raytracing = False                                     # no screen-space reflections
except Exception: pass

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
