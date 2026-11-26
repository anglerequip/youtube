"""AnglerMind host "Captain Finn" v1 (Blender, procedural), the recurring character of the HOST style (docs/styles/HOST.md).

  python tools/blender/host_v1.py --out assets/characters [--preview out_dir] [--shots front,face] [--no-export]

Same skeleton, bone names and part names as the v7 presenters (tools/blender/presenters_v7.py), so
renderer/characters.js poses him with the same API plus the extra host gestures (host()).

Design (our own, original; Caesar picked it 2026-11-26):
  * A confident fishing guide in his late thirties: angular jaw, short trimmed copper-brown beard, a grin made for
    shouting one key word.
  * Identity piece: wraparound polarised sunglasses with a lake-blue mirror lens that throws a white glint. They
    hide the eyes, so the acting lives in the mouth and the brows (above the frame).
  * Silhouette: a sand bucket hat with a dark olive band and two bright lures pinned to it, a long open rust waxed
    jacket that flares at the knee, olive chest waders with braces, a cream knit roll-neck, dark wader boots.
  * Three value levels (cream / rust / dark olive) plus one warm/cool split (rust jacket vs blue mirror lens),
    in AnglerMind's own brand colours (docs/BRAND.md).
  * Hands about 15 % oversized (they present, point and count), fingerless olive gloves, and an index finger for
    pointing down at the call to action.
Not modelled on any real person, actor or existing character.
"""
import bpy, bmesh, math, sys, os, argparse, random
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from presenters import (reset, link, mat, mesh_obj, sphere, grid, tube, strands, parent_keep, surface_hit, build_body, apply_mods,
                        g2, scalp_cap, stage, look)
from presenters_v7 import build_head7, ring_tube, standard_edges, export


def build_host():
    M = {
        'skin': mat('h_skin', '#d9a184', 0.5, sss=0.18), 'nose': mat('h_nose', '#d48f78', 0.48, sss=0.15),
        'knit': mat('h_knit', '#e6dcc4', 0.92, sheen=0.4), 'jacket': mat('h_jacket', '#a4492a', 0.62, coat=0.15),
        'lining': mat('h_lining', '#5d6b3d', 0.85), 'cord': mat('h_cord', '#3b2a1c', 0.8),
        'wader': mat('h_wader', '#3d4a2a', 0.55, coat=0.1), 'brace': mat('h_brace', '#24291b', 0.7),
        'boot': mat('h_boot', '#2a2219', 0.5, coat=0.2), 'sole': mat('h_sole', '#151210', 0.8),
        'glove': mat('h_glove', '#47532f', 0.8), 'hat': mat('h_hat', '#c8b48a', 0.9, sheen=0.2), 'band': mat('h_band', '#2c3520', 0.75),
        'hair': mat('h_hair', '#6b4126', 0.5), 'beard': mat('h_beard', '#7a4a2a', 0.6, sheen=0.2),
        'frame': mat('h_frame', '#1b1d1f', 0.3, coat=0.5),
        'lens': mat('h_lens', '#2f6f86', 0.04, metal=0.9),
        'lureA': mat('h_lure_a', '#d7e04a', 0.3, coat=0.6), 'lureB': mat('h_lure_b', '#e2742e', 0.3, coat=0.6),
        'steel': mat('h_steel', '#b8bcc0', 0.25, metal=0.9), 'brass': mat('h_brass', '#c9a258', 0.32, metal=0.6),
        'eyewhite': mat('h_eyewhite', '#f2ede6', 0.15), 'iris': mat('h_iris', '#4f6f7a', 0.2), 'irisring': mat('h_iris_ring', '#1f2c33', 0.3),
        'pupil': mat('h_pupil', '#050506', 0.1), 'lash': mat('h_lash', '#3a2416', 0.6), 'brow': mat('h_brow', '#5a3620', 0.7),
        'lip': mat('h_lip', '#b8705e', 0.5), 'mouth': mat('h_mouth', '#3a1518', 0.8), 'earin': mat('h_earin', '#cf8f78', 0.5),
        'glint': mat('h_glint', '#ffffff', 0.1, emit='#ffffff', emit_s=1.0), 'teeth': mat('h_teeth', '#ece6da', 0.35),
    }
    # 1.84 m, broad shoulders, long legs; hands ~15 % oversized
    J = {
        'pelvis': ((0, 0, 1.0), (0.145, 0.105)), 'spine': ((0, 0.008, 1.15), (0.14, 0.105)), 'chest': ((0, 0.0, 1.34), (0.165, 0.11)),
        'neck': ((0, 0.012, 1.54), (0.058, 0.056)), 'head': ((0, 0.01, 1.62), (0.047, 0.047)),
    }
    for s, n in ((1, 'L'), (-1, 'R')):
        J.update({
            f'clav_{n}': ((s * 0.075, 0.008, 1.49), (0.066, 0.058)), f'shoulder_{n}': ((s * 0.215, 0.012, 1.47), (0.062, 0.058)),
            f'elbow_{n}': ((s * 0.255, 0.035, 1.205), (0.046, 0.045)), f'wrist_{n}': ((s * 0.27, -0.03, 0.97), (0.034, 0.029)),
            f'hand_{n}': ((s * 0.272, -0.05, 0.885), (0.04, 0.019)), f'thumb_{n}': ((s * 0.255, -0.088, 0.925), (0.014, 0.014)),
            f'hip_{n}': ((s * 0.1, 0.0, 0.93), (0.088, 0.088)), f'thigh_{n}': ((s * 0.104, 0.0, 0.74), (0.08, 0.082)),
            f'knee_{n}': ((s * 0.106, 0.004, 0.52), (0.06, 0.062)), f'calf_{n}': ((s * 0.107, 0.016, 0.35), (0.064, 0.066)),
            f'ankle_{n}': ((s * 0.108, 0.012, 0.095), (0.045, 0.047)), f'toe_{n}': ((s * 0.11, -0.12, 0.045), (0.045, 0.034)),
        })
    # relaxed confident stance: weight on his right leg, left foot a little out
    J['ankle_L'] = ((0.13, 0.0, 0.095), J['ankle_L'][1]); J['toe_L'] = ((0.16, -0.115, 0.045), J['toe_L'][1])
    E = standard_edges()
    bib_top = 1.36

    def region(b, c):
        if b.startswith(('hand', 'thumb')): return M['glove'] if c.z > 0.905 or b.startswith('thumb') else M['skin']
        if b.startswith('wrist') and c.z < 0.99: return M['glove']
        if b.startswith('head') or (b.startswith('neck') and c.z > 1.585): return M['skin']
        if b.startswith('neck'): return M['knit']
        if b.startswith(('toe', 'ankle')) or (b.startswith('calf') and c.z < 0.3): return M['boot']
        if b.startswith(('thigh', 'knee', 'calf', 'hip', 'pelvis')): return M['wader']
        if b.startswith(('shoulder', 'elbow', 'wrist')): return M['jacket']        # jacket sleeves
        if b.startswith('clav') and abs(c.x) > 0.15: return M['jacket']
        if c.z < bib_top and c.y < 0.02 and abs(c.x) < 0.14: return M['wader']     # chest waders bib in front
        if c.z < 1.17: return M['wader']
        return M['knit']

    def shape(ob):                       # heroic chest, slight taper to the waist
        for v in ob.data.vertices:
            x, y, z = v.co
            if y < 0: v.co.y -= 0.018 * math.exp(-((z - 1.36) / 0.09) ** 2) * (abs(x) < 0.16)
            v.co.x *= 1 - 0.06 * math.exp(-((z - 1.12) / 0.08) ** 2) * (abs(x) < 0.16)
    body, rig = build_body('host', J, E, region, shape)

    C = (0, 0.004, 1.69)
    P = dict(size=(0.079, 0.096, 0.108), lower=1.0, jaw=0.26, chin=0.14, chinfwd=0.09, cheek=0.03, socket=0.06, ridge=0.03, nose=0.085,
             alar=0.02, cheekbone=0.09, apple_z=-0.12, hollow=0.03, philtrum=0.012, dimple=0.012, tip=0.05, lips=0.03,
             nose_z=-0.17, nose_sx=0.075, nose_sz=0.2,
             eye_r=0.0135, eye_x=0.41, eye_z=0.07, iris=0.64, lid=0.55, lid_tilt=0.0, lowlid=0.6, low_tilt=-0.06, lash=0.0009, wing=False,
             brow_x0=0.14, brow_x1=0.8, brow_z=0.33, brow_arch=0.05, brow_w=0.0058, brow_drop=0.03, brow_tilt=-0.03, bushy=60,
             paint=dict(blush=(0.95, 0.68, 0.6, 0.45), socket=(0.85, 0.72, 0.66, 0.35), nose_blush=0.4),
             mouth_z=-0.55, ulip=(0.018, 0.0028), llip=(0.017, 0.0038), smile=0.0035, ear=1.0,
             sculpt_lips=True, lipw=0.25, lip_h=(0.04, 0.058), lip_vol=0.028, smile_u=0.03, lip_mul=(0.85, 0.62, 0.6))
    head, hit = build_head7('h_head', P, C, M)
    a, d, h = P['size']
    Cv = Vector(C)
    parts = []
    # teeth: a bright strip behind the lips that shows when the jaw opens (talk / shout)
    mz = C[2] + P['mouth_z'] * h
    pm, _ = hit(C[0], mz)
    parts.append(sphere('teeth_upper', 1, 32, 12, (C[0], pm.y + 0.009, mz + 0.002), (0.017, 0.006, 0.0035), M['teeth']))
    # short hair under the hat (sides and back) + a cap so no scalp shows
    parts.append(scalp_cap('h_hair_cap', head, C, P, lambda az: 0.45 if abs(az) < 1.25 else -0.4, M['hair'], 1.02))
    for s in (-1, 1):
        def side(u, v, s=s):
            az = s * math.radians(70 + 115 * u)
            zu = 0.42 - 0.75 * v
            k = 1.03 + 0.035 * v * (0.7 + 0.3 * math.sin(u * 19))
            return Vector((C[0] + a * k * math.sin(az), C[1] - d * k * math.cos(az), C[2] + h * zu))
        parts.append(strands('h_str_hair', side, 220, 6, Cv, M['hair'], 0.0022, 0.0012, 0.0022, seed=50 + s))
    # short trimmed beard along the jaw and chin (below the mouth, so the mouth stays free to act) + moustache
    top_cache = {}
    def beard(u, v):
        ang = math.radians(-96 + 192 * u)
        c2 = math.cos(ang) ** 2
        if u not in top_cache:
            z0 = C[2] - h * (0.08 + 0.62 * c2)
            dirv = Vector((math.sin(ang), -math.cos(ang), 0))
            p, n = surface_hit(head, Vector((C[0], C[1], z0)) + dirv * 0.5, -dirv)
            top_cache[u] = (p if p is not None else Vector((C[0], C[1], z0)) + dirv * a, n)
        top, n = top_cache[u]
        z1 = C[2] - h * (0.78 + 0.32 * c2) - 0.012 * c2
        dirv = Vector((math.sin(ang), -math.cos(ang), 0))
        bot0 = Vector((C[0] + a * 0.78 * math.sin(ang) * (1 - 0.35 * c2), C[1] - d * 0.86 * math.cos(ang) - 0.004, z1))
        p2, n2 = surface_hit(head, Vector((bot0.x, bot0.y, z1)) + dirv * 0.4, -dirv)
        bot = p2 if p2 is not None else bot0
        q = top.lerp(bot, v)
        p3, n3 = surface_hit(head, Vector((q.x, q.y, q.z)) + dirv * 0.4, -dirv)
        base = p3 if p3 is not None else q
        return base + dirv * (0.004 + 0.003 * math.sin(math.pi * v))
    parts.append(grid('h_beard', 72, 16, beard, M['beard'], False, 2, 0.004))
    parts.append(strands('h_str_beard', beard, 520, 10, Vector((C[0], C[1] + 0.02, C[2] - h * 0.3)), M['beard'], 0.0016, 0.0008, 0.0026, seed=11))
    for s in (-1, 1):
        p0, _ = hit(C[0] + s * 0.002, C[2] - h * 0.43)
        p1, _ = hit(C[0] + s * 0.02, C[2] - h * 0.47)
        p2, _ = hit(C[0] + s * 0.035, C[2] - h * 0.56)
        pts = [p0 + Vector((0, -0.005, 0)), p1 + Vector((0, -0.0055, -0.001)), p2 + Vector((s * 0.002, -0.004, -0.004))]
        parts.append(tube('h_moustache', [tuple(p) for p in pts], [0.0065, 0.0058, 0.0035], M['beard'], 10, 6))

    # wraparound polarised sunglasses: a curved mirror lens band across the eyes, a dark frame on top, temples to the ears
    ez = C[2] + h * P['eye_z']
    def lensf(u, v):
        az = math.radians(-82 + 164 * u)
        zz = ez + h * (0.2 - 0.42 * v) - h * 0.06 * (abs(az) / 1.4) ** 2 - h * 0.05 * math.sin(math.pi * v) * 0
        k = 1.0
        dirv = Vector((math.sin(az), -math.cos(az), 0))
        p, n = surface_hit(head, Vector((C[0], C[1], zz)) + dirv * 0.5, -dirv)
        base = p if p is not None else Vector((C[0], C[1], zz)) + dirv * a
        nose_gap = 0.012 * math.exp(-(az / 0.12) ** 2) * v ** 2                     # notch over the nose bridge
        return base + dirv * (0.012 + 0.004 * math.cos(az) ** 2) + Vector((0, 0, nose_gap))
    lens = grid('h_shades_lens', 96, 10, lensf, M['lens'], False, 2, 0.002)
    parts.append(lens)
    top_pts = [tuple(lensf(k / 24, 0.0) + Vector((0, 0, 0.002))) for k in range(25)]
    parts.append(tube('h_shades_frame', top_pts, [0.0032] * 25, M['frame'], 6, 4))
    for s in (-1, 1):
        e0 = lensf(0.0 if s < 0 else 1.0, 0.15)
        pts = [e0, e0 + Vector((s * 0.004, 0.03, 0.0)), Vector((C[0] + s * (a + 0.006), C[1] + 0.035, ez + 0.004)), Vector((C[0] + s * (a + 0.002), C[1] + 0.07, ez - 0.012))]
        parts.append(tube('h_shades_temple', [tuple(p) for p in pts], [0.0034, 0.003, 0.0028, 0.0025], M['frame'], 8, 4))

    # bucket hat: soft crown + downward brim, olive band, two lures pinned to the band
    hb = Vector((C[0], C[1] + 0.004, C[2] + h * 0.52))
    def crown(u, v):
        ang = u * 2 * math.pi
        r = (0.104 - 0.012 * v ** 2) * (1 + 0.02 * math.sin(ang * 5 + v * 3))
        zz = 0.105 * v
        if v > 0.85: r *= 1 - (v - 0.85) / 0.15 * 0.6
        return hb + Vector((r * math.sin(ang), -r * 0.96 * math.cos(ang), zz + (0.012 * (v - 0.85) / 0.15 if v > 0.85 else 0)))
    def ctop(u, v):
        ang = u * 2 * math.pi; r = 0.104 * 0.4 * (1 - v)
        return hb + Vector((r * math.sin(ang), -r * 0.96 * math.cos(ang), 0.117 + 0.006 * (1 - v ** 2)))
    hat = [grid('h_hat_crown', 96, 20, crown, M['hat'], True, 1, 0.006), grid('h_hat_top', 96, 6, ctop, M['hat'], True, 1, 0.006)]
    def brim(u, v):
        ang = u * 2 * math.pi; r = 0.102 + 0.07 * v
        droop = -0.045 * v ** 1.2 - 0.008 * math.sin(ang * 3) * v
        return hb + Vector((r * math.sin(ang), -r * 0.98 * math.cos(ang), 0.004 + droop))
    hat.append(grid('h_hat_brim', 128, 10, brim, M['hat'], True, 1, 0.006))
    hat.append(grid('h_hat_band', 128, 2, lambda u, v: hb + Vector((0.106 * math.sin(u * 2 * math.pi), -0.102 * math.cos(u * 2 * math.pi), 0.006 + 0.026 * v)), M['band'], True, 1, 0.003))
    # stitched rings on the brim
    for rr in (0.12, 0.15):
        hat.append(ring_tube('h_hat_stitch', (hb.x, hb.y), rr, rr * 0.98, lambda ang, rr=rr: hb.z + 0.006 - 0.045 * ((rr - 0.102) / 0.07) ** 1.2 - 0.008 * math.sin(ang * 3) * ((rr - 0.102) / 0.07) + 0.002, 0.0012, M['band'], 96))
    lures = []
    for ang, m, ln in ((math.radians(-38), M['lureA'], 0.05), (math.radians(-62), M['lureB'], 0.042)):
        c = hb + Vector((0.112 * math.sin(ang), -0.108 * math.cos(ang), 0.019))
        body = sphere('h_lure', 1, 32, 20, c, (0.011, 0.006, ln / 2), m, 1)
        body.rotation_euler = (math.radians(12), 0, -ang); lures.append(body)
        eye = sphere('h_lure_eye', 1, 12, 8, c + Vector((0.0 * math.sin(ang), -0.006 * math.cos(ang), ln * 0.33)), (0.0035, 0.0035, 0.0035), M['frame'])
        lures.append(eye)
        ring = ring_tube('h_lure_ring', (c.x, c.y - 0.004), 0.004, 0.0, lambda t, c=c, ln=ln: c.z - ln * 0.55 + 0.004 * math.cos(t), 0.0008, M['steel'], 20)
        lures.append(ring)
        hook = tube('h_lure_hook', [tuple(c + Vector((0, -0.004, -ln * 0.6))), tuple(c + Vector((0, -0.004, -ln * 0.85))), tuple(c + Vector((0.0, -0.012, -ln * 0.9))), tuple(c + Vector((0.0, -0.012, -ln * 0.8)))], [0.0008] * 4, M['steel'], 6, 3)
        lures.append(hook)

    # long open rust waxed jacket: shoulders to just above the knee, open at the front, flaring at the hem
    open_half = 0.2                                  # fraction of the circumference left open at the front
    def jacket(u, v):
        ang = math.pi * open_half + u * 2 * math.pi * (1 - open_half)        # from the left front edge round the back to the right
        z = 1.47 - 0.88 * v
        sh = math.exp(-((z - 1.46) / 0.05) ** 2)
        w = 0.205 + 0.02 * v + 0.06 * max(0.0, v - 0.45) ** 1.2 - 0.03 * sh
        dd = 0.13 + 0.02 * v + 0.035 * max(0.0, v - 0.45) ** 1.2
        chest = 0.02 * math.exp(-((z - 1.33) / 0.1) ** 2) * max(0.0, math.cos(ang)) ** 2
        fold = (0.003 + 0.006 * max(0.0, v - 0.4)) * math.sin(ang * 9 + 0.5 * math.sin(ang * 4)) * v
        edge = max(0.0, math.cos(ang)) ** 6 * 0.035 * v                                   # front edges hang a little apart
        x = (w + fold) * math.sin(ang) + math.copysign(edge, math.sin(ang))
        return Vector((x, -(dd + fold + chest) * math.cos(ang) + 0.008, z))
    jk = grid('h_jacket', 128, 48, jacket, M['jacket'], False, 1, 0.01)
    lining = grid('h_jacket_lining', 128, 3, lambda u, v: jacket(u, 0.97 + 0.03 * v), M['lining'], False, 1, 0.004)
    # collar: a standing corduroy collar round the back of the neck, open at the front
    def collar(u, v):
        ang = math.pi * 0.28 + u * 2 * math.pi * 0.72
        r = 0.083 + 0.025 * v; zz = 1.5 + 0.06 * v - 0.025 * max(0.0, math.cos(ang)) * v
        return Vector((r * math.sin(ang) * 1.12, -r * 0.92 * math.cos(ang) + 0.012, zz))
    cl = grid('h_collar', 96, 6, collar, M['cord'], False, 1, 0.006)
    # chest pocket flaps and brass snaps on both jacket fronts
    jdet = []
    for s in (-1, 1):
        for zz, w in ((1.27, 0.065), (0.9, 0.085)):
            pc = jacket(0.02 if s > 0 else 0.98, (1.47 - zz) / 0.88)
            ofs = Vector((-s * 0.05, -0.004, 0))
            flap = sphere('h_pocket', 1, 24, 8, pc + ofs + Vector((0, -0.006, 0)), (w / 2, 0.006, 0.018), M['jacket'], 1)
            jdet.append(flap)
            jdet.append(sphere('h_snap', 1, 16, 8, pc + ofs + Vector((0, -0.013, -0.006)), (0.006, 0.003, 0.006), M['brass']))
    # wader braces over the knit, from the bib up over the shoulders
    braces = []
    for s in (-1, 1):
        pts = []
        for zz in (bib_top, 1.42, 1.48):
            p, n = surface_hit(body, (s * 0.085, -1.0, zz), (0, 1, 0))
            if p is not None: pts.append(tuple(p + n * 0.004))
        for y in (-0.03, 0.03):
            p, n = surface_hit(body, (s * 0.1, y, 1.9), (0, 0, -1))
            if p is not None and p.z < 1.6: pts.append(tuple(p + n * 0.004))
        if len(pts) >= 3: braces.append(tube('h_brace', pts, [0.008] * len(pts), M['brace'], 8, 3))
        p, n = surface_hit(body, (s * 0.085, -1.0, bib_top - 0.01), (0, 1, 0))
        if p is not None: braces.append(sphere('h_brace_clip', 1, 16, 8, p + n * 0.006, (0.013, 0.004, 0.009), M['brass']))
    # bib top hem + a front pocket on the waders
    bh = []
    for k in range(15):
        x = -0.13 + 0.26 * k / 14
        p, n = surface_hit(body, (x, -1.0, bib_top), (0, 1, 0))
        if p is not None: bh.append(tuple(p + n * 0.003))
    if len(bh) > 3: braces.append(tube('h_bib_hem', bh, [0.006] * len(bh), M['brace'], 4, 3))
    p, n = surface_hit(body, (0, -1.0, 1.23), (0, 1, 0))
    if p is not None: braces.append(sphere('h_bib_pocket', 1, 24, 10, p + n * 0.006, (0.075, 0.008, 0.05), M['wader'], 1))
    # knit roll neck
    rn = ring_tube('h_rollneck', (0, 0.012), 0.066, 0.062, lambda ang: 1.545, 0.016, M['knit'], 64)
    # boot soles and a boot cuff
    soles = []
    for s, n in ((1, 'L'), (-1, 'R')):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        an, to = Vector(J[f'ankle_{n}'][0]), Vector(J[f'toe_{n}'][0])
        dv = Vector((to.x - an.x, to.y - an.y)); ang = math.atan2(dv.x, -dv.y); mid = an.lerp(to, 0.45)
        for v in bm.verts:
            x0, y0 = v.co.x * 0.1, v.co.y * 0.3
            v.co = Vector((mid.x + x0 * math.cos(ang) - y0 * math.sin(ang), mid.y + x0 * math.sin(ang) + y0 * math.cos(ang), v.co.z * 0.03 + 0.015))
        so = mesh_obj(f'h_sole_{n}', bm, M['sole'], True, 2); bv = so.modifiers.new('bev', 'BEVEL'); bv.width = 0.01; bv.segments = 4
        so.modifiers.move(1, 0); soles.append((so, f'toe_{n}'))
        k = Vector(J[f'calf_{n}'][0])
        soles.append((ring_tube(f'h_boot_cuff_{n}', (k.x, k.y), 0.07, 0.072, lambda ang: 0.3, 0.012, M['boot'], 48), f'calf_{n}'))
    # glove cuffs and the pointing index finger on each hand (shown by the pose, folded otherwise)
    hands = []
    for s, n in ((1, 'L'), (-1, 'R')):
        w, hd = Vector(J[f'wrist_{n}'][0]), Vector(J[f'hand_{n}'][0])
        ax = (hd - w).normalized(); q = ax.to_track_quat('Z', 'Y')
        pts = [tuple(w + ax * 0.03 + q @ Vector((0.038 * math.cos(t / 32 * 2 * math.pi), 0.034 * math.sin(t / 32 * 2 * math.pi), 0))) for t in range(33)]
        hands.append((tube(f'h_glove_cuff_{n}', pts, [0.007] * 33, M['glove'], 2, 4), f'hand_{n}'))
        tipb = hd + ax * 0.035 + Vector((-s * 0.012, -0.022, 0))
        fpts = [tipb, tipb + ax * 0.035, tipb + ax * 0.07]
        f = tube(f'h_finger_{n}', [tuple(p) for p in fpts], [0.0105, 0.0098, 0.0085], M['skin'], 8, 6)
        hands.append((f, f'hand_{n}'))
    # attach
    for o in [head] + parts + hat + lures: parent_keep(o, rig, 'head')
    for o in [cl, rn] + braces + jdet[:0]: parent_keep(o, rig, 'chest')
    for o in [jk, lining] + jdet: parent_keep(o, rig, 'spine')
    for o, b in soles + hands: parent_keep(o, rig, b)
    return rig


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='assets/characters'); ap.add_argument('--preview', default='')
    ap.add_argument('--shots', default='all'); ap.add_argument('--samples', type=int, default=48)
    ap.add_argument('--budget', type=int, default=22000); ap.add_argument('--no-export', action='store_true')
    ap.add_argument('--res', default='900x1600')
    A = ap.parse_args(argv)
    os.makedirs(A.out, exist_ok=True)
    reset()
    rig = build_host()
    if not A.no_export:
        export(rig, os.path.join(A.out, 'host.glb'), A.budget)
    if A.preview:
        os.makedirs(A.preview, exist_ok=True)
        done = set()
        for o in bpy.data.objects:
            if o.type != 'MESH' or 'Col' not in o.data.color_attributes: continue
            for i, m in enumerate(o.data.materials):
                if m is None: continue
                if m.name not in done:
                    m2 = m.copy(); m2.name = m.name + '_paint'; nt = m2.node_tree; bsdf = nt.nodes['Principled BSDF']
                    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'Col'
                    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
                    mx.inputs[6].default_value = bsdf.inputs['Base Color'].default_value
                    nt.links.new(at.outputs['Color'], mx.inputs[7]); nt.links.new(mx.outputs[2], bsdf.inputs['Base Color'])
                    done.add(m.name); bpy.data.materials[m.name]['paint'] = m2.name
                o.data.materials[i] = bpy.data.materials[bpy.data.materials[m.name]['paint']]
        cam = stage(); sc = bpy.context.scene; sc.cycles.samples = A.samples
        sc.render.resolution_x, sc.render.resolution_y = map(int, A.res.split('x'))
        hz = 1.72
        shots = {'front': ((0, -4.9, 1.2), (0, 0, 1.0), 50), 'threeq': ((3.0, -3.7, 1.25), (0, 0, 1.0), 50),
                 'side': ((4.9, 0, 1.2), (0, 0, 1.0), 50), 'back': ((0, 4.9, 1.2), (0, 0, 1.0), 50),
                 'face': ((0.12, -0.95, hz + 0.02), (0, 0, hz - 0.02), 85), 'face3q': ((0.6, -0.7, hz + 0.03), (0, 0, hz - 0.02), 85),
                 'mcu': ((0.35, -1.9, 1.55), (0, 0, 1.5), 50)}
        for name, (pos, tgt, lens) in shots.items():
            if A.shots != 'all' and name not in A.shots.split(','): continue
            look(cam, pos, tgt, lens)
            sc.render.filepath = os.path.join(A.preview, f'{name}.png')
            bpy.ops.render.render(write_still=True)
            print('rendered', name, flush=True)
