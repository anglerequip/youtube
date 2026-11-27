"""OMEGA Milestone 3: static calibration renders on the Lake Committee dock set.

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/blender/omega/calib_m3.py -- --shot prop --out <dir>
  then: venv python tools/blender/omega/post.py <dir>/<shot>_raw.png

Shots: prop (hero insert: bell, wet ticket, float), wide (the set), portrait/desk (need Nils, added when he exists).
Everything is built here from scratch. Dimensions in metres; the dock deck top is z = 0.
"""
import math, os, random, sys
import bpy, bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
from kit import hexc

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default
SHOT = arg('--shot', 'prop')
OUT = arg('--out', r'D:\CounterPhysical\research\omega\m3')
PCT = int(arg('--pct', '50'))
SAMPLES = int(arg('--samples', '96'))
os.makedirs(OUT, exist_ok=True)

sc = kit.reset(); kit.eevee_quality(sc, SAMPLES); kit.output(sc, pct=PCT)
R = random.Random(7)

# ----------------------------------------------------------------------------------------------------- materials
M = dict(
    plank=kit.painted('plank', ['#3a2617', '#5c3d24', '#7a5433'], rough=0.72, scale=0.8, stripes=(9.0, 0.5)),
    plank_wet=kit.painted('plank_wet', ['#2a1d14', '#43301f', '#5a4128'], rough=0.35, scale=0.8, stripes=(9.0, 0.45)),
    desk=kit.painted('desk', ['#3a2216', '#5a3420', '#77492b'], rough=0.42, scale=1.2, stripes=(12.0, 0.4), grain_axis='X'),
    desk_y=kit.painted('desk_y', ['#3a2216', '#5a3420', '#77492b'], rough=0.42, scale=1.2, stripes=(12.0, 0.4)),
    post=kit.painted('post', ['#2b211a', '#46372a', '#5c4a38'], rough=0.8, scale=1.0, stripes=(7.0, 0.5)),
    felt=kit.painted('felt', ['#5e1414', '#7a1d1a', '#8f2a22'], rough=0.9, scale=3.0, cavity=0.3),
    paper=kit.painted('paper', ['#d9d0bb', '#e8e1cf', '#efe9da'], rough=0.8, scale=4.0, cavity=0.25),
    paper_wet=kit.painted('paper_wet', ['#b9ab8c', '#cfc3a6', '#ddd3ba'], rough=0.28, scale=5.0, cavity=0.3),
    ink=kit.flat('ink', '#1d1a1a', rough=0.6),
    ink_red=kit.flat('ink_red', '#9a1f1b', rough=0.6),
    brass=kit.painted('brass', ['#6a4a17', '#a5782c', '#d8ac52'], rough=0.2, metal=1.0, scale=3.0, cavity=0.7, rough_var=0.05),
    steel=kit.painted('steel', ['#3c3f42', '#5f6367', '#8a8e91'], rough=0.3, metal=1.0, scale=3.0, cavity=0.6),
    float_red=kit.painted('float_red', ['#8f1612', '#b8231a', '#cf3a25'], rough=0.22, scale=6.0, cavity=0.4, coat=0.0),
    float_ivory=kit.painted('float_ivory', ['#cbbd98', '#e2d6b5', '#efe6cb'], rough=0.25, scale=6.0, cavity=0.4),
    cork=kit.painted('cork', ['#7a5a36', '#9b7848', '#b48f5c'], rough=0.85, scale=9.0),
    rope=kit.painted('rope', ['#6f5f45', '#8f7c5a', '#a8946d'], rough=0.9, scale=8.0),
    glass=kit.flat('glass', '#d8e4e0', rough=0.05, transmission=1.0, ior=1.45),
    flame=kit.flat('flame', '#ffb347', emit='#ffb347', emit_strength=40.0),
    drop=kit.flat('drop', '#cfe0e0', rough=0.02, transmission=1.0, ior=1.33),
    water=kit.water(),
    reed=kit.painted('reed', ['#2c3517', '#3e4a1d', '#56602a'], rough=0.7, scale=2.0, cavity=0.2),
    tree2=kit.painted('tree2', ['#1d2a17', '#28361d', '#334224'], rough=0.9, scale=0.3, cavity=0.0),
    bank=kit.painted('bank', ['#1b2016', '#252b1c', '#2f3522'], rough=0.95, scale=0.1, cavity=0.0),
    cattail=kit.painted('cattail', ['#3a2414', '#4f321c', '#603e22'], rough=0.9, scale=20.0),
    tree=kit.painted('tree', ['#18241a', '#22301f', '#2d3c25'], rough=0.9, scale=0.2, cavity=0.0),
    hill=kit.painted('hill', ['#2a3428', '#34402f', '#3d4a35'], rough=0.95, scale=0.05, cavity=0.0),
)

# ----------------------------------------------------------------------------------------------------- dock
def dock():
    L_, W_ = 4.2, 2.6                                     # dock length (into the lake, +Y) and width (X)
    n = 14; pw = W_ / n
    for i in range(n):
        x = -W_ / 2 + pw * (i + 0.5)
        segs = [(0.0, L_)] if i % 3 else [(0.0, 1.7 + R.uniform(-.2, .2)), (None, None)]
        y0, y1 = 0.0, L_
        cut = 1.4 + R.uniform(-0.4, 0.6) if i % 2 else 2.6 + R.uniform(-0.4, 0.4)
        for (a, b) in ((y0, cut - 0.006), (cut + 0.006, y1)):
            ln = b - a
            o = kit.box(f'plank_{i}_{a:.1f}', (pw - 0.012, ln, 0.05),
                        (x, -1.6 + a + ln / 2, -0.025 + R.uniform(-0.004, 0.004)),
                        (R.uniform(-.006, .006), R.uniform(-.004, .004), R.uniform(-.004, .004)),
                        M['plank'], bev=0.008, segs=2, jitter=0.002, seed=i * 13 + int(a * 10))
            # nail heads at the joists
            for jy in (0.3, 1.5, 2.7, 3.9):
                yy = jy + 0.0
                if a < yy < b:
                    for dx in (-pw * 0.28, pw * 0.28):
                        kit.cyl('nail', 0.006, 0.004, (x + dx, -1.6 + yy, 0.001), mat=M['steel'], seg=8, bev=0)
    # joists and the fascia beam on the water side
    for jy in (0.3, 1.5, 2.7, 3.9):
        kit.box('joist', (W_ + 0.1, 0.09, 0.12), (0, -1.6 + jy, -0.11), mat=M['post'], bev=0.01)
    for sx in (-1, 1):
        kit.box('stringer', (0.08, L_ + 0.1, 0.16), (sx * (W_ / 2 + 0.02), -1.6 + L_ / 2, -0.12), mat=M['post'], bev=0.01)
    # posts with rope wraps
    for (px, py) in ((-W_ / 2 - 0.06, 2.5), (W_ / 2 + 0.06, 2.5), (-W_ / 2 - 0.06, -1.5), (W_ / 2 + 0.06, -1.5)):
        h = 1.25 + R.uniform(-0.1, 0.1)
        kit.cyl('post', 0.075, h, (px, py, h / 2 - 0.75), seg=10, mat=M['post'], bev=0.01, r2=0.068)
        kit.cyl('post_cap', 0.08, 0.03, (px, py, h - 0.75 + 0.01), seg=10, mat=M['post'], bev=0.008)
        for k in range(5):
            t = bpy.data.meshes.new('rope')
            bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=0.086, radius2=0.086, depth=0.022)
            o = kit.from_bm('rope', bm, M['rope'])
            o.location = (px, py, 0.18 + k * 0.024); o.rotation_euler = (R.uniform(-.06, .06), R.uniform(-.06, .06), 0)
            sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.014
    # water
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.55))
    w = bpy.context.active_object; w.name = 'lake'; w.data.materials.append(M['water'])


def reeds(center, count=40, spread=0.6, h=(0.6, 1.3), seed=1):
    """Clumps of curved, tapered blades (bent by a few segments) plus a few cattail heads."""
    r = random.Random(seed)
    for i in range(count):
        a = r.uniform(0, 6.283); d = r.uniform(0, spread) ** 0.7 * spread ** 0.3
        x, y = center[0] + math.cos(a) * d, center[1] + math.sin(a) * d
        hh = r.uniform(*h); lean = r.uniform(0.05, 0.35); yaw = r.uniform(0, 6.283); w = r.uniform(0.008, 0.016)
        bm = bmesh.new(); prev = None; n = 6
        for k in range(n + 1):
            t = k / n
            c = Vector((lean * t * t * hh * math.cos(yaw), lean * t * t * hh * math.sin(yaw), t * hh))
            side = Vector((-math.sin(yaw), math.cos(yaw), 0)) * w * (1 - t) ** 0.8
            ring = (bm.verts.new(c - side), bm.verts.new(c + side))
            if prev:
                bm.faces.new((prev[0], prev[1], ring[1], ring[0]))
            prev = ring
        o = kit.from_bm('reed', bm, M['reed'], smooth_angle=60)
        sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.003
        o.location = (x, y, -0.58)
        if r.random() < 0.12:
            top = c
            ct = kit.cyl('cattail', 0.014, 0.11, (x + top.x, y + top.y, -0.58 + top.z + 0.03), seg=10, mat=M['cattail'], bev=0.004)


def conifer(x, y, z, s, r):
    """Stacked, jittered faceted tiers on a trunk: reads as a hand-carved miniature fir, not a cone primitive."""
    kit.cyl('trunk', s * 0.035, s * 0.3, (x, y, z + s * 0.15), seg=6, mat=M['post'], bev=0)
    tiers = r.randint(3, 4)
    for k in range(tiers):
        t = k / tiers
        rad = s * (0.3 - 0.2 * t) * r.uniform(0.9, 1.1); hh = s * 0.42 * (1 - 0.3 * t)
        zz = z + s * 0.18 + s * 0.62 * t
        bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=r.choice((7, 8, 9)), radius1=rad, radius2=0.0, depth=hh)
        for v in bm.verts:
            if v.co.z < 0:
                v.co += Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-0.6, 0.4))) * rad * 0.12
        o = kit.from_bm('tier', bm, M['tree'], smooth_angle=None)
        o.location = (x + r.uniform(-.02, .02) * s, y, zz + hh / 2); o.rotation_euler = (0, 0, r.uniform(0, 6.28))


def broadleaf(x, y, z, s, r):
    kit.cyl('trunk', s * 0.04, s * 0.45, (x, y, z + s * 0.22), seg=6, mat=M['post'], bev=0)
    for k in range(r.randint(3, 5)):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=s * r.uniform(0.18, 0.26))
        o = kit.from_bm('crown', bm, M['tree2'], smooth_angle=None)
        o.location = (x + r.uniform(-.2, .2) * s, y + r.uniform(-.15, .15) * s, z + s * r.uniform(0.5, 0.78))
        o.scale = (1, 1, r.uniform(0.8, 1.05)); o.rotation_euler = (r.uniform(0, 3), r.uniform(0, 3), r.uniform(0, 3))


def far_bank():
    """A low shore strip with grouped tree silhouettes (25-60 m) and hills behind."""
    r = random.Random(3)
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=60, y_segments=10, size=1.0)
    for v in bm.verts:
        v.co.x *= 70; v.co.y = 42 + v.co.y * 18
        v.co.z = -0.55 + max(0.0, (v.co.y - 25) * 0.12) + r.uniform(0, 0.25)
    o = kit.from_bm('shore', bm, M['bank'], smooth_angle=None)
    for i in range(110):
        x = r.uniform(-55, 55); y = r.uniform(27, 58)
        z = -0.55 + max(0.0, (y - 25) * 0.12)
        s = r.uniform(5, 10)
        (conifer if r.random() < 0.75 else broadleaf)(x, y, z, s, r)
    for i in range(6):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=30)
        o = kit.from_bm('hill', bm, M['hill'], smooth_angle=None)
        o.location = (-100 + i * 40 + r.uniform(-10, 10), 110 + r.uniform(0, 30), -22 + r.uniform(0, 6)); o.scale = (1.6, 1, 0.8)


# ----------------------------------------------------------------------------------------------------- desk + props
DESK_H = 0.92; DESK = Vector((0.0, 1.25, DESK_H))   # top centre of the inspection desk


def desk():
    x0, y0, z = DESK
    for k in range(4):                                  # four boards with hairline gaps
        kit.box(f'desk_board{k}', (1.15, 0.153, 0.055), (x0, y0 - 0.2325 + k * 0.155, z - 0.0275), mat=M['desk'],
                bev=0.006, segs=2, jitter=0.0015, seed=40 + k)
    kit.box('desk_apron', (1.05, 0.54, 0.12), (x0, y0, z - 0.115), mat=M['desk'], bev=0.01)
    for sx in (-1, 1):
        for sy in (-1, 1):
            kit.box('desk_leg', (0.075, 0.075, z - 0.06), (x0 + sx * 0.49, y0 + sy * 0.25, (z - 0.06) / 2), mat=M['desk'], bev=0.01)
    kit.box('desk_rail', (1.0, 0.04, 0.05), (x0, y0 + 0.25, 0.18), mat=M['desk'], bev=0.008)
    # red felt mat
    kit.box('mat', (0.56, 0.42, 0.006), (x0 - 0.14, y0 - 0.02, z + 0.003), mat=M['felt'], bev=0.002)


def clipboard(loc, rot_z=0.0):
    o = kit.box('clip_board', (0.25, 0.34, 0.008), (loc[0], loc[1], loc[2] + 0.004), (0, 0, rot_z), M['desk'], bev=0.003)
    p = kit.box('form', (0.215, 0.285, 0.0012), (0, -0.012, 0.0046), mat=M['paper'], bev=0.0004)
    p.parent = o
    t = kit.text_mesh('heading', 'ANGLER', 0.034, (0, 0.09, 0.0056), (0, 0, 0), M['ink'])
    t.parent = o
    for k in range(5):
        ln = kit.box('line', (0.16, 0.0016, 0.0003), (0.0, 0.045 - k * 0.03, 0.0055), mat=M['ink'], bev=0); ln.parent = o
    sig = kit.box('sigbox', (0.17, 0.05, 0.0003), (0.0, -0.11, 0.0055), mat=M['ink_red'], bev=0); sig.parent = o
    inner = kit.box('siginner', (0.164, 0.044, 0.0004), (0.0, -0.11, 0.0056), mat=M['paper'], bev=0); inner.parent = o
    clip = kit.box('clip', (0.11, 0.035, 0.014), (0, 0.155, 0.011), mat=M['brass'], bev=0.004, segs=3); clip.parent = o
    return o


def bell(loc):
    """Brass desk bell bolted to a plank so narrow the bell looks excessive (brief)."""
    x, y, z = loc
    kit.box('bell_plank', (0.06, 0.32, 0.02), (x, y, z + 0.01), mat=M['plank'], bev=0.004)
    for dy in (-0.12, 0.12):
        kit.cyl('bolt', 0.008, 0.008, (x, y + dy, z + 0.022), seg=6, mat=M['steel'], bev=0.0015)
    kit.lathe('bell_base', [(0.0, 0), (0.056, 0.0), (0.058, 0.005), (0.055, 0.017), (0.036, 0.022), (0.0, 0.022)],
              seg=8, loc=(x, y, z + 0.02), mat=M['desk_y'], angle=20)
    prof = [(0.0, 0.0), (0.05, 0.0), (0.053, 0.005), (0.05, 0.014), (0.044, 0.028), (0.035, 0.04),
            (0.022, 0.048), (0.0, 0.051)]
    kit.lathe('bell_dome', prof, seg=36, loc=(x, y, z + 0.042), mat=M['brass'], angle=12)
    kit.cyl('plunger', 0.0045, 0.022, (x, y, z + 0.1), seg=12, mat=M['steel'], bev=0.001)
    kit.lathe('button', [(0.0, 0), (0.011, 0), (0.012, 0.004), (0.009, 0.008), (0.0, 0.009)], seg=24,
              loc=(x, y, z + 0.11), mat=M['brass'], angle=12)


def ticket(loc, rot_z=0.0, number='No 47'):
    """Wet numbered ticket: slightly curled card with a few water drops."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=12, y_segments=6, size=1.0)
    for v in bm.verts:
        v.co.x *= 0.05; v.co.y *= 0.028
        v.co.z = 0.6 * (v.co.x * 10) ** 2 * 0.004 + 0.0008
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.0012)
    o = kit.from_bm('ticket', bm, M['paper_wet'], smooth_angle=50)
    o.location = loc; o.rotation_euler = (0, 0, rot_z)
    t = kit.text_mesh('ticket_no', number, 0.022, (0, 0.0, 0.0028), (0, 0, 0), M['ink_red']); t.parent = o
    for k in range(5):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=R.uniform(0.002, 0.005))
        for v in bm.verts:
            v.co.z = max(v.co.z, 0) * 0.55
        d = kit.from_bm('drop', bm, M['drop'], smooth_angle=None)
        d.data.shade_smooth()
        d.location = (R.uniform(-0.04, 0.04), R.uniform(-0.02, 0.02), 0.0024); d.parent = o
    # a drop that has run off onto the desk
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.012)
    for v in bm.verts:
        v.co.z = max(v.co.z, 0) * 0.08; v.co.x *= 1.5
    d = kit.from_bm('puddle', bm, M['drop'], smooth_angle=None); d.data.shade_smooth()
    d.location = (loc[0] + 0.06, loc[1] + 0.01, loc[2] - 0.0012); d.scale = (0.7, 0.6, 1)
    return o


def float_bob(loc, rot=(0, 0, 0)):
    """Red-and-ivory egg float with a wooden peg (Nils's float, also a desk prop)."""
    prof = []
    for k in range(25):
        t = k / 24
        z = -0.035 + 0.075 * t
        r = 0.026 * math.sin(math.pi * t) ** 0.85 * (1.0 - 0.18 * t)
        prof.append((r, z))
    prof[0] = (0.0, prof[0][1]); prof[-1] = (0.0, prof[-1][1])
    lower = [p for p in prof if p[1] <= 0.004]; upper = [p for p in prof if p[1] >= 0.004]
    a = kit.lathe('float_ivory', lower + [(0.0, lower[-1][1])], seg=32, mat=M['float_ivory'], angle=14)
    b = kit.lathe('float_red', [(0.0, upper[0][1])] + upper, seg=32, mat=M['float_red'], angle=14)
    kit.lathe('float_band', [(0.0, 0.002), (0.0264, 0.002), (0.0264, 0.006), (0.0, 0.006)], seg=32, mat=M['ink'], angle=14)
    peg = kit.cyl('float_peg', 0.0035, 0.06, (0, 0, 0.06), seg=10, mat=M['cork'], bev=0.0008, r2=0.0022)
    root = bpy.data.objects.new('float', None); kit.link(root)
    for o in bpy.context.scene.objects:
        if o.name.startswith(('float_ivory', 'float_red', 'float_band', 'float_peg')) and o.parent is None and o is not root:
            o.parent = root
    root.location = loc; root.rotation_euler = rot
    return root


def lantern(loc):
    x, y, z = loc
    kit.lathe('lantern_base', [(0, 0), (0.055, 0), (0.058, 0.006), (0.05, 0.03), (0.035, 0.04), (0, 0.04)], seg=32,
              loc=(x, y, z), mat=M['brass'], angle=30)
    kit.lathe('lantern_glass', [(0.0, 0.0), (0.03, 0.0), (0.042, 0.04), (0.038, 0.09), (0.022, 0.12), (0.0, 0.12)], seg=32,
              loc=(x, y, z + 0.04), mat=M['glass'], angle=60)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        kit.cyl('lantern_bar', 0.0035, 0.13, (x + math.cos(a) * 0.046, y + math.sin(a) * 0.046, z + 0.105), seg=8, mat=M['brass'], bev=0.0008)
    kit.lathe('lantern_cap', [(0, 0), (0.05, 0), (0.035, 0.03), (0.012, 0.05), (0, 0.055)], seg=32, loc=(x, y, z + 0.165), mat=M['brass'], angle=30)
    kit.lathe('flame', [(0, 0), (0.007, 0.006), (0.006, 0.018), (0, 0.032)], seg=12, loc=(x, y, z + 0.07), mat=M['flame'], angle=80)
    kit.point('lantern_light', (x, y, z + 0.085), color='#ffaa55', power=14.0, radius=0.01)


def ruler(loc, rot_z):
    o = kit.box('ruler', (0.3, 0.032, 0.004), loc, (0, 0, rot_z), M['desk'], bev=0.0015)
    for k in range(13):
        tk = kit.box('tick', (0.0012, 0.008 if k % 2 else 0.013, 0.0003), (-0.14 + k * 0.0233, 0.009, 0.0022), mat=M['ink'], bev=0)
        tk.parent = o
    pol = kit.box('polish', (0.05, 0.026, 0.0003), (0.11, -0.001, 0.0021), mat=M['brass'], bev=0)   # thumb-polished patch
    pol.parent = o
    return o


# ----------------------------------------------------------------------------------------------------- lighting
def light_sunset():
    s_ = kit.sun('sun', (79, 0, 172), color='#ffa860', strength=5.5, angle=1.2)
    bpy.context.view_layer.update()
    d = s_.matrix_world.to_quaternion() @ Vector((0, 0, 1))          # towards the sun
    kit.sky_world(top='#0e2a45', mid='#cf6d38', horizon='#ffc27a', strength=1.4, fog_density=float(arg('--fog', '0.006')),
                  fog_color='#e3a77c', ambient=('#5f7fa3', 0.55), fog_box=((0, 52, 6), (100, 80, 16)), sun_dir=d)
    # key from front-right at about 45 degrees, warm-neutral, semi-hard
    kit.area('key', (1.6, -1.2, 2.2), (DESK.x, DESK.y, DESK.z + 0.1), color='#fff0dc', power=650, size=0.45, shape='DISK')
    # cool sky fill from the left (about 1/5 of the key)
    kit.area('fill', (-2.5, -0.5, 1.6), (DESK.x, DESK.y, DESK.z), color='#9fb8d6', power=70, size=2.5, shape='DISK')


# ----------------------------------------------------------------------------------------------------- build + shots
dock(); far_bank()
reeds((-1.9, 3.4), 110, 0.8, seed=2); reeds((2.0, 0.2), 90, 0.7, seed=5); reeds((-2.2, -0.6), 60, 0.6, seed=9)
desk()
cb = clipboard((DESK.x - 0.13, DESK.y - 0.02, DESK.z + 0.006), rot_z=math.radians(-6))
bell((DESK.x + 0.30, DESK.y + 0.02, DESK.z))
ticket((DESK.x + 0.21, DESK.y - 0.13, DESK.z + 0.002), rot_z=math.radians(-12))
float_bob((DESK.x + 0.43, DESK.y - 0.07, DESK.z + 0.025), rot=(0, math.radians(80), math.radians(-30)))
lantern((DESK.x - 0.47, DESK.y + 0.17, DESK.z))
ruler((DESK.x + 0.05, DESK.y + 0.22, DESK.z + 0.002), math.radians(3))
light_sunset()

NILS = arg('--nils', '')
if NILS:
    with bpy.data.libraries.load(NILS, link=False) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects:
        kit.link(o)
        if o.parent: continue
        o.location = (DESK.x + float(arg('--nx', '0.05')), DESK.y + 0.55, 0.0)
        o.rotation_euler = (0, 0, math.radians(float(arg('--nyaw', '0'))))

if SHOT == 'portrait':
    head = Vector((DESK.x + 0.05, DESK.y + 0.55, 1.54))
    kit.camera('cam', tuple(head + Vector((0.30, -0.95, -0.04))), tuple(head + Vector((0, 0, -0.07))), lens=55, fstop=2.8,
               focus=(Vector((0.30, -0.95, -0.04)) - Vector((0, -0.2, 0))).length)
    # portrait light: a semi-hard key at 45 degrees so the face planes separate, a warm rim from the sun side
    for n in ('key', 'fill'):
        bpy.data.objects[n].hide_render = True
    kit.area('pkey', tuple(head + Vector((0.85, -0.75, 0.55))), tuple(head), color='#fff0dc', power=95, size=0.22)
    kit.area('pfill', tuple(head + Vector((-1.2, -0.9, 0.1))), tuple(head), color='#9fb8d6', power=14, size=1.5)
    kit.area('prim', tuple(head + Vector((-0.7, 0.9, 0.35))), tuple(head), color='#ffb36b', power=90, size=0.4)
elif SHOT == 'desk':
    kit.camera('cam', (DESK.x + 0.62, DESK.y - 1.05, 1.36), (DESK.x + 0.05, DESK.y + 0.35, 1.18), lens=32, fstop=4.0)
elif SHOT == 'prop':
    # hero insert: low across the desk at the bell and the wet ticket, sun rim behind, lantern soft in the back
    tgt = (DESK.x + 0.30, DESK.y + 0.02, DESK.z + 0.10)
    kit.camera('cam', (DESK.x + 0.20, DESK.y - 0.46, DESK.z + 0.17), tgt, lens=42, fstop=3.2,
               focus=(Vector((DESK.x + 0.3, DESK.y + 0.02, DESK.z + 0.05)) - Vector((DESK.x + 0.20, DESK.y - 0.46, DESK.z + 0.17))).length)
elif SHOT == 'wide':
    kit.camera('cam', (1.9, -3.4, 1.55), (0.0, 1.4, 0.75), lens=30, fstop=8.0)
elif SHOT == 'skit':
    import anim_skit
    anim_skit.build(sc, DESK, kit, NILS, arg('--theo', ''), arg('--timeline', ''))
elif SHOT == 'anim':
    import anim_m5
    anim_m5.build(sc, DESK, kit)
else:
    raise SystemExit(f'unknown shot {SHOT}')

if SHOT in ('anim', 'skit'):
    fdir = os.path.join(OUT, 'frames'); os.makedirs(fdir, exist_ok=True)
    sc.render.filepath = os.path.join(fdir, 'f')
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'{SHOT}.blend'))
    if '--still' in argv:
        sc.frame_set(int(arg('--still', '1'))); sc.render.filepath = os.path.join(OUT, f'anim_still_{sc.frame_current}_raw.png')
        bpy.ops.render.render(write_still=True)
    else:
        bpy.ops.render.render(animation=True)
    print('WROTE', fdir)
else:
    raw = os.path.join(OUT, f'{SHOT}_raw.png')
    sc.render.filepath = raw
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'{SHOT}.blend'))
    bpy.ops.render.render(write_still=True)
    print('WROTE', raw)
