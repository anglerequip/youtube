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

# ----------------------------------------------------------------------------------------------- cycle 9: big actions
# (Caesar: "he may slide over in a chair, camera gets close up, he opens a big box, big smooth hand movements")
ACT = '--actions' in argv
BOXP = Vector((0.1, -0.08, 0.0))
if ACT:
    kit.box('act_crate', (0.5, 0.4, 0.62), (BOXP.x, BOXP.y, 0.31), mat=M['bench'], bev=0.012)
    BIG = kit.painted('bigbox', ['#1f4a30', '#2a5e3c', '#357248'], rough=0.7, scale=5.0, cavity=0.5)
    kit.box('act_box', (0.56, 0.34, 0.2), (BOXP.x, BOXP.y, 0.72), mat=BIG, bev=0.015, segs=2)
    kit.box('act_tray', (0.52, 0.3, 0.012), (BOXP.x, BOXP.y, 0.815), mat=M['tray'], bev=0.003)
    for i in range(7):
        for j in range(2):
            kit.box('act_div', (0.004, 0.13, 0.03), (BOXP.x - 0.24 + i * 0.08, BOXP.y - 0.07 + j * 0.14, 0.83), mat=M['tray'], bev=0)
            body_ = kit.lathe('act_lure', [(0, 0), (0.011, 0.01), (0.015, 0.035), (0.01, 0.065), (0, 0.08)], seg=14,
                              loc=(BOXP.x - 0.21 + i * 0.08, BOXP.y - 0.07 + j * 0.14 + 0.02, 0.828), rot=(math.radians(90), 0, math.radians(90)),
                              mat=LURES[(i * 2 + j) % len(LURES)], angle=20)
    hinge = bpy.data.objects.new('act_hinge', None); kit.link(hinge)
    hinge.location = (BOXP.x, BOXP.y + 0.17, 0.82)                  # hinge on Nils's side, the lid lifts toward him
    lid = kit.box('act_lid', (0.57, 0.35, 0.05), (0, -0.175, 0.025), mat=BIG, bev=0.015, segs=2); lid.parent = hinge
    handle = kit.box('act_handle', (0.16, 0.03, 0.03), (0, -0.36, 0.03), mat=M['steel'], bev=0.008); handle.parent = hinge
    # Theo's rolling stool, carried by his rig
    STOOL = kit.painted('stool', ['#2a2a2e', '#38383e', '#46464e'], rough=0.6, scale=8.0)
    seat = kit.cyl('stool_seat', 0.2, 0.06, (0, 0.06, 0.98), seg=24, mat=kit.painted('seatpad', ['#7a2a20', '#8e3428', '#a03e30'], rough=0.75, scale=10.0), bev=0.02)
    post = kit.cyl('stool_post', 0.025, 0.45, (0, 0.06, 0.73), seg=12, mat=STOOL, bev=0.004)
    parts_ = [seat, post]
    for k in range(5):
        a_ = k * 2 * math.pi / 5
        leg = kit.box('stool_leg', (0.3, 0.035, 0.03), (0.15 * math.cos(a_), 0.06 + 0.15 * math.sin(a_), 0.46), (0, 0, a_), mat=STOOL, bev=0.006)
        wh = kit.cyl('stool_wheel', 0.03, 0.025, (0.29 * math.cos(a_), 0.06 + 0.29 * math.sin(a_), 0.41), (math.radians(90), 0, a_), seg=12, mat=STOOL, bev=0.004)
        parts_ += [leg, wh]
    for o_ in parts_:
        mw_ = o_.matrix_world.copy(); o_.parent = theo; o_.matrix_world = theo.matrix_world @ mw_
    bpy.context.view_layer.update()

# ----------------------------------------------------------------------------------------------- cameras + cuts
TL = json.load(open(arg('--timeline'))); N = int(math.ceil(TL['total'] * FPS))
sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, N
# Camera language from One Bold Chemist (v1/v5/v6/v8 overviews): every shot creeps slowly (dolly in a few %),
# punchlines get a fast push-in (zoom over ~0.3 s, ease-out, then hold), inserts pull focus onto the prop.
def F(t): return int(round(t * FPS))
TPL = {}
def tpl(name, loc, tgt, lens, fstop=3.5):
    TPL[name] = (Vector(loc), Vector(tgt), lens, fstop)
tpl('two', (0.1, -2.0, 1.48), (0.05, 0.0, 1.22), 30, 8.0)
tpl('nils', tuple(H_N + Vector((-0.78, -1.15, -0.02))), tuple(H_N + Vector((0, 0, -0.18))), 45, 4.0)
tpl('theo', tuple(H_T + Vector((1.05, -0.55, -0.05))), tuple(H_T + Vector((0, 0, -0.2))), 50, 4.0)
tpl('wall', (-0.8, 0.6, 1.55), (PX, -0.15, 1.6), 32, 2.8)
tpl('wide', (-0.2, -1.75, 1.35), (0.05, 0.0, 1.3), 35, 5.6)
tpl('boxcam', tuple(BOXP + Vector((0.18, -0.78, 1.32))), tuple(BOXP + Vector((0.0, 0.08, 0.84))), 30, 3.2)
tpl('hero', tuple(H_N + Vector((-0.6, -0.95, -0.12))), tuple(H_N + Vector((0, 0, -0.2))), 40, 4.0)   # eye level now
tpl('ecu', tuple(H_N + Vector((-0.75, -1.1, 0.0))), tuple(H_N + Vector((0, 0, -0.02))), 85, 3.5)
tpl('clock', tuple(CLOCK + Vector((-0.12, -0.7, -0.05))), tuple(CLOCK), 45, 2.8)
tpl('baro', tuple(BARO + Vector((0.12, -0.7, -0.05))), tuple(BARO), 45, 2.8)
lines = {l['i']: l for l in TL['lines']}
def ts(i): return lines[i]['start']
def word_t(i, word):
    for w in lines[i]['words']:
        if w['w'].strip('.,?!').lower().startswith(word.lower()): return lines[i]['start'] + w['s']
    return lines[i]['start']
# (start, template, move); moves: ('creep', frac) | ('punch', time, lens_factor) | ('rack', near_m)
cuts = [(0.0, 'two', ('creep', 0.06)), (ts(2) - 0.05, 'nils', ('punch', word_t(2, 'weather') - 0.1, 1.3)),
        (ts(3) - 0.05, 'theo', ('creep', 0.05)), (ts(4) - 0.05, 'nils', ('creep', 0.05)), (ts(5) - 0.05, 'theo', ('creep', 0.06)),
        (ts(6) - 0.05, 'nils', ('punch', word_t(6, 'wrong') - 0.05, 1.2)), (ts(7) - 0.05, 'wide', ('creep', 0.05)), (ts(7) + 1.4, 'clock', ('rack', 0.25)),
        (ts(7) + 2.9, 'baro', ('rack', 0.25)),
        *(((ts(7) + 4.6, 'two', ('creep', 0.06)), (ts(7) + 5.75, 'boxcam', ('creep', 0.3)), (ts(7) + 7.6, 'nils', ('creep', 0.06)))
          if ACT else ((ts(7) + 4.6, 'hero', ('creep', 0.06)), (ts(7) + 6.6, 'nils', ('creep', 0.06)))),
        (ts(8) - 0.05, 'wall', ('creep', 0.12)),
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
def ease_inout(u):
    u = min(1.0, max(0.0, u)); return u * u * u * (u * (u * 6 - 15) + 10)       # smootherstep: no snap, no overshoot
anim_skit.ease_back = ease_inout
rig = {'nils': nils, 'theo': theo}; other = {'nils': 'theo', 'theo': 'nils'}
CH = {w: {b: {a: Chan(0.0) for a in 'pyr'} for b in ('neck', 'chest', 'spine', 'shoulder.L', 'shoulder.R') + ('upper_arm.L', 'upper_arm.R', 'forearm.L', 'forearm.R', 'hand.L', 'hand.R')} for w in rig}
NOD = {w: [] for w in rig}
BEAT = {w: [] for w in rig}                                       # arm beats on stressed words                                          # (frame, amplitude) accents
def pose(who, f, d, T=5):
    T = max(int(T * 1.3), 7)                                          # cycle 8: ~0.3 s, smooth (no overshoot)
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
                NOD[who].append((F(w['s']) - 3, (4.2 if len(core) >= 7 else 3.0) * amp))
                BEAT[who].append(F(w['s']) - 2)
    fe = F(t0 + L['dur'])
    pose(who, fe + 2, {'neck': {'y': 0, 'r': 0, 'p': 3}, 'chest': {'y': 0}}, T=8)
    NOD[other[who]].append((fe - 4, 2.5))                              # the listener acknowledges
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

# ------------------------------------------------------------------ gestures (jointed arms, 27 Nov). Armature axes,
# measured on the rig: forward raise = -pitch on upper_arm, outward = -roll (L) / +roll (R), elbow bend = -pitch on forearm.
def G(side, up_p=0, up_out=0, fo_p=0, ha_p=-18, ha_y=0):          # 20-deg wrist bend by default
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

# the beats of the script, per line (speaker's free arm; Nils gestures with his right, Theo with both or his left)
gesture('theo', ts(1) + 0.1, 'shrug', hold=1.4)
gesture('nils', ts(2) + 0.6, 'explain', 'R', hold=1.6)
gesture('theo', ts(3) + 0.05, 'shrug', hold=1.1)
gesture('nils', ts(4) + 0.1, 'beat', 'R', hold=1.4)
gesture('theo', ts(5) + 0.1, 'chin', 'L', hold=1.2)
gesture('nils', ts(6) + 0.05, 'point', 'R', T=4, hold=1.0)
gesture('nils', ts(7) + 0.3, 'explain', 'R', hold=None)
gesture('nils', ts(7) + 1.3, 'point', 'R', T=5)            # the clock
gesture('nils', ts(7) + 3.0, 'point', 'R', T=5)            # the barometer
gesture('nils', ts(7) + 4.6, 'explain', 'R', T=6)
gesture('nils', ts(7) + 7.0, 'beat', 'R', T=5, hold=2.0)
gesture('theo', ts(8) + 0.1, 'point', 'L', T=5, hold=1.3)   # the lure wall
gesture('nils', ts(9) + 0.05, 'one', 'R', T=5, hold=1.6)    # "You need one."

if ACT:
    T0 = word_t(7, 'then')
    # Theo: seated on the stool for the whole scene, then rolls over to look into the box
    th0 = theo.location.copy()
    theo.location = (-1.0, -0.62, -0.38); theo.rotation_euler = (0, 0, math.radians(62))
    theo.keyframe_insert('location', frame=1); theo.keyframe_insert('rotation_euler', frame=1)
    for f_, loc_, yaw_ in ((F(T0 + 0.1), (-1.0, -0.62, -0.38), 62), (F(T0 + 1.0), (-0.5, -0.3, -0.38), 80),
                           (F(T0 + 1.25), (-0.53, -0.31, -0.38), 76)):
        theo.location = loc_; theo.rotation_euler = (0, 0, math.radians(yaw_))
        theo.keyframe_insert('location', frame=f_); theo.keyframe_insert('rotation_euler', frame=f_)
    for b_, pv in (('thigh.L', -84), ('thigh.R', -84), ('shin.L', 86), ('shin.R', 86)):
        set_bone(theo, b_, pv, 0, 0); theo.pose.bones[b_].keyframe_insert('rotation_quaternion', frame=1)
    pose('theo', F(T0 + 0.9), {'spine': {'p': 14}, 'chest': {'p': 8}}, T=8)
    pose('theo', F(ts(8) - 0.2), {'spine': {'p': 2}, 'chest': {'p': 2}}, T=8)
    # Nils: lean in and reach with both hands, lift the lid in one big smooth move, then present with open arms
    reach = {**G('L', -52, 4, -38, -25), **G('R', -52, 4, -38, -25)}
    lift = {**G('L', -88, 2, -62, -10), **G('R', -88, 2, -62, -10)}
    present = {**G('L', -25, 26, -68, 0, 35), **G('R', -25, 26, -68, 0, 35)}
    pose('nils', F(T0 - 0.1), {'spine': {'p': 16}, 'chest': {'p': 10}, 'neck': {'p': 14}, **reach}, T=8)
    pose('nils', F(T0 + 0.95), {'spine': {'p': 10}, 'chest': {'p': 4}, 'neck': {'p': 6}, **lift}, T=11)
    pose('nils', F(word_t(7, 'one') + 0.1), {'spine': {'p': 2}, 'chest': {'p': 0}, 'neck': {'p': 2}, **present}, T=9)
    pose('nils', F(ts(8) - 0.3), {**G('L'), **G('R')}, T=10)
    hinge = bpy.data.objects['act_hinge']
    for f_, ang in ((1, 0), (F(T0 + 0.9), 0), (F(T0 + 2.0), -108), (F(T0 + 2.2), -104)):
        hinge.rotation_euler = (math.radians(ang), 0, 0); hinge.keyframe_insert('rotation_euler', frame=f_)
    H_T = Vector((-0.52, -0.3, 1.22))                                 # Theo's head while seated (gaze/cameras)

GAZE = {'nils': [(0, 'other'), (ts(7) + 1.3, 'clock'), (ts(7) + 4.5, 'other'), (ts(9) + 1.1, 'cam')],
        'theo': [(0, 'other'), (ts(8) - 0.1, 'wall'), (ts(8) + 1.3, 'other')]}
if ACT:
    GAZE = {'nils': [(0, 'other'), (ts(7) + 1.3, 'clock'), (ts(7) + 4.5, 'other'), (ts(7) + 5.3, 'box'), (ts(7) + 7.5, 'other'), (ts(9) + 1.1, 'cam')],
            'theo': [(0, 'other'), (ts(7) + 5.8, 'box'), (ts(8) - 0.1, 'wall'), (ts(8) + 1.3, 'other')]}
def gaze(who, t):
    g = [x for (tt, x) in GAZE[who] if tt <= t][-1]
    return {'other': H_T if who == 'nils' else H_N, 'clock': (CLOCK + BARO) / 2, 'wall': Vector((PX, -0.1, 1.55)),
            'cam': cams['cut%d' % (len(cuts) - 1)].location, 'box': BOXP + Vector((0, 0, 0.85))}[g]
BLINK = {w: [] for w in rig}
for who in rig:
    t = R.uniform(0.6, 1.5)
    while t < TL['total']:
        BLINK[who].append(F(t)); t += R.uniform(2.2, 4.2)
VIS = {who: lipsync.visemes([w for (wh, s, e, ws) in speaking if wh == who for w in ws], N, FPS) for who in rig}

def nod(who, f):
    v = 0.0
    for (f0, a) in NOD[who]:                                         # a soft, symmetric nod over ~0.6 s
        d = (f - f0) / 10.0
        if 0 <= d < 1: v += a * math.sin(math.pi * d) ** 2
    return v

P_ = {'nils': 'nils_', 'theo': 'theo_'}
eyes = {'nils': ['eye_L', 'eye_R'], 'theo': ['theo_eye_L', 'theo_eye_R']}
lids = {'nils': ['lid_L', 'lid_R'], 'theo': ['theo_lid_L', 'theo_lid_R']}
e0 = {w: [bpy.data.objects[n].rotation_euler.copy() for n in eyes[w]] for w in rig}
l0 = {w: [bpy.data.objects[n].rotation_euler.copy() for n in lids[w]] for w in rig}
# ------------------------------------------------------------------ cycle 10: motion capture under everything
MOCAP = '--mocap' in argv
if MOCAP:
    import retarget
    SRC = retarget.Source(r'D:\CounterPhysical\assets-cc0\anim\UAL1_Standard.glb')
    MOFS = {'nils': 0.0, 'theo': 1.7}
    T0A = word_t(7, 'then') if ACT else None
    def mocap_state(who, t):
        talking_ = any(s_ - 0.15 <= t <= e_ + 0.3 for (w_, s_, e_, _) in speaking if w_ == who)
        if who == 'nils' and ACT and T0A - 0.3 <= t <= T0A + 2.6:
            return ('PickUp_Table', t - (T0A - 0.3))
        if who == 'theo' and ACT:
            return ('Sitting_Talking_Loop' if talking_ else 'Sitting_Idle_Loop', t + MOFS[who])
        return ('Idle_Talking_Loop' if talking_ else 'Idle_Loop', t + MOFS[who])
    def mocap_pose(who, t):
        """Blend over 0.4 s into each new state so changes never pop."""
        a, ta = mocap_state(who, t)
        b, tb = mocap_state(who, t - 0.4)
        A_ = retarget.solve(SRC, SRC.sample(a, ta, 30), rig[who])
        if b == a: return A_
        B_ = retarget.solve(SRC, SRC.sample(b, tb, 30), rig[who])
        w_ = 0.0
        for k in range(1, 9):                                         # time since the switch, in 0.05 s steps
            if mocap_state(who, t - 0.05 * k)[0] != a: w_ = 1 - (k - 1) / 8.0; break
        u = 1.0 - w_
        u = u * u * (3 - 2 * u)
        return retarget.blend(B_, A_, u)
    MP = {w_: {} for w_ in rig}
    _fa, _fb = (int(x) for x in arg('--frames', '1,%d' % N).split(','))
    for f_ in range(_fa, _fb + 1):                                    # pre-pass: sampling moves the scene frame
        for w_ in rig: MP[w_][f_] = mocap_pose(w_, (f_ - 1) / FPS)

for f in range(1, N + 1):
    t = (f - 1) / FPS
    sc.frame_set(f)
    for who, arm in rig.items():
        c = CH[who]; br = math.sin(t * 2 * math.pi / 4.0 + (0 if who == 'nils' else 1.7))
        nk = {a: c['neck'][a].at(f) for a in 'pyr'}; lag = {a: c['neck'][a].at(f - 3) for a in 'pyr'}
        nd = nod(who, f)
        talking = any(s_ - 0.1 <= t <= e_ + 0.2 for (w_, s_, e_, _) in speaking if w_ == who)
        A = 1.6 if talking else 1.0                                   # cycle 8: always alive, livelier while talking
        ph = 0.0 if who == 'nils' else 2.1
        def osc(a1, f1, a2, f2, k):
            return A * (a1 * math.sin(t * f1 + ph + k) + a2 * math.sin(t * f2 + 1.7 * ph + 2 * k))
        set_bone(arm, 'neck', nk['p'] + nd + osc(1.6, 1.1, 0.8, 2.3, 0), nk['y'] + osc(2.2, 0.7, 1.0, 1.9, 1), nk['r'] + osc(1.4, 0.9, 0.7, 2.1, 2))
        set_bone(arm, 'hips', 0, osc(2.0, 0.55, 0.8, 1.3, 3), osc(1.2, 0.7, 0.5, 1.6, 4))
        set_bone(arm, 'chest', c['chest']['p'].at(f) + 0.3 * lag['p'] + 0.25 * nd + 0.7 * br, c['chest']['y'].at(f) + 0.3 * lag['y'],
                 0.3 * lag['r'])
        set_bone(arm, 'spine', c['spine']['p'].at(f) + 0.3 * br + osc(1.2, 0.8, 0.5, 1.7, 5), osc(1.5, 0.6, 0.6, 1.5, 6), osc(1.0, 0.75, 0.4, 1.8, 7))
        set_bone(arm, 'shoulder.L', 0, 0, c['shoulder.L']['r'].at(f) - 0.8 * br)
        set_bone(arm, 'shoulder.R', 0, 0, c['shoulder.R']['r'].at(f) + 0.8 * br)
        for b in ('upper_arm.L', 'upper_arm.R', 'forearm.L', 'forearm.R', 'hand.L', 'hand.R'):
            side_k = 0 if b.endswith('L') else 1.4
            sway = (2.5 * math.sin(t * 0.9 + side_k + ph) + 1.0 * math.sin(t * 2.1 + side_k)) if b.startswith('upper') else 0.0
            if b.startswith('forearm'): sway = 2.0 * math.sin(t * 1.2 + side_k + ph)
            beat = 0.0
            if talking and not b.startswith('hand'):
                for f0 in BEAT[who]:
                    dd = (f - f0) / 10.0
                    if 0 <= dd < 1: beat += math.sin(math.pi * dd) ** 2
                beat *= (-11 if b.startswith('forearm') else -4) * (1.0 if b.endswith('R' if who == 'nils' else 'L') else 0.45)
            set_bone(arm, b, c[b]['p'].at(f) + sway + beat, c[b]['y'].at(f), c[b]['r'].at(f))
        v = VIS[who][f - 1]; vis = v['vis']
        jaw = sum(VIS[who][max(0, min(N - 1, f - 1 + k))]['jaw'] * wk for k, wk in ((-2, 0.15), (-1, 0.2), (0, 0.3), (1, 0.2), (2, 0.15)))
        jaw = max(0.0, jaw - 0.08) * (0.55 if who == 'nils' else 0.65)
        set_bone(arm, 'jaw', 13 * jaw, 0, 0)
        if MOCAP:
            mp = MP[who].get(f) or mocap_pose(who, t)
            for b_, q_ in mp.items():
                pb_ = arm.pose.bones[b_]; pb_.rotation_mode = 'QUATERNION'
                if b_ == 'neck':
                    pb_.rotation_quaternion = q_ @ pb_.rotation_quaternion      # our gaze turns and nods ride on top
                elif b_ in ('chest', 'spine'):
                    pb_.rotation_quaternion = q_ @ pb_.rotation_quaternion.slerp(Quaternion(), 0.6)
                else:
                    pb_.rotation_quaternion = q_
                pb_.keyframe_insert('rotation_quaternion', frame=f)
        for b in ('neck', 'chest', 'spine', 'hips', 'shoulder.L', 'shoulder.R', 'jaw') + ('upper_arm.L', 'upper_arm.R', 'forearm.L', 'forearm.R', 'hand.L', 'hand.R'):
            arm.pose.bones[b].keyframe_insert('rotation_quaternion', frame=f)
        hd = bpy.data.objects[P_[who] + 'head'].data.shape_keys.key_blocks
        hd['jaw_open'].value = jaw; hd['wide'].value = vis.get('EE', 0) * 0.8; hd['round'].value = vis.get('OO', 0)
        for k in ('jaw_open', 'wide', 'round'): hd[k].keyframe_insert('value', frame=f)
        mo = bpy.data.objects[P_[who] + 'mouth']
        mo.scale = (1.0 + 0.2 * vis.get('EE', 0) - 0.25 * vis.get('OO', 0), 1.0, max(0.0, 1.6 * jaw - 0.02)); mo.keyframe_insert('scale', frame=f)
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
