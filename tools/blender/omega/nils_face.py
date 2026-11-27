"""Nils face kit: separate, rig-ready parts placed on the TripoSG head (which resolves the masses, not the features).

  blender -b -P tools/blender/omega/nils_face.py -- --blend <nils_painted.blend> --out <nils_v002.blend>

Parts (each its own object, parented to the body, origin at its pivot, so gaze, blink, brows and mouth can be animated):
eyes (white + iris + pupil, looking at the camera), upper lids (thick, half-closed: the sheet's resting look), brows
(heavy grey sculpted blocks with an underside that shades the eyes), a long wedge nose, a level mouth with an upper-lip
overhang, sideburns. Positions are measured from the head (see the profile probe in the M3 notes) for a 1.75 m Nils.
"""
import math, os, sys
import bpy, bmesh
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit

argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
bpy.ops.wm.open_mainfile(filepath=arg('--blend'))
VARIANT = arg('--variant', 'nils')
PFX = 'theo_' if VARIANT == 'theo' else 'nils_'
body = bpy.data.objects['nils_tsg']
headob = bpy.data.objects.get('nils_head', body)
_bm = bmesh.new(); _bm.from_mesh(headob.data); _bm.transform(headob.matrix_world)
from mathutils.bvhtree import BVHTree
HB = BVHTree.FromBMesh(_bm)
def surf_y(x, z):
    h = HB.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 2.0)
    return h[0].y if h[0] else None
GENERATED_FEATURES = headob is not body      # the generated head already carries nose, brows, sideburns and lips
mats = {m.name: m for m in bpy.data.materials}
SKIN, HAIR = mats[PFX + 'skin'], mats[PFX + 'hair']
NOSE = kit.painted('nils_nose', ['#b0634a', '#c8775b', '#d88d6e'], rough=0.55, scale=6.0, cavity=0.5, cavity_dist=0.02)
WHITE = kit.flat('nils_eyewhite', '#d8d0c4', rough=0.3)
IRIS = kit.flat('nils_iris', '#5a4630', rough=0.25)
PUPIL = kit.flat('nils_pupil', '#0d0b0a', rough=0.15)
LIP = kit.painted('nils_lip', ['#7a3e30', '#8e4c3a', '#9c5843'], rough=0.5, scale=8.0, cavity=0.4)
MOUTH = kit.flat('nils_mouthline', '#2a1611', rough=0.7)

parts = []
def keep(o):
    o.parent = body; parts.append(o); return o


def sculpt_block(name, verts_fn, mat, smooth=28.0):
    """A block built from an explicit 8-corner cage then bevelled: crisp planes with a highlight line."""
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts_fn()]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True)
    o = kit.from_bm(name, bm, mat, smooth_angle=smooth)
    kit.bevel(o, 0.0025, 2, angle=30)
    return keep(o)


HAIRS = kit.painted('nils_hairlock', ['#403d3a', '#5b5753', '#77726c'], rough=0.72, scale=30.0, cavity=0.6,
                    cavity_dist=0.012, stripes=(70.0, 0.4), grain_axis='X')
HAIRS_T = kit.painted('theo_hairlock', ['#3a2414', '#53351f', '#6c472a'], rough=0.7, scale=30.0, cavity=0.5,
                      cavity_dist=0.01, stripes=(70.0, 0.4), grain_axis='X')
def surf_x(side, y, z):
    h = HB.ray_cast(Vector((side * 1.0, y, z)), Vector((-side, 0, 0)), 2.0)
    return h[0].x if h[0] else side * 0.11

def loft(name, rows, mat, smooth=35.0):
    """rows: list of 4-point cross-sections along the lock (front-top, front-bottom, back-bottom, back-top)."""
    bm = bmesh.new(); rings = [[bm.verts.new(p) for p in r] for r in rows]
    for a, b in zip(rings, rings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = kit.from_bm(name, bm, mat, smooth_angle=smooth); kit.bevel(o, 0.0018, 2, angle=30)
    return keep(o)

def loft_brow(side, lift):
    """A heavy brow lock: a rounded bar (6-point section) that stands 7-10 mm proud of the brow ridge, thick at the
    inner end, arching and flaring to a squared outer tip, so its underside shades the lid (brief: 'the brow as a mass
    with an underside')."""
    n = 8; rings = []
    bm = bmesh.new()
    for k in range(n):
        t = k / (n - 1)
        x = side * (0.008 + 0.088 * t)
        zc = 1.589 + lift + 0.014 * t + 0.006 * math.sin(math.pi * t)
        hgt = 0.031 * (1 - 0.42 * t) * (0.8 if k in (0, n - 1) else 1.0)
        ys = (surf_y(x, zc) or -0.19)
        yf = ys - 0.011 * (1 - 0.3 * t)                         # proud of the surface, most at the inner end
        sec = [(yf + 0.004, zc + hgt * 0.55), (yf, zc + hgt * 0.15), (yf + 0.001, zc - hgt * 0.35),
               (yf + 0.006, zc - hgt * 0.5), (ys + 0.012, zc - hgt * 0.35), (ys + 0.012, zc + hgt * 0.5)]
        rings.append([bm.verts.new((x, yy, zz)) for yy, zz in sec])
    m = len(rings[0])
    for a_, b_ in zip(rings, rings[1:]):
        for i in range(m):
            j = (i + 1) % m
            bm.faces.new((a_[i], a_[j], b_[j], b_[i]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = kit.from_bm(f'brow_{"L" if side > 0 else "R"}', bm, HAIRS, smooth_angle=40); kit.bevel(o, 0.0015, 2, angle=35)
    keep(o)

def theo_brow(side):
    """Thin worried brow: inner end raised, a short arch, brown."""
    n = 7; rows = []
    for k in range(n):
        t = k / (n - 1)
        x = side * (0.012 + 0.07 * t)
        zc = 1.596 - 0.008 * t + 0.004 * math.sin(math.pi * t) + 0.004 * (1 - t)
        hgt = 0.011 * (1 - 0.4 * t)
        ys = surf_y(x, zc) or -0.19
        yf = ys - 0.004
        rows.append([(x, yf, zc + hgt / 2), (x, yf + 0.002, zc - hgt / 2), (x, ys + 0.006, zc - hgt / 2), (x, ys + 0.006, zc + hgt / 2)])
    loft(f'brow_{"L" if side > 0 else "R"}', rows, HAIRS_T, smooth=40)

def sideburn(side):
    """Squared grey sideburn hugging the side of the face: a raycast surface patch lifted 3 mm, 5 mm thick."""
    rows, cols = 6, 4
    bm = bmesh.new(); grid = []
    for r in range(rows):
        z = 1.586 - 0.07 * r / (rows - 1)
        row = []
        for c in range(cols):
            y = -0.088 + 0.032 * c / (cols - 1) + 0.004 * r / (rows - 1)
            h = HB.ray_cast(Vector((side * 1.0, y, z)), Vector((-side, 0, 0)), 2.0)
            p = h[0] + h[1] * 0.003 if h[0] else Vector((side * 0.11, y, z))
            row.append(bm.verts.new(p))
        grid.append(row)
    for r in range(rows - 1):
        for c in range(cols - 1):
            f = (grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c])
            bm.faces.new(f if side > 0 else tuple(reversed(f)))
    o = kit.from_bm(f'sideburn_{"L" if side > 0 else "R"}', bm, HAIRS, smooth_angle=50)
    sol = o.modifiers.new('thick', 'SOLIDIFY'); sol.thickness = 0.005; sol.offset = -1
    kit.bevel(o, 0.0012, 1, angle=40)
    keep(o)

EYE_Z, EYE_X, EYE_R = float(arg('--eyez', '1.556')), float(arg('--eyex', '0.042')), 0.0125
for side in (-1, 1):
    sy = surf_y(side * EYE_X, EYE_Z)
    c = Vector((side * EYE_X, sy + EYE_R - 0.0035, EYE_Z))   # the front of the eye sits 3.5 mm proud of the socket
    root = bpy.data.objects.new(f'eye_{"L" if side > 0 else "R"}', None); kit.link(root); root.location = c; keep(root)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=EYE_R)
    w = kit.from_bm('eyeball', bm, WHITE, smooth_angle=89); w.parent = root
    for nm, r, m, dy in (('iris', 0.0068, IRIS, 0.0), ('pupil', 0.0032, PUPIL, 0.0004)):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r)
        for v in bm.verts:
            v.co.y = min(v.co.y, 0) * 0.25
        o = kit.from_bm(nm, bm, m, smooth_angle=89); o.parent = root
        o.location = (0, -EYE_R + 0.0012 - dy, 0)
    # upper lid: a thick shell over the top of the eye, rotated down to half-closed
    lid_root = bpy.data.objects.new(f'lid_{"L" if side > 0 else "R"}', None); kit.link(lid_root); lid_root.location = c; keep(lid_root)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=EYE_R * 1.12)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -EYE_R * 0.05], context='VERTS')
    lid = kit.from_bm('lid', bm, SKIN, smooth_angle=60)
    sol = lid.modifiers.new('thick', 'SOLIDIFY'); sol.thickness = 0.0022; sol.offset = 1
    lid.parent = lid_root
    lid_root.rotation_euler = (math.radians(float(arg('--lid', '38'))), 0, 0)      # rotate the open edge down over the eye: half-lidded
    # lower lid: a thin rim
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=EYE_R * 1.08)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > -EYE_R * 0.55], context='VERTS')
    ll = kit.from_bm('lowlid', bm, SKIN, smooth_angle=60); ll.parent = lid_root.parent if False else root
    ll.modifiers.new('thick', 'SOLIDIFY').thickness = 0.0016
    # brow: heavy grey block, inner end lower (stern), outer end flared; the brief's left brow sits a little higher
    lift = 0.004 if side > 0 else 0.0
    def brow():
        x0, x1 = side * 0.018, side * 0.074
        zi, zo = 1.585 + lift, 1.593 + lift * 1.5
        return [(x0, -0.205, zi - 0.011), (x1, -0.188, zo - 0.008), (x1, -0.188, zo + 0.012), (x0, -0.205, zi + 0.009),
                (x0, -0.178, zi - 0.006), (x1, -0.16, zo - 0.004), (x1, -0.16, zo + 0.014), (x0, -0.178, zi + 0.012)]
    if not GENERATED_FEATURES: sculpt_block(f'brow_{"L" if side > 0 else "R"}', brow, HAIR)
    elif VARIANT == 'theo': theo_brow(side)
    else: loft_brow(side, lift)
    # sideburn: squared grey block down the side of the face
    def burn():
        x = side * 0.104
        return [(x, -0.095, 1.525), (x, -0.06, 1.522), (x, -0.06, 1.6), (x, -0.1, 1.6),
                (x + side * 0.014, -0.095, 1.525), (x + side * 0.014, -0.06, 1.522), (x + side * 0.014, -0.06, 1.6),
                (x + side * 0.014, -0.1, 1.6)]
    if not GENERATED_FEATURES: sculpt_block(f'sideburn_{"L" if side > 0 else "R"}', burn, HAIR)
    elif VARIANT != 'theo': sideburn(side)

# nose: long wedge from the bridge between the brows to a blunt, downward-turned tip
def nose():
    return [(-0.011, -0.198, 1.582), (0.011, -0.198, 1.582), (0.022, -0.262, 1.53), (-0.022, -0.262, 1.53),
            (-0.017, -0.178, 1.578), (0.017, -0.178, 1.578), (0.026, -0.215, 1.516), (-0.026, -0.215, 1.516)]
if not GENERATED_FEATURES: sculpt_block('nose', nose, NOSE, smooth=24)
# the cage above is top face (0-3) and back face (4-7); fix winding by recomputing normals already done.

# mouth: level line with a slight pull at the corners, and an upper-lip overhang
bm = bmesh.new()
MZ = float(arg('--mouthz', '1.482'))
pts = [(x, surf_y(x, MZ + dz) - 0.0008, MZ + dz) for x, dz in ((-0.026, -0.0012), (-0.013, 0.0), (0.0, 0.0), (0.013, 0.0003), (0.027, 0.0014))]
prev = None
for p in pts:
    a = bm.verts.new((p[0], p[1], p[2] + 0.0012)); b = bm.verts.new((p[0], p[1], p[2] - 0.0012))
    if prev: bm.faces.new((prev[0], prev[1], b, a))
    prev = (a, b)
if not GENERATED_FEATURES:
    ml = kit.from_bm('mouth', bm, MOUTH, smooth_angle=60); keep(ml)
    ml.modifiers.new('t', 'SOLIDIFY').thickness = 0.002
def lip():
    return [(-0.024, -0.198, 1.4905), (0.024, -0.198, 1.4915), (0.02, -0.203, 1.499), (-0.02, -0.203, 1.498),
            (-0.024, -0.186, 1.4905), (0.024, -0.186, 1.4915), (0.02, -0.19, 1.5), (-0.02, -0.19, 1.499)]
if not GENERATED_FEATURES: sculpt_block('upper_lip', lip, SKIN, smooth=30)

if VARIANT == 'nils':
    # braces: modelled straps from the bib's top corners up over the shoulders and down the back, with brass buckles
    LEATHER = kit.painted('nils_leather', ['#2e1c10', '#45291a', '#5c3a24'], rough=0.42, scale=20.0, cavity=0.6, cavity_dist=0.01)
    BRASS = bpy.data.materials.get('nils_brass') or kit.painted('nils_brass2', ['#6e5422', '#a07c3a', '#c9a55c'], rough=0.22, metal=1.0)
    _bb0 = bmesh.new(); _bb0.from_mesh(body.data); _bb0.transform(body.matrix_world); BODY_BVH = BVHTree.FromBMesh(_bb0)
    def strap(side):
        """Path points (x, y, z) are seeds; each is projected onto the body along its own direction, lifted 3 mm."""
        w = 0.034
        path = []
        for k in range(6):                                     # front: bib corner up to the shoulder top
            t = k / 5; path.append(((side * (0.115 - 0.01 * t)), None, 1.235 + 0.2 * t, Vector((0, 1, 0))))
        for k in range(1, 5):                                  # over the shoulder, from front to back
            t = k / 5; path.append((side * (0.105 - 0.015 * t), -0.1 + 0.2 * t, None, Vector((0, 0, -1))))
        for k in range(5):                                     # down the back, angling to the centre
            t = k / 4; path.append((side * (0.09 - 0.05 * t), None, 1.42 - 0.2 * t, Vector((0, -1, 0))))
        bm = bmesh.new(); prev = None
        for (x, y, z, d) in path:
            if z is None:   o = Vector((x, y, 3.0))
            elif y is None: o = Vector((x, -d.y * 3.0, z))
            h = BODY_BVH.ray_cast(o, d, 6.0)
            if not h[0]: continue
            p = h[0] + h[1] * 0.004
            across = Vector((1, 0, 0))
            pair = (bm.verts.new(p - across * w / 2), bm.verts.new(p + across * w / 2))
            if prev:
                f = (prev[0], prev[1], pair[1], pair[0])
                bm.faces.new(f)
            prev = pair
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        o = kit.from_bm(f'strap_{"L" if side > 0 else "R"}', bm, LEATHER, smooth_angle=50)
        sol = o.modifiers.new('thick', 'SOLIDIFY'); sol.thickness = 0.006; sol.offset = 0
        kit.bevel(o, 0.0015, 2, angle=40); keep(o)
        # buckle at the bib corner: a squared brass frame with a bar
        hb = BODY_BVH.ray_cast(Vector((side * 0.115, -3.0, 1.262)), Vector((0, 1, 0)), 6.0)
        if hb[0]:
            bk = kit.box(f'buckle_{"L" if side > 0 else "R"}', (0.046, 0.012, 0.036), tuple(hb[0] + Vector((0, -0.008, 0))),
                         mat=BRASS, bev=0.003, segs=2)
            inner = kit.box('buckle_hole', (0.03, 0.02, 0.02), (0, 0, 0), mat=LEATHER, bev=0.002)
            bo = bk.modifiers.new('hole', 'BOOLEAN'); bo.object = inner; bo.operation = 'DIFFERENCE'
            inner.parent = bk; inner.hide_render = True; inner.hide_viewport = True
            keep(bk)
    for side in (-1, 1):
        strap(side)

    # bib top hem: a raised, bevelled band along the bib's top edge (hides the paint border, gives the panel its edge)
    OIL = bpy.data.materials.get('nils_bib')
    bm = bmesh.new(); top = []; bot = []
    for k in range(17):
        x = -0.2 + 0.4 * k / 16
        for z, lst in ((1.252, top), (1.226, bot)):
            h = BODY_BVH.ray_cast(Vector((x, -3.0, z)), Vector((0, 1, 0)), 6.0)
            lst.append(bm.verts.new(h[0] + h[1] * 0.003 if h[0] else Vector((x, -0.2, z))))
    for k in range(16):
        bm.faces.new((bot[k], bot[k + 1], top[k + 1], top[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    hem = kit.from_bm('bib_hem', bm, OIL, smooth_angle=40)
    hem.modifiers.new('thick', 'SOLIDIFY').thickness = 0.008
    kit.bevel(hem, 0.002, 2, angle=40); keep(hem)

    # the red-and-ivory float hanging from his left strap (viewer's right), a brass clip above it (brief: check it after
    # every costume change)
    _bb = bmesh.new(); _bb.from_mesh(body.data); _bb.transform(body.matrix_world); BB = BVHTree.FromBMesh(_bb)
    fx, fz = float(arg('--floatx', '0.135')), float(arg('--floatz', '1.19'))
    h = BB.ray_cast(Vector((fx, -1.0, fz)), Vector((0, 1, 0)), 2.0)
    fy = (h[0].y if h[0] else -0.2) - 0.03
    RED = kit.painted('nils_float_red', ['#8f1612', '#b8231a', '#cf3a25'], rough=0.22, scale=40.0, cavity=0.4)
    IVO = kit.painted('nils_float_ivory', ['#cbbd98', '#e2d6b5', '#efe6cb'], rough=0.25, scale=40.0, cavity=0.4)
    froot = bpy.data.objects.new('float_hang', None); kit.link(froot); froot.location = (fx, fy, fz); keep(froot)
    prof = []
    for k in range(25):
        t = k / 24; zz = -0.03 + 0.065 * t
        prof.append((0.024 * math.sin(math.pi * t) ** 0.85 * (1.0 - 0.18 * t), zz))
    prof[0] = (0.0, prof[0][1]); prof[-1] = (0.0, prof[-1][1])
    lo = [p_ for p_ in prof if p_[1] <= 0.004]; up = [p_ for p_ in prof if p_[1] >= 0.004]
    for nm, pr, m in (('float_lo', lo + [(0.0, lo[-1][1])], IVO), ('float_up', [(0.0, up[0][1])] + up, RED)):
        o = kit.lathe(nm, pr, seg=32, mat=m, angle=14); o.parent = froot
    peg = kit.cyl('float_peg', 0.003, 0.045, (0, 0, -0.05), seg=10, mat=NOSE, bev=0.0006, r2=0.002); peg.parent = froot
    clip = kit.cyl('float_clip', 0.006, 0.03, (0, 0.004, 0.048), seg=12, mat=bpy.data.materials.get('nils_brass') or IRIS, bev=0.001)
    clip.parent = froot
    froot.rotation_euler = (math.radians(6), math.radians(-8), 0)

if VARIANT == 'theo':
    _bb0 = bmesh.new(); _bb0.from_mesh(body.data); _bb0.transform(body.matrix_world); BODY_BVH = BVHTree.FromBMesh(_bb0)
    # glasses: round wire frames on a bridge, resting on the nose (the beginner reads the instructions)
    FRAME = kit.painted('theo_frame', ['#1b1b1d', '#2a2a2e', '#3a3a40'], rough=0.3, metal=0.6, scale=40.0, cavity=0.2)
    GLASS = kit.flat('theo_lens', '#e6eef0', rough=0.03, transmission=1.0, ior=1.3)
    groot = bpy.data.objects.new('glasses', None); kit.link(groot); keep(groot)
    for side in (-1, 1):
        c = Vector((side * EYE_X, surf_y(side * EYE_X, EYE_Z) - 0.016, EYE_Z + 0.001))
        bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=40, radius1=0.021, radius2=0.021, depth=0.003)
        rim = kit.from_bm('rim', bm, FRAME, smooth_angle=60); rim.location = c; rim.rotation_euler = (math.radians(90), 0, 0)
        rim.modifiers.new('t', 'SOLIDIFY').thickness = 0.0025; rim.parent = groot
        # temple arm back to the ear
        arm = kit.box('temple', (0.0025, 0.1, 0.0025), (side * (EYE_X + 0.03), c.y + 0.05, c.z + 0.002), mat=FRAME, bev=0.0008)
        arm.rotation_euler = (0, 0, math.radians(side * -6)); arm.parent = groot
    br = kit.box('bridge', (0.02, 0.003, 0.003), (0, surf_y(0.0, EYE_Z + 0.004) - 0.012, EYE_Z + 0.004), mat=FRAME, bev=0.001)
    br.parent = groot
    # brown fringe peeking out under the beanie and over the ears
    for k in range(6):
        t = k / 5; x = -0.085 + 0.17 * t
        zc = 1.60
        ys = surf_y(x, zc) or -0.18
        ln_ = 0.016 + 0.008 * ((k * 7) % 3) / 2
        rows = []
        for j in range(4):
            u = j / 3; wdt = 0.014 * (1 - 0.55 * u)
            rows.append([(x - wdt, ys - 0.006, zc - ln_ * u), (x + wdt, ys - 0.006, zc - ln_ * u),
                         (x + wdt, ys + 0.004, zc - ln_ * u + 0.002), (x - wdt, ys + 0.004, zc - ln_ * u + 0.002)])
        loft(f'fringe_{k}', rows, HAIR, smooth=50)
    # brand-new gear: a price tag still hanging from the beanie on a string
    TAG = kit.painted('theo_tag', ['#e8e2d0', '#f1ecdd', '#faf6ea'], rough=0.7, scale=20.0, cavity=0.2)
    hb = HB.ray_cast(Vector((1.0, -0.05, 1.63)), Vector((-1, 0, 0)), 2.0)
    tp = (hb[0] if hb[0] else Vector((0.12, -0.05, 1.63))) + Vector((0.006, 0, 0))
    tag = kit.box('price_tag', (0.003, 0.03, 0.045), tuple(tp + Vector((0.004, -0.01, -0.05))), mat=TAG, bev=0.001)
    tag.rotation_euler = (math.radians(8), math.radians(4), 0); keep(tag)
    tt = kit.text_mesh('tag_price', '49.-', 0.011, tuple(tp + Vector((0.0062, -0.01, -0.05))), (math.radians(90), 0, math.radians(90)),
                       kit.flat('theo_tagink', '#a5231c', rough=0.6), extrude=0.0002); keep(tt)
    st = kit.cyl('tag_string', 0.0007, 0.035, tuple(tp + Vector((0.003, -0.004, -0.017))), seg=6,
                 mat=kit.flat('theo_string', '#d9d4c8', rough=0.8), bev=0); keep(st)
    # jacket zip down the front, with a pull
    ZIP = kit.painted('theo_zip', ['#55585c', '#7a7e83', '#9ca0a5'], rough=0.3, metal=0.8, scale=40.0, cavity=0.3)
    bm = bmesh.new(); prev = None
    for k in range(14):
        z = 1.40 - 0.42 * k / 13
        h = BODY_BVH.ray_cast(Vector((0.0, -3.0, z)), Vector((0, 1, 0)), 6.0)
        if not h[0]: continue
        p = h[0] + h[1] * 0.002
        pair = (bm.verts.new(p - Vector((0.004, 0, 0))), bm.verts.new(p + Vector((0.004, 0, 0))))
        if prev: bm.faces.new((prev[0], prev[1], pair[1], pair[0]))
        prev = pair
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    zp = kit.from_bm('zip', bm, ZIP, smooth_angle=50); zp.modifiers.new('t', 'SOLIDIFY').thickness = 0.003; keep(zp)
    h = BODY_BVH.ray_cast(Vector((0.0, -3.0, 1.30)), Vector((0, 1, 0)), 6.0)
    if h[0]:
        pull = kit.box('zip_pull', (0.012, 0.004, 0.026), tuple(h[0] + Vector((0, -0.006, -0.012))), mat=ZIP, bev=0.0015); keep(pull)

for o in parts:
    o.matrix_parent_inverse = body.matrix_world.inverted()
bpy.ops.wm.save_as_mainfile(filepath=arg('--out'))
print('PARTS', [o.name for o in parts])
