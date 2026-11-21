"""Counterphysical presenters v7: much higher-poly rebuilds of the wizard and the young woman (Blender, procedural).

  python tools/blender/presenters_v7.py --out assets/characters [--preview out_dir] [--only woman|wizard]

Same skeleton, bone names, part names and facing as v6 (tools/blender/presenters.py, whose helpers this reuses), so
renderer/characters.js poses them with the same API. v7 changes:
  * Wizard: a playful, cartoon-warm look. Big bright eyes with smiling lower lids, bushy raised brows, a round rosy
    nose, a curly handlebar moustache and a big forked white beard with curled tips, a crooked teal hat with a patch,
    a bell on the drooping tip and science goggles on the band, a plum robe with a round belly, gold stars and a
    mustard hem, potion vials on the belt, curly-toed slippers and a gnarled staff with a glowing orb.
  * Woman: a stylish, laid-back art-student look (family friendly). Dark espresso hair past the shoulders with soft
    curtain bangs and loose waves, warm brown eyes, natural makeup, light freckles, a gentle smile; cream ribbed top
    under an open rust cardigan with pushed-up sleeves, high-waisted dark jeans with rolled cuffs, brown ankle boots,
    small gold hoops and a fine necklace.
  * Higher density everywhere: heads 96 x 72 (+ subdivision), denser strand hair, a larger export budget.

Both are our own original designs. They are not modelled on any real person, actor or existing character.
"""
import bpy, bmesh, math, sys, os, argparse, random
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from presenters import (reset, link, mat, mesh_obj, sphere, grid, tube, strands, parent_keep, surface_hit, build_body,
                        g2, scalp_cap, stage, look)

# ---------------------------------------------------------------- head (v6 head, denser and more expressive)
def build_head7(name, P, center, mats):
    a, d, h = P['size']
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=72, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        front = max(0.0, -y)
        if z < 0:
            z *= P.get('lower', 1.0)
            t = -z / P.get('lower', 1.0)
            x *= 1 - P['jaw'] * t ** 1.6 - P['chin'] * t ** 5
            y = y * (1 - 0.12 * t * t) - P['chinfwd'] * t ** 3 * front
        x *= 1 + P['cheek'] * math.exp(-(((z + 0.12) / 0.2) ** 2)) * (front ** 0.5)
        for s in (-1, 1):
            y += P['socket'] * g2(x, z, s * 0.37, 0.06, 0.16, 0.12) * front
            y -= P['ridge'] * g2(x, z, s * 0.33, 0.26, 0.22, 0.07) * front
        y -= P['nose'] * g2(x, z, 0, -0.14, 0.085, 0.24) * front
        y -= P['tip'] * g2(x, z, 0, -0.33, 0.085, 0.07) * front
        for s in (-1, 1):
            y -= P.get('alar', 0) * g2(x, z, s * 0.1, -0.36, 0.05, 0.05) * front
            y -= P.get('cheekbone', 0) * g2(x, z, s * 0.42, P.get('apple_z', -0.1), 0.16, 0.1) * front
            y += P.get('hollow', 0) * g2(x, z, s * 0.45, -0.4, 0.14, 0.1) * front
            y += P.get('philtrum', 0) * g2(x, z, s * 0.06, -0.46, 0.035, 0.06) * front
            y += P.get('dimple', 0) * g2(x, z, s * 0.27, -0.55, 0.035, 0.04) * front    # smile corners
        y -= P['lips'] * g2(x, z, 0, -0.55, 0.22, 0.1) * front
        y += 0.05 * g2(x, z, 0, -0.68, 0.2, 0.05) * front
        v.co = Vector((x * a, y * d, z * h)) + Vector(center)
    head = mesh_obj(name, bm, mats['skin'], True, 1)
    C = Vector(center)
    mats.setdefault('glint', mat('glint', '#ffffff', 0.1, emit='#ffffff', emit_s=0.6))
    paint = P.get('paint')
    if paint:
        rnd = random.Random(11)
        freckles = [(rnd.uniform(-0.5, 0.5), rnd.uniform(-0.36, -0.12)) for _ in range(paint.get('freckles', 0))]
        freckles = [(x, z) for x, z in freckles if abs(x) > 0.07 or z < -0.28]
        ca = head.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        for i, v in enumerate(head.data.vertices):
            x, y, z = (v.co.x - C.x) / a, (v.co.y - C.y) / d, (v.co.z - C.z) / h
            front = max(0.0, -y)
            col = Vector((1.0, 1.0, 1.0))
            for s in (-1, 1):
                b = paint['blush'][3] * g2(x, z, s * 0.44, -0.22, 0.17, 0.12) * front
                col = col.lerp(Vector(paint['blush'][:3]), min(1, b))
                e = paint['socket'][3] * g2(x, z, s * 0.38, 0.1, 0.2, 0.11) * front
                col = col.lerp(Vector(paint['socket'][:3]), min(1, e))
            t = paint['blush'][3] * paint.get('nose_blush', 0.6) * (g2(x, z, 0, -0.34, 0.07, 0.06) + 0.6 * g2(x, z, 0, -0.85, 0.15, 0.08)) * front
            col = col.lerp(Vector(paint['blush'][:3]), min(1, t))
            for fx, fz in freckles:
                f = paint.get('freckle_s', 0.6) * g2(x, z, fx, fz, 0.018, 0.016) * front
                if f > 0.01: col = col.lerp(Vector((0.72, 0.5, 0.4)), min(1, f))
            ca.data[i].color = (*col, 1.0)
        head.data.color_attributes.active_color = ca
    def hit(x, z, depth=0.0):
        p, n = surface_hit(head, (x, C.y - 1.0, z), (0, 1, 0))
        return p + n * depth, n
    parts = []
    r = P['eye_r']
    for s in (-1, 1):
        x, z = C.x + s * P['eye_x'] * a, C.z + P['eye_z'] * h
        p, n = hit(x, z)
        ec = Vector((x, p.y + r * 0.62, z))
        parts.append(sphere(f'eye_{"L" if s > 0 else "R"}', r, 48, 36, ec, material=mats['eyewhite']))
        ir = P['iris']
        parts.append(sphere('iris_ring', r * ir * 1.06, 48, 16, ec + Vector((0, -r * 0.925, 0)), (1, 0.16, 1), mats['irisring']))
        parts.append(sphere('iris', r * ir, 48, 16, ec + Vector((0, -r * 0.94, 0)), (1, 0.18, 1), mats['iris']))
        parts.append(sphere('pupil', r * ir * 0.42, 32, 12, ec + Vector((0, -r * 0.99, 0)), (1, 0.12, 1), mats['pupil']))
        parts.append(sphere('pupil_glint', r * 0.15, 16, 8, ec + Vector((r * 0.24, -r * 1.0, r * 0.27)), (1, 0.3, 1), mats['glint']))
        parts.append(sphere('pupil_glint2', r * 0.07, 12, 6, ec + Vector((-r * 0.2, -r * 0.99, -r * 0.18)), (1, 0.3, 1), mats['glint']))
        def lid(nm, keep, scale=1.07, m=None):
            bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=56, v_segments=32, radius=r * scale)
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep(v.co)], context='VERTS')
            for v in bm.verts: v.co = v.co + ec
            o = mesh_obj(nm, bm, m or mats['skin'], True, 0)
            so = o.modifiers.new('solid', 'SOLIDIFY'); so.thickness = r * 0.12
            return o
        tilt = P['lid_tilt'] * s
        parts.append(lid(f'lid_{"L" if s > 0 else "R"}', lambda c: c.z - tilt * c.x > r * P['lid'] and c.y < r * 0.55, 1.07, mats.get('lidc')))
        lo_z = P.get('lowlid', 0.78)
        parts.append(lid('lowlid', lambda c: c.z + P.get('low_tilt', 0) * s * c.x < -r * lo_z and c.y < r * 0.4, 1.05))
        # lash line on the lid edge (+ wing), and a few separate lashes at the outer corner
        pts = []
        for k in range(11):
            ang = math.pi * (0.06 + 0.88 * k / 10)
            xx = math.cos(ang) * r
            zz = r * P['lid'] + tilt * xx + 0.0005
            yy = -math.sqrt(max(0.0, (r * 1.09) ** 2 - xx ** 2 - zz ** 2))
            pts.append(ec + Vector((xx, yy, zz)))
        pts.sort(key=lambda q: q.x * s)
        rad = [0.35 + 0.65 * math.sin(math.pi * (0.15 + 0.85 * k / 10)) for k in range(11)]
        if P['wing']:
            o = pts[-1]; pts.append(o + Vector((s * r * 0.25, r * 0.05, r * 0.12))); rad.append(0.5)
            pts.append(o + Vector((s * r * 0.48, r * 0.1, r * 0.25))); rad.append(0.18)
        parts.append(tube('lash', [tuple(q) for q in pts], [P['lash'] * x for x in rad], mats['lash'], 8, 4))
        for k in range(P.get('lash_flicks', 0)):
            q = pts[6 + k]
            parts.append(tube('lash', [tuple(q), tuple(q + Vector((s * r * 0.12, -r * 0.18, r * 0.2))), tuple(q + Vector((s * r * 0.25, -r * 0.2, r * 0.38)))],
                              [P['lash'] * 0.6, P['lash'] * 0.4, P['lash'] * 0.12], mats['lash'], 4, 3))
        # brows: a smooth tube (woman) or bushy short strands (wizard)
        bp, br = [], []
        for k in range(9):
            u = k / 8
            bx = C.x + s * a * (P['brow_x0'] + (P['brow_x1'] - P['brow_x0']) * u)
            bz = C.z + h * (P['brow_z'] + P['brow_arch'] * math.sin(math.pi * min(1, u * 1.25)) - P.get('brow_drop', 0.04) * u + P.get('brow_tilt', 0) * (u - 0.5))
            q, nn = hit(bx, bz, 0.0012); bp.append(Vector(q)); br.append(P['brow_w'] * (1.0 - 0.6 * u) if u > 0.2 else P['brow_w'] * (0.6 + 2 * u))
        if P.get('bushy'):
            def bf(u, v, bp=bp, s=s):
                i = min(7, int(u * 8)); f = u * 8 - i
                base = bp[i].lerp(bp[i + 1], f)
                return base + Vector((s * (0.004 + 0.004 * u) * v, -0.004 * v, (0.007 - 0.003 * u) * v * (1 + 0.6 * math.sin(u * 3))))
            parts.append(strands('brow', bf, P['bushy'], 4, C, mats['brow'], 0.0018, 0.0006, 0.0012, seed=20 + s))
        else:
            parts.append(tube('brow', [tuple(q) for q in bp], br, mats['brow'], 8, 6))
    # lips + mouth interior; `smile` lifts the corners
    mz = C.z + P['mouth_z'] * P.get('lower', 1.0) * h
    p, n = hit(C.x, mz)
    sm = P.get('smile', 0.0)
    def lipshape(o, w):
        for v in o.data.vertices:
            dx = (v.co.x - C.x) / w
            v.co.z += sm * dx * dx
            v.co.y += 0.25 * sm * dx * dx * 0.0   # keep depth
    ul = sphere('lip_upper', 1, 48, 24, (C.x, p.y + 0.0025, mz + P['ulip'][1] * 0.8), (P['ulip'][0], 0.0042, P['ulip'][1]), mats['lip']); lipshape(ul, P['ulip'][0]); parts.append(ul)
    ll = sphere('lip_lower', 1, 48, 24, (C.x, p.y + 0.0022, mz - P['llip'][1] * 1.0), (P['llip'][0], 0.0046, P['llip'][1]), mats['lip']); lipshape(ll, P['ulip'][0]); parts.append(ll)
    mi = sphere('mouth_inside', 1, 32, 12, (C.x, p.y + 0.004, mz), (P['ulip'][0] * 0.85, 0.004, 0.0008), mats['mouth']); lipshape(mi, P['ulip'][0]); parts.append(mi)
    # ears
    for s in ((-1, 1) if P['ear'] > 0 else ()):
        p2, n2 = surface_hit(head, (C.x + s * 1.0, C.y + 0.01, C.z - 0.01 * h), (-s, 0, 0))
        e = sphere('ear', 1, 32, 24, p2 + Vector((s * 0.004, 0.006, 0)), (0.008, 0.017, 0.028 * P['ear']), mats['skin'], 1)
        e.rotation_euler = (0, 0, -s * 0.25); parts.append(e)
        inner = sphere('ear_in', 1, 24, 16, p2 + Vector((s * 0.0105, 0.004, 0)), (0.0025, 0.011, 0.019 * P['ear']), mats.get('earin', mats['skin']), 1)
        inner.rotation_euler = (0, 0, -s * 0.25); parts.append(inner)
    for o in parts: parent_keep(o, head)
    head['hit'] = 1
    return head, hit

def on_surface(name, target, origin, direction, size, material, lift=0.001, spin=0.0):
    """A thin plate lying on a surface (patch, star). size = (x, y, thickness)."""
    p, n = surface_hit(target, origin, direction)
    if p is None: return None
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    o = mesh_obj(name, bm, material, False, 0)
    o.location = p + n * lift; o.rotation_euler = n.to_track_quat('Z', 'Y').to_euler(); o.rotation_euler.rotate_axis('Z', spin)
    return o

def star(name, target, origin, direction, R, material, lift=0.0015, spin=0.0):
    p, n = surface_hit(target, origin, direction)
    if p is None: return None
    bm = bmesh.new()
    vs = [bm.verts.new((math.sin(k * math.pi / 5) * (R if k % 2 == 0 else R * 0.45), math.cos(k * math.pi / 5) * (R if k % 2 == 0 else R * 0.45), 0)) for k in range(10)]
    f = bm.faces.new(vs)
    ex = bmesh.ops.extrude_face_region(bm, geom=[f]);
    for v in [g for g in ex['geom'] if isinstance(g, bmesh.types.BMVert)]: v.co.z += R * 0.18
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = mesh_obj(name, bm, material, False, 0)
    o.location = p + n * lift; o.rotation_euler = n.to_track_quat('Z', 'Y').to_euler(); o.rotation_euler.rotate_axis('Z', spin)
    return o

def ring_tube(name, center, rx, ry, z_fn, radius, material, n=48, a0=0.0, a1=2 * math.pi):
    pts = []
    for k in range(n + 1):
        ang = a0 + (a1 - a0) * k / n
        pts.append((center[0] + rx * math.sin(ang), center[1] - ry * math.cos(ang), z_fn(ang)))
    return tube(name, pts, [radius] * len(pts), material, 2, 4)

def body_joints(scale_w=1.0):
    pass

def standard_edges():
    E = [('pelvis', 'spine'), ('spine', 'chest'), ('chest', 'neck'), ('neck', 'head')]
    for n in 'LR':
        E += [('chest', f'clav_{n}'), (f'clav_{n}', f'shoulder_{n}'), (f'shoulder_{n}', f'elbow_{n}'), (f'elbow_{n}', f'wrist_{n}'),
              (f'wrist_{n}', f'hand_{n}'), (f'wrist_{n}', f'thumb_{n}'), ('pelvis', f'hip_{n}'), (f'hip_{n}', f'thigh_{n}'),
              (f'thigh_{n}', f'knee_{n}'), (f'knee_{n}', f'calf_{n}'), (f'calf_{n}', f'ankle_{n}'), (f'ankle_{n}', f'toe_{n}')]
    return E

# ---------------------------------------------------------------- the woman
def build_woman():
    M = {
        'skin': mat('w_skin', '#eec3a9', 0.46, sss=0.22), 'top': mat('w_top', '#e8dfcc', 0.85, sheen=0.2),
        'cardi': mat('w_cardigan', '#a3532f', 0.9, sheen=0.35), 'cardrib': mat('w_cardigan_rib', '#8f4626', 0.9, sheen=0.3),
        'denim': mat('w_denim', '#2f3e57', 0.8), 'cuff': mat('w_denim_cuff', '#4a5b78', 0.85),
        'boot': mat('w_boot', '#5b3a26', 0.42, coat=0.3), 'sole': mat('w_sole', '#2a1d16', 0.7),
        'hair': mat('w_hair', '#1d1512', 0.45), 'hairs': mat('w_hair_str', '#2a1e18', 0.38),
        'eyewhite': mat('w_eyewhite', '#f3eee8', 0.12), 'iris': mat('w_iris', '#6a4026', 0.2), 'irisring': mat('w_iris_ring', '#2a170e', 0.3),
        'pupil': mat('w_pupil', '#050506', 0.1), 'lash': mat('w_lash', '#120c0a', 0.5), 'brow': mat('w_brow', '#2a1d17', 0.7),
        'lidc': mat('w_lidshadow', '#c99a8c', 0.55), 'lip': mat('w_lip', '#b8626a', 0.35), 'mouth': mat('w_mouth', '#3a1518', 0.8),
        'gold': mat('w_gold', '#e0b860', 0.3, metal=0.35), 'earin': mat('w_earin', '#e3a996', 0.5, sss=0.2),
    }
    J = {
        'pelvis': ((0, 0, 0.95), (0.126, 0.09)), 'spine': ((0, 0.005, 1.08), (0.104, 0.07)), 'chest': ((0, 0.0, 1.25), (0.118, 0.08)),
        'neck': ((0, 0.008, 1.44), (0.041, 0.04)), 'head': ((0, 0.005, 1.51), (0.036, 0.036)),
    }
    for s, n in ((1, 'L'), (-1, 'R')):
        J.update({
            f'clav_{n}': ((s * 0.06, 0.005, 1.4), (0.05, 0.045)), f'shoulder_{n}': ((s * 0.163, 0.008, 1.385), (0.042, 0.04)),
            f'elbow_{n}': ((s * 0.212, 0.02, 1.13), (0.032, 0.032)), f'wrist_{n}': ((s * 0.237, -0.005, 0.895), (0.021, 0.018)),
            f'hand_{n}': ((s * 0.242, -0.012, 0.825), (0.023, 0.011)), f'thumb_{n}': ((s * 0.233, -0.04, 0.85), (0.009, 0.009)),
            f'hip_{n}': ((s * 0.085, 0.0, 0.88), (0.074, 0.074)), f'thigh_{n}': ((s * 0.088, 0.0, 0.7), (0.064, 0.066)),
            f'knee_{n}': ((s * 0.09, 0.005, 0.49), (0.047, 0.05)), f'calf_{n}': ((s * 0.09, 0.015, 0.33), (0.047, 0.049)),
            f'ankle_{n}': ((s * 0.09, 0.012, 0.085), (0.034, 0.036)), f'toe_{n}': ((s * 0.092, -0.1, 0.035), (0.033, 0.025)),
        })
    E = standard_edges()
    def region(b, c):
        if b.startswith(('hand', 'thumb', 'head')): return M['skin']
        if b.startswith('wrist'): return M['cardi'] if c.z > 1.02 else M['skin']          # sleeves pushed up past the elbow
        if b.startswith(('elbow', 'shoulder')): return M['cardi']
        if b.startswith(('ankle', 'toe')) or (b.startswith('calf') and c.z < 0.15): return M['boot']
        if b.startswith(('thigh', 'knee', 'calf', 'hip')): return M['denim']
        if c.z > 1.405 and b.startswith(('neck', 'chest', 'clav')):
            return M['skin'] if (c.y < 0.03 or c.z > 1.418) else M['cardi']
        if c.y < 0 and abs(c.x) < 0.09:                                                       # front gap of the open cardigan
            return M['denim'] if c.z < 1.0 else M['top']
        if b.startswith('pelvis') and c.z < 1.0: return M['denim']
        return M['cardi']
    def shape(ob):
        for v in ob.data.vertices:
            x, y, z = v.co
            if y < 0:
                for s in (-1, 1): v.co.y -= 0.022 * g2(x, z, s * 0.058, 1.275, 0.05, 0.05)
        # smooth the skin-modifier branch crease at the top of the sternum (showed as a small triangle on the top)
        bm = bmesh.new(); bm.from_mesh(ob.data)
        vs = [v for v in bm.verts if v.co.y < 0 and abs(v.co.x) < 0.07 and 1.28 < v.co.z < 1.43]
        for _ in range(12): bmesh.ops.smooth_vert(bm, verts=vs, factor=0.6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bm.to_mesh(ob.data); bm.free()
    body, rig = build_body('woman', J, E, region, shape)
    C = (0, -0.004, 1.565)
    P = dict(size=(0.077, 0.089, 0.1), lower=0.86, jaw=0.25, chin=0.15, chinfwd=0.07, cheek=0.055, socket=0.055, ridge=0.014, nose=0.075, alar=0.022,
             cheekbone=0.04, hollow=0.012, philtrum=0.012, dimple=0.01, tip=0.055, lips=0.04,
             eye_r=0.0134, eye_x=0.43, eye_z=0.05, iris=0.64, lid=0.5, lid_tilt=0.08, lowlid=0.74, lash=0.0015, wing=True, lash_flicks=3,
             brow_x0=0.17, brow_x1=0.8, brow_z=0.27, brow_arch=0.06, brow_w=0.0027,
             paint=dict(blush=(1.0, 0.7, 0.68, 0.6), socket=(0.84, 0.66, 0.64, 0.6), freckles=30, freckle_s=0.3, nose_blush=0.7),
             mouth_z=-0.56, ulip=(0.0152, 0.0037), llip=(0.0142, 0.0048), smile=0.0024, ear=0)   # ears are under the hair
    head, hit = build_head7('w_head', P, C, M)
    a, d, h = P['size']
    def ellp(az, zu, k):
        lat = math.asin(max(-1.0, min(1.0, zu)))
        return Vector((C[0] + a * k * math.cos(lat) * math.sin(az), C[1] - d * k * math.cos(lat) * math.cos(az), C[2] + h * k * math.sin(lat)))
    Cv = Vector(C)
    # scalp with a centre parting, soft curtain bangs that sweep out to the cheekbones, loose waves past the shoulders
    cap = scalp_cap('w_hair_cap', head, C, P, lambda az: 0.62 - 0.77 * min(1.0, max(0.0, (abs(az) - 0.35) / 1.1)) - 0.4 * min(1.0, max(0.0, (abs(az) - 1.8) / 0.6)), M['hair'], 0.995)
    hs = []
    bang_fns = []
    for s in (-1, 1):
        def bang(u, v, s=s):
            zE = 0.3 - 0.8 * u ** 0.85
            zu = 0.9 + (zE - 0.9) * v
            az = s * math.radians(3 + 58 * u + 24 * v ** 1.6 * (1 - 0.7 * u))
            k = 1.115 + 0.03 * v ** 1.5 + 0.02 * u * v
            return ellp(az, zu, k)
        bang_fns.append(bang)
        hs.append(grid('w_hair_bangs', 40, 16, bang, M['hair'], False, 2, 0.007))
        hs.append(strands('w_str_bangs', bang, 150, 16, Cv, M['hairs'], 0.0016, 0.0011, 0.003, seed=3 + s))
    def wave(z, u, amp):
        return amp * math.sin(z * 38 + u * 5.0)
    def back(u, v):
        az = math.radians(96 + 168 * u)
        zt = C[2] + h * 0.55; zb = 1.255
        z = zt + (zb - zt) * v
        jaw = C[2] - h * 0.72
        if z > jaw:
            return ellp(az, max(-0.95, (z - C[2]) / (h * 1.07)), 1.07)
        t = min(1.0, max(0.0, (jaw - z) / 0.12)); e = t * t * (3 - 2 * t)
        top = ellp(az, -0.72, 1.07); top.z = z
        r = 1.0 + wave(z, u, 0.06) * e + 0.12 * max(0.0, (v - 0.82) / 0.18) ** 2      # waves, ends flick out
        hang = Vector((0.172 * math.sin(az) * r, 0.03 - 0.12 * math.cos(az) * r, z))
        return top.lerp(hang, e)
    hs.append(grid('w_hair_back', 48, 34, back, M['hair'], False, 2, 0.012))
    hs.append(strands('w_str_back', back, 360, 34, Cv, M['hairs'], 0.0021, 0.0011, 0.0045, seed=4))
    def crown(u, v):
        az = math.radians(72 + 216 * u); return ellp(az, 0.98 - 0.42 * v, 1.06)
    hs.append(strands('w_str_crown', crown, 240, 12, Cv, M['hairs'], 0.0019, 0.0017, 0.0035, seed=5))
    def unit(az, zu):
        lat = math.asin(max(-1.0, min(1.0, zu)))
        return Vector((math.cos(lat) * math.sin(az), -math.cos(lat) * math.cos(az), math.sin(lat)))
    for s in (-1, 1):
        def side(u, v, s=s):
            th = math.radians(40 + 120 * u)                                              # along the parting, front to back
            st = Vector((s * 0.03, -math.cos(th), math.sin(th))).normalized()
            en = unit(s * math.radians(62 + 110 * u), -0.15 - 0.2 * u)
            q = st.lerp(en, v).normalized()
            k = 1.07 + 0.012 * math.sin(math.pi * v)
            return Vector((C[0] + a * k * q.x, C[1] + d * k * q.y, C[2] + h * k * q.z))
        hs.append(strands('w_str_side', side, 260, 14, Cv, M['hairs'], 0.0019, 0.0015, 0.003, seed=40 + s))
    for i, sgn in enumerate((-1, 1)):
        def panel(u, v, sgn=sgn):
            az = sgn * math.radians(70 + 28 * u)
            z0 = C[2] + h * 0.15; z = z0 + (1.29 - z0) * v
            jaw = C[2] - h * 0.68
            if z > jaw:
                return ellp(az, max(-0.95, (z - C[2]) / (h * 1.06)), 1.065 + 0.015 * u)
            t = min(1.0, (jaw - z) / 0.1); e = t * t * (3 - 2 * t)
            top = ellp(az, -0.68, 1.065 + 0.015 * u); top.z = z
            w = wave(z, u + i, 0.012) * e
            sh = Vector((sgn * (0.092 + 0.05 * u + w), -0.098 + 0.045 * u + 0.5 * w, z))
            return top.lerp(sh, e)
        hs.append(grid('w_hair_front', 12, 30, panel, M['hair'], False, 2, 0.008))
        hs.append(strands(f'w_str_front{i}', panel, 140, 30, Cv, M['hairs'], 0.0018, 0.001, 0.004, seed=6 + i))
    # open cardigan: a shell round the torso, open at the front, ribbed edges, collar behind the neck, cuffs
    def interp(tab, z):
        for (z0, v0), (z1, v1) in zip(tab, tab[1:]):
            if z0 >= z >= z1: return v0 + (v1 - v0) * (z0 - z) / (z0 - z1)
        return tab[0][1] if z > tab[0][0] else tab[-1][1]
    Wt = [(1.37, 0.125), (1.25, 0.138), (1.1, 0.13), (0.98, 0.15), (0.86, 0.178)]
    Ft = [(1.37, 0.085), (1.28, 0.118), (1.18, 0.1), (1.05, 0.092), (0.86, 0.118)]
    Bt = [(1.37, 0.08), (1.25, 0.092), (1.1, 0.084), (0.86, 0.108)]
    OPEN = 0.5
    def cardi(u, v):
        ang = OPEN + (2 * math.pi - 2 * OPEN) * u
        z = 1.37 - 0.51 * v
        w = interp(Wt, z) + 0.004; dd = (interp(Ft, z) if math.cos(ang) > 0 else interp(Bt, z)) + 0.004
        hang = 0.012 * v * v * max(0.0, math.cos(ang))                                     # fronts hang slightly open
        fold = 0.0025 * math.sin(ang * 9) * v
        return Vector(((w + fold) * math.sin(ang) * (1 + 0.15 * hang / 0.012 * 0.2), -(dd + fold + hang) * math.cos(ang) + 0.002, z))
    cd = grid('w_cardigan', 80, 28, cardi, M['cardi'], False, 1, 0.006)
    edges = []
    for s in (-1, 1):
        u0 = 0.0 if s > 0 else 1.0
        pts = [tuple(cardi(u0, k / 14) + Vector((0, -0.003, 0))) for k in range(15)]
        top = Vector(pts[0])
        neck_pt = Vector((s * 0.05, -0.02, 1.43))
        pts = [tuple(neck_pt), tuple(top.lerp(neck_pt, 0.5) + Vector((s * 0.01, -0.01, 0)))] + pts
        edges.append(tube('w_cardigan_edge', pts, [0.0075] * len(pts), M['cardrib'], 6, 4))
    collar = ring_tube('w_cardigan_collar', (0, 0.008), 0.056, 0.05, lambda ang: 1.425 + 0.008 * math.cos(ang - math.pi), 0.0085, M['cardrib'], 40, math.radians(60), math.radians(300))
    hem = ring_tube('w_cardigan_hem', (0, 0.002), interp(Wt, 0.862) + 0.007, interp(Ft, 0.862) + 0.006, lambda ang: 0.862, 0.008, M['cardrib'], 64, OPEN, 2 * math.pi - OPEN)
    cuffs = []
    for s, n in ((1, 'L'), (-1, 'R')):
        e, w = Vector(J[f'elbow_{n}'][0]), Vector(J[f'wrist_{n}'][0])
        ax = (w - e).normalized(); c0 = e + ax * ((1.02 - e.z) / (w.z - e.z) * (w - e).length)
        q = ax.to_track_quat('Z', 'Y')
        pts = [tuple(c0 + q @ Vector((0.03 * math.cos(t / 24 * 2 * math.pi), 0.028 * math.sin(t / 24 * 2 * math.pi), 0))) for t in range(25)]
        cuffs.append((tube(f'w_cuff_{n}', pts, [0.008] * 25, M['cardrib'], 2, 4), f'wrist_{n}'))
    # neckline trim of the top, jeans waistband + rolled cuffs, boot soles
    nl = []
    for k in range(17):
        x = -0.072 + 0.144 * k / 16
        p, n = surface_hit(body, (x, -1.0, 1.401), (0, 1, 0))
        if p is not None: nl.append(tuple(p + n * 0.0015))
    trims = [tube('w_top_neckline', nl, [0.0025] * len(nl), M['top'], 4, 3)]
    wb = []
    for k in range(13):
        x = -0.09 + 0.18 * k / 12
        p, n = surface_hit(body, (x, -1.0, 1.0), (0, 1, 0))
        if p is not None: wb.append(tuple(p + n * 0.002))
    trims.append(tube('w_waistband', wb, [0.006] * len(wb), M['denim'], 4, 3))
    rolls = []
    for s, n in ((1, 'L'), (-1, 'R')):
        rolls.append((ring_tube(f'w_jean_roll_{n}', (s * 0.09, 0.014), 0.05, 0.052, lambda ang: 0.16, 0.012, M['cuff'], 40), f'calf_{n}'))
    soles = []
    for s, n in ((1, 'L'), (-1, 'R')):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts: v.co = Vector((v.co.x * 0.084 + s * 0.091, v.co.y * 0.215 - 0.042, v.co.z * 0.035 + 0.0175))
        so = mesh_obj(f'w_sole_{n}', bm, M['sole'], True, 2); bv = so.modifiers.new('bev', 'BEVEL'); bv.width = 0.01; bv.segments = 3
        so.modifiers.move(1, 0); soles.append((so, f'toe_{n}'))
    # jewellery: small gold hoops, a fine necklace with a tiny pendant
    jw = []
    for s in (-1, 1):
        jw.append(tube('w_hoop', [(s * (a + 0.004), C[1] + 0.006 + 0.007 * math.cos(t / 20 * 2 * math.pi), C[2] - 0.035 * h / 0.108 - 0.008 + 0.007 * math.sin(t / 20 * 2 * math.pi)) for t in range(21)], [0.0009] * 21, M['gold'], 2, 3))
    neck_pts = []
    for k in range(49):
        ang = k / 48 * 2 * math.pi; f = (1 + math.cos(ang)) / 2
        rr = 0.046 + 0.01 * f ** 2
        neck_pts.append((rr * math.sin(ang), 0.008 - rr * math.cos(ang) - 0.004 * f, 1.44 - 0.03 * f ** 2))
    jw.append(tube('w_necklace', neck_pts, [0.0007] * 49, M['gold'], 2, 3))
    pend = sphere('w_pendant', 1, 24, 16, (0, neck_pts[0][1] - 0.002, neck_pts[0][2] - 0.006), (0.0035, 0.0018, 0.005), M['gold'])
    jw.append(pend)
    # attach
    for o in [head, cap] + hs + jw[:2]: parent_keep(o, rig, 'head')
    for o in [collar, jw[2], pend] + edges[:0]: parent_keep(o, rig, 'neck')
    for o in [cd, hem, *edges, trims[0]]: parent_keep(o, rig, 'chest')
    parent_keep(trims[1], rig, 'spine')
    for o, b in cuffs + rolls + soles: parent_keep(o, rig, b)
    return rig

# ---------------------------------------------------------------- the wizard
def build_wizard():
    M = {
        'skin': mat('z_skin', '#e3b092', 0.52, sss=0.15), 'nose': mat('z_nose', '#e59a85', 0.45, sss=0.15),
        'robe': mat('z_robe', '#5a3a6e', 0.88, sheen=0.3), 'mantle': mat('z_mantle', '#4a2f5c', 0.85, sheen=0.3),
        'trim': mat('z_trim', '#d9a53c', 0.6, sheen=0.2), 'gold': mat('z_gold', '#e2b850', 0.35, metal=0.35),
        'leather': mat('z_leather', '#6a4128', 0.55), 'boot': mat('z_slipper', '#b8462f', 0.6),
        'hair': mat('z_hair', '#ebe7df', 0.55, sheen=0.3), 'beard': mat('z_beard', '#f1ede6', 0.6, sheen=0.25),
        'hat': mat('z_hat', '#2f7377', 0.85, sheen=0.2), 'patch': mat('z_patch', '#c98b3a', 0.85), 'band': mat('z_band', '#4a2e1f', 0.6),
        'wood': mat('z_wood', '#7b5a3c', 0.7), 'brass': mat('z_brass', '#c9a258', 0.32, metal=0.45),
        'lens': mat('z_lens', '#7fd0c8', 0.08, emit='#6fd8cc', emit_s=0.6), 'stone': mat('z_stone', '#9ff3ff', 0.2, emit='#55e4ff', emit_s=7.0),
        'potion_a': mat('z_potion_a', '#ff7a5c', 0.15, emit='#ff6040', emit_s=1.5), 'potion_b': mat('z_potion_b', '#8cff7a', 0.15, emit='#60ff58', emit_s=1.5),
        'cork': mat('z_cork', '#a8835a', 0.8),
        'eyewhite': mat('z_eyewhite', '#f2ede6', 0.15), 'iris': mat('z_iris', '#4c8a5a', 0.2), 'irisring': mat('z_iris_ring', '#1f3a26', 0.3),
        'pupil': mat('z_pupil', '#050506', 0.1), 'lash': mat('z_lash', '#8a7a6c', 0.6), 'brow': mat('z_brow', '#f3f0ea', 0.7),
        'lip': mat('z_lip', '#b8715f', 0.5), 'mouth': mat('z_mouth', '#3a1518', 0.8), 'earin': mat('z_earin', '#d99a82', 0.5),
    }
    J = {
        'pelvis': ((0, 0, 1.0), (0.14, 0.1)), 'spine': ((0, 0.01, 1.14), (0.14, 0.11)), 'chest': ((0, 0.005, 1.32), (0.15, 0.1)),
        'neck': ((0, 0.015, 1.52), (0.056, 0.054)), 'head': ((0, 0.01, 1.605), (0.046, 0.046)),
    }
    for s, n in ((1, 'L'), (-1, 'R')):
        J.update({
            f'clav_{n}': ((s * 0.07, 0.01, 1.47), (0.06, 0.055)), f'shoulder_{n}': ((s * 0.195, 0.012, 1.455), (0.052, 0.05)),
            f'elbow_{n}': ((s * 0.245, 0.03, 1.19), (0.038, 0.038)), f'wrist_{n}': ((s * 0.27, 0.0, 0.95), (0.027, 0.022)),
            f'hand_{n}': ((s * 0.275, -0.01, 0.87), (0.03, 0.014)), f'thumb_{n}': ((s * 0.264, -0.045, 0.9), (0.011, 0.011)),
            f'hip_{n}': ((s * 0.095, 0.0, 0.93), (0.08, 0.08)), f'thigh_{n}': ((s * 0.098, 0.0, 0.74), (0.068, 0.07)),
            f'knee_{n}': ((s * 0.1, 0.005, 0.52), (0.05, 0.052)), f'calf_{n}': ((s * 0.1, 0.015, 0.35), (0.05, 0.052)),
            f'ankle_{n}': ((s * 0.1, 0.012, 0.09), (0.034, 0.036)), f'toe_{n}': ((s * 0.102, -0.11, 0.04), (0.036, 0.026)),
        })
    E = standard_edges()
    def region(b, c):
        if b.startswith(('hand', 'thumb', 'head')) or (b.startswith('neck') and c.z > 1.535): return M['skin']
        if b.startswith(('ankle', 'toe')): return M['boot']
        return M['robe']
    body, rig = build_body('wizard', J, E, region)
    C = (0, 0.002, 1.668)
    P = dict(size=(0.08, 0.094, 0.104), jaw=0.16, chin=0.08, chinfwd=0.05, cheek=0.08, socket=0.06, ridge=0.02, nose=0.08,
             tip=0.03, lips=0.03, cheekbone=0.075, apple_z=-0.2, dimple=0.012,
             eye_r=0.0138, eye_x=0.4, eye_z=0.07, iris=0.66, lid=0.62, lid_tilt=-0.04, lowlid=0.52, low_tilt=-0.12, lash=0.0009, wing=False,
             brow_x0=0.16, brow_x1=0.85, brow_z=0.33, brow_arch=0.1, brow_w=0.005, brow_drop=0.02, brow_tilt=0.04, bushy=70,
             paint=dict(blush=(0.95, 0.58, 0.55, 0.85), socket=(0.9, 0.76, 0.72, 0.35), nose_blush=0.2),
             mouth_z=-0.56, ulip=(0.016, 0.0028), llip=(0.0152, 0.004), smile=0.004, ear=1.12)
    head, hit = build_head7('z_head', P, C, M)
    a, d, h = P['size']
    # round rosy nose
    np_, nn = hit(C[0], C[2] - h * 0.3)
    nose = sphere('z_nose', 1, 48, 36, np_ + Vector((0, 0.002, 0)), (0.0175, 0.017, 0.016), M['nose'], 1)
    parts = [nose]
    for s in (-1, 1):
        parts.append(sphere('z_nostril', 1, 24, 16, np_ + Vector((s * 0.012, 0.004, -0.008)), (0.0075, 0.007, 0.006), M['nose'], 1))
    hair = scalp_cap('z_hair', head, C, P, lambda az: 0.5 if abs(az) < 1.35 else -0.35, M['hair'], 1.035)
    # fluffy white tufts poking out under the hat at the sides and back
    tufts = []
    for s in (-1, 1):
        def tuft(u, v, s=s):
            az = s * math.radians(78 + 110 * u)
            zu = 0.35 - 0.6 * v
            k = 1.04 + 0.22 * v ** 1.3 * (0.7 + 0.3 * math.sin(u * 17))
            return Vector((C[0] + a * k * math.sin(az), C[1] - d * k * math.cos(az), C[2] + h * zu * (1 + 0.1 * v)))
        tufts.append(strands('z_str_hair', tuft, 150, 8, Vector(C), M['hair'], 0.0034, 0.0012, 0.003, seed=30 + s))
    # plum robe with a round belly, mustard hem band and gold stars; shoulder mantle with a hood
    def robe(u, v):
        ang = u * 2 * math.pi
        z = 1.42 - 1.39 * v
        w = 0.17 + 0.03 * v + 0.07 * max(0, v - 0.35) ** 1.3
        dd = 0.115 + 0.03 * v + 0.05 * max(0, v - 0.35) ** 1.3
        front = max(0.0, math.cos(ang)) ** 1.5
        belly = 0.055 * math.exp(-((z - 1.12) / 0.17) ** 2) * front
        w += 0.02 * math.exp(-((z - 1.12) / 0.2) ** 2)
        fold = 0.004 * math.sin(ang * 11) * v
        return Vector(((w + fold) * math.sin(ang), -(dd + fold + belly) * math.cos(ang) + 0.01, z))
    rb = grid('z_robe', 128, 56, robe, M['robe'], True, 1, 0.008)
    hemband = grid('z_robe_hem', 128, 3, lambda u, v: robe(u, 0.955 + 0.045 * v) * 1.0 + Vector((0.006 * math.sin(u * 2 * math.pi), -0.006 * math.cos(u * 2 * math.pi), 0)), M['trim'], True, 1, 0.006)
    def mantle(u, v):
        ang = u * 2 * math.pi
        z = 1.565 - 0.31 * v
        e = math.sin(min(1, max(0.0, v - 0.18) / 0.82 * 1.6) * math.pi / 2)
        w = 0.066 + 0.184 * e; dd = 0.062 + 0.083 * e
        scallop = 0.012 * max(0.0, v - 0.85) / 0.15 * (0.5 + 0.5 * math.cos(ang * 14))
        return Vector((w * math.sin(ang), -dd * math.cos(ang) + 0.012, z + scallop))
    mn = grid('z_mantle', 128, 24, mantle, M['mantle'], True, 1, 0.01)
    mtrim = ring_tube('z_mantle_trim', (0, 0.012), 0.25 + 0.004, 0.145 + 0.004, lambda ang: 1.255 + 0.012 * (0.5 + 0.5 * math.cos(ang * 14)), 0.005, M['trim'], 112)
    hood = sphere('z_hood', 1, 48, 32, (0, 0.11, 1.5), (0.11, 0.07, 0.07), M['mantle'], 1)
    stars = []
    rnd = random.Random(5)
    for k in range(26):
        ang = rnd.uniform(-2.6, 2.6); z = rnd.uniform(0.12, 1.2)
        if abs(ang) < 0.35 and z > 0.75: continue                                    # keep the beard area clear
        dv = Vector((math.sin(ang), -math.cos(ang), 0))
        o = star('z_star', rb, Vector((0, 0.01, z)) + dv * 0.6, -dv, rnd.uniform(0.012, 0.022), M['gold'], 0.006, rnd.uniform(0, 1.2))
        if o: stars.append(o)
    def belt(u, v):
        ang = u * 2 * math.pi
        front = max(0.0, math.cos(ang)) ** 1.5
        return Vector((0.205 * math.sin(ang), -(0.15 + 0.048 * front) * math.cos(ang) + 0.01, 1.03 - 0.035 * v))
    bt = grid('z_belt', 128, 2, belt, M['leather'], True, 1, 0.006)
    buckle = ring_tube('z_buckle', (0, -0.192), 0.022, 0.0, lambda ang: 1.013 + 0.018 * math.cos(ang), 0.003, M['brass'], 32)
    pouch = sphere('z_pouch', 1, 40, 28, (0.165, -0.14, 0.97), (0.042, 0.026, 0.05), M['leather'], 1)
    vials = []
    for x, y, m in ((-0.12, -0.175, 'potion_a'), (-0.175, -0.13, 'potion_b')):
        vials.append(tube('z_vial', [(x, y, 0.93), (x, y, 0.95), (x, y, 0.985), (x, y, 1.0)], [0.012, 0.016, 0.009, 0.006], M[m], 10, 6))
        vials.append(sphere('z_cork', 1, 20, 12, (x, y, 1.006), (0.007, 0.007, 0.007), M['cork']))
    sleeves = []
    for s, n in ((1, 'L'), (-1, 'R')):
        e, w = Vector(J[f'elbow_{n}'][0]), Vector(J[f'wrist_{n}'][0])
        ax = (w - e).normalized()
        q = ax.to_track_quat('Z', 'Y')
        def sl(u, v, e=e, ax=ax, q=q):
            ang = u * 2 * math.pi; r = 0.05 + 0.045 * v ** 1.5
            return e + ax * (-0.04 + 0.25 * v) + q @ Vector((r * math.cos(ang), r * math.sin(ang), 0))
        sleeves.append((grid(f'z_sleeve_{n}', 64, 16, sl, M['robe'], True, 1, 0.006), f'wrist_{n}'))
        c1 = e + ax * 0.21
        pts = [tuple(c1 + q @ Vector((0.097 * math.cos(t / 40 * 2 * math.pi), 0.097 * math.sin(t / 40 * 2 * math.pi), 0))) for t in range(41)]
        sleeves.append((tube(f'z_sleeve_trim_{n}', pts, [0.007] * 41, M['trim'], 2, 4), f'wrist_{n}'))
    # crooked teal hat: wide wavy brim, a cone that kinks and droops, a patch, a little bell, science goggles on the band
    hat_base = Vector((C[0], C[1] + 0.008, C[2] + h * 0.69))
    def brim(u, v):
        ang = u * 2 * math.pi; r = 0.08 + 0.13 * v
        return hat_base + Vector((r * math.sin(ang), -r * 0.95 * math.cos(ang), -0.014 * v * v + 0.008 * math.sin(ang * 3 + 0.5) * v))
    hb = grid('z_hat_brim', 128, 10, brim, M['hat'], True, 1, 0.006)
    def cone_c(v):
        return Vector((0.035 * math.sin(v * math.pi * 1.1), 0.05 * v ** 2, 0.36 * v - 0.12 * max(0.0, v - 0.7) ** 1.5 * 3))
    def cone(u, v):
        ang = u * 2 * math.pi
        r = 0.096 * (1 - v) ** 1.05 + 0.003
        crease = 1 + 0.03 * math.sin(v * 18) * (1 - v)
        cc = cone_c(v)
        droop = Vector((0, 0.11 * max(0.0, v - 0.72) ** 1.3, -0.05 * max(0.0, v - 0.72) ** 1.2))
        return hat_base + cc + droop + Vector((r * crease * math.sin(ang), -r * crease * 0.95 * math.cos(ang), -0.01))
    hc = grid('z_hat_cone', 96, 48, cone, M['hat'], True, 1, 0.005)
    tipp = cone(0, 1.0)
    bell = sphere('z_bell', 1, 32, 24, tipp + Vector((0, 0.006, -0.02)), (0.016, 0.016, 0.016), M['brass'], 1)
    hband = grid('z_hat_band', 128, 2, lambda u, v: hat_base + Vector((0.098 * math.sin(u * 2 * math.pi), -0.093 * math.cos(u * 2 * math.pi), 0.004 + 0.024 * v)), M['band'], True, 1, 0.004)
    patch = on_surface('z_hat_patch', hc, hat_base + Vector((-0.4, -0.25, 0.13)), Vector((0.4, 0.25, 0.0)).normalized(), (0.04, 0.034, 0.003), M['patch'], 0.0015, 0.3)
    goggles = []
    for s in (-1, 1):
        gc = hat_base + Vector((s * 0.03, -0.1, 0.03))
        nrm = Vector((s * 0.3, -1, 0.35)).normalized(); q = nrm.to_track_quat('Z', 'Y')
        pts = [tuple(gc + q @ Vector((0.018 * math.cos(t / 32 * 2 * math.pi), 0.018 * math.sin(t / 32 * 2 * math.pi), 0))) for t in range(33)]
        goggles.append(tube('z_goggle_rim', pts, [0.0042] * 33, M['brass'], 2, 6))
        lens = sphere('z_goggle_lens', 1, 32, 16, (0, 0, 0), (0.0165, 0.0165, 0.004), M['lens']); lens.rotation_euler = q.to_euler(); lens.location = gc
        goggles.append(lens)
    goggles.append(tube('z_goggle_bridge', [tuple(hat_base + Vector((-0.012, -0.106, 0.035))), tuple(hat_base + Vector((0, -0.11, 0.04))), tuple(hat_base + Vector((0.012, -0.106, 0.035)))], [0.003] * 3, M['brass'], 6, 4))
    # big forked white beard with curled tips, curly handlebar moustache
    top_cache = {}
    def beard(u, v):
        ang = math.radians(-100 + 200 * u)
        if u not in top_cache:
            z0 = C[2] - h * (0.12 + 0.6 * math.cos(ang) ** 2)
            dirv = Vector((math.sin(ang), -math.cos(ang), 0))
            p, n = surface_hit(head, Vector((C[0], C[1], z0)) + dirv * 0.5, -dirv)
            top_cache[u] = (p - n * 0.001 if p is not None else Vector((C[0], C[1], z0)) + dirv * a, n)
        top, n = top_cache[u]
        c2 = math.cos(ang) ** 2
        fork = 0.03 * math.exp(-((abs(math.sin(ang)) - 0.22) / 0.14) ** 2)               # two lobes either side of centre
        z1 = C[2] - h * 1.05 - (0.17 + 0.06 * fork / 0.03) * c2
        tip = Vector((top.x * 0.45 + math.copysign(0.025, math.sin(ang) + 1e-6) * c2, C[1] - d * 1.05 - 0.02, z1))
        ring = Vector((0.074 * math.sin(ang), 0.015 - 0.07 * math.cos(ang), 1.56))
        bot = ring.lerp(tip, c2 ** 0.7)
        mid = top.lerp(bot, 0.5); mid += (mid - Vector((C[0], C[1] + 0.01, mid.z))).normalized() * 0.022 * c2
        q = top.lerp(mid, v * 2) if v < 0.5 else mid.lerp(bot, (v - 0.5) * 2)
        q += Vector((math.sin(ang) * 0.6, -math.cos(ang), 0)).normalized() * (0.022 * math.sin(math.pi * v) * (0.25 + 0.75 * c2))
        return q
    bd = grid('z_beard', 64, 32, beard, M['beard'], False, 2, 0.012)
    bds = strands('z_str_beard', beard, 420, 22, Vector((C[0], C[1] + 0.02, C[2] - h * 0.3)), M['beard'], 0.0028, 0.001, 0.0045, seed=9)
    curls = []
    for s in (-1, 1):
        b0 = beard(0.5, 1.0) + Vector((s * 0.018, -0.004, 0.012))
        pts = [b0 + Vector((-s * 0.008, 0, 0.05)), b0, b0 + Vector((s * 0.02, -0.006, -0.018)), b0 + Vector((s * 0.042, -0.004, -0.008)),
               b0 + Vector((s * 0.045, -0.002, 0.012)), b0 + Vector((s * 0.03, 0.0, 0.016))]
        curls.append(tube('z_beard_curl', [tuple(p) for p in pts], [0.02, 0.016, 0.012, 0.009, 0.006, 0.003], M['beard'], 10, 6))
    mus = []
    for s in (-1, 1):
        p0, _ = hit(C[0] + s * 0.003, C[2] - h * 0.45)
        p1, _ = hit(C[0] + s * 0.028, C[2] - h * 0.52)
        p2, _ = hit(C[0] + s * 0.05, C[2] - h * 0.55)
        pts = [p0 + Vector((0, -0.006, 0)), p1 + Vector((0, -0.008, -0.002)), p2 + Vector((s * 0.012, -0.006, 0.002)),
               p2 + Vector((s * 0.028, -0.002, 0.016)), p2 + Vector((s * 0.026, 0.0, 0.03)), p2 + Vector((s * 0.015, 0.0, 0.028))]
        mus.append(tube('z_moustache', [tuple(p) for p in pts], [0.009, 0.0115, 0.0085, 0.006, 0.004, 0.0015], M['beard'], 10, 6))
    # curly-toed slippers with pom-poms
    toes = []
    for s, n in ((1, 'L'), (-1, 'R')):
        t0 = Vector(J[f'toe_{n}'][0])
        pts = [t0 + Vector((0, 0.02, -0.005)), t0 + Vector((0, -0.03, -0.012)), t0 + Vector((0, -0.075, 0.0)), t0 + Vector((0, -0.095, 0.035)),
               t0 + Vector((0, -0.08, 0.06)), t0 + Vector((0, -0.062, 0.05))]
        toes.append((tube(f'z_slipper_curl_{n}', [tuple(p) for p in pts], [0.034, 0.028, 0.017, 0.01, 0.006, 0.004], M['boot'], 10, 6), f'toe_{n}'))
        toes.append((sphere(f'z_pompom_{n}', 1, 24, 16, t0 + Vector((0, -0.06, 0.05)), (0.011, 0.011, 0.011), M['trim'], 1), f'toe_{n}'))
    # gnarled staff with a twisted cage round a glowing orb
    hand = Vector(J['hand_L'][0])
    sp = [(hand.x + 0.01, hand.y - 0.025, 0.02), (hand.x + 0.018, hand.y - 0.03, 0.45), (hand.x + 0.004, hand.y - 0.026, 0.95),
          (hand.x + 0.016, hand.y - 0.03, 1.4), (hand.x + 0.006, hand.y - 0.028, 1.75)]
    staff = tube('z_staff', sp, [0.016, 0.017, 0.016, 0.018, 0.021], M['wood'], 16, 8)
    knots = [sphere('z_knot', 1, 20, 14, Vector(p) + Vector((0.012, -0.004, 0)), (0.012, 0.011, 0.018), M['wood'], 1) for p in sp[1:4]]
    top = Vector(sp[-1])
    orb_c = top + Vector((0, 0, 0.085))
    cage = []
    for k in range(4):
        pts = []
        for j in range(13):
            t = j / 12; ang = k * math.pi / 2 + t * 2.2
            rr = 0.012 + 0.035 * math.sin(math.pi * min(1.0, t * 1.05))
            pts.append(tuple(top + Vector((rr * math.cos(ang), rr * math.sin(ang), 0.16 * t))))
        cage.append(tube('z_cage', pts, [0.008 - 0.005 * j / 12 for j in range(13)], M['wood'], 6, 5))
    stone = sphere('z_stone', 1, 40, 30, orb_c, (0.03, 0.03, 0.03), M['stone'], 1)
    # attach
    for o in [head, hair, hb, hc, hband, bell, bd, bds] + parts + tufts + mus + curls + goggles + ([patch] if patch else []): parent_keep(o, rig, 'head')
    for o in (hood, mn, mtrim): parent_keep(o, rig, 'chest')
    for o in [rb, hemband, bt, buckle, pouch] + stars + vials: parent_keep(o, rig, 'spine')
    for o, b in sleeves + toes: parent_keep(o, rig, b)
    for o in [staff, stone] + knots + cage: parent_keep(o, rig, 'hand_L')
    return rig

# ---------------------------------------------------------------- export
def export(rig, path, budget):
    bpy.ops.object.select_all(action='DESELECT')
    def sel(o):
        o.select_set(True)
        for c in o.children: sel(c)
    sel(rig); bpy.context.view_layer.objects.active = rig
    added, total = [], 0
    dg = bpy.context.evaluated_depsgraph_get()
    for o in bpy.context.selected_objects:
        if o.type != 'MESH': continue
        n = len(o.evaluated_get(dg).data.vertices)
        # only strand hair and hair/beard shells are slimmed; bodies, heads, faces and clothes keep full density
        if n > budget and ('_str_' in o.name or 'hair' in o.name or 'beard' in o.name):
            m = o.modifiers.new('slim', 'DECIMATE'); m.ratio = max(0.3, budget / n); added.append((o, m)); n = int(n * m.ratio)
        total += n
    print(f'{os.path.basename(path)}: ~{total} vertices after slimming', flush=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                              export_skins=True, export_animations=False, export_vertex_color='ACTIVE')
    for o, m in added: o.modifiers.remove(m)

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='assets/characters'); ap.add_argument('--preview', default='')
    ap.add_argument('--only', default=''); ap.add_argument('--shots', default='all'); ap.add_argument('--samples', type=int, default=48)
    ap.add_argument('--budget', type=int, default=22000); ap.add_argument('--no-export', action='store_true')
    ap.add_argument('--res', default='900x1600')
    A = ap.parse_args(argv)
    os.makedirs(A.out, exist_ok=True)
    reset()
    rigs = {}
    for k, f in {'woman': build_woman, 'wizard': build_wizard}.items():
        if A.only and k != A.only: continue
        rigs[k] = f()
    if not A.no_export:
        for k, r in rigs.items(): export(r, os.path.join(A.out, f'{k}.glb'), A.budget)
    if A.preview:
        os.makedirs(A.preview, exist_ok=True)
        cam = stage(); sc = bpy.context.scene; sc.cycles.samples = A.samples
        sc.render.resolution_x, sc.render.resolution_y = map(int, A.res.split('x'))
        if 'woman' in rigs and 'wizard' in rigs:
            rigs['wizard'].location.x = -0.45; rigs['woman'].location.x = 0.45
        shots = {'front': ((0, -4.9, 1.2), (0, 0, 1.0), 50), 'threeq': ((3.0, -3.7, 1.25), (0, 0, 1.0), 50),
                 'side': ((4.9, 0, 1.2), (0, 0, 1.0), 50), 'back': ((0, 4.9, 1.2), (0, 0, 1.0), 50)}
        for k, r in rigs.items():
            hx = r.location.x; hz = 1.585 if k == 'woman' else 1.7
            shots[f'face_{k}'] = ((hx + 0.12, -0.8, hz + 0.02), (hx, 0, hz - 0.01), 85)
            shots[f'face3q_{k}'] = ((hx + 0.55, -0.62, hz + 0.03), (hx, 0, hz - 0.01), 85)
            shots[f'full_{k}'] = ((hx + 0.6, -3.2, 1.1), (hx, 0, 0.98 if k == 'woman' else 1.05), 50)
        for name, (pos, tgt, lens) in shots.items():
            if A.shots != 'all' and name not in A.shots.split(','): continue
            look(cam, pos, tgt, lens)
            sc.render.filepath = os.path.join(A.preview, f'{name}.png')
            bpy.ops.render.render(write_still=True)
            print('rendered', name, flush=True)
