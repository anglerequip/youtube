"""v3 characters (Caesar 27 Nov: "everything is bugged ... textures, animations, clipping"): Nils and Theo rebuilt on the
Quaternius Universal Animation Library mannequin (CC0): a clean, professionally weighted body on the exact skeleton the
motion capture was recorded on, so actions play natively. Clothes are shells cut from the body itself and pushed out
along the normals: same vertex groups, same deformation, so they cannot clip through it. One matte material per piece.

  blender -b -P v3_char.py -- --who nils|theo --out <dir> [--test]    (--test renders turnaround + posed stills)
"""
import math, os, sys
import bpy, bmesh
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(n, d=None): return argv[argv.index(n) + 1] if n in argv else d
WHO = arg('--who', 'nils'); OUT = arg('--out'); os.makedirs(OUT, exist_ok=True)
VOX = 0.008
UAL = kit.asset(r'D:\CounterPhysical\assets-cc0\anim\UAL1_Standard.glb')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=UAL)
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); arm.name = WHO + '_rig'
body = next(o for o in bpy.data.objects if o.type == 'MESH'); body.name = WHO + '_body'
arm.animation_data_clear() if arm.animation_data else None
for pb in arm.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()
me = body.data
VG = {g.index: g.name for g in body.vertex_groups}

def region_of(gname):
    g = gname.lower()
    if g.startswith(('head', 'neck')): return 'head'
    if g.startswith(('hand', 'index', 'middle', 'pinky', 'ring', 'thumb')): return 'hand'
    if g.startswith(('foot', 'ball')): return 'foot'
    if g.startswith(('calf',)): return 'calf'
    if g.startswith(('thigh', 'pelvis')): return 'legs'
    if g.startswith(('lowerarm',)): return 'forearm'
    if g.startswith(('upperarm', 'clavicle')): return 'upperarm'
    return 'torso'
vreg = []
for v in me.vertices:
    best = max(v.groups, key=lambda g: g.weight, default=None)
    vreg.append(region_of(VG[best.group]) if best else 'torso')
Z = [v.co.z for v in me.vertices]
print('HEIGHT', round(max(Z) - min(Z), 3), 'min', round(min(Z), 3))

import math as _m
def sculpt_body():
    """Proportions before anything is cut from the body: Nils is stocky with a belly and a bigger head; Theo slimmer.
    Applied to the rest-pose mesh, so the weights carry it into every pose."""
    for v, r in zip(me.vertices, vreg):
        c = v.co
        if r == 'head':                                                 # bigger, friendlier heads (stylised)
            hc = Vector((0, 0.0, 1.6)); k = 1.3 if WHO == 'nils' else 1.26
            u_ = min(1.0, max(0.0, (c.z - 1.53) / 0.06))          # the head grows, the neck below the jaw does not
            if u_ > 0: v.co = hc + (c - hc) * (1 + (k - 1) * u_ * u_ * (3 - 2 * u_))
        if WHO == 'nils' and r in ('torso', 'legs'):
            g = _m.exp(-((c.z - 1.08) / 0.16) ** 2)                      # belly
            if c.y < 0.02: c.y -= 0.07 * g * (1 if c.y < -0.05 else 0.6)
            c.x *= 1 + 0.12 * g
        if WHO == 'nils' and r in ('torso', 'upperarm'):
            c.x *= 1.04
        if r == 'torso' and 1.18 < c.z < 1.48 and c.y < -0.03:     # flatten the mannequin's chest plates (both)
            c.y = -0.03 + (c.y + 0.03) * (0.6 if WHO == 'theo' else 0.75)
sculpt_body()

from mathutils.kdtree import KDTree
def make_clean():
    """One closed, smooth body surface (the mannequin is built from separate segments and joint rings, which made
    every shell lumpy and gappy): voxel remesh a copy at rest, smooth it, give it the body's weights back, and label
    each new vertex with the region of the nearest original vertex."""
    o = body.copy(); o.data = body.data.copy(); o.name = WHO + '_clean'; kit.link(o)
    for m_ in list(o.modifiers): o.modifiers.remove(m_)
    o.vertex_groups.clear()
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    r = o.modifiers.new('remesh', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = VOX
    bpy.ops.object.modifier_apply(modifier=r.name)
    sm = o.modifiers.new('smooth', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 6
    bpy.ops.object.modifier_apply(modifier=sm.name)
    ls = o.modifiers.new('lap', 'LAPLACIANSMOOTH'); ls.iterations = 40; ls.lambda_factor = 2.0; ls.use_volume_preserve = True
    bpy.ops.object.modifier_apply(modifier=ls.name)                   # the mannequin's gym muscles flatten into soft volumes
    kd = KDTree(len(me.vertices))
    for v in me.vertices: kd.insert(v.co, v.index)
    kd.balance()
    reg = [vreg[kd.find(v.co)[1]] for v in o.data.vertices]
    # region labels follow the nearest original vertex, which is noisy at borders: majority-vote them over the
    # neighbourhood so every garment edge is a clean line
    nb = [[] for _ in o.data.vertices]
    for e in o.data.edges:
        a_, b_ = e.vertices; nb[a_].append(b_); nb[b_].append(a_)
    for _ in range(8):
        new = reg[:]
        for i_, ns in enumerate(nb):
            cnt = {}
            for j_ in ns + [i_]: cnt[reg[j_]] = cnt.get(reg[j_], 0) + 1
            new[i_] = max(cnt, key=cnt.get)
        reg = new
    return o, reg
CLEAN, CREG = make_clean()

def bind(o):
    """Skin weights from the original body (nearest surface), armature on top."""
    for m_ in list(o.modifiers): o.modifiers.remove(m_)
    o.vertex_groups.clear()
    for g in body.vertex_groups: o.vertex_groups.new(name=g.name)
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    dt = o.modifiers.new('dt', 'DATA_TRANSFER'); dt.object = body; dt.use_vert_data = True
    dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.modifier_apply(modifier=dt.name)
    am = o.modifiers.new('arm', 'ARMATURE'); am.object = arm
    o.parent = arm

def shell(name, regions, off, mat, extra=None, solid=0.008, hem=True, relax=12, cuts=(), neck=False):
    """Faces of the clean body whose vertices are all in `regions` (or pass `extra`), pushed out by `off`; the cut
    border is relaxed into a smooth line and rolled into a hem, then the shell gets the body's weights."""
    o = CLEAN.copy(); o.data = CLEAN.data.copy(); o.name = name; kit.link(o)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    keep = lambda f: all(CREG[v.index] in regions for v in f.verts) or (extra and extra(f))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f)], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    # drop crumbs (islands under 40 faces) left by the region test
    seen = set(); kill = []
    for f in bm.faces:
        if f in seen: continue
        isl = []; st = [f]; seen.add(f)
        while st:
            g = st.pop(); isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h not in seen: seen.add(h); st.append(h)
        if len(isl) < 40: kill += isl
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    for (pc, pn) in cuts:                                              # straight garment edges: cut by planes, drop the outside
        g = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=g, plane_co=Vector(pc), plane_no=Vector(pn), clear_outer=True)
    if neck:                                                           # a round neck opening, cut as a cylinder round the neck
        NC = sum((v.co for v in CLEAN.data.vertices if abs(v.co.z - 1.52) < 0.01 and CREG[v.index] == 'head'), Vector())
        nn = sum(1 for v in CLEAN.data.vertices if abs(v.co.z - 1.52) < 0.01 and CREG[v.index] == 'head'); NC /= max(1, nn)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z > 1.44 and
                                   ((f.calc_center_median().x - NC.x) ** 2 + ((f.calc_center_median().y - NC.y) / 1.1) ** 2) ** 0.5 < 0.105], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    for _ in range(0 if cuts else 12):                                 # a smooth cut line, not a voxel staircase
        bnd = [v for v in bm.verts if v.is_boundary]
        bmesh.ops.smooth_vert(bm, verts=bnd, factor=0.6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    for v in bm.verts: v.co += v.normal * (off(v.co) if callable(off) else off)
    for _ in range(int(relax)):                                        # cloth drapes over muscles instead of hugging them
        bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if not v.is_boundary], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(o.data); bm.free()
    for p in o.data.polygons: p.use_smooth = True
    bind(o)
    if solid:
        s_ = o.modifiers.new('solid', 'SOLIDIFY'); s_.thickness = solid; s_.offset = -1.0; s_.use_rim = True
        o.modifiers.move(len(o.modifiers) - 1, 0)
    o.data.materials.clear(); o.data.materials.append(mat)
    return o

def collar(matname, z=1.515, k=0.09):
    """Rolled collar: a clean torus fitted round the neck (cutting the voxel surface there leaves a ragged edge)."""
    nv = [v.co for v in CLEAN.data.vertices if abs(v.co.z - z) < 0.012 and CREG[v.index] == 'head' and abs(v.co.x) < 0.11]   # the neck only
    nc = sum(nv, Vector()) / max(1, len(nv)); rx = max(abs(v.x - nc.x) for v in nv); ry = max(abs(v.y - nc.y) for v in nv)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.2, major_segments=48, minor_segments=16, location=(nc.x, nc.y, z))
    rx = 0.1; ry = 0.105
    col = bpy.context.active_object; col.name = 'collar'; col.scale = (rx + 0.022, ry + 0.022, k)
    bpy.ops.object.transform_apply(scale=True); col.data.materials.append(bpy.data.materials[matname])
    for p_ in col.data.polygons: p_.use_smooth = True
    bind(col)

WX = abs(arm.data.bones['hand_l'].head_local.x) - 0.012                     # wrist line (arms lie along x at rest)
SLEEVE_CUTS = [((WX, 0, 0), (1, 0, 0)), ((-WX, 0, 0), (-1, 0, 0))]
def cuff(matname, r=0.042, k=0.022):
    """A rolled cuff at each wrist hides the sleeve's cut edge."""
    for sg in (1, -1):
        hb = arm.data.bones['hand_l' if sg > 0 else 'hand_r']
        bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=k, major_segments=32, minor_segments=10,
                                         location=(sg * (WX - 0.005), hb.head_local.y, hb.head_local.z), rotation=(0, math.radians(90), 0))
        c_ = bpy.context.active_object; c_.name = f'cuff_{sg}'; c_.data.materials.append(bpy.data.materials[matname])
        for p_ in c_.data.polygons: p_.use_smooth = True
        bind(c_)

def M(name, hexcol, tex=None, scale=2.0, detail=0.5, bump=0.08, rough=0.85):
    if tex: return kit.tex_material(name, tex, scale=scale, flat=hexcol, detail=detail, rough_add=0.4, normal=bump)
    return kit.flat(name, hexcol, rough=rough)

if WHO == 'nils':
    SKIN = M('skin', '#d6a183', rough=0.7)
    shirt = shell('shirt', {'torso', 'upperarm', 'forearm'}, 0.028, M('shirt', '#46596e', 'Fabric016_1K-JPG', 4.0, 0.45, 0.15),
                  relax=30, cuts=SLEEVE_CUTS, neck=True)                # a roll-neck jumper (collar below)
    cuff('shirt')
    collar('shirt', 1.52, 0.13)
    BIBM = M('bib', '#6f6b2e', 'Fabric028_1K-JPG', 1.5, 0.6)
    bib = shell('bib', {'legs', 'calf'}, 0.026, BIBM, cuts=[((0, 0, 1.02), (0, 0, 1))])
    bibf = shell('bib_front', {'torso', 'legs'}, 0.075, BIBM, relax=4, solid=0,
                 cuts=[((0, 0, 1.34), (0, 0, 1)), ((0, 0, 1.0), (0, 0, -1)), ((0.155, 0, 0), (1, 0, 0)), ((-0.155, 0, 0), (-1, 0, 0)), ((0, 0.0, 0), (0, 1, 0))])
    from mathutils.bvhtree import BVHTree
    _bm = bmesh.new(); _bm.from_mesh(CLEAN.data); TREE = BVHTree.FromBMesh(_bm); _bm.free()
    def on_surface(x, z, front, out):
        o_ = Vector((x, -1.0 if front else 1.0, z)); d_ = Vector((0, 1 if front else -1, 0))
        h = TREE.ray_cast(o_, d_, 3.0)
        return (h[0] + h[1] * out) if h[0] is not None else None
    def over_top(x, out):
        h = TREE.ray_cast(Vector((x, 0.0, 1.5)), Vector((0, 0, -1)), 3.0)   # from below the head: lands on the shoulder
        return h[0] + h[1] * out
    for sg in (1, -1):                                                 # straps: clean flat bands over the shoulders
        x0 = sg * 0.1
        fr = [on_surface(x0, z, True, o_) for z, o_ in ((1.3, 0.085), (1.36, 0.05), (1.42, 0.042))]
        bk = [on_surface(x0, z, False, o_) for z, o_ in ((1.42, 0.042), (1.34, 0.042), (1.24, 0.045), (1.12, 0.05), (1.02, 0.05))]
        top = (fr[-1] + bk[0]) / 2; top.z = max(fr[-1].z, bk[0].z) + 0.045             # over the shoulder
        pts = [p_ for p_ in fr + [top] + bk if p_ is not None]
        cu = bpy.data.curves.new(f'strap_{sg}', 'CURVE'); cu.dimensions = '3D'
        sp = cu.splines.new('NURBS'); sp.points.add(len(pts) - 1)
        for k_, p_ in enumerate(pts): sp.points[k_].co = (p_.x, p_.y, p_.z, 1)
        sp.use_endpoint_u = True; sp.order_u = 3
        cu.extrude = 0.004; cu.bevel_depth = 0.0; cu.offset = 0
        prof = bpy.data.curves.new('strap_prof', 'CURVE')                # a flat band 3.5 cm wide
        cu.bevel_mode = 'OBJECT'
        po = bpy.data.objects.new('strap_prof_ob', prof); kit.link(po); prof.dimensions = '2D'
        ps = prof.splines.new('POLY'); ps.points.add(3)
        for k_, (a1, a2) in enumerate(((-0.0175, -0.003), (0.0175, -0.003), (0.0175, 0.003), (-0.0175, 0.003))): ps.points[k_].co = (a1, a2, 0, 1)
        ps.use_cyclic_u = True
        cu.bevel_object = po; cu.use_fill_caps = True
        so_ = bpy.data.objects.new(f'strap_{sg}', cu); kit.link(so_)
        bpy.context.view_layer.objects.active = so_; bpy.ops.object.select_all(action='DESELECT'); so_.select_set(True)
        bpy.ops.object.convert(target='MESH'); so_ = bpy.context.active_object
        bpy.data.objects.remove(po)
        so_.data.materials.clear(); so_.data.materials.append(BIBM); bind(so_)
        kit.box(f'buckle_{sg}', (0.04, 0.012, 0.03), tuple(pts[0] + Vector((0, -0.004, 0))), mat=kit.flat('brass_b', '#b08a3a', rough=0.5), bev=0.004)
        bind(bpy.data.objects[f'buckle_{sg}'])
    boots = shell('boots', {'foot'}, 0.018, M('boot', '#38332f', 'Rubber004_1K-JPG', 2.0, 0.4),
                  extra=lambda f: f.calc_center_median().z < 0.38)
else:
    SKIN = M('skin', '#e2b08e', rough=0.7)
    shirt = shell('jacket', {'torso', 'upperarm', 'forearm'}, 0.03, M('jacket', '#f2c230', 'Fabric035_1K-JPG', 2.0, 0.15),
                  relax=30, cuts=SLEEVE_CUTS + [((0, 0, 0.93), (0, 0, -1))], neck=True)
    cuff('jacket', 0.048, 0.024)
    collar('jacket', 1.52, 0.14)
    bib = shell('jeans', {'legs', 'calf'}, 0.012, M('jeans', '#3a5a80', 'Fabric022_1K-JPG', 2.0, 0.6))
    boots = shell('boots', {'foot'}, 0.018, M('boot', '#2f6a40', 'Rubber004_1K-JPG', 2.0, 0.3), extra=lambda f: f.calc_center_median().z < 0.3)
bpy.data.objects.remove(CLEAN)
import v3_head
HEAD = v3_head.build(WHO, arm, body, vreg)
body.data.materials.clear(); body.data.materials.append(SKIN)
# the body under the clothes is never seen: keep only head, neck and hands, so nothing can poke through
bm = bmesh.new(); bm.from_mesh(body.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(vreg[v.index] not in ('head', 'hand') for v in f.verts)], context='FACES')
bm.to_mesh(body.data); bm.free()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'{WHO}_v3.blend'))

if '--test' in argv:
    sc = bpy.context.scene; kit.eevee_quality(sc, 24); kit.output(sc, 1080, 1350, 70)
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = kit.hexc('#8a8278'); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
    kit.sun('sun', (50, 0, 30), color='#fff1e0', strength=3.0, angle=3.0)
    bpy.ops.mesh.primitive_plane_add(size=10); bpy.context.active_object.data.materials.append(kit.flat('floor', '#a09484', rough=0.9))
    KEEP = set(bpy.data.objects)
    acts = {}
    for k, (yaw, act, t) in enumerate(((0, 'Idle_Loop', 0.2), (150, 'Idle_Loop', 0.2), (90, 'Idle_Loop', 0.2), (20, 'Idle_Talking_Loop', 0.6), (20, 'Consume', 0.5), (20, 'Chest_Open', 0.6))):
        arm.rotation_mode = 'XYZ'; arm.rotation_euler = (0, 0, math.radians(yaw))
        if act:
            ac = bpy.data.actions.get(act)
            if ac is None:
                bpy.ops.import_scene.gltf(filepath=UAL.replace('UAL1', 'UAL2'))
                for o in [o for o in bpy.data.objects if o not in KEEP]: bpy.data.objects.remove(o)
                ac = bpy.data.actions[act]
            arm.animation_data_create(); arm.animation_data.action = ac
            try: arm.animation_data.action_slot = ac.slots[0]
            except Exception: pass
            sc.frame_set(int(ac.frame_range[0] + t * (ac.frame_range[1] - ac.frame_range[0])))
        else:
            if arm.animation_data: arm.animation_data.action = None
            for pb in arm.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0)
            # arms down from the T/A pose for the turnaround
            for s_, sg in (('l', 1), ('r', -1)):
                pb = arm.pose.bones['upperarm_' + s_]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, 0)
        cam = kit.camera(f'c{k}', (0, -3.6, 1.1), (0, 0, 0.95), lens=40) if k != 3 else kit.camera('cu', (0.25, -1.1, 1.62), (0, 0, 1.6), lens=50)
        sc.camera = cam; sc.render.filepath = os.path.join(OUT, f'{WHO}_t{k}.png'); bpy.ops.render.render(write_still=True)
print('V3', WHO, 'done')
