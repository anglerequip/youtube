"""Clean stylised heads for the v3 characters (imported by v3_char.py). Every feature is its own clean primitive, placed
on the head surface by ray casts and parented to the Head bone: big readable eyes with lids, brows, nose, ears, mouth
(dark inner + lips, opened by scaling), Nils's moustache and grey hair under an orange knit cap, Theo's glasses and
teal beanie. Smooth-shaded, one matte colour each: no painted patches, nothing to smear."""
import math
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import kit


def build(WHO, arm, body, vreg):
    dg = bpy.context.evaluated_depsgraph_get()
    hv = [body.data.vertices[i].co.copy() for i, r in enumerate(vreg) if r == 'head' and i < len(body.data.vertices)]
    hv = [v for v in hv if v.z > 1.5]
    zs = [v.z for v in hv]; top, bot = max(zs), min(zs)
    xs = [v.x for v in hv]; ys = [v.y for v in hv]
    C = Vector((0, (max(ys) + min(ys)) / 2, (top + bot) / 2))
    R_ = (max(xs) - min(xs)) / 2
    bm = bmesh.new(); bm.from_mesh(body.data); bvh = BVHTree.FromBMesh(bm); bm.free()

    def surf(x, z, back=False):
        """Point on the head surface at (x, z), seen from the front (-Y) or the back."""
        o = Vector((x, -1.0 if not back else 1.0, z)); d = Vector((0, 1 if not back else -1, 0))
        hit = bvh.ray_cast(o, d, 3.0)
        return hit[0] if hit[0] is not None else Vector((x, C.y - R_, z))
    def side(z, s):
        hit = bvh.ray_cast(Vector((s * 1.0, C.y, z)), Vector((-s, 0, 0)), 3.0)
        return hit[0] if hit[0] is not None else Vector((s * R_, C.y, z))

    mats = {}
    def mat(name, col, rough=0.8, emit=None):
        if name not in mats: mats[name] = kit.flat(f'{WHO}_{name}', col, rough=rough, emit=emit, emit_strength=0.4 if emit else 0.0)
        return mats[name]
    parts = []
    def sphere(name, loc, r, scale=(1, 1, 1), m=None, seg=(32, 20), rot=(0, 0, 0)):
        b = bmesh.new(); bmesh.ops.create_uvsphere(b, u_segments=seg[0], v_segments=seg[1], radius=r)
        o = kit.from_bm(f'{WHO}_{name}', b, m, smooth_angle=None)
        for p in o.data.polygons: p.use_smooth = True
        o.location = loc; o.scale = scale; o.rotation_euler = rot; parts.append(o); return o

    P = dict(nils=dict(skin='#d6a183', eye_z=0.47, eye_x=0.34, eye_r=0.17, iris='#3f6f8a', brow='#b9b4aa', brow_t=0.05,
                       nose=(0.15, 0.14, 0.17), nose_col='#cf8f72', nose_z=0.3, mouth_z=0.13, cap='#c9531c', hair='#8e8a84'),
             theo=dict(skin='#e2b08e', eye_z=0.47, eye_x=0.33, eye_r=0.175, iris='#5a3a22', brow='#4a3222', brow_t=0.03,
                       nose=(0.1, 0.1, 0.12), nose_col='#d99a80', nose_z=0.29, mouth_z=0.13, cap='#3fa7a0', hair='#5a3a22'))[WHO]
    H = top - bot
    def Z(f): return bot + f * H
    SK = mat('face_skin', P['skin'], 0.7)
    # eyes: white ball, iris, pupil, upper lid (rotated for blinks), lower lid
    for s, n in ((1, 'L'), (-1, 'R')):
        x = s * P['eye_x'] * R_; p = surf(x, Z(P['eye_z']))
        r = P['eye_r'] * R_
        c = p + Vector((0, r * 0.45, 0))
        sphere(f'eye_{n}', c, r, m=mat('eyewhite', '#f2efe8', 0.4))
        sphere(f'iris_{n}', c + Vector((0, -r * 0.82, 0)), r * 0.56, (1, 0.35, 1), mat('iris', P['iris'], 0.4))
        sphere(f'pupil_{n}', c + Vector((0, -r * 0.98, 0)), r * 0.3, (1, 0.25, 1), mat('pupil', '#141210', 0.3))
        lid = sphere(f'lid_{n}', c, r * 1.12, (1, 1, 1), SK, rot=(math.radians(-20), 0, 0))
        b = bmesh.new(); b.from_mesh(lid.data)                       # keep the upper half: a lid that rotates down to blink
        bmesh.ops.delete(b, geom=[v for v in b.verts if v.co.z < -0.15 * r * 1.12], context='VERTS'); b.to_mesh(lid.data); b.free()
        lo = sphere(f'lowlid_{n}', c, r * 1.08, (1, 1, 1), SK, rot=(math.radians(25), 0, 0))
        b = bmesh.new(); b.from_mesh(lo.data)
        bmesh.ops.delete(b, geom=[v for v in b.verts if v.co.z > -0.55 * r * 1.08], context='VERTS'); b.to_mesh(lo.data); b.free()
        # brow: a curved tapered bar
        bz = Z(P['eye_z']) + r * 1.9
        b = bmesh.new(); prev = None
        pts = [Vector((x + s * (k - 2) * r * 0.55, 0, bz + 0.25 * r * math.cos((k - 2) * 0.6))) for k in range(5)]
        for k, q in enumerate(pts):
            q.y = surf(q.x, q.z).y - 0.006
        o = sphere(f'brow_{n}', (pts[1] + pts[3]) / 2, 1.0, (r * 1.45, P['brow_t'] * R_ * 0.9, P['brow_t'] * R_ * (1.3 if WHO == 'nils' else 0.8)),
                   mat('brow', P['brow'], 0.9), rot=(0, s * math.radians(-8 if WHO == 'nils' else -4), 0))
        # ear
        e = side(Z(0.42), s)
        sphere(f'ear_{n}', e + Vector((s * 0.004, 0.01, 0)), 1.0, (0.012, 0.03, 0.045), SK)
    # nose
    nz = Z(P['nose_z']); np_ = surf(0, nz)
    sx, sy, sz = (v * R_ for v in P['nose'])
    sphere('nose', np_ + Vector((0, -sy * 0.35, 0)), 1.0, (sx, sy, sz), mat('nose', P['nose_col'], 0.65))
    sphere('nose_bridge', surf(0, nz + sz * 0.9) + Vector((0, -sy * 0.05, 0)), 1.0, (sx * 0.5, sy * 0.5, sz * 1.2), SK)
    # mouth: dark inner (scaled open by the lip sync) + two lips
    mz = Z(P['mouth_z']); mp = surf(0, mz)
    mouth = sphere('mouth', mp + Vector((0, 0.004, 0)), 1.0, (0.22 * R_, 0.03 * R_, 0.035 * R_), mat('mouth_in', '#3a1612', 0.5))
    sphere('lip_upper', mp + Vector((0, -0.002, 0.04 * R_)), 1.0, (0.24 * R_, 0.04 * R_, 0.035 * R_), mat('lip', '#b9706a', 0.6))
    sphere('lip_lower', mp + Vector((0, -0.002, -0.045 * R_)), 1.0, (0.22 * R_, 0.045 * R_, 0.04 * R_), mat('lip', '#b9706a', 0.6))
    if WHO == 'nils':                                               # moustache: two drooping lobes
        for s in (1, -1):
            sphere(f'moustache_{s}', surf(s * 0.13 * R_, mz + 0.1 * R_) + Vector((0, -0.012, 0)), 1.0,
                   (0.2 * R_, 0.07 * R_, 0.075 * R_), mat('brow', P['brow'], 0.9), rot=(0, s * math.radians(22), 0))
    CAPM = kit.tex_material(f'{WHO}_capknit', 'Fabric016_1K-JPG', scale=9.0, flat=P['cap'], detail=0.6, rough_add=0.4, normal=0.35)
    # knit ribs you can read on a phone: vertical stripes (by angle round the head) darken the colour slightly
    _nt = CAPM.node_tree; _b = _nt.nodes['Principled BSDF']; _src = _b.inputs['Base Color'].links[0].from_socket
    _tc = _nt.nodes.new('ShaderNodeTexCoord'); _sp = _nt.nodes.new('ShaderNodeSeparateXYZ'); _nt.links.new(_tc.outputs['Object'], _sp.inputs['Vector'])
    _at = _nt.nodes.new('ShaderNodeMath'); _at.operation = 'ARCTAN2'; _nt.links.new(_sp.outputs['Y'], _at.inputs[0]); _nt.links.new(_sp.outputs['X'], _at.inputs[1])
    _m1 = _nt.nodes.new('ShaderNodeMath'); _m1.operation = 'MULTIPLY'; _m1.inputs[1].default_value = 22.0; _nt.links.new(_at.outputs[0], _m1.inputs[0])
    _sn = _nt.nodes.new('ShaderNodeMath'); _sn.operation = 'SINE'; _nt.links.new(_m1.outputs[0], _sn.inputs[0])
    _mr = _nt.nodes.new('ShaderNodeMapRange'); _mr.inputs['To Min'].default_value = 0.72; _mr.inputs['To Max'].default_value = 1.0
    _nt.links.new(_sn.outputs[0], _mr.inputs['Value']); _mr.inputs['From Min'].default_value = -1.0
    _mx = _nt.nodes.new('ShaderNodeMix'); _mx.data_type = 'RGBA'; _mx.blend_type = 'MULTIPLY'; _mx.inputs['Factor'].default_value = 1.0
    _nt.links.new(_src, _mx.inputs['A']); _nt.links.new(_mr.outputs['Result'], _mx.inputs['B']); _nt.links.new(_mx.outputs['Result'], _b.inputs['Base Color'])
    def head_shell(name, keep, off, m, solid=0.01):
        """Cap and hair are cut from the head surface itself, so they fit it exactly (no forehead poking through)."""
        o = body.copy(); o.data = body.data.copy(); o.name = f'{WHO}_{name}'; kit.link(o)
        for m_ in list(o.modifiers): o.modifiers.remove(m_)
        o.vertex_groups.clear(); o.parent = None; o.matrix_world = body.matrix_world.copy()
        b = bmesh.new(); b.from_mesh(o.data)
        bmesh.ops.delete(b, geom=[f for f in b.faces if not (all(vreg[v.index] == 'head' for v in f.verts) and keep(f.calc_center_median()))], context='FACES')
        bmesh.ops.delete(b, geom=[v for v in b.verts if not v.link_faces], context='VERTS')
        for _ in range(10):
            bmesh.ops.smooth_vert(b, verts=[v for v in b.verts if v.is_boundary], factor=0.6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        b.normal_update()
        for v in b.verts: v.co += v.normal * off
        b.to_mesh(o.data); b.free()
        for p in o.data.polygons: p.use_smooth = True
        if solid:
            s_ = o.modifiers.new('solid', 'SOLIDIFY'); s_.thickness = solid; s_.offset = -1.0; s_.use_rim = True
        sd = o.modifiers.new('sub', 'SUBSURF'); sd.levels = 1; sd.render_levels = 2
        o.data.materials.clear(); o.data.materials.append(m); parts.append(o); return o
    cap_z = Z(P['eye_z']) + P['eye_r'] * R_ * 3.2                    # the cap comes down to just above the brows
    cap = head_shell('cap', lambda c: c.z > cap_z - 0.02 * max(0.0, c.y - C.y) / max(R_, 1e-3) * 3, 0.018, CAPM, 0.012)
    b = bmesh.new(); b.from_mesh(cap.data)                             # knit ribs and a little slouch at the back
    for v in b.verts:
        a = math.atan2(v.co.y - C.y, v.co.x)
        k = 1 + 0.03 * max(0.0, math.cos(a * 22)) ** 0.5
        v.co.x *= k; v.co.y = C.y + (v.co.y - C.y) * k
        if v.co.z > top - 0.03: v.co.z += 0.02; v.co.y += 0.025
    b.to_mesh(cap.data); b.free()
    # the folded band: a thicker shell just over the cap's bottom edge
    head_shell('capband', lambda c: cap_z - 0.002 < c.z < cap_z + 0.045, 0.03, CAPM, 0.02)
    if WHO == 'nils':                                                # short grey hair below the cap, sides and back only
        head_shell('hair', lambda c: c.z <= cap_z + 0.005 and c.z > Z(0.3) and c.y > C.y - 0.35 * R_, 0.006, mat('hair', P['hair'], 0.9), 0.006)
    else:
        head_shell('hair', lambda c: c.z <= cap_z + 0.005 and c.z > Z(0.33) and c.y > C.y - 0.2 * R_, 0.006, mat('hair', P['hair'], 0.9), 0.006)
    if WHO == 'theo':                                               # glasses
        for s in (1, -1):
            c = surf(s * P['eye_x'] * R_, Z(P['eye_z'])) + Vector((0, -0.02, 0))
            bpy.ops.mesh.primitive_torus_add(major_radius=P['eye_r'] * R_ * 1.55, minor_radius=0.0028, major_segments=32, minor_segments=8,
                                             location=c, rotation=(math.radians(90), 0, 0))
            g = bpy.context.active_object; g.name = f'theo_glass_{s}'; g.data.materials.append(mat('frame', '#2a2420', 0.5)); parts.append(g)
        kit.cyl('theo_bridge', 0.0025, 0.03, tuple(surf(0, Z(P['eye_z'])) + Vector((0, -0.024, 0.005))), (0, math.radians(90), 0), seg=8, mat=mat('frame', '#2a2420'), bev=0)
        parts.append(bpy.data.objects['theo_bridge'])
    # parent everything to the Head bone, keeping world placement
    hb = arm.data.bones['Head']
    for o in parts:
        mw = o.matrix_world.copy() if o.parent is None else o.matrix_world.copy()
        bpy.context.view_layer.update(); mw = o.matrix_world.copy()
        o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = 'Head'
        bpy.context.view_layer.update()
        o.matrix_world = mw
    return {o.name: o for o in parts}
