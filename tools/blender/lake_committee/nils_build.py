"""The Lake Committee: Nils Brack, editable character master, stage 1 (geometry, matching camera, clay and first-pass
materials). Brief: content/characters/nils-brack/BRIEF.md; approved design: content/characters/nils-brack/model_sheet.png.

Nils is a stylised, chunky miniature with sculpted planes. Every form is built here from scratch (no MakeHuman body):
skin and boots are unions of simple masses, voxel-remeshed into one surface, smoothed, then reduced to broad planes
(the faceted "sculpted" look of the sheet) and shaded smooth only inside a plane angle. Garments are lofted panels with
a few deliberate folds, reduced the same way. Separate objects: eyes, upper/lower lids, brows, sideburns, hair, mouth
interior, cap (crown + rolled cuff), shirt, collar, sweater neck, sleeves + cuffs, hands, bib trousers, bib, pocket,
straps, brass fittings, boots + soles, float.

Run (Blender 5.2, headless; reruns update the owned objects by name and keep anything else in the file):
  blender -b --factory-startup --python tools/blender/lake_committee/nils_build.py -- --stage1
      [--root D:\\CounterPhysical\\lake-committee] [--previews content/characters/nils-brack/previews]
Outputs:
  <root>/assets/characters/nils_brack/v001/Nils_Brack.blend     collection "Nils_Brack" (asset-marked), objects NB_*
  <previews>/nils_v001_*.jpg                                     match, turnaround, portrait, thumbnail test
Coordinates: metres, z up, Nils stands at the origin facing -Y; his anatomical left is +X (the float side).
"""
import bpy, bmesh, math, os, sys, json, random, argparse
from mathutils import Vector, Matrix, Euler, noise

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SHEET = os.path.join(REPO, 'content', 'characters', 'nils-brack', 'model_sheet.png')
H = 1.70                                  # cap top above the ground

# Landmarks measured on the model sheet (pixels, 1024 x 1536; ground 1440, cap top 52), and the model's own heights
SHEET_GUIDES = {'cap rim': 90, 'eyes': 130, 'chin': 262, 'collar': 300, 'bib top': 455, 'fingertips': 962,
                'boot tops': 1180, 'ground': 1440}
COL = {'skin': '#c98f6e', 'knit': '#b5521f', 'shirt': '#2e3a44', 'bib': '#5d6332', 'strap': '#4a2d1c',
       'brass': '#b08a45', 'boot': '#2b2a27', 'sole': '#1c1b19', 'hair': '#8d8f8c', 'sweater': '#6b4a2e',
       'red': '#b8241c', 'ivory': '#e6dcc2', 'eye': '#ece6da', 'iris': '#4a3a2a', 'mouth': '#3a1a16'}


# ------------------------------------------------------------------------------------------------------------- utils
def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def smooth01(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def V(*a):
    return Vector(a)


def coll():
    c = bpy.data.collections.get('Nils_Brack')
    if not c:
        c = bpy.data.collections.new('Nils_Brack'); bpy.context.scene.collection.children.link(c)
    return c


def new_obj(name, bm, mat=None, smooth=False):
    """Create or replace the owned object `name` (stable name, reruns update it)."""
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth
    o = bpy.data.objects.new(name, me); coll().objects.link(o)
    if mat: me.materials.append(mat)
    return o


def ellipsoid(bm, c, r, seg=(32, 20), rot=(0, 0, 0)):
    M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*r, 1))
    bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=1.0, matrix=M)


def capsule(bm, a, b, r, seg=20):
    a, b = Vector(a), Vector(b); d = b - a
    q = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length,
                          matrix=Matrix.Translation((a + b) / 2) @ q)
    for p in (a, b):
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg // 2), radius=r, matrix=Matrix.Translation(p))


def tcapsule(bm, a, b, ra, rb, seg=24):
    """Capsule whose radius tapers from ra at a to rb at b."""
    a, b = Vector(a), Vector(b); d = b - a
    q = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=ra, radius2=rb, depth=d.length, matrix=Matrix.Translation((a + b) / 2) @ q)
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg // 2), radius=ra, matrix=Matrix.Translation(a))
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg // 2), radius=rb, matrix=Matrix.Translation(b))


def garment(o, faces, folds, voxel=0.008, angle=22, bevel=0.003):
    """Closed garment volume -> one surface (voxel remesh), large compressed folds pushed in while dense, then
    reduced to broad facets with crisp-but-soft edges (the sheet's faceted cloth)."""
    m = o.modifiers.new('rm', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = voxel
    sm = o.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.6; sm.iterations = 6
    apply_mods(o)
    for f in folds: fold_noise(o, *f[:3], mask=f[3] if len(f) > 3 else None)
    d = o.modifiers.new('dc', 'DECIMATE'); d.decimate_type = 'COLLAPSE'
    d.ratio = min(1.0, faces / max(1, len(o.data.polygons))); d.use_collapse_triangulate = True
    apply_mods(o)
    facet(o, angle, bevel)
    return o


def rbox(bm, c, half, rot=(0, 0, 0), bevel=0.01):
    tmp = bmesh.new(); bmesh.ops.create_cube(tmp, size=1.0)
    for v in tmp.verts: v.co = Vector((v.co.x * 2 * half[0], v.co.y * 2 * half[1], v.co.z * 2 * half[2]))
    if bevel: bmesh.ops.bevel(tmp, geom=list(tmp.edges), offset=bevel, segments=3, affect='EDGES', profile=0.5)
    M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4()
    for v in tmp.verts: v.co = M @ v.co
    me = bpy.data.meshes.new('_t'); tmp.to_mesh(me); tmp.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)


def hull(bm, pts):
    tmp = bmesh.new(); vs = [tmp.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(tmp, input=vs)
    me = bpy.data.meshes.new('_t'); tmp.to_mesh(me); tmp.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)


def loft(rings, cap0=False, cap1=False):
    """Closed rings (lists of Vectors, equal count) -> bmesh tube."""
    bm = bmesh.new(); R = [[bm.verts.new(p) for p in ring] for ring in rings]; n = len(rings[0])
    for a, b in zip(R, R[1:]):
        for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    if cap0: bm.faces.new(list(reversed(R[0])))
    if cap1: bm.faces.new(R[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def ring(c, rx, ry, n, z=None, rot=0.0, front_flat=0.0):
    c = Vector(c); pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = math.cos(a) * rx, math.sin(a) * ry
        if front_flat and y < 0: y *= (1 - front_flat)
        xr = x * math.cos(rot) - y * math.sin(rot); yr = x * math.sin(rot) + y * math.cos(rot)
        pts.append(Vector((c.x + xr, c.y + yr, c.z if z is None else z)))
    return pts


def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for x in bpy.context.view_layer.objects: x.select_set(False)
    o.select_set(True)
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def sculpt(o, voxel=0.004, smooth_iter=8, smooth_fac=0.6, ratio=None, faces=None, angle=34, bevel=0.0):
    """Union the masses into one surface (voxel remesh), soften, then reduce to broad planes and shade smooth only
    within a plane angle: the faceted miniature look of the sheet."""
    m = o.modifiers.new('rm', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = voxel; m.use_smooth_shade = True
    s = o.modifiers.new('sm', 'SMOOTH'); s.factor = smooth_fac; s.iterations = smooth_iter
    apply_mods(o)
    if faces or ratio:
        r = ratio or min(1.0, faces / max(1, len(o.data.polygons)))
        d = o.modifiers.new('dc', 'DECIMATE'); d.decimate_type = 'COLLAPSE'; d.ratio = r; d.use_collapse_triangulate = True
        apply_mods(o)
    facet(o, angle, bevel)
    return o


def facet(o, angle=34, bevel=0.0):
    me = o.data
    for p in me.polygons: p.use_smooth = True
    try: me.set_sharp_from_angle(angle=math.radians(angle))
    except Exception: pass
    if bevel:
        b = o.modifiers.new('edge', 'BEVEL'); b.width = bevel; b.segments = 2; b.limit_method = 'ANGLE'
        b.angle_limit = math.radians(angle); b.harden_normals = False


def cloth(o, faces, angle=26, bevel=0.003, folds=None):
    """Open garment panels: subdivide (smooth form), add the chosen folds, then reduce to broad facets."""
    sd = o.modifiers.new('sd', 'SUBSURF'); sd.levels = 3; sd.render_levels = 3
    apply_mods(o)
    for f in (folds or []): fold_noise(o, *f[:3], mask=f[3] if len(f) > 3 else None)
    d = o.modifiers.new('dc', 'DECIMATE'); d.decimate_type = 'COLLAPSE'
    d.ratio = min(1.0, faces / max(1, len(o.data.polygons))); d.use_collapse_triangulate = True
    apply_mods(o)
    facet(o, angle, bevel)
    return o


def fold_noise(o, amp, scale, seed=0, mask=None, ridge=True):
    """Displace along normals with low-frequency noise: compressed garment folds."""
    me = o.data; me.update()
    for v in me.vertices:
        p = o.matrix_world @ v.co
        k = mask(p) if mask else 1.0
        if k <= 0: continue
        n = noise.noise(p * scale + Vector((seed * 3.1, seed * 1.7, seed * 2.3)))
        n = 1.0 - 2.0 * abs(n) if ridge else n            # ridged: sharp creases between broad planes
        v.co += v.normal * amp * n * k
    me.update()


# --------------------------------------------------------------------------------------------------------- materials
def mat(name, color, rough=0.6, metal=0.0, sss=0.0, coat=0.0, sheen=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        if n.type not in ('OUTPUT_MATERIAL',): nt.nodes.remove(n)
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(b.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    b.inputs['Base Color'].default_value = (*lin(color), 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if sss: b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = (1.0, 0.4, 0.2); b.inputs['Subsurface Scale'].default_value = 0.01
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.3
    if sheen: b.inputs['Sheen Weight'].default_value = sheen; b.inputs['Sheen Roughness'].default_value = 0.5
    m['nb_base'] = color
    return m


def _rest_coord(N, L):
    """Object coordinates (the build places every object at the origin, so these are rest-space metres)."""
    tc = N.new('ShaderNodeTexCoord'); return tc.outputs['Object']


def proc(m, *, noise_amt=0.0, noise_scale=8.0, grime=None, rib=None, weave=None, wear=0.0, bump_noise=0.0):
    """First-pass procedural surfacing (Blender shader nodes; bakeable later):
    noise_amt  large soft colour variation; grime (height_m, colour): dirt rising from the ground;
    rib (period_m, depth, axis) knit ribs; weave (period_m, depth) canvas grid; wear: lighter rubbed high points
    from AO; bump_noise: fine surface relief."""
    N = m.node_tree.nodes; L = m.node_tree.links; b = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    co = _rest_coord(N, L)
    col = None
    base = b.inputs['Base Color'].default_value[:]

    def rgb(c):
        n = N.new('ShaderNodeRGB'); n.outputs[0].default_value = c; return n.outputs[0]
    col = rgb(base)
    if noise_amt:
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = noise_scale; nz.inputs['Detail'].default_value = 4
        L.new(co, nz.inputs['Vector'])
        mr = N.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 1 - noise_amt; mr.inputs['To Max'].default_value = 1 + noise_amt
        L.new(nz.outputs['Fac'], mr.inputs['Value'])
        mm = N.new('ShaderNodeMix'); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'; mm.inputs['Factor'].default_value = 1
        cc = N.new('ShaderNodeCombineColor')
        for k in range(3): L.new(mr.outputs[0], cc.inputs[k])
        L.new(col, mm.inputs[6]); L.new(cc.outputs[0], mm.inputs[7]); col = mm.outputs[2]
    if wear:
        ao = N.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.03; ao.only_local = True
        mm = N.new('ShaderNodeMix'); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'
        ar = N.new('ShaderNodeMapRange'); ar.inputs['To Min'].default_value = 1 - wear; ar.inputs['To Max'].default_value = 1 + wear * 0.6
        L.new(ao.outputs['AO'], ar.inputs['Value']); cc = N.new('ShaderNodeCombineColor')
        for k in range(3): L.new(ar.outputs[0], cc.inputs[k])
        mm.inputs['Factor'].default_value = 1; L.new(col, mm.inputs[6]); L.new(cc.outputs[0], mm.inputs[7]); col = mm.outputs[2]
    if grime:
        sep = N.new('ShaderNodeSeparateXYZ'); L.new(co, sep.inputs['Vector'])
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 14; nz.inputs['Detail'].default_value = 6
        L.new(co, nz.inputs['Vector'])
        hz = N.new('ShaderNodeMath'); hz.operation = 'MULTIPLY_ADD'; hz.inputs[1].default_value = 0.15
        L.new(nz.outputs['Fac'], hz.inputs[0]); L.new(sep.outputs['Z'], hz.inputs[2])
        mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = grime[0]; mr.inputs['From Max'].default_value = grime[0] * 0.3
        L.new(hz.outputs[0], mr.inputs['Value'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = (*lin(grime[1]), 1)
        f = N.new('ShaderNodeMath'); f.operation = 'MULTIPLY'; f.inputs[1].default_value = 0.85
        L.new(mr.outputs[0], f.inputs[0]); L.new(f.outputs[0], mx.inputs['Factor']); L.new(col, mx.inputs[6]); col = mx.outputs[2]
    L.new(col, b.inputs['Base Color'])
    heights = []

    def wave(period, axis):
        w = N.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = axis
        w.inputs['Scale'].default_value = 2 * math.pi / (10 * period); w.inputs['Distortion'].default_value = 0.4
        L.new(co, w.inputs['Vector']); return w.outputs['Fac']
    if rib:
        heights.append((wave(rib[0], rib[2]), rib[1]))
    if weave:
        mu = N.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'
        L.new(wave(weave[0], 'X'), mu.inputs[0]); L.new(wave(weave[0], 'Z'), mu.inputs[1]); heights.append((mu.outputs[0], weave[1]))
    if bump_noise:
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 120; nz.inputs['Detail'].default_value = 8
        L.new(co, nz.inputs['Vector']); heights.append((nz.outputs['Fac'], bump_noise))
    for h, depth in heights:
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 1.0; bp.inputs['Distance'].default_value = depth
        L.new(h, bp.inputs['Height'])
        if b.inputs['Normal'].is_linked: L.new(b.inputs['Normal'].links[0].from_socket, bp.inputs['Normal'])
        L.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def materials():
    M = {}
    M['skin'] = proc(mat('NB_skin', COL['skin'], 0.55, sss=0.25), noise_amt=0.08, noise_scale=20, bump_noise=0.0004)
    M['knit'] = proc(mat('NB_knit', COL['knit'], 0.85, sheen=0.4), noise_amt=0.07, rib=(0.006, 0.0012, 'X'))
    M['shirt'] = proc(mat('NB_shirt', COL['shirt'], 0.55, sheen=0.15), noise_amt=0.12, noise_scale=6, weave=(0.0016, 0.0002), wear=0.35)
    M['bib'] = proc(mat('NB_oilskin', COL['bib'], 0.48, coat=0.12), noise_amt=0.16, noise_scale=5, grime=(0.55, '#4a3b26'), wear=0.4,
                    bump_noise=0.0006)
    M['strap'] = proc(mat('NB_leather', COL['strap'], 0.5, coat=0.1), noise_amt=0.12, wear=0.4)
    M['brass'] = mat('NB_brass', COL['brass'], 0.3, metal=1.0)
    M['boot'] = proc(mat('NB_rubber', COL['boot'], 0.42, coat=0.2), noise_amt=0.1, grime=(0.18, '#4a3a28'), bump_noise=0.0005)
    M['sole'] = mat('NB_sole', COL['sole'], 0.8)
    M['hair'] = proc(mat('NB_hair', COL['hair'], 0.65, sheen=0.3), noise_amt=0.12, noise_scale=40, rib=(0.0025, 0.0008, 'Z'))
    M['sweater'] = proc(mat('NB_sweater', COL['sweater'], 0.9, sheen=0.4), noise_amt=0.1, rib=(0.004, 0.0008, 'X'))
    M['red'] = mat('NB_float_red', COL['red'], 0.3, coat=0.5)
    M['ivory'] = mat('NB_float_ivory', COL['ivory'], 0.4, coat=0.3)
    M['eye'] = eye_mat()
    M['mouth'] = mat('NB_mouth', COL['mouth'], 0.6)
    M['clay'] = mat('NB_clay', '#9a9690', 0.62)
    return M


def eye_mat():
    """Sclera with a painted iris and pupil facing local -Y (the eyeball looks along -Y)."""
    m = mat('NB_eye', COL['eye'], 0.15, coat=0.6)
    N = m.node_tree.nodes; L = m.node_tree.links; b = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs['Vector'])
    # angle from the -Y axis: use the XZ radius on the front half
    vm = N.new('ShaderNodeVectorMath'); vm.operation = 'MULTIPLY'; vm.inputs[1].default_value = (1, 0, 1)
    L.new(tc.outputs['Object'], vm.inputs[0]); ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; L.new(vm.outputs[0], ln.inputs[0])
    rr = N.new('ShaderNodeValToRGB'); E = rr.color_ramp.elements
    E[0].position = 0.0; E[0].color = (0.01, 0.008, 0.006, 1)
    E[1].position = 0.0042; E[1].color = (*lin(COL['iris']), 1)
    e = E.new(0.0078); e.color = (*lin('#6a5038'), 1)
    e = E.new(0.0086); e.color = (*lin(COL['eye']), 1)
    L.new(ln.outputs['Value'], rr.inputs['Fac'])
    front = N.new('ShaderNodeMath'); front.operation = 'LESS_THAN'; front.inputs[1].default_value = 0.0
    L.new(sep.outputs['Y'], front.inputs[0])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = (*lin(COL['eye']), 1)
    L.new(front.outputs[0], mx.inputs['Factor']); L.new(rr.outputs['Color'], mx.inputs[7])
    L.new(mx.outputs[2], b.inputs['Base Color'])
    return m


# --------------------------------------------------------------------------------------------------------- the build
HEAD_PIVOT = V(0, 0.02, 1.44)              # neck pivot: the head tips up and turns around this
HEAD_TILT = math.radians(-7)               # chin up (rotation about X; negative lifts the face)
HEAD_TURN = math.radians(14)               # toward his left (+Z rotation turns the face toward +X)


def head_xf(p):
    """Rest-space head point -> posed (tipped up, turned) position."""
    R = Matrix.Rotation(HEAD_TURN, 4, 'Z') @ Matrix.Rotation(HEAD_TILT, 4, 'X') @ Matrix.Scale(HEAD_SCALE, 4)
    return HEAD_PIVOT + (R @ (Vector(p) - HEAD_PIVOT).to_4d()).to_3d()


HEAD_SCALE = 1.1


def place_head(o):
    """Head objects are modelled upright, then scaled, tipped and turned as one piece around the neck pivot."""
    R = Matrix.Translation(HEAD_PIVOT) @ Matrix.Rotation(HEAD_TURN, 4, 'Z') @ Matrix.Rotation(HEAD_TILT, 4, 'X') @ Matrix.Scale(HEAD_SCALE, 4) @ Matrix.Translation(-HEAD_PIVOT)
    o.data.transform(R); o.data.update()


def build_head(M):
    """Skull, face planes, wedge nose, square chin, cheekbones, ears and neck as one sculpted surface."""
    bm = bmesh.new()
    ellipsoid(bm, (0, 0.012, 1.598), (0.094, 0.108, 0.098), (40, 28))             # cranium
    ellipsoid(bm, (0, -0.03, 1.52), (0.088, 0.078, 0.086), (36, 24))              # face mass / cheeks
    rbox(bm, (0, -0.055, 1.468), (0.064, 0.05, 0.032), bevel=0.018)                # square chin and jaw shelf
    rbox(bm, (0, -0.02, 1.488), (0.083, 0.06, 0.03), bevel=0.02)                   # jaw corners
    for s in (-1, 1):
        ellipsoid(bm, (s * 0.06, -0.068, 1.565), (0.032, 0.028, 0.022), (24, 16))  # cheekbones
        ellipsoid(bm, (s * 0.1, 0.022, 1.575), (0.014, 0.03, 0.04), (20, 14))      # ears
        ellipsoid(bm, (s * 0.048, -0.093, 1.628), (0.03, 0.02, 0.016), (20, 12))  # brow bone (under the hair)
    capsule(bm, (0, 0.02, 1.36), (0, 0.015, 1.47), 0.068, 28)                      # neck
    hull(bm, [V(-0.013, -0.098, 1.625), V(0.013, -0.098, 1.625),                   # wedge nose: bridge,
              V(-0.016, -0.192, 1.538), V(0.016, -0.192, 1.538),                   # long forward tip,
              V(-0.008, -0.172, 1.522), V(0.008, -0.172, 1.522),                   # abrupt underside,
              V(-0.028, -0.106, 1.522), V(0.028, -0.106, 1.522),                   # nostril wings
              V(-0.03, -0.098, 1.555), V(0.03, -0.098, 1.555)])
    capsule(bm, (-0.03, -0.106, 1.5065), (0.03, -0.106, 1.5065), 0.0075, 16)      # upper lip (overhang)
    capsule(bm, (-0.024, -0.1, 1.4955), (0.024, -0.1, 1.4955), 0.0068, 16)        # lower lip
    o = new_obj('NB_head', bm, M['skin'])
    sculpt(o, voxel=0.0028, smooth_iter=6, smooth_fac=0.55, faces=9000, angle=30)
    place_head(o)
    return o


def build_face_parts(M):
    objs = []
    for s, name in ((1, 'L'), (-1, 'R')):
        c = V(s * 0.04, -0.084, 1.604)
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=28, radius=0.0145, matrix=Matrix.Translation(c))
        e = new_obj('NB_eye_' + name, bm, M['eye'], True); place_head(e); objs.append(e)
        # upper lid: a thick shell over the top 55 % of the eye, its edge a little below centre (half-lidded)
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=28, radius=0.0162, matrix=Matrix.Translation(c))
        cut = c + V(0, 0, -0.0035 if s > 0 else -0.0045)       # asymmetric: his left lid a touch more open
        kill = [v for v in bm.verts if v.co.z < cut.z + 0.004 * (v.co.y - c.y) / 0.016 or v.co.y > c.y + 0.006]
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        lid = new_obj('NB_lid_upper_' + name, bm, M['skin'], True)
        so = lid.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.0026; so.offset = 1.0
        apply_mods(lid); place_head(lid); objs.append(lid)
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=28, radius=0.0158, matrix=Matrix.Translation(c))
        kill = [v for v in bm.verts if v.co.z > c.z - 0.0085 or v.co.y > c.y + 0.004]
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        lo = new_obj('NB_lid_lower_' + name, bm, M['skin'], True)
        so = lo.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.002; so.offset = 1.0
        apply_mods(lo); place_head(lo); objs.append(lo)
    # brows: angular grey masses with an underside; built asymmetric (his right lower and heavier, his left higher
    # at the outer end and set a little further forward), never mirrored
    brows = {'L': dict(inner=V(0.014, -0.106, 1.624), outer=V(0.074, -0.082, 1.646), h=0.02, d=0.024, fwd=-0.006),
             'R': dict(inner=V(-0.014, -0.105, 1.62), outer=V(-0.074, -0.083, 1.634), h=0.022, d=0.022, fwd=0.0)}
    for name, B in brows.items():
        a, b = B['inner'] + V(0, B['fwd'], 0), B['outer'] + V(0, B['fwd'], 0)
        pts = []
        for p, hk in ((a, 1.0), (a.lerp(b, 0.5) + V(0, -0.004, 0.006), 1.05), (b, 0.7)):
            for dz in (-0.45, 0.55):
                for dy in (0.0, 1.0):
                    pts.append(p + V(0, dy * B['d'] - 0.004, dz * B['h'] * hk - (0.004 if dy and dz > 0 else 0)))
        bm = bmesh.new(); hull(bm, pts)
        br = new_obj('NB_brow_' + name, bm, M['hair'])
        r = br.modifiers.new('r', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = 0.0018
        apply_mods(br)
        d = br.modifiers.new('d', 'DECIMATE'); d.ratio = 0.12; apply_mods(br)
        facet(br, 28); place_head(br); objs.append(br)
    # squared grey sideburns and the hair band under the cap
    for s, name in ((1, 'L'), (-1, 'R')):
        bm = bmesh.new()
        hull(bm, [V(s * 0.087, -0.032, 1.648), V(s * 0.087, 0.018, 1.648), V(s * 0.081, -0.03, 1.548), V(s * 0.083, 0.004, 1.548),
                  V(s * 0.101, -0.03, 1.646), V(s * 0.103, 0.016, 1.646), V(s * 0.095, -0.028, 1.55), V(s * 0.097, 0.002, 1.55)])
        sb = new_obj('NB_sideburn_' + name, bm, M['hair']); facet(sb, 25, 0.0015); place_head(sb); objs.append(sb)
    bm = bmesh.new()
    pts = []
    for k in range(25):
        a = math.radians(-70 + k * (320 / 24))                     # round the back, open at the face
        for z, r in ((1.665, 0.104), (1.605, 0.104), (1.57, 0.096)):
            pts.append(V(math.sin(a) * r, 0.012 + math.cos(a) * r * 1.05, z))
    rings = [[pts[k * 3 + j] for k in range(25)] for j in range(3)]
    bm2 = bmesh.new(); R = [[bm2.verts.new(p) for p in rr] for rr in rings]
    for A_, B_ in zip(R, R[1:]):
        for i in range(24): bm2.faces.new((A_[i], A_[i + 1], B_[i + 1], B_[i]))
    hb = new_obj('NB_hair_back', bm2, M['hair'], True)
    so = hb.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.01; so.offset = 1; apply_mods(hb); place_head(hb); objs.append(hb)
    # mouth: a dark seam between the lips and a simple interior behind it
    bm = bmesh.new(); rbox(bm, (0, -0.103, 1.5008), (0.026, 0.006, 0.0012), bevel=0.0008)
    ml = new_obj('NB_mouth_line', bm, M['mouth']); place_head(ml); objs.append(ml)
    bm = bmesh.new(); ellipsoid(bm, (0, -0.075, 1.498), (0.026, 0.022, 0.014), (24, 14))
    mi = new_obj('NB_mouth_interior', bm, M['mouth'], True); place_head(mi); objs.append(mi)
    return objs


def build_cap(M):
    """Copper rib-knit cap: a clean crown sitting low on the skull with a few large compressed folds, and a
    distinct rolled cuff whose ribs turn with it."""
    rings = []
    n = 96
    for k, (z, r, dy) in enumerate(((1.648, 1.0, 0.0), (1.67, 1.005, 0.0), (1.692, 0.97, 0.004), (1.716, 0.87, 0.008),
                                     (1.733, 0.7, 0.012), (1.74, 0.46, 0.014), (1.743, 0.2, 0.015))):
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            rx, ry = 0.106 * r, 0.12 * r
            rib = 0.0016 * math.cos(a * 40) * (1 - k / 7)
            fold = 0.004 * math.sin(a * 3 + 1.0) * (k / 6)
            pts.append(V(math.sin(a) * (rx + rib + fold), 0.014 + dy - math.cos(a) * (ry + rib + fold), z - 0.008 * math.cos(a)))
        rings.append(pts)
    bm = loft(rings, cap1=True)
    crown = new_obj('NB_cap_crown', bm, M['knit'], True)
    sub = crown.modifiers.new('s', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
    place_head(crown)
    # rolled cuff: a thick roll (a tube swept round the rim), ribs running across the roll
    rings = []
    m = 20
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        cx, cy = math.sin(a) * 0.113, 0.014 - math.cos(a) * 0.127
        cz = 1.646 - 0.008 * math.cos(a)
        out = V(math.sin(a), -math.cos(a), 0)
        rib = 0.0018 * math.cos(a * 70)
        rr = []
        for j in range(m):
            t = 2 * math.pi * j / m
            w = 0.017 + rib
            rr.append(V(cx, cy, cz) + out * (w * 0.75 * math.cos(t)) + V(0, 0, (w * math.sin(t))))
        rings.append(rr)
    bm = bmesh.new(); R = [[bm.verts.new(p) for p in rr] for rr in rings[:-1]]
    for i in range(n):
        A_, B_ = R[i], R[(i + 1) % n]
        for j in range(m): bm.faces.new((A_[j], A_[(j + 1) % m], B_[(j + 1) % m], B_[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cuff = new_obj('NB_cap_cuff', bm, M['knit'], True)
    sub = cuff.modifiers.new('s', 'SUBSURF'); sub.levels = 1; sub.render_levels = 1
    place_head(cuff)
    return [crown, cuff]


def build_shirt(M):
    """Charcoal-blue work shirt: torso, collar with a little air under its flap, sleeves with three primary folds
    (back of shoulder, inside elbow, above the turned cuff), and the brown sweater neckline."""
    bm = bmesh.new()
    ellipsoid(bm, (0, 0.0, 1.12), (0.215, 0.17, 0.16), (40, 24))           # chest and belly under the bib
    ellipsoid(bm, (0, 0.008, 1.3), (0.24, 0.165, 0.11), (40, 24))           # upper chest
    capsule(bm, (-0.16, 0.01, 1.37), (0.16, 0.01, 1.37), 0.085, 24)         # sloping shoulder line / traps
    sleeves = []
    paths = {}
    for s_ in (1, -1):
        path = [V(s_ * 0.2, 0.01, 1.36), V(s_ * 0.285, 0.015, 1.3), V(s_ * 0.322, 0.03, 1.15), V(s_ * 0.335, 0.03, 1.04),
                V(s_ * 0.342, -0.005, 0.95), V(s_ * 0.345, -0.035, 0.9)]
        radii = [0.1, 0.118, 0.112, 0.104, 0.097, 0.092]
        for k in range(len(path) - 1): tcapsule(bm, path[k], path[k + 1], radii[k], radii[k + 1], 24)
        paths[s_] = path
    torso = new_obj('NB_shirt', bm, M['shirt'])
    els = [paths[1][3], paths[-1][3]]
    garment(torso, 700, [(0.022, 5.5, 1), (0.02, 9.0, 4, lambda p: max(smooth01(1 - (p - e).length / 0.13) for e in els))], voxel=0.007)
    for s_, name in ((1, 'L'), (-1, 'R')):
        path = paths[s_]
        # the turned cuff: a broad band with a fold edge
        c = path[-1] + (path[-1] - path[-2]).normalized() * 0.006
        d = (path[-1] - path[-2]).normalized(); q = d.to_track_quat('Z', 'Y')
        rings = []
        for t, r in ((-0.05, 0.1), (-0.012, 0.104), (0.01, 0.1), (0.016, 0.088)):
            rings.append([c + q @ V(math.cos(2 * math.pi * i / 20) * r, math.sin(2 * math.pi * i / 20) * r * 0.92, t) for i in range(20)])
        bm = loft(rings)
        cf = new_obj('NB_cuff_' + name, bm, M['shirt']); facet(cf, 30, 0.002); sleeves.append(cf)
    # collar: two flaps that stand around the neck and turn out, with air under the points
    rings = []
    n = 40
    for z, r, out in ((1.4, 0.104, 0.0), (1.442, 0.11, 0.0), (1.455, 0.13, 0.02), (1.43, 0.16, 0.045)):
        pts = []
        for i in range(n):
            a = -math.pi * 0.86 + (2 * math.pi * 0.86) * i / (n - 1)           # open at the front
            rr = r + out * (0.6 + 0.4 * math.cos(a)) + (0.012 if abs(a) > 2.2 and out else 0)
            pts.append(V(math.sin(a) * rr, 0.02 - math.cos(a) * rr * 0.9 + 0.0, z - (0.03 if abs(a) > 2.3 and out else 0)))
        rings.append(pts)
    bm = bmesh.new(); R = [[bm.verts.new(p) for p in rr] for rr in rings]
    for A_, B_ in zip(R, R[1:]):
        for i in range(n - 1): bm.faces.new((A_[i], A_[i + 1], B_[i + 1], B_[i]))
    col_ = new_obj('NB_collar', bm, M['shirt'])
    so = col_.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.006; so.offset = 1; apply_mods(col_); facet(col_, 30, 0.002)
    # sweater neckline (brown knit) under the collar
    bm = loft([ring((0, 0.02, 0), 0.09, 0.083, 40, z=1.39), ring((0, 0.02, 0), 0.084, 0.078, 40, z=1.43)])
    sw = new_obj('NB_sweater_neck', bm, M['sweater'], True)
    so = sw.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.01; so.offset = 1; apply_mods(sw)
    return [torso, col_, sw] + sleeves


def build_hands(M):
    """Heavy relaxed hands: narrower wrist than palm, the fingers one relaxed group curling forward, knuckles
    turning the light, a clear gap between thumb and forefinger."""
    out = []
    for s, name in ((1, 'L'), (-1, 'R')):
        bm = bmesh.new()
        w = V(s * 0.338, -0.05, 0.875)                                   # wrist (inside the cuff)
        capsule(bm, w + V(0, 0, 0.04), w + V(0, -0.004, -0.02), 0.032, 20)  # wrist
        pc = w + V(s * 0.003, -0.012, -0.07)                            # palm centre
        rbox(bm, pc, (0.026, 0.054, 0.052), rot=(math.radians(8), 0, math.radians(s * -6)), bevel=0.018)
        for k in range(4):                                               # fingers: index (front) .. little (back)
            y0 = pc.y - 0.034 + k * 0.022
            base = V(pc.x + s * 0.002, y0, pc.z - 0.048)
            L1 = (0.046, 0.05, 0.046, 0.038)[k]; L2 = (0.036, 0.039, 0.036, 0.03)[k]
            curl = math.radians(30 + 8 * k)
            mid = base + V(-s * math.sin(curl) * L1 * 0.45, -0.004, -math.cos(curl * 0.45) * L1)
            tip = mid + V(-s * math.sin(curl * 1.9) * L2, -0.003, -math.cos(curl * 1.9) * L2)
            r = (0.0148, 0.0152, 0.0145, 0.0125)[k]
            capsule(bm, base, mid, r, 14); capsule(bm, mid, tip, r * 0.93, 14)
        tb = pc + V(-s * 0.008, -0.05, 0.01)                            # thumb in front, apart from the forefinger
        tm = tb + V(-s * 0.012, -0.02, -0.035); tt = tm + V(-s * 0.012, -0.008, -0.026)
        capsule(bm, tb, tm, 0.017, 14); capsule(bm, tm, tt, 0.015, 14)
        o = new_obj('NB_hand_' + name, bm, M['skin'])
        sculpt(o, voxel=0.0022, smooth_iter=5, smooth_fac=0.5, faces=5000, angle=32)
        out.append(o)
    return out


def build_bib(M):
    """Olive oilskin bib trousers: roomy seat and belly, baggy legs going into the boots, the bib panel with edge
    thickness, a broad front pocket with a flap, a waist seam."""
    bm = bmesh.new()
    ellipsoid(bm, (0, 0.0, 0.93), (0.268, 0.228, 0.2), (40, 26))             # belly and seat, roomy
    ellipsoid(bm, (0, 0.012, 1.1), (0.232, 0.2, 0.09), (40, 20))             # high waist under the bib
    hull(bm, [V(-0.17, -0.235, 0.98), V(0.17, -0.235, 0.98), V(-0.145, -0.205, 1.21), V(0.145, -0.205, 1.21),
              V(-0.17, -0.05, 0.98), V(0.17, -0.05, 1.0), V(-0.145, -0.08, 1.21), V(0.145, -0.08, 1.21)])  # bib front
    for s_ in (1, -1):
        tcapsule(bm, (s_ * 0.12, 0.0, 0.82), (s_ * 0.132, -0.01, 0.5), 0.152, 0.146, 24)   # thigh to a baggy knee
        tcapsule(bm, (s_ * 0.132, -0.01, 0.5), (s_ * 0.142, -0.015, 0.3), 0.146, 0.106, 24)  # into the boot
    trousers = new_obj('NB_bib_trousers', bm, M['bib'])
    garment(trousers, 650, [(0.032, 5.0, 7, lambda p: smooth01((p.z - 0.3) / 0.12) * (1 - smooth01((p.z - 0.96) / 0.06))), (0.016, 9.0, 9)], voxel=0.008)
    # bib panel over the torso
    pts_l, pts_r = [], []
    rows = [(0.98, 0.175, -0.246), (1.06, 0.165, -0.238), (1.14, 0.155, -0.226), (1.212, 0.148, -0.214)]
    bm = bmesh.new(); grid = []
    for z, hw, y in rows:
        row = []
        for i in range(9):
            u = -1 + 2 * i / 8
            row.append(bm.verts.new(V(u * hw, y + 0.025 * u * u, z)))
        grid.append(row)
    for a, b in zip(grid, grid[1:]):
        for i in range(8): bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    bib = new_obj('NB_bib_panel', bm, M['bib'])
    so = bib.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.007; so.offset = 1; apply_mods(bib)
    fold_noise(bib, 0.004, 9.0, 13); facet(bib, 25, 0.002)
    # broad pocket with its flap
    bm = bmesh.new(); rbox(bm, (0, -0.25, 1.06), (0.125, 0.006, 0.066), rot=(math.radians(8), 0, 0), bevel=0.004)
    pk = new_obj('NB_bib_pocket', bm, M['bib']); facet(pk, 30)
    bm = bmesh.new(); rbox(bm, (0, -0.252, 1.124), (0.13, 0.008, 0.016), rot=(math.radians(-4), 0, 0), bevel=0.004)
    fl = new_obj('NB_bib_pocket_flap', bm, M['bib']); facet(fl, 30)
    return [trousers, bib, pk, fl]


def strap_path(s):
    """Bib corner -> over the shoulder -> down the back."""
    return [V(s * 0.12, -0.22, 1.205), V(s * 0.13, -0.19, 1.3), V(s * 0.15, -0.12, 1.39), V(s * 0.16, -0.02, 1.43),
            V(s * 0.15, 0.09, 1.39), V(s * 0.12, 0.17, 1.27), V(s * 0.06, 0.2, 1.08)]


def build_straps(M):
    objs = []
    for s, name in ((1, 'L'), (-1, 'R')):
        pts = strap_path(s)
        cu = bpy.data.curves.new('NB_strap_' + name, 'CURVE'); cu.dimensions = '3D'
        sp = cu.splines.new('NURBS'); sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
        sp.use_endpoint_u = True; sp.order_u = 3; cu.resolution_u = 10
        prof = bpy.data.curves.new('_sp', 'CURVE'); ps = prof.splines.new('POLY'); ps.points.add(3)
        for i, (a, b) in enumerate(((-0.022, -0.003), (0.022, -0.003), (0.022, 0.003), (-0.022, 0.003))): ps.points[i].co = (a, b, 0, 1)
        ps.use_cyclic_u = True
        po = bpy.data.objects.new('_sp', prof); bpy.context.scene.collection.objects.link(po)
        cu.bevel_mode = 'OBJECT'; cu.bevel_object = po; cu.use_fill_caps = True; cu.twist_mode = 'MINIMUM'
        old = bpy.data.objects.get('NB_strap_' + name)
        if old: bpy.data.objects.remove(old, do_unlink=True)
        co = bpy.data.objects.new('NB_strap_' + name, cu); coll().objects.link(co)
        bpy.context.view_layer.objects.active = co
        for x in bpy.context.view_layer.objects: x.select_set(False)
        co.select_set(True); bpy.ops.object.convert(target='MESH')
        so = bpy.context.view_layer.objects.active; bpy.data.objects.remove(po)
        so.data.materials.clear(); so.data.materials.append(M['strap']); facet(so, 40, 0.0012)
        objs.append(so)
        # brass: square buckle ring at the bib corner, a slider above it
        for nm, c, sz in (('buckle', V(s * 0.122, -0.222, 1.205), (0.03, 0.005, 0.03)), ('slider', V(s * 0.135, -0.18, 1.29), (0.028, 0.004, 0.012))):
            bm = bmesh.new(); rbox(bm, c, sz, bevel=0.002)
            inner = bmesh.new(); rbox(inner, c, (sz[0] * 0.65, sz[1] * 2, sz[2] * 0.55), bevel=0.0)
            b = new_obj(f'NB_{nm}_{name}', bm, M['brass'])
            cut = new_obj('_cut', inner)
            bo = b.modifiers.new('cut', 'BOOLEAN'); bo.object = cut; bo.operation = 'DIFFERENCE'; bo.solver = 'EXACT'
            apply_mods(b); bpy.data.objects.remove(cut, do_unlink=True); facet(b, 30, 0.0008); objs.append(b)
    return objs


def build_float(M):
    """The red-and-ivory egg float on his anatomical LEFT strap (+X): ring, clip, a swing pivot, a quill stem."""
    piv = V(0.122, -0.228, 1.182)                          # swings about this point (under the left buckle)
    c = piv + V(0.004, -0.008, -0.058)
    bm = bmesh.new(); ellipsoid(bm, c, (0.021, 0.021, 0.03), (40, 28))
    eg = new_obj('NB_float', bm, None, True)
    eg.data.materials.append(M['red']); eg.data.materials.append(M['ivory'])
    for p in eg.data.polygons: p.material_index = 0 if p.center.z > c.z + 0.004 else 1
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.0028, radius2=0.0018, depth=0.04, matrix=Matrix.Translation(c + V(0, 0, -0.045)))
    st = new_obj('NB_float_stem', bm, M['ivory'], True)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.0016, radius2=0.0016, depth=0.03,
                                            matrix=Matrix.Translation(c + V(0, 0, 0.038)))
    wi = new_obj('NB_float_clip', bm, M['brass'], True)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.006, minor_radius=0.0014, location=piv, rotation=(math.radians(90), 0, 0))
    rg = bpy.context.active_object; rg.name = 'NB_float_ring'
    for cc in rg.users_collection: cc.objects.unlink(rg)
    coll().objects.link(rg); rg.data.materials.append(M['brass'])
    root = bpy.data.objects.get('NB_float_pivot') or bpy.data.objects.new('NB_float_pivot', None)
    if root.name not in coll().objects: coll().objects.link(root)
    root.location = piv; root.empty_display_size = 0.02
    for o in (eg, st, wi):
        o.parent = root; o.matrix_parent_inverse = Matrix.Translation(-piv)
    return [eg, st, wi, rg]


def build_boots(M):
    """Chunky dark rubber boots: a blunt toe, a faceted shaft, a separate sole with a narrow bevel, a heel, tread."""
    out = []
    for s, name in ((1, 'L'), (-1, 'R')):
        cx = s * 0.15; yaw = math.radians(s * 8)
        R = Matrix.Rotation(yaw, 4, 'Z')
        def P(x, y, z): return (R @ V(x, y, 0).to_4d()).to_3d() + V(cx, 0, z)
        bm = bmesh.new()
        tcapsule(bm, P(0, -0.01, 0.1), P(0, -0.0, 0.3), 0.118, 0.112, 8)                 # faceted shaft
        rbox(bm, P(0, -0.07, 0.07), (0.088, 0.15, 0.05), rot=(0, 0, yaw), bevel=0.03)      # foot
        rbox(bm, P(0, -0.185, 0.068), (0.084, 0.05, 0.045), rot=(math.radians(-10), 0, yaw), bevel=0.028)  # blunt raised toe
        o = new_obj('NB_boot_' + name, bm, M['boot'])
        sculpt(o, voxel=0.006, smooth_iter=3, smooth_fac=0.5, faces=420, angle=20, bevel=0.004)
        # cut the shaft top flat at the opening
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=V(0, 0, 0.32), plane_no=V(0, 0, 1), clear_outer=True)
        bm.to_mesh(o.data); bm.free()
        out.append(o)
        bm = bmesh.new(); rbox(bm, P(0, -0.07, 0.016), (0.094, 0.165, 0.018), rot=(0, 0, yaw), bevel=0.006)
        so = new_obj('NB_sole_' + name, bm, M['sole']); facet(so, 30); out.append(so)
        bm = bmesh.new(); rbox(bm, P(0, 0.075, 0.03), (0.075, 0.05, 0.03), rot=(0, 0, yaw), bevel=0.005)
        he = new_obj('NB_heel_' + name, bm, M['sole']); facet(he, 30); out.append(he)
        bm = bmesh.new()
        for k in range(9):
            for side in (-1, 1):
                rbox(bm, P(side * 0.09, -0.215 + k * 0.035, 0.012), (0.008, 0.01, 0.01), rot=(0, 0, yaw), bevel=0.002)
        tr = new_obj('NB_tread_' + name, bm, M['sole']); facet(tr, 30); out.append(tr)
    return out


def build(M):
    objs = []
    objs.append(build_head(M)); objs += build_face_parts(M); objs += build_cap(M)
    objs += build_shirt(M); objs += build_hands(M); objs += build_bib(M); objs += build_straps(M)
    objs += build_float(M); objs += build_boots(M)
    c = coll()
    try:
        c.asset_mark(); c.asset_data.description = ('Nils Brack v001: stylised fisherman master, 1.70 m to the cap top, faces -Y, '
                                                    'origin between the boots. Stage 1: geometry and first-pass materials; no rig yet.')
    except Exception as e:
        print('[nils] asset mark', e)
    return objs


# ------------------------------------------------------------------------------------------------- studio and camera
MATCH_CAM = dict(loc=(-2.85, -3.35, 0.62), target=(0.0, 0.0, 0.86), lens=82)


def studio():
    sc = bpy.context.scene
    for o in [o for o in sc.objects if o.name.startswith('ST_')]: bpy.data.objects.remove(o, do_unlink=True)
    w = bpy.data.worlds.get('NB_studio') or bpy.data.worlds.new('NB_studio'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (*lin('#5a4d4a'), 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.35
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=12)
    fl = bpy.data.meshes.new('ST_floor'); bm.to_mesh(fl); bm.free()
    o = bpy.data.objects.new('ST_floor', fl); sc.collection.objects.link(o)
    bd = mat('ST_backdrop', '#6b5c58', 0.9); fl.materials.append(bd)
    # curved cyclorama behind him
    bm = bmesh.new()
    rings = []
    for k in range(13):
        t = k / 12 * (math.pi / 2)
        rings.append([V(x, 3.0 + 1.5 * math.sin(t), 1.5 * (1 - math.cos(t))) for x in (-8, 8)])
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    for a, b in zip(vs, vs[1:]): bm.faces.new((a[0], a[1], b[1], b[0]))
    for r in vs:
        pass
    top = [bm.verts.new(V(x, 4.5, 8)) for x in (-8, 8)]
    bm.faces.new((vs[-1][0], vs[-1][1], top[1], top[0]))
    cy = bpy.data.meshes.new('ST_cyc'); bm.to_mesh(cy); bm.free()
    o = bpy.data.objects.new('ST_cyc', cy); sc.collection.objects.link(o); cy.materials.append(bd)
    for p in cy.polygons: p.use_smooth = True
    # one broad key above and to one side, a soft fill, a faint rim
    def area(name, e, loc, size, tgt, color='#fff4ea'):
        l = bpy.data.lights.new(name, 'AREA'); l.energy = e; l.size = size; l.color = lin(color)
        o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (V(*tgt) - V(*loc)).to_track_quat('-Z', 'Y').to_euler()
    area('ST_key', 900, (-2.6, -2.4, 3.4), 2.6, (0, 0, 1.2))
    area('ST_fill', 160, (2.8, -2.6, 1.4), 3.0, (0, 0, 1.0), '#dfe6f2')
    area('ST_rim', 260, (1.4, 2.6, 2.6), 1.5, (0, 0, 1.3))


def camera(loc, target, lens, name='ST_cam'):
    sc = bpy.context.scene
    cam = bpy.data.objects.get(name)
    if not cam:
        cd = bpy.data.cameras.new(name); cam = bpy.data.objects.new(name, cd); sc.collection.objects.link(cam)
    cam.location = loc; cam.rotation_euler = (V(*target) - V(*loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens; cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 36
    sc.camera = cam
    return cam


def render_setup(w=1024, h=1536, samples=48):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = w; sc.render.resolution_y = h; sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = samples
    for k, v in (('use_raytracing', True), ('use_shadows', True), ('use_gtao', True)):
        try: setattr(sc.eevee, k, v)
        except Exception: pass
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 90


def set_clay(on, M):
    """Swap every Nils material slot for clay (and back)."""
    for o in coll().all_objects:
        if o.type != 'MESH': continue
        if on:
            o['nb_mats'] = [m.name if m else '' for m in o.data.materials]
            for i in range(len(o.data.materials)): o.data.materials[i] = M['clay']
        elif 'nb_mats' in o:
            for i, n in enumerate(o['nb_mats']):
                if n: o.data.materials[i] = bpy.data.materials[n]


def landmarks():
    """3D points for the guide lines (posed model)."""
    return {'cap rim': head_xf(V(0, -0.11, 1.648)), 'eyes': head_xf(V(0.04, -0.09, 1.604)), 'chin': head_xf(V(0, -0.1, 1.437)),
            'collar': V(0.12, -0.1, 1.43), 'bib top': V(0, -0.186, 1.207), 'fingertips': V(0.33, -0.08, 0.64),
            'boot tops': V(0.15, -0.12, 0.32), 'ground': V(0.15, -0.24, 0.0)}


def render(path):
    bpy.context.scene.render.filepath = path; bpy.ops.render.render(write_still=True); print('[nils] wrote', path, flush=True)


def guide_y(cam, p):
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene; co = world_to_camera_view(sc, cam, V(*p))
    return (1 - co.y) * sc.render.resolution_y


def match_sheet(out_dir, cam, tag):
    """Clay render at the sheet's size plus the projected guide heights (compose.py puts it beside the sheet)."""
    sc = bpy.context.scene; sc.render.image_settings.file_format = 'PNG'
    clay = os.path.join(out_dir, f'_clay_{tag}.png'); render(clay); sc.render.image_settings.file_format = 'JPEG'
    rows = {name: guide_y(cam, landmarks()[name]) for name in SHEET_GUIDES}
    json.dump({'render': clay, 'res': [sc.render.resolution_x, sc.render.resolution_y], 'guides': rows,
               'sheet_guides': SHEET_GUIDES}, open(os.path.join(out_dir, f'_guides_{tag}.json'), 'w'), indent=1)
    print('[nils] guides', json.dumps({k: round(v) for k, v in rows.items()}), flush=True)
    return clay


def turnaround(out_dir, M):
    sc = bpy.context.scene; sc.render.image_settings.file_format = 'PNG'
    for ang, nm in ((0, 'front'), (35, 'three_quarter'), (90, 'side'), (180, 'back')):
        a = math.radians(ang); D = 5.0
        camera((-math.sin(a) * D, -math.cos(a) * D, 0.95), (0, 0, 0.9), 50, 'ST_turn')
        render(os.path.join(out_dir, f'_turn_{nm}.png'))
    sc.render.image_settings.file_format = 'JPEG'


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage1', action='store_true'); ap.add_argument('--root', default=r'D:\CounterPhysical\lake-committee')
    ap.add_argument('--previews', default=os.path.join(REPO, 'content', 'characters', 'nils-brack', 'previews'))
    ap.add_argument('--only', default='')               # match | all
    a = ap.parse_args(argv)
    asset_dir = os.path.join(a.root, 'assets', 'characters', 'nils_brack', 'v001')
    os.makedirs(os.path.join(asset_dir, 'textures'), exist_ok=True); os.makedirs(a.previews, exist_ok=True)
    blend = os.path.join(asset_dir, 'Nils_Brack.blend')
    if os.path.exists(blend):
        bpy.ops.wm.open_mainfile(filepath=blend)
        for o in [o for o in bpy.data.objects if o.name.startswith(('NB_', '_cut', '_sp'))]: bpy.data.objects.remove(o, do_unlink=True)
    else:
        bpy.ops.wm.read_homefile(use_empty=True)
    M = materials()
    build(M)
    studio(); render_setup()
    bpy.ops.wm.save_as_mainfile(filepath=blend, relative_remap=True)
    print('[nils] saved', blend, flush=True)
    cam = camera(MATCH_CAM['loc'], MATCH_CAM['target'], MATCH_CAM['lens'])
    set_clay(True, M)
    match_sheet(a.previews, cam, 'clay')
    if a.only == 'match': return
    turnaround(a.previews, M)
    set_clay(False, M)
    cam = camera(MATCH_CAM['loc'], MATCH_CAM['target'], MATCH_CAM['lens'])
    render(os.path.join(a.previews, 'nils_v001_lit_fullbody.jpg'))
    head = head_xf(V(0, -0.05, 1.56))
    camera((head.x - 0.55, head.y - 1.05, head.z - 0.08), (head.x, head.y, head.z - 0.02), 85, 'ST_portrait')
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1080, 1350
    render(os.path.join(a.previews, 'nils_v001_lit_portrait.jpg'))
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1024, 1536
    bpy.context.scene.camera = bpy.data.objects['ST_cam']
    bpy.ops.wm.save_mainfile()


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
