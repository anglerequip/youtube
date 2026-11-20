"""Build the two Counterphysical presenters in Blender (procedural, original designs) and export GLB.

  python tools/blender/presenters.py --out assets/characters [--preview out_dir]

Runs with the `bpy` Python module (pip install bpy) or `blender -b -P`. Everything is generated from code:
a skin-modifier body with a real armature and smooth weights, a sculpted head (deformed sphere + raycast-placed
eyes, lids, lips, brows), and hair / clothing meshes. Characters face -Y in Blender (= +Z in three.js), feet on z=0.

Both characters are our own designs. They are not modelled on any real person or existing character.
"""
import bpy, bmesh, math, sys, os, argparse
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

# ---------------------------------------------------------------- helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob); return ob

def mat(name, color, rough=0.6, metal=0.0, emit=None, emit_s=0.0, coat=0.0, sheen=0.0, sss=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes['Principled BSDF']
    c = Vector(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c]
    b.inputs['Base Color'].default_value = (*lin, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if coat: b.inputs['Coat Weight'].default_value = coat
    if sheen: b.inputs['Sheen Weight'].default_value = sheen
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (0.012, 0.005, 0.003)
    if emit:
        e = Vector(int(emit[i:i + 2], 16) / 255 for i in (1, 3, 5))
        b.inputs['Emission Color'].default_value = (*e, 1); b.inputs['Emission Strength'].default_value = emit_s
    m.diffuse_color = (*lin, 1)
    if any(k in name for k in ('hair', 'beard')):
        nt = m.node_tree; w = nt.nodes.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'Z'
        w.inputs['Scale'].default_value = 160; w.inputs['Distortion'].default_value = 6; w.inputs['Detail'].default_value = 4
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.1
        nt.links.new(w.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
        if 'Anisotropic' in b.inputs: b.inputs['Anisotropic'].default_value = 0.5
    return m

def mesh_obj(name, bm, material=None, smooth=True, subsurf=0):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me))
    if smooth:
        for p in me.polygons: p.use_smooth = True
    if material: me.materials.append(material)
    if subsurf:
        m = ob.modifiers.new('sub', 'SUBSURF'); m.levels = subsurf; m.render_levels = subsurf
    return ob

def sphere(name, r=1.0, seg=48, rings=32, loc=(0, 0, 0), scale=(1, 1, 1), material=None, subsurf=0):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    for v in bm.verts: v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) + Vector(loc)
    return mesh_obj(name, bm, material, True, subsurf)

def grid(name, nu, nv, f, material=None, closed_u=False, subsurf=1, solid=0.0):
    """Quad grid from f(u, v) -> Vector with u in [0,1] (around) and v in [0,1] (down)."""
    bm = bmesh.new(); vs = []
    cu = nu if closed_u else nu + 1
    for j in range(nv + 1):
        row = []
        for i in range(cu): row.append(bm.verts.new(f(i / nu, j / nv)))
        vs.append(row)
    for j in range(nv):
        for i in range(nu):
            a, b = vs[j][i], vs[j][(i + 1) % cu]
            c, d = vs[j + 1][(i + 1) % cu], vs[j + 1][i]
            bm.faces.new((a, b, c, d))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_obj(name, bm, material, True, 0)
    if solid:
        s = ob.modifiers.new('solid', 'SOLIDIFY'); s.thickness = solid; s.offset = 0
    if subsurf:
        m = ob.modifiers.new('sub', 'SUBSURF'); m.levels = subsurf; m.render_levels = subsurf
    return ob

def tube(name, pts, radii, material=None, res=6, bevel_res=6):
    """A smooth tapered tube along points (radii per point), converted to a mesh."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 1.0; cu.bevel_resolution = bevel_res
    cu.resolution_u = res; cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp, p, r in zip(sp.bezier_points, pts, radii):
        bp.co = Vector(p); bp.handle_left_type = bp.handle_right_type = 'AUTO'; bp.radius = r
    tmp = link(bpy.data.objects.new(name + '_c', cu))
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    ob = link(bpy.data.objects.new(name, me))
    for p in me.polygons: p.use_smooth = True
    if material: me.materials.clear(); me.materials.append(material)
    return ob

def strands(name, fn, n, steps, center, material, r0=0.0026, r1=0.0012, push=0.003, jitter=0.6, seed=1, u_range=(0.0, 1.0)):
    """Hair as many thin tapered tubes that follow a surface fn(u, v): one strand per u, running along v.
    Strands are pushed slightly outward from `center` so they lie on top of the shell underneath."""
    import random
    rnd = random.Random(seed)
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 1.0; cu.bevel_resolution = 1
    cu.resolution_u = 2; cu.use_fill_caps = True
    c = Vector(center)
    for i in range(n):
        u = u_range[0] + (u_range[1] - u_range[0]) * min(1.0, max(0.0, (i + 0.5 + rnd.uniform(-jitter, jitter) * 0.5) / n))
        pu = rnd.uniform(0.6, 1.4) * push
        wob = rnd.uniform(0, 6.28); amp = rnd.uniform(0.0005, 0.0018)
        pts = []
        for k in range(steps + 1):
            v = k / steps
            q = fn(u, v)
            off = q - c if q.z > c.z - 0.06 else Vector((q.x - c.x, q.y - c.y, 0))
            q = q + off.normalized() * (pu + amp * math.sin(wob + v * 9))
            pts.append(q)
        sp = cu.splines.new('NURBS'); sp.points.add(len(pts) - 1); sp.use_endpoint_u = True; sp.order_u = 3
        rr = rnd.uniform(0.75, 1.25)
        for k, (pt, q) in enumerate(zip(sp.points, pts)):
            t = k / steps
            pt.co = (q.x, q.y, q.z, 1.0); pt.radius = rr * (r0 + (r1 - r0) * t ** 2)
    tmp = link(bpy.data.objects.new(name + '_c', cu))
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    ob = link(bpy.data.objects.new(name, me))
    for p in me.polygons: p.use_smooth = True
    me.materials.append(material)
    return ob

def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data; ob.modifiers.clear(); ob.data = me; bpy.data.meshes.remove(old)

def parent_keep(child, parent, bone=None):
    mw = child.matrix_world.copy()
    child.parent = parent
    if bone: child.parent_type = 'BONE'; child.parent_bone = bone
    bpy.context.view_layer.update(); child.matrix_world = mw

def surface_hit(ob, origin, direction):
    """Ray-cast in world space against an object's evaluated mesh."""
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
    inv = ev.matrix_world.inverted()
    o = inv @ Vector(origin); d = (inv.to_3x3() @ Vector(direction)).normalized()
    ok, loc, nrm, _ = ev.ray_cast(o, d)
    if not ok: return None, None
    return ev.matrix_world @ loc, (ev.matrix_world.to_3x3() @ nrm).normalized()

# ---------------------------------------------------------------- body (skin modifier + manual armature)
def build_body(name, joints, edges, region_mat, shape=None):
    """joints: {name: ((x,y,z), (rx, ry))}; edges: [(parent, child)], first parent is the root."""
    names = list(joints)
    me = bpy.data.meshes.new(name)
    me.from_pydata([joints[n][0] for n in names], [(names.index(a), names.index(b)) for a, b in edges], [])
    ob = link(bpy.data.objects.new(name, me))
    sk = ob.modifiers.new('skin', 'SKIN'); sk.use_smooth_shade = True; sk.branch_smoothing = 0.6
    for i, n in enumerate(names):
        me.skin_vertices[0].data[i].radius = joints[n][1]
    me.skin_vertices[0].data[names.index(edges[0][0])].use_root = True
    sub = ob.modifiers.new('sub', 'SUBSURF'); sub.levels = 3; sub.render_levels = 3
    apply_mods(ob)
    for p in ob.data.polygons: p.use_smooth = True
    if shape: shape(ob)
    # armature: one bone per edge, named after its child joint
    arm = bpy.data.armatures.new(name + '_rig'); ao = link(bpy.data.objects.new(name + '_rig', arm))
    bpy.context.view_layer.objects.active = ao
    with bpy.context.temp_override(active_object=ao, object=ao, selected_objects=[ao]):
        bpy.ops.object.mode_set(mode='EDIT')
        ebs = {}
        for a, b in edges:
            eb = arm.edit_bones.new(b); eb.head = joints[a][0]; eb.tail = joints[b][0]
            ebs[b] = eb
        for a, b in edges:
            if a in ebs: ebs[b].parent = ebs[a]; ebs[b].use_connect = False
        bpy.ops.object.mode_set(mode='OBJECT')
    # smooth weights from distance to bone segments (top 2 bones)
    segs = [(b, Vector(joints[a][0]), Vector(joints[b][0])) for a, b in edges]
    groups = {b: ob.vertex_groups.new(name=b) for _, b in edges}
    dom = []
    for v in ob.data.vertices:
        ds = []
        for b, h, t in segs:
            ab = t - h; u = max(0.0, min(1.0, (v.co - h).dot(ab) / max(1e-9, ab.length_squared)))
            ds.append(((v.co - (h + ab * u)).length, b))
        ds.sort(); top = ds[:2]
        ws = [1.0 / (d + 0.004) ** 4 for d, _ in top]; s = sum(ws)
        for (d, b), w in zip(top, ws): groups[b].add([v.index], w / s, 'REPLACE')
        dom.append(top[0][1])
    # materials by dominant bone (+ optional override by position)
    mats = []
    for p in ob.data.polygons:
        c = p.center; bones = [dom[i] for i in p.vertices]
        b = max(set(bones), key=bones.count)
        m = region_mat(b, c)
        if m not in mats: mats.append(m)
        p.material_index = mats.index(m)
    for m in mats: ob.data.materials.append(m)
    am = ob.modifiers.new('rig', 'ARMATURE'); am.object = ao
    ob.parent = ao
    return ob, ao

# ---------------------------------------------------------------- head
def g2(x, y, cx, cy, sx, sy):
    return math.exp(-(((x - cx) / sx) ** 2 + ((y - cy) / sy) ** 2))

def build_head(name, P, center, mats):
    """P: shape parameters. Head faces -Y. Returns the head object (children: eyes, lids, lips, brows...)."""
    a, d, h = P['size']                                           # half width, half depth, half height
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=48, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        front = max(0.0, -y)
        if z < 0:
            t = -z
            x *= 1 - P['jaw'] * t ** 1.6 - P['chin'] * t ** 5
            y = y * (1 - 0.12 * t * t) - P['chinfwd'] * t ** 3 * front
        x *= 1 + P['cheek'] * math.exp(-(((z + 0.12) / 0.2) ** 2)) * (front ** 0.5)
        # eye sockets (in), brow ridge (out), nose (out), mouth (slightly out), temples
        for s in (-1, 1):
            y += P['socket'] * g2(x, z, s * 0.37, 0.06, 0.16, 0.12) * front
            y -= P['ridge'] * g2(x, z, s * 0.33, 0.26, 0.22, 0.07) * front
        y -= P['nose'] * g2(x, z, 0, -0.14, 0.085, 0.24) * front
        y -= P['tip'] * g2(x, z, 0, -0.33, 0.085, 0.07) * front
        y -= P['lips'] * g2(x, z, 0, -0.55, 0.22, 0.1) * front
        y += 0.05 * g2(x, z, 0, -0.68, 0.2, 0.05) * front         # crease under the lower lip
        v.co = Vector((x * a, y * d, z * h)) + Vector(center)
    head = mesh_obj(name, bm, mats['skin'], True, 1)
    C = Vector(center)
    def hit(x, z, depth=0.0):
        p, n = surface_hit(head, (x, C.y - 1.0, z), (0, 1, 0))
        return p + n * depth, n
    parts = []
    # eyes
    r = P['eye_r']
    for s in (-1, 1):
        x, z = C.x + s * P['eye_x'] * a, C.z + P['eye_z'] * h
        p, n = hit(x, z)
        ec = Vector((x, p.y + r * 0.62, z))
        eye = sphere(f'eye_{"L" if s > 0 else "R"}', r, 32, 24, ec, material=mats['eyewhite']); parts.append(eye)
        iris = sphere('iris', r * P['iris'], 32, 16, ec + Vector((0, -r * 0.93, 0)), (1, 0.18, 1), mats['iris']); parts.append(iris)
        pupil = sphere('pupil', r * P['iris'] * 0.45, 24, 12, ec + Vector((0, -r * 0.985, 0)), (1, 0.12, 1), mats['pupil']); parts.append(pupil)
        # upper lid: a skin cap over the top of the eyeball, edge tilted; lower lid: thin cap below
        def lid(nm, keep, scale=1.07):
            bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=r * scale)
            kill = [v for v in bm.verts if not keep(v.co)]
            bmesh.ops.delete(bm, geom=kill, context='VERTS')
            for v in bm.verts: v.co = v.co + ec
            o = mesh_obj(nm, bm, mats['skin'], True, 0)
            so = o.modifiers.new('solid', 'SOLIDIFY'); so.thickness = r * 0.12
            return o
        tilt = P['lid_tilt'] * s
        up = lid(f'lid_{"L" if s > 0 else "R"}', lambda c: c.z - tilt * c.x > r * P['lid'] and c.y < r * 0.55); parts.append(up)
        lo = lid('lowlid', lambda c: c.z < -r * 0.78 and c.y < r * 0.4, 1.05); parts.append(lo)
        # lash line along the lid edge, with an outward wing
        pts, rad = [], []
        for k in range(9):
            ang = math.pi * (0.06 + 0.88 * k / 8)
            xx = -math.cos(ang) * r * 1.0 * s * -1
            zz = r * P['lid'] + tilt * xx + 0.0005
            yy = -math.sqrt(max(0.0, (r * 1.09) ** 2 - xx ** 2 - zz ** 2))
            pts.append(ec + Vector((xx * -s if False else xx, yy, zz))); rad.append(1.0)
        pts.sort(key=lambda q: q.x * s)
        rad = [0.35 + 0.65 * math.sin(math.pi * (0.15 + 0.85 * k / 8)) for k in range(9)]
        if P['wing']:
            o = pts[-1]; pts.append(o + Vector((s * r * 0.55, r * 0.1, r * 0.32))); rad.append(0.15)
        lash = tube('lash', [tuple(q) for q in pts], [P['lash'] * x for x in rad], mats['lash']); parts.append(lash)
        # brow along the surface
        bp, br = [], []
        for k in range(7):
            u = k / 6
            bx = C.x + s * a * (P['brow_x0'] + (P['brow_x1'] - P['brow_x0']) * u)
            bz = C.z + h * (P['brow_z'] + P['brow_arch'] * math.sin(math.pi * min(1, u * 1.25)) - 0.04 * u)
            q, nn = hit(bx, bz, 0.0012); bp.append(tuple(q)); br.append(P['brow_w'] * (1.0 - 0.6 * u) if u > 0.2 else P['brow_w'] * (0.6 + 2 * u))
        parts.append(tube('brow', bp, br, mats['brow']))
    # lips + mouth interior (named so the renderer can open the mouth)
    mz = C.z + P['mouth_z'] * h
    p, n = hit(C.x, mz)
    ul = sphere('lip_upper', 1, 32, 16, (C.x, p.y + 0.0025, mz + P['ulip'][1] * 0.8), (P['ulip'][0], 0.0042, P['ulip'][1]), mats['lip']); parts.append(ul)
    ll = sphere('lip_lower', 1, 32, 16, (C.x, p.y + 0.0022, mz - P['llip'][1] * 1.0), (P['llip'][0], 0.0046, P['llip'][1]), mats['lip']); parts.append(ll)
    mi = sphere('mouth_inside', 1, 24, 12, (C.x, p.y + 0.004, mz), (P['ulip'][0] * 0.85, 0.004, 0.0008), mats['mouth']); parts.append(mi)
    # ears
    for s in (-1, 1):
        p, n = surface_hit(head, (C.x + s * 1.0, C.y + 0.01, C.z - 0.01 * h), (-s, 0, 0))
        e = sphere('ear', 1, 24, 16, p + Vector((s * 0.004, 0.006, 0)), (0.008, 0.017, 0.028 * P['ear']), mats['skin'], 1)
        e.rotation_euler = (0, 0, -s * 0.25); parts.append(e)
    for o in parts: parent_keep(o, head)
    return head

# ---------------------------------------------------------------- hair helpers
def scalp_cap(name, head, C, P, hairline, material, scale=1.04):
    """Copy of the skull, pushed out, keeping only vertices above a hairline(azimuth, z_unit) test."""
    a, d, h = P['size']
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=40, radius=1.0)
    kill = []
    for v in bm.verts:
        az = math.atan2(v.co.x, -v.co.y)
        if v.co.z < hairline(az): kill.append(v)
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    for v in bm.verts: v.co = Vector((v.co.x * a * scale, v.co.y * d * scale, v.co.z * h * scale)) + Vector(C)
    o = mesh_obj(name, bm, material, True, 0)
    s = o.modifiers.new('solid', 'SOLIDIFY'); s.thickness = 0.006; s.offset = 1
    m = o.modifiers.new('sub', 'SUBSURF'); m.levels = 1; m.render_levels = 2
    return o

# ---------------------------------------------------------------- the woman
def build_woman():
    M = {
        'skin': mat('w_skin', '#eec7b4', 0.48, sss=0.2), 'top': mat('w_top', '#1b1a1e', 0.88, sheen=0.3),
        'skirt': mat('w_skirt', '#151417', 0.75), 'tights': mat('w_tights', '#2a2327', 0.55),
        'boot': mat('w_boot', '#121114', 0.3, coat=0.4), 'sole': mat('w_sole', '#0c0b0d', 0.7),
        'hair': mat('w_hair', '#0d0b0f', 0.45), 'hairs': mat('w_hair_str', '#141117', 0.38), 'eyewhite': mat('w_eyewhite', '#f1ece6', 0.12),
        'iris': mat('w_iris', '#4a5a58', 0.2), 'pupil': mat('w_pupil', '#050506', 0.1), 'lash': mat('w_lash', '#070608', 0.5),
        'brow': mat('w_brow', '#1a1517', 0.7), 'lip': mat('w_lip', '#9c4f5c', 0.35), 'mouth': mat('w_mouth', '#3a1518', 0.8),
        'silver': mat('w_silver', '#d0d3d8', 0.2, metal=1.0),
    }
    J = {
        'pelvis': ((0, 0, 0.95), (0.128, 0.09)), 'spine': ((0, 0.005, 1.08), (0.108, 0.072)), 'chest': ((0, 0.0, 1.25), (0.12, 0.082)),
        'neck': ((0, 0.008, 1.44), (0.043, 0.042)), 'head': ((0, 0.005, 1.53), (0.034, 0.034)),
    }
    for s, n in ((1, 'L'), (-1, 'R')):
        J.update({
            f'clav_{n}': ((s * 0.06, 0.005, 1.4), (0.05, 0.045)), f'shoulder_{n}': ((s * 0.165, 0.008, 1.385), (0.042, 0.04)),
            f'elbow_{n}': ((s * 0.215, 0.02, 1.13), (0.03, 0.03)), f'wrist_{n}': ((s * 0.24, -0.005, 0.895), (0.022, 0.018)),
            f'hand_{n}': ((s * 0.245, -0.012, 0.825), (0.024, 0.011)), f'thumb_{n}': ((s * 0.236, -0.04, 0.85), (0.009, 0.009)),
            f'hip_{n}': ((s * 0.085, 0.0, 0.88), (0.074, 0.074)), f'thigh_{n}': ((s * 0.088, 0.0, 0.7), (0.062, 0.064)),
            f'knee_{n}': ((s * 0.09, 0.005, 0.49), (0.044, 0.047)), f'calf_{n}': ((s * 0.09, 0.015, 0.33), (0.044, 0.046)),
            f'ankle_{n}': ((s * 0.09, 0.012, 0.085), (0.029, 0.031)), f'toe_{n}': ((s * 0.092, -0.1, 0.035), (0.03, 0.022)),
        })
    E = [('pelvis', 'spine'), ('spine', 'chest'), ('chest', 'neck'), ('neck', 'head')]
    for n in 'LR':
        E += [('chest', f'clav_{n}'), (f'clav_{n}', f'shoulder_{n}'), (f'shoulder_{n}', f'elbow_{n}'), (f'elbow_{n}', f'wrist_{n}'),
              (f'wrist_{n}', f'hand_{n}'), (f'wrist_{n}', f'thumb_{n}'), ('pelvis', f'hip_{n}'), (f'hip_{n}', f'thigh_{n}'),
              (f'thigh_{n}', f'knee_{n}'), (f'knee_{n}', f'calf_{n}'), (f'calf_{n}', f'ankle_{n}'), (f'ankle_{n}', f'toe_{n}')]
    def region(b, c):
        if b.startswith(('hand', 'thumb', 'head')) or (b.startswith('neck') and c.z > 1.435): return M['skin']
        if b.startswith(('ankle', 'toe')) or (b.startswith('calf') and c.z < 0.3): return M['boot']
        if b.startswith(('thigh', 'knee', 'calf')): return M['tights']
        if b.startswith('hip') and c.z < 0.86: return M['tights']
        return M['top']
    def shape(ob):   # modest bust and a narrower waist-to-hip line
        for v in ob.data.vertices:
            x, y, z = v.co
            if y < 0:
                for s in (-1, 1): v.co.y -= 0.024 * g2(x, z, s * 0.058, 1.275, 0.05, 0.05)
    body, rig = build_body('woman', J, E, region, shape)
    C = (0, -0.004, 1.585)
    P = dict(size=(0.075, 0.088, 0.1), jaw=0.27, chin=0.2, chinfwd=0.08, cheek=0.06, socket=0.05, ridge=0.014, nose=0.09,
             tip=0.045, lips=0.035, eye_r=0.0122, eye_x=0.43, eye_z=0.05, iris=0.6, lid=0.52, lid_tilt=0.1, lash=0.0016, wing=True,
             brow_x0=0.2, brow_x1=0.78, brow_z=0.25, brow_arch=0.06, brow_w=0.0016, mouth_z=-0.56, ulip=(0.0135, 0.0028),
             llip=(0.0125, 0.0036), ear=0.9)
    head = build_head('w_head', P, C, M)
    a, d, h = P['size']
    # hair: scalp cap, blunt piecey bangs, long back curtain behind the shoulders, two front panels over the chest
    cap = scalp_cap('w_hair_cap', head, C, P, lambda az: 0.3 if abs(az) < 1.0 else (-0.2 if abs(az) < 2.0 else -0.55), M['hair'], 1.05)
    def ellp(az, zu, k):
        lat = math.asin(max(-1.0, min(1.0, zu)))
        return Vector((C[0] + a * k * math.cos(lat) * math.sin(az), C[1] - d * k * math.cos(lat) * math.cos(az), C[2] + h * k * math.sin(lat)))
    def bangs(u, v):
        az = math.radians(-64 + 128 * u)
        zu = 0.88 - 0.68 * v                                       # crown -> just over the brows
        k = 1.065 + 0.03 * v ** 2
        q = ellp(az, zu, k)
        return q
    hair_bangs = grid('w_hair_bangs', 48, 14, bangs, M['hair'], False, 2, 0.008)
    def back(u, v):
        az = math.radians(100 + 160 * u)                           # sides-behind-ears round the back
        zt = C[2] + h * 0.6; z = zt + (1.17 - zt) * v
        jaw = C[2] - h * 0.75
        q = ellp(az, max(-0.95, (z - C[2]) / (h * 1.07)), 1.07) if z > jaw else None
        t = min(1.0, max(0.0, (jaw - z) / 0.12))
        hang = Vector((0.175 * math.sin(az), 0.03 - 0.125 * math.cos(az), z))
        top = ellp(az, -0.75, 1.07); top.z = z
        return q if q is not None else top.lerp(hang, t * t * (3 - 2 * t))
    hair_back = grid('w_hair_back', 40, 30, back, M['hair'], False, 2, 0.012)
    panels = []; panels_fn = []
    for sgn in (-1, 1):
        def panel(u, v, sgn=sgn):
            az = sgn * math.radians(64 + 32 * u)
            z0 = C[2] + h * 0.45
            z = z0 + (1.24 - z0) * v
            jaw = C[2] - h * 0.7
            if z > jaw:
                return ellp(az, max(-0.95, (z - C[2]) / (h * 1.06)), 1.06 + 0.015 * u)
            t = min(1.0, (jaw - z) / 0.1)
            top = ellp(az, -0.7, 1.06 + 0.015 * u); top.z = z
            chest = Vector((sgn * (0.07 + 0.045 * u), -0.075 - 0.012 * (1 - u) + 0.02 * u + 0.01 * max(0, (1.36 - z)) * 0, z))
            return top.lerp(chest, t * t * (3 - 2 * t))
        panels.append(grid('w_hair_front', 10, 30, panel, M['hair'], False, 2, 0.008)); panels_fn.append(panel)
    # outfit pieces: pleated mini skirt, boot soles, choker, small silver hoops
    def skirt(u, v):
        ang = u * 2 * math.pi
        z = 0.99 - 0.2 * v
        r = 0.142 + 0.055 * v + 0.006 * v * abs(math.sin(ang * 14))
        return Vector((r * math.sin(ang), -r * 0.78 * math.cos(ang) + 0.004, z))
    sk = grid('w_skirt', 112, 10, skirt, M['skirt'], True, 1, 0.006)
    soles = []
    for s, n in ((1, 'L'), (-1, 'R')):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts: v.co = Vector((v.co.x * 0.085 + s * 0.091, v.co.y * 0.21 - 0.045, v.co.z * 0.045 + 0.0225))
        so = mesh_obj(f'w_sole_{n}', bm, M['sole'], True, 2); bv = so.modifiers.new('bev', 'BEVEL'); bv.width = 0.012; bv.segments = 3
        so.modifiers.move(1, 0)
        soles.append((so, f'toe_{n}'))
    chk = tube('w_choker', [(0.046 * math.sin(t / 24 * 2 * math.pi), 0.008 - 0.044 * math.cos(t / 24 * 2 * math.pi), 1.465) for t in range(25)], [0.0035] * 25, M['top'], 2, 4)
    hoops = []
    for s in (-1, 1):
        hp = tube('w_hoop', [(s * (a + 0.004), C[1] + 0.006 + 0.006 * math.cos(t / 16 * 2 * math.pi), C[2] - 0.035 * h / 0.108 - 0.006 + 0.006 * math.sin(t / 16 * 2 * math.pi)) for t in range(17)], [0.0009] * 17, M['silver'], 2, 3)
        hoops.append(hp)
    # attach
    Cv = Vector(C)
    hs = [strands('w_str_bangs', bangs, 200, 14, Cv, M['hairs'], 0.0016, 0.0013, 0.0035, seed=3),
          strands('w_str_back', back, 280, 30, Cv, M['hairs'], 0.0021, 0.0011, 0.0045, seed=4)]
    def crown(u, v):   # top of the head: from the parting back over the crown to the back curtain start
        az = math.radians(70 + 220 * u); return ellp(az, 0.97 - 0.42 * v, 1.06)
    hs.append(strands('w_str_crown', crown, 200, 10, Cv, M['hairs'], 0.0019, 0.0017, 0.0035, seed=5))
    for i, pf in enumerate(panels_fn):
        hs.append(strands(f'w_str_front{i}', pf, 70, 30, Cv, M['hairs'], 0.0018, 0.001, 0.004, seed=6 + i))
    for o in [head, cap, hair_back, hair_bangs, chk] + panels + hoops + hs: parent_keep(o, rig, 'head' if o is not chk else 'neck')
    parent_keep(sk, rig, 'spine')
    for so, b in soles: parent_keep(so, rig, b)
    return rig

# ---------------------------------------------------------------- the wizard
def build_wizard():
    M = {
        'skin': mat('z_skin', '#d9a98c', 0.55, sss=0.12), 'robe': mat('z_robe', '#2c3a5c', 0.9, sheen=0.3),
        'mantle': mat('z_mantle', '#22304c', 0.85, sheen=0.3), 'leather': mat('z_leather', '#4a3324', 0.55),
        'boot': mat('z_boot', '#2c211b', 0.5), 'hair': mat('z_hair', '#8a7c70', 0.55, sheen=0.3), 'beard': mat('z_beard', '#5e4a3c', 0.6, sheen=0.2),
        'hat': mat('z_hat', '#2a3758', 0.85, sheen=0.2), 'wood': mat('z_wood', '#8a6a48', 0.65), 'brass': mat('z_brass', '#b08a4a', 0.35, metal=0.8),
        'stone': mat('z_stone', '#ffb35c', 0.25, emit='#ff9a3c', emit_s=6.0),
        'eyewhite': mat('z_eyewhite', '#ece6dd', 0.15), 'iris': mat('z_iris', '#5d7a8f', 0.2), 'pupil': mat('z_pupil', '#050506', 0.1),
        'lash': mat('z_lash', '#4a3e36', 0.6), 'brow': mat('z_brow', '#6e5a4c', 0.7), 'lip': mat('z_lip', '#a36a5e', 0.5), 'mouth': mat('z_mouth', '#3a1518', 0.8),
    }
    J = {
        'pelvis': ((0, 0, 1.0), (0.14, 0.1)), 'spine': ((0, 0.01, 1.14), (0.135, 0.095)), 'chest': ((0, 0.005, 1.32), (0.15, 0.1)),
        'neck': ((0, 0.015, 1.52), (0.045, 0.045)), 'head': ((0, 0.01, 1.63), (0.035, 0.035)),
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
    E = [('pelvis', 'spine'), ('spine', 'chest'), ('chest', 'neck'), ('neck', 'head')]
    for n in 'LR':
        E += [('chest', f'clav_{n}'), (f'clav_{n}', f'shoulder_{n}'), (f'shoulder_{n}', f'elbow_{n}'), (f'elbow_{n}', f'wrist_{n}'),
              (f'wrist_{n}', f'hand_{n}'), (f'wrist_{n}', f'thumb_{n}'), ('pelvis', f'hip_{n}'), (f'hip_{n}', f'thigh_{n}'),
              (f'thigh_{n}', f'knee_{n}'), (f'knee_{n}', f'calf_{n}'), (f'calf_{n}', f'ankle_{n}'), (f'ankle_{n}', f'toe_{n}')]
    def region(b, c):
        if b.startswith(('hand', 'thumb', 'head')) or (b.startswith('neck') and c.z > 1.5): return M['skin']
        if b.startswith(('ankle', 'toe')): return M['boot']
        return M['robe']
    body, rig = build_body('wizard', J, E, region)
    C = (0, 0.002, 1.69)
    P = dict(size=(0.078, 0.094, 0.104), jaw=0.18, chin=0.08, chinfwd=0.06, cheek=0.05, socket=0.075, ridge=0.03, nose=0.12,
             tip=0.06, lips=0.03, eye_r=0.0115, eye_x=0.41, eye_z=0.06, iris=0.6, lid=0.45, lid_tilt=-0.06, lash=0.0008, wing=False,
             brow_x0=0.18, brow_x1=0.8, brow_z=0.25, brow_arch=0.035, brow_w=0.0042, mouth_z=-0.56, ulip=(0.015, 0.0028),
             llip=(0.0145, 0.0036), ear=1.05)
    head = build_head('z_head', P, C, M)
    a, d, h = P['size']
    hair = scalp_cap('z_hair', head, C, P, lambda az: 0.5 if abs(az) < 1.35 else -0.35, M['hair'], 1.035)
    # long robe from chest to ankles, a short shoulder mantle with a folded hood behind the neck, belt + pouch
    def robe(u, v):
        ang = u * 2 * math.pi
        z = 1.42 - 1.39 * v
        w = 0.17 + 0.03 * v + 0.07 * max(0, v - 0.35) ** 1.3
        dd = 0.115 + 0.03 * v + 0.05 * max(0, v - 0.35) ** 1.3
        fold = 0.004 * math.sin(ang * 11) * v
        return Vector(((w + fold) * math.sin(ang), -(dd + fold) * math.cos(ang) + 0.01, z))
    rb = grid('z_robe', 96, 40, robe, M['robe'], True, 1, 0.008)
    def mantle(u, v):
        ang = u * 2 * math.pi
        z = 1.5 - 0.24 * v
        w = 0.1 + 0.15 * math.sin(min(1, v * 1.6) * math.pi / 2)
        dd = 0.075 + 0.07 * math.sin(min(1, v * 1.6) * math.pi / 2)
        return Vector((w * math.sin(ang), -dd * math.cos(ang) + 0.012, z))
    mn = grid('z_mantle', 96, 16, mantle, M['mantle'], True, 1, 0.01)
    hood = sphere('z_hood', 1, 40, 24, (0, 0.11, 1.5), (0.11, 0.07, 0.07), M['mantle'], 1)
    def belt(u, v):
        ang = u * 2 * math.pi
        return Vector((0.183 * math.sin(ang), -0.128 * math.cos(ang) + 0.01, 1.05 - 0.035 * v))
    bt = grid('z_belt', 96, 2, belt, M['leather'], True, 1, 0.006)
    pouch = sphere('z_pouch', 1, 32, 20, (0.15, -0.11, 0.98), (0.04, 0.025, 0.05), M['leather'], 1)
    # wide sleeves around the forearms (bone-parented)
    sleeves = []
    for s, n in ((1, 'L'), (-1, 'R')):
        e, w = Vector(J[f'elbow_{n}'][0]), Vector(J[f'wrist_{n}'][0])
        ax = (w - e).normalized()
        def sl(u, v, e=e, ax=ax):
            ang = u * 2 * math.pi
            r = 0.05 + 0.04 * v ** 1.5
            q = ax.to_track_quat('Z', 'Y')
            return e + ax * (-0.04 + 0.25 * v) + q @ Vector((r * math.cos(ang), r * math.sin(ang), 0))
        so = grid(f'z_sleeve_{n}', 48, 12, sl, M['robe'], True, 1, 0.006); sleeves.append((so, f'wrist_{n}'))
    # hat: soft wide brim + tall cone with a gentle bend, leather band
    hat_base = Vector((C[0], C[1] + 0.008, C[2] + h * 0.69))
    def brim(u, v):
        ang = u * 2 * math.pi; r = 0.078 + 0.12 * v
        return hat_base + Vector((r * math.sin(ang), -r * 0.95 * math.cos(ang), -0.012 * v * v + 0.004 * math.sin(ang * 2) * v))
    hb = grid('z_hat_brim', 96, 8, brim, M['hat'], True, 1, 0.006)
    def cone(u, v):
        ang = u * 2 * math.pi; hgt = 0.33 * v
        r = 0.093 * (1 - v) ** 1.1 + 0.002
        bend = Vector((0, 0.06 * v ** 2.5, -0.03 * v ** 3))
        return hat_base + Vector((r * math.sin(ang), -r * 0.95 * math.cos(ang), hgt - 0.01)) + bend
    hc = grid('z_hat_cone', 64, 30, cone, M['hat'], True, 1, 0.005)
    hband = grid('z_hat_band', 96, 2, lambda u, v: hat_base + Vector((0.095 * math.sin(u * 2 * math.pi), -0.09 * math.cos(u * 2 * math.pi), 0.005 + 0.022 * v)), M['brass'], True, 1, 0.004)
    # beard: a sculpted shell from the jaw line down to the upper chest, moustache tubes
    top_cache = {}
    def beard(u, v):
        ang = math.radians(-100 + 200 * u)
        if u not in top_cache:
            z0 = C[2] - h * (0.12 + 0.56 * math.cos(ang) ** 2)
            dirv = Vector((math.sin(ang), -math.cos(ang), 0))
            p, n = surface_hit(head, Vector((C[0], C[1], z0)) + dirv * 0.5, -dirv)
            top_cache[u] = (p + n * 0.002 if p is not None else Vector((C[0], C[1], z0)) + dirv * a, n)
        top, n = top_cache[u]
        z1 = C[2] - h * 1.0 - 0.1 * math.cos(ang) ** 2
        bot = Vector((top.x * 0.3, C[1] - d * 0.8 + 0.02 * abs(math.sin(ang)), z1))
        q = top.lerp(bot, v)
        q += Vector((math.sin(ang) * 0.6, -math.cos(ang), 0)).normalized() * (0.014 * math.sin(math.pi * v) * (0.6 + 0.4 * math.cos(ang) ** 2))
        return q
    bd = grid('z_beard', 48, 24, beard, M['beard'], False, 2, 0.01)
    bds = strands('z_str_beard', beard, 240, 18, Vector((C[0], C[1] + 0.02, C[2] - h * 0.3)), M['beard'], 0.0024, 0.0009, 0.006, seed=9)
    mus = []
    for s in (-1, 1):
        p0, _ = surface_hit(head, (C[0] + s * 0.004, C[1] - 1, C[2] - h * 0.43), (0, 1, 0))
        p1, _ = surface_hit(head, (C[0] + s * 0.03, C[1] - 1, C[2] - h * 0.5), (0, 1, 0))
        p2, _ = surface_hit(head, (C[0] + s * 0.045, C[1] - 1, C[2] - h * 0.7), (0, 1, 0))
        mus.append(tube('z_moustache', [tuple(p0 + Vector((0, -0.004, 0))), tuple(p1 + Vector((0, -0.006, 0))), tuple(p2 + Vector((0, -0.006, 0)))], [0.006, 0.008, 0.004], M['beard'], 8, 6))
    # staff in the left hand: ash wood with a knot, carved fork holding an amber stone
    hand = Vector(J['hand_L'][0])
    sp = [(hand.x + 0.01, hand.y - 0.025, 0.02), (hand.x + 0.012, hand.y - 0.03, 0.6), (hand.x + 0.005, hand.y - 0.028, 1.3), (hand.x + 0.012, hand.y - 0.03, 1.78)]
    staff = tube('z_staff', sp, [0.017, 0.016, 0.017, 0.02], M['wood'], 12, 6)
    top = Vector(sp[-1])
    forks = [tube('z_fork', [tuple(top), tuple(top + Vector((0.03 * math.cos(k * 2.1), 0.03 * math.sin(k * 2.1), 0.06))), tuple(top + Vector((0.012 * math.cos(k * 2.1 + 0.6), 0.012 * math.sin(k * 2.1 + 0.6), 0.12)))], [0.012, 0.008, 0.003], M['wood'], 8, 5) for k in range(3)]
    stone = sphere('z_stone', 1, 24, 16, top + Vector((0, 0, 0.065)), (0.024, 0.024, 0.036), M['stone'], 1)
    soles = []
    for o in [head, hair, hb, hc, hband, bd, bds] + mus: parent_keep(o, rig, 'head')
    parent_keep(hood, rig, 'chest'); parent_keep(mn, rig, 'chest')
    for o in (rb, bt, pouch): parent_keep(o, rig, 'spine')
    for so, b in sleeves: parent_keep(so, rig, b)
    for o in [staff, stone] + forks: parent_keep(o, rig, 'hand_L')
    return rig

# ---------------------------------------------------------------- preview stage + export
def stage(night=False):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 900, 1600
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.62, 0.66, 0.7, 1); bg.inputs[1].default_value = 0.9
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(1.5); sun.color = (1, 0.93, 0.84)
    so = link(bpy.data.objects.new('sun', sun)); so.rotation_euler = (math.radians(58), 0, math.radians(35))
    fill = bpy.data.lights.new('fill', 'AREA'); fill.energy = 120; fill.size = 3
    fo = link(bpy.data.objects.new('fill', fill)); fo.location = (-2.5, -3, 2.2); fo.rotation_euler = (math.radians(60), 0, math.radians(-40))
    rim = bpy.data.lights.new('rim', 'AREA'); rim.energy = 160; rim.size = 2; rim.color = (0.85, 0.9, 1)
    ro = link(bpy.data.objects.new('rim', rim)); ro.location = (1.5, 3, 2.4); ro.rotation_euler = (math.radians(-60), 0, math.radians(160))
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=20)
    g = mesh_obj('ground', bm, mat('ground', '#6a6b3a', 0.95), False)
    cam = bpy.data.cameras.new('cam'); cam.lens = 50; co = link(bpy.data.objects.new('cam', cam)); sc.camera = co
    return co

def look(cam, pos, target, lens=50):
    cam.location = Vector(pos); cam.data.lens = lens
    cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()

def export(rig, path):
    bpy.ops.object.select_all(action='DESELECT')
    def sel(o):
        o.select_set(True)
        for c in o.children: sel(c)
    sel(rig); bpy.context.view_layer.objects.active = rig
    # slim for the real-time renderer: cap each mesh at about `budget` vertices with a temporary decimate
    budget, added = 9000, []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in bpy.context.selected_objects:
        if o.type != 'MESH': continue
        n = len(o.evaluated_get(dg).data.vertices)
        if n > budget:
            m = o.modifiers.new('slim', 'DECIMATE'); m.ratio = max(0.12, budget / n); added.append((o, m))
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                              export_skins=True, export_animations=False)
    for o, m in added: o.modifiers.remove(m)

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='assets/characters'); ap.add_argument('--preview', default='')
    ap.add_argument('--only', default=''); ap.add_argument('--shots', default='all'); ap.add_argument('--samples', type=int, default=48)
    A = ap.parse_args(argv)
    os.makedirs(A.out, exist_ok=True)
    reset()
    builders = {'woman': build_woman, 'wizard': build_wizard}
    rigs = {}
    for k, f in builders.items():
        if A.only and k != A.only: continue
        rigs[k] = f()
    for k, r in rigs.items():
        # export each on its own: hide others by deselecting (export uses selection)
        export(r, os.path.join(A.out, f'{k}.glb'))
    if A.preview:
        os.makedirs(A.preview, exist_ok=True)
        cam = stage(); bpy.context.scene.cycles.samples = A.samples
        if 'woman' in rigs and 'wizard' in rigs:
            rigs['wizard'].location.x = -0.45; rigs['woman'].location.x = 0.45
        shots = {
            'front': ((0, -4.6, 1.15), (0, 0, 0.95), 50), 'threeq': ((2.9, -3.5, 1.2), (0, 0, 0.95), 50),
            'side': ((4.6, 0, 1.15), (0, 0, 0.95), 50), 'back': ((0, 4.6, 1.15), (0, 0, 0.95), 50),
        }
        for k, r in rigs.items():
            hx = r.location.x
            hz = 1.6 if k == 'woman' else 1.69
            shots[f'face_{k}'] = ((hx + 0.12, -0.75, hz + 0.02), (hx, 0, hz - 0.02), 85)
        for name, (pos, tgt, lens) in shots.items():
            if A.shots != 'all' and name not in A.shots.split(','): continue
            look(cam, pos, tgt, lens)
            bpy.context.scene.render.filepath = os.path.join(A.preview, f'{name}.png')
            bpy.ops.render.render(write_still=True)
            print('rendered', name, flush=True)
