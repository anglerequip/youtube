"""Render a HOST-style episode (Captain Finn) from its plan.json with Blender Eevee.

  blender -b --python tools/blender/render_episode.py -- --plan out/<slug>/plan.json --episode content/episodes/<slug>
          --out out/<slug>/frames [--stills 0.0,2.5,...] [--from F --to F] [--scale 1.0] [--samples 32]

factory/production.py (renderer: blender) calls this. The plan (content/episodes/<slug>/plan.py) lists shots (camera
from/to, target, lens, focus, f-stop, roll), Finn's pose keys, lip-sync amplitude per frame, blinks, which prop is
in his hand when, and what the phone screen shows. This file builds the set (finn_set.py), loads Finn
(finn_v1.py), makes the props, and renders frame by frame. Frames: <out>/f00000.png ...
"""
import bpy, bmesh, math, os, sys, json, argparse, random
from mathutils import Vector, Euler, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import finn_set

FONT_DIR = os.path.join(ROOT, 'assets', 'fonts')


# ---------------------------------------------------------------- helpers
def ease(u):
    u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return [x + (y - x) * u for x, y in zip(a, b)]


def emission_mat(name, img_path, strength=1.6):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(img_path); tex.extension = 'CLIP'
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = strength
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.05
    mix = nt.nodes.new('ShaderNodeMixShader'); mix.inputs['Fac'].default_value = 0.08
    nt.links.new(tex.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs[0], mix.inputs[1]); nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    m['tex'] = tex.name
    return m


# ---------------------------------------------------------------- phone screen pages (real Lure Finder output)
def screen_pages(plan, outdir):
    """tools/blender/screen_pages.py draws them; with the system Python when Blender's has no PIL."""
    outdir = os.path.abspath(outdir)
    try:
        import PIL  # noqa: F401
        import screen_pages as sp
        return sp.screen_pages(plan, outdir)
    except ImportError:
        import subprocess, shutil, tempfile
        os.makedirs(outdir, exist_ok=True)
        pj = os.path.join(outdir, 'plan_for_pages.json'); json.dump(plan, open(pj, 'w'))
        py = os.environ.get('PYTHON_EXE') or shutil.which('python') or shutil.which('python3')
        subprocess.run([py, os.path.join(HERE, 'screen_pages.py'), pj, outdir], check=True)
        return json.load(open(os.path.join(outdir, 'pages.json')))


# ---------------------------------------------------------------- props
def make_phone(M):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * 0.074, v.co.y * 0.0085, v.co.z * 0.155))
    body = finn_set._obj('phone', bm, M['phone_body'], True)
    bv = body.modifiers.new('bev', 'BEVEL'); bv.width = 0.009; bv.segments = 6
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts: v.co = Vector((v.co.x * 0.068, -0.0044, v.co.y * 0.148))
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops: l[uv].uv = (l.vert.co.x / 0.068 + 0.5, l.vert.co.z / 0.148 + 0.5)
    scr = finn_set._obj('phone_screen', bm, None, False); scr.parent = body
    return body, scr


def make_lure(M, color='#d7e04a', length=0.11):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=1.0)
    o = bpy.context.active_object; o.name = 'lure'; o.scale = (length / 2, 0.012, 0.016)
    o.data.materials.append(finn_set._mat('lure_' + color, color, 0.25))
    for p in o.data.polygons: p.use_smooth = True
    for s in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.0045, location=(length * 0.33, s * 0.011, 0.004))
        e = bpy.context.active_object; e.data.materials.append(M['ink']); e.parent = o; e.matrix_parent_inverse = o.matrix_world.inverted()
    return o


def make_box(M, rnd):
    """Open tackle box: green plastic body, lid hinged open, two cantilever trays full of bright lures."""
    root = bpy.data.objects.new('tackle_box', None); bpy.context.scene.collection.objects.link(root)
    parts = []
    def box(name, size, loc, mat, rot=(0, 0, 0)):
        o = finn_set._box(name, size, loc, mat, rot, bevel=0.004); o.parent = root; parts.append(o); return o
    box('tb_body', (0.42, 0.24, 0.16), (0, 0, 0.08), M['box'])
    box('tb_lid', (0.42, 0.012, 0.24), (0, 0.13, 0.28), M['box'], rot=(math.radians(-12), 0, 0))
    for k, (dy, dz) in enumerate(((-0.07, 0.2), (0.06, 0.22))):
        box(f'tb_tray{k}', (0.4, 0.11, 0.03), (0, dy, dz), M['tray'])
        for i in range(6):
            for j in range(2):
                c = rnd.choice(['#d7e04a', '#e2742e', '#c92a2e', '#f2f0e6', '#3d7a2a', '#e8b81c', '#8fa6c8', '#e85a8f'])
                bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1.0,
                                                     location=(-0.17 + i * 0.068, dy - 0.025 + j * 0.05, dz + 0.022))
                l = bpy.context.active_object; l.scale = (0.026, 0.009, 0.009); l.rotation_euler = (0, 0, rnd.uniform(-0.3, 0.3))
                l.data.materials.append(finn_set._mat('lure_' + c, c, 0.25)); l.parent = root; parts.append(l)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.05, minor_radius=0.008, location=(0, 0, 0.175), rotation=(math.radians(90), 0, 0))
    h = bpy.context.active_object; h.data.materials.append(M['tray']); h.parent = root
    return root


def make_rod(M):
    pts = [(0, 0, -0.35), (0, 0, 0.0), (0, 0, 1.2), (0, 0, 2.3)]
    cu = bpy.data.curves.new('rod', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 1.0; cu.bevel_resolution = 4
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, q, r in zip(sp.points, pts, (0.016, 0.012, 0.006, 0.0025)): p.co = (*q, 1); p.radius = r
    o = bpy.data.objects.new('rod', cu); bpy.context.scene.collection.objects.link(o); cu.materials.append(M['rod'])
    return o


def make_pike(M):
    """A northern pike's head and shoulders breaking the surface: a long body, the head flattening forward into a
    broad, rounded duck-bill snout with an underslung jaw line, eyes set high, a gill cover; olive with pale bean
    spots. Local +X is the snout."""
    L = 0.62
    bm = bmesh.new()
    nu, nv = 64, 32
    rings = []
    for i in range(nu + 1):
        u = i / nu                       # 0 tail end .. 1 snout tip
        x = -0.45 * L + u * L
        snout = smooth01((u - 0.55) / 0.42)
        ry = 0.058 * (1 - 0.2 * snout) * math.sin(math.pi * min(1.0, 0.12 + u * 0.95)) ** 0.35
        rz = 0.07 * (1 - 0.8 * snout) * math.sin(math.pi * min(1.0, 0.12 + u * 0.95)) ** 0.5
        if u > 0.97: ry *= (1 - (u - 0.97) / 0.03 * 0.9); rz *= (1 - (u - 0.97) / 0.03 * 0.9)
        zc = -0.012 * snout
        ring = []
        for j in range(nv):
            a = 2 * math.pi * j / nv
            cy, cz = math.cos(a), math.sin(a)
            r_y = ry * (1 + 0.15 * snout * (1 - abs(cz)))                  # the bill is broad and flat
            z = zc + rz * cz * (0.8 if cz < 0 else 1.0)
            if snout > 0.2 and abs(cz) < 0.12: z -= 0.0025 * snout          # mouth line along the side
            ring.append(bm.verts.new((x, r_y * cy, z)))
        rings.append(ring)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % nv], rings[i + 1][(j + 1) % nv], rings[i + 1][j]))
    for ring in (rings[0], rings[-1]):
        bm.faces.new(list(reversed(ring)) if ring is rings[0] else ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = finn_set._obj('pike', bm, M['pike'], True)
    sub = o.modifiers.new('s', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
    for s_ in (-1, 1):                    # eyes high on the head, gold iris, black pupil
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.011, location=(0.62 * L - 0.45 * L + 0.02, s_ * 0.036, 0.03))
        e = bpy.context.active_object; e.data.materials.append(M['pike_eye']); e.parent = o
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.0055, location=(0.62 * L - 0.45 * L + 0.022, s_ * 0.045, 0.031))
        e2 = bpy.context.active_object; e2.data.materials.append(M['ink']); e2.parent = o
    return o


def smooth01(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def prop_materials():
    M = {}
    M['phone_body'] = finn_set._mat('phone_body', '#1d2024', 0.3, metal=0.6)
    M['ink'] = finn_set._mat('ink', '#101214', 0.3)
    M['box'] = finn_set._mat('box', '#3f5a3a', 0.45, noise=0.1)
    M['tray'] = finn_set._mat('tray', '#d9d2b8', 0.5)
    M['rod'] = finn_set._mat('rod', '#20262a', 0.25, metal=0.2)
    pk = bpy.data.materials.new('pike'); pk.use_nodes = True; nt = pk.node_tree; b = nt.nodes['Principled BSDF']
    vo = nt.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 28
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 2.4, 2.4)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], vo.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.12
    ramp.color_ramp.elements[0].color = (*finn_set._lin('#d6d29a'), 1); ramp.color_ramp.elements[1].position = 0.16
    ramp.color_ramp.elements[1].color = (*finn_set._lin('#4a5a2a'), 1)
    nt.links.new(vo.outputs['Distance'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.25; M['pike'] = pk
    M['pike_eye'] = finn_set._mat('pike_eye', '#d4a93a', 0.1)
    return M


def attach(prop, rig, bone, local=(0, 0, 0), rot=(0, 0, 0)):
    prop.parent = rig; prop.parent_type = 'BONE'; prop.parent_bone = bone
    prop.location = local; prop.rotation_euler = rot


# ---------------------------------------------------------------- clipping check
GARMENT_PAIRS = [   # (outer, inner): inner surface points that end up OUTSIDE the outer garment are visible poke-through
    ('finn_jacket', 'finn_body'), ('finn_waders', 'finn_body'), ('finn_knit', 'finn_body'), ('finn_turtleneck', 'finn_body'),
    ('finn_jacket', 'finn_waders'), ('finn_jacket', 'finn_knit'), ('finn_boots', 'finn_waders'), ('finn_boots', 'finn_body')]
# Staging rules that keep contacts clean (used with this check; docs/styles/HOST.md):
#  1. never show a hand closing on a prop in one continuous shot: props appear and change on a cut
#  2. hand + prop actions (lure, phone taps, box) are tight inserts posed for that camera, body out of focus
#  3. close-ups carry something soft near the lens (reed, rope, rod butt) and focus on Finn
#  4. a low sun behind/beside Finn rims the hat and shoulders (finn_v1.host_look)


_PLAIN = {}      # per-keyframe cache, cleared by clipping_report


def _bvh_plain(o, off_types=('SOLIDIFY',)):
    """BVH of one object with some modifiers switched off (garment thickness, the body's hide-under-clothes masks),
    plus a KD-tree of its open-edge (boundary) vertices."""
    from mathutils.kdtree import KDTree
    key = (o.name, off_types)
    if key in _PLAIN:
        return _PLAIN[key]
    off = [m for m in o.modifiers if m.type in off_types and m.show_viewport]
    for m in off: m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(ev.matrix_world); ev.to_mesh_clear()
    for m in off: m.show_viewport = True
    bnd = [v.co.copy() for v in bm.verts if v.is_boundary]
    kd = KDTree(max(1, len(bnd)))
    for k, c in enumerate(bnd): kd.insert(c, k)
    kd.balance()
    verts = [v.co.copy() for v in bm.verts]
    if not bm.faces:
        bm.free(); _PLAIN[key] = (None, kd, verts); return _PLAIN[key]
    t = BVHTree.FromBMesh(bm); bm.free()
    _PLAIN[key] = (t, kd, verts)
    return _PLAIN[key]


def _poke_through(outer, inner, body, every=3, reach=0.03, margin=0.002, edge=0.03):
    """Visible poke-through, judged against the body (no reliance on normals):
    - garment X under garment Y: an X vertex lies further from the body than the nearest point of Y, away from Y's
      open edges (an open jacket front or a boot rim is not poke-through);
    - body under garment Y: a Y vertex lies inside the body.
    Returns the number of offending vertices (sampled every n-th, scaled back)."""
    if outer is None or inner is None or inner.hide_render or outer.hide_render or body is None:
        return 0
    b_bvh, _, _ = _bvh_plain(body, ('MASK',))
    o_bvh, o_edge, o_verts = _bvh_plain(outer)
    if b_bvh is None or o_bvh is None:
        return 0
    n = 0
    if inner == body:
        for vi in range(0, len(o_verts), every):
            co = o_verts[vi]
            loc, nrm, idx, dist = b_bvh.find_nearest(co, reach)
            if loc is not None and (co - loc).dot(nrm) < -margin and o_edge.find(co)[2] > edge:
                n += 1
    else:
        _, _, i_verts = _bvh_plain(inner)
        for vi in range(0, len(i_verts), every):
            co = i_verts[vi]
            loc, nrm, idx, dist = o_bvh.find_nearest(co, reach)
            if loc is None or o_edge.find(loc)[2] < edge:
                continue
            bi = b_bvh.find_nearest(co); bo = b_bvh.find_nearest(loc)
            if bi[0] is not None and bo[0] is not None and bi[3] > bo[3] + margin:
                n += 1
    return n * every if n > 8 else 0          # a handful of verts at a cuff or hem is not visible


def _needed_lift(objs, hand_bvh, dg, step=0.005, limit=0.04):
    """How far the prop must move out of the palm (its parent socket's +Z) before it stops crossing the hand."""
    root = objs[0]
    if root.parent_type != 'BONE':
        return None
    base = root.location.copy(); found = None
    for k in range(1, int(limit / step) + 1):
        root.location = base + Vector((0, 0, step * k)); bpy.context.view_layer.update()
        pb, _ = _bvh_world(objs, bpy.context.evaluated_depsgraph_get())
        if pb is not None and not hand_bvh.overlap(pb):
            found = round(step * k, 3); break
    root.location = base; bpy.context.view_layer.update()
    return found if found is not None else '>%.2f' % limit
PROP_TOUCH_OK = 0          # any triangle pair crossing counts; resting contact is modelled with a small gap


def _bvh_world(objs, dg):
    """One BVH of the evaluated, world-space geometry of objs (modifiers, armature pose, masks applied)."""
    bm = bmesh.new()
    for o in objs:
        if o.hide_render or o.type not in ('MESH', 'CURVE'):
            continue
        ev = o.evaluated_get(dg)
        try:
            me = ev.to_mesh()
        except RuntimeError:
            continue
        if me is None:
            continue
        tmp = bmesh.new(); tmp.from_mesh(me); tmp.transform(ev.matrix_world)
        me2 = bpy.data.meshes.new('_clip_tmp'); tmp.to_mesh(me2); tmp.free(); bm.from_mesh(me2); bpy.data.meshes.remove(me2)
        ev.to_mesh_clear()
    if not bm.faces:
        bm.free(); return None, 0
    bmesh.ops.triangulate(bm, faces=bm.faces)
    n = len(bm.faces)
    t = BVHTree.FromBMesh(bm); bm.free()
    return t, n


def clipping_report(plan, pose_frame, rig, props, fps):
    """Interpenetration check at each shot's start, middle and end: Finn's body, clothes, gloves and beard shell
    against every prop in view (overlapping triangle pairs), garment-vs-body and garment-vs-garment poke-through,
    and the boot soles against the deck (sunk or floating). Returns {'rows': [...], 'md': report}."""
    finn = {o.name.split('.')[0]: o for o in rig.children_recursive if o.type == 'MESH' and o.name.startswith('finn_')}
    deck = plan['deck_z']
    rows = []
    for si, sh in enumerate(plan['shots']):
        for tag, t in (('start', sh['start'] + 0.04), ('mid', (sh['start'] + sh['end']) / 2), ('end', sh['end'] - 0.04)):
            i = max(0, min(plan['n_frames'] - 1, int(t * fps)))
            pose_frame(i); bpy.context.scene.frame_set(i)
            dg = bpy.context.evaluated_depsgraph_get()
            cache = {}; _PLAIN.clear()

            def B(name):
                if name not in cache:
                    o = finn.get(name)
                    cache[name] = _bvh_world([o], dg) if o and not o.hide_render else (None, 0)
                return cache[name][0]
            hits = []
            person = [o for o in finn.values() if not o.hide_render and not o.name.startswith(('finn_hatlure', 'finn_lens'))]
            body_all, _ = _bvh_world(person, dg)
            for pname, objs in props.items():
                if all(o.hide_render for o in objs):
                    continue
                pb, _ = _bvh_world(objs, dg)
                lift = None
                if pb is None or body_all is None:
                    continue
                for fname, fo in finn.items():
                    if fo.hide_render:
                        continue
                    fb = B(fname)
                    if fb is None:
                        continue
                    k = len(fb.overlap(pb))
                    if k > PROP_TOUCH_OK:
                        hits.append((pname, fname, k))
                        if lift is None and fname in ('finn_gloves', 'finn_body'):
                            lift = _needed_lift(objs, fb, dg)
                if lift is not None:
                    hits.append((pname, 'clear of the hand after lifting along the palm normal (m)', lift))
            for outer, inner in GARMENT_PAIRS:
                k = _poke_through(finn.get(outer), finn.get(inner), finn.get('finn_body'))
                if k:
                    hits.append((inner + ' through ' + outer, 'verts', k))
            boots = finn.get('finn_boots')
            feet = ''
            if boots is not None:
                ev = boots.evaluated_get(dg); me = ev.to_mesh()
                zs = sorted((ev.matrix_world @ v.co).z for v in me.vertices); ev.to_mesh_clear()
                lo = zs[0] - deck
                feet = 'sunk %.1f cm' % (-lo * 100) if lo < -0.006 else ('floating %.1f cm' % (lo * 100) if lo > 0.012 else 'on deck')
            rows.append({'shot': si, 'kind': sh['kind'], 'note': sh.get('note', ''), 'at': tag, 't': round(t, 2), 'frame': i,
                         'hits': hits, 'feet': feet})
            print('[clip]', si, tag, round(t, 2), feet, hits, flush=True)
    bad = [r for r in rows if r['hits'] or not r['feet'].startswith('on deck')]
    md = ['# Clipping report', '', f'{len(rows)} keyframes over {len(plan["shots"])} shots; {len(bad)} with a finding.', '',
          'Staging rules this check backs up:', '',
          '1. Never show a hand closing on a prop in one continuous shot: props appear, change and leave on a cut '
          '(prop spans and pose keys marked `snap` start at the cut).',
          '2. Hand + prop actions (lure, phone, box) are tight inserts posed for that camera, the body out of focus.',
          '3. Close-ups carry something soft near the lens (reed, rope, rod butt) and focus on Finn.',
          '4. A low sun behind/beside Finn rims the hat and shoulders (finn_v1.host_look).',
          '5. Props sit on the socket frame with a measured gap (this check prints how far to lift a prop off the palm).',
          '6. Garment rows count vertices of an inner layer that end up further from the body than the layer over it, '
          'away from that layer\'s open edges; confirm them on the frames before changing the cloth.', '',
          '| shot | kind | note | at | t | feet | overlaps (a, b, triangle pairs) |', '|---|---|---|---|---|---|---|']
    for r in rows:
        md.append(f"| {r['shot']} | {r['kind']} | {r['note']} | {r['at']} | {r['t']} | {r['feet']} | "
                  f"{'; '.join(f'{a} x {b}: {k}' for a, b, k in r['hits']) or 'none'} |")
    return {'rows': rows, 'md': '\n'.join(md) + '\n'}


# ---------------------------------------------------------------- main
def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True); ap.add_argument('--episode', default=''); ap.add_argument('--out', required=True)
    ap.add_argument('--stills', default=''); ap.add_argument('--from', dest='f0', type=int, default=0); ap.add_argument('--to', dest='f1', type=int, default=-1)
    ap.add_argument('--scale', type=float, default=float(os.environ.get('RENDER_SCALE', '1.0')))
    ap.add_argument('--samples', type=int, default=int(os.environ.get('RENDER_SAMPLES', '48')))
    ap.add_argument('--engine', default=os.environ.get('RENDER_ENGINE', 'EEVEE'))
    ap.add_argument('--check-clipping', action='store_true', help='pose every shot at its keyframes, test for interpenetration, write a report, render nothing')
    ap.add_argument('--tex', default=os.environ.get('CC0_TEXTURES', r'D:\CounterPhysical\assets-cc0\textures'))
    ap.add_argument('--finn', default=os.environ.get('FINN_BLEND', os.path.join(ROOT, 'assets', 'characters', 'finn.blend')))
    A = ap.parse_args(argv)
    plan = json.load(open(A.plan))
    os.makedirs(A.out, exist_ok=True)
    rnd = random.Random(11)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    S = finn_set.build_set({'tex_dir': A.tex if os.path.isdir(A.tex) else None, 'sun_az': 160, 'sun_elev': 9})
    M = prop_materials()

    # Finn
    try:
        import finn_v1
        rig = finn_v1.load_finn(A.finn if os.path.exists(A.finn) else None)
        api = finn_v1
    except ImportError:
        import host_v1
        rig = host_v1.build_host(); api = None
    fp = plan['finn']['pos']
    rig.location = (fp[0], fp[1], fp[2] + (api.SOLE + 0.007 if api else 0.0))     # boot soles on the deck (clipping check: idle dips ~7 mm)
    rig.rotation_euler = (0, 0, plan['finn'].get('yaw', 0.0))
    sock = (lambda s: api.hand_socket(rig, s)) if api else (lambda s: f'hand_{"R" if s == "R" else "L"}')

    # props
    pages = screen_pages(plan, os.path.join(A.out, '_screen'))
    phone, scr = make_phone(M)
    scr_mats = {k: emission_mat('scr_' + k, p) for k, p in pages.items()}
    scr.data.materials.append(scr_mats['cond0'])
    # props on the hand socket frame documented in finn_v1 (origin mid-palm, +Y along the fingers, +Z out of the
    # palm): the phone lies on the palm with its screen facing out of it, the lure is pinched along X, the rod
    # runs across the fist along X
    attach(phone, rig, sock('R'), (0.0, 0.03, 0.035), (math.radians(-90), 0, 0))   # +5 mm: clipping check
    lure = make_lure(M); attach(lure, rig, sock('R'), (0.0, 0.08, 0.035), (0, 0, math.radians(90)))
    rod = make_rod(M); attach(rod, rig, sock('R'), (0.0, 0.05, 0.04), (0, math.radians(90), 0))
    box = make_box(M, rnd); bx = plan['box']; box.location = bx; box.rotation_euler = (0, 0, math.radians(15))
    pike = make_pike(M); pk = plan['pike_at']; pike.rotation_euler = (0, math.radians(-22), math.radians(-45))   # side-on to the camera: the bill reads in profile; pike.scale = (0.8, 0.8, 0.8)

    # render settings
    try: sc.render.engine = 'BLENDER_EEVEE' if A.engine.upper().startswith('EEVEE') else 'CYCLES'
    except TypeError: sc.render.engine = 'BLENDER_EEVEE_NEXT'
    if sc.render.engine == 'CYCLES':
        sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
            for d in prefs.devices: d.use = True
            sc.cycles.device = 'GPU'
        except Exception: pass
    if api:
        api.host_look(fp, A.samples)          # same light rig and grade as the preview stills
    sc.render.resolution_x = int(plan['W'] * A.scale); sc.render.resolution_y = int(plan['H'] * A.scale)
    sc.render.fps = plan['fps']; sc.render.image_settings.file_format = 'PNG'
    cam_data = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_data); sc.collection.objects.link(cam); sc.camera = cam
    cam_data.sensor_width = 36; cam_data.clip_start = 0.02; cam_data.clip_end = 1000; cam_data.dof.use_dof = True

    shots = plan['shots']; keys = plan['keys']; fps = plan['fps']; talk = plan['talk']; props = plan['props']
    cond = next(s for s in plan['screen'] if s['page'] == 'conditions')
    in_any = lambda t, spans: any(a <= t < b for a, b in spans)

    def pose_frame(i):
        t = i / fps
        # Finn's pose first (prop-tracking cameras need this frame's hands): blend from the previous key into the
        # current one over 0.35 s
        k = max([j for j, kk in enumerate(keys) if kk['t'] <= t] or [0])
        cur = keys[k]; prev = keys[k - 1] if k else cur
        mix = 1.0 if cur.get('snap') else ease((t - cur['t']) / 0.35)     # snap: the pose changes on a hard cut
        a = talk[min(i, len(talk) - 1)]
        blink = 1.0 if any(0 <= t - b < 0.12 for b in plan['blinks']) else 0.0
        if api:
            api.apply_pose(rig, prev['pose'], cur['pose'], mix, frame=i)
            api.set_face(rig, mouth=cur.get('mouth', 'talk'), open=a * (1.4 if cur.get('mouth') == 'shout' else 1.0),
                         brow=cur.get('brow', 0.0), blink=blink)
        pose_props(i, t)
        bpy.context.view_layer.update()
        sh = next((s for s in shots if s['start'] <= t < s['end']), shots[-1])
        u = ease((t - sh['start']) / max(0.01, sh['end'] - sh['start']))
        p = Vector(lerp(sh['cam0'], sh['cam1'], u)); tg = Vector(lerp(sh['tgt0'], sh['tgt1'], u))
        tr = sh.get('track')
        if tr:                       # follow a prop: the camera keeps its offset from the planned target
            obj = {'phone': phone, 'phone_screen': phone, 'box': box, 'pike': pike, 'lure': lure}[tr]
            w = obj.matrix_world.translation.copy()
            if tr == 'phone_screen':        # a screen insert: in front of the screen, slightly above, a slow push
                nrm = (phone.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
                up = (phone.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
                d = sh.get('dist', 0.3) * (1.08 - 0.12 * u)
                p = w + nrm * d + up * 0.05 * d / 0.3
            else:
                p = w + (p - tg)
            tg = w; sh = dict(sh, focus=list(w))
        drift = Vector((0.004 * math.sin(t * 0.9), 0.003 * math.sin(t * 0.7 + 1), 0.004 * math.sin(t * 1.1 + 2)))
        cam.location = p + drift
        q = (tg - cam.location).to_track_quat('-Z', 'Y'); cam.rotation_euler = q.to_euler()
        cam.rotation_euler.rotate_axis('Z', math.radians(sh.get('roll', 0)))
        cam_data.lens = sh['lens']
        cam_data.dof.focus_distance = (Vector(sh['focus']) - cam.location).length; cam_data.dof.aperture_fstop = sh.get('fstop', 2.8)
        bpy.context.view_layer.update()

    def pose_props(i, t):
        lure.hide_render = not in_any(t, props['lure_hand'])
        for ch in lure.children: ch.hide_render = lure.hide_render       # its eyes go with it
        rod.hide_render = not in_any(t, props['rod'])
        phone.hide_render = not in_any(t, props['phone'])
        scr.hide_render = phone.hide_render                              # the screen is its own object
        page = 'cond0'
        for s in plan['screen']:
            if t >= s['t']: page = s['page']
        if page == 'conditions':
            n_t = sum(1 for tt in cond['tap_times'] if t >= tt); page = f'cond{n_t}'
        scr.data.materials[0] = scr_mats.get(page, scr_mats['cond0'])
        if in_any(t, props['box_in_hands']):
            bpy.context.view_layer.update()
            hr = (rig.matrix_world @ rig.pose.bones[sock('R')].matrix).translation
            hl = (rig.matrix_world @ rig.pose.bones[sock('L')].matrix).translation
            mid = (hr + hl) / 2
            # the hands hold the box by its sides at mid-height (box root = its bottom, 16 cm tall body)
            yaw = rig.rotation_euler.z
            fwd = Vector((math.sin(yaw), -math.cos(yaw), 0))           # Finn faces -y at yaw 0
            side = Vector((math.cos(yaw), math.sin(yaw), 0))
            span = abs((hr - hl).dot(side))
            box.scale = (max(0.5, min(1.0, (span - 0.11) / 0.42)), 1.0, 1.0)   # its sides sit in his palms, fingers outside
            c = mid + fwd * 0.05                                        # and its back clears the jacket
            box.location = (c.x, c.y, mid.z - 0.08); box.rotation_euler = (0, 0, yaw)
        else:
            box.location = bx; box.rotation_euler = (0, 0, math.radians(15)); box.scale = (1, 1, 1)
        t0, t1 = props['pike']
        if t0 <= t < t1 + 0.6:
            h = math.sin(math.pi * min(1.0, (t - t0) / (t1 - t0 + 0.6)))
            pike.hide_render = False; pike.location = (pk[0], pk[1], -0.09 + 0.12 * h)
        else:
            pike.hide_render = True

    n = plan['n_frames']
    if A.check_clipping:
        rep = clipping_report(plan, pose_frame, rig, {'phone': [phone, scr], 'lure': [lure] + list(lure.children), 'rod': [rod],
                                                     'box': [c for c in box.children_recursive if c.type == 'MESH']}, fps)
        out_md = os.path.join(A.out, 'clipping.md'); os.makedirs(A.out, exist_ok=True)
        open(out_md, 'w', encoding='utf-8').write(rep['md']); json.dump(rep['rows'], open(out_md[:-3] + '.json', 'w'), indent=1)
        print(rep['md'], flush=True)
        return
    if A.stills:
        frames = [min(n - 1, int(float(x) * fps)) for x in A.stills.split(',')]
        names = [f'still_{float(x):05.1f}.png' for x in A.stills.split(',')]
    else:
        f1 = n if A.f1 < 0 else min(n, A.f1)
        frames = list(range(A.f0, f1)); names = [f'f{i:05d}.png' for i in frames]
    for i, nm in zip(frames, names):
        path = os.path.join(A.out, nm)
        if not A.stills and os.path.exists(path): continue          # resumable
        pose_frame(i); sc.frame_set(i)
        sc.render.filepath = path; bpy.ops.render.render(write_still=True)
        print('frame', i, flush=True)


if __name__ == '__main__':
    main()
