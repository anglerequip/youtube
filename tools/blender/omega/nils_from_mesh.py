"""Turn a TripoSG image-to-3D mesh of Nils into a painted, faceted Blender asset.

  blender -b -P tools/blender/omega/nils_from_mesh.py -- --glb <candidate.glb> --img <nils_input_rgba.png> --out <dir>
        [--faces 60000] [--sharp 32]

1. Import, join, find which axis the input picture was seen along (best silhouette IoU against the image alpha).
2. Paint: every vertex the picture can see takes the model sheet's colour at its projected pixel (lightly blurred, so
   it stays painted, not photographic); hidden vertices get their colour diffused from visible neighbours.
3. Facet: collapse-decimate to a few tens of thousands of faces and mark plane borders sharp (HOST_RENDER_RULES 7.3).
4. Scale to 1.75 m, feet on the floor, facing -Y. Saves <out>/nils_tsg.blend and a preview log.
The model sheet's baked-in light is in those colours; the plan is to flatten it (de-light) in a later pass.
"""
import math, os, sys, json
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
GLB, IMG, OUT = arg('--glb'), arg('--img'), arg('--out')
FACES, SHARP = int(arg('--faces', '60000')), float(arg('--sharp', '32'))
HEIGHT, VOXEL, SMOOTH = float(arg('--height', '1.75')), float(arg('--voxel', '0')), int(arg('--smooth', '0'))
os.makedirs(OUT, exist_ok=True)
log = {}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active; ob.name = 'nils_tsg'
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = ob.data
log['faces_in'] = len(me.polygons)

# ------------------------------------------------------------------ image
img = bpy.data.images.load(IMG)
W, H = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1]   # row 0 = top
alpha = px[..., 3] > 0.5
ys, xs = np.where(alpha); ab = (xs.min(), ys.min(), xs.max(), ys.max())
# light blur of the colours (painted, not photographic)
def blur(a, r=2):
    k = np.ones(2 * r + 1) / (2 * r + 1)
    a = np.apply_along_axis(lambda m: np.convolve(m, k, mode='same'), 0, a)
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode='same'), 1, a)
rgb = np.stack([blur(px[..., c] * px[..., 3]) for c in range(3)], -1)
aw = blur(px[..., 3]); rgb = rgb / np.maximum(aw[..., None], 1e-4)

V = np.array([v.co[:] for v in me.vertices], dtype=np.float64)

# ------------------------------------------------------------------ view axis: (screen-x axis, screen-up axis, view dir)
AX = {'-Y': (0, 2, (0, 1, 0)), '+Y': (0, 2, (0, -1, 0)), '-X': (1, 2, (1, 0, 0)), '+X': (1, 2, (-1, 0, 0))}
def project(name, flip):
    i, j, d = AX[name]
    u = V[:, i] * (-1 if flip else 1); w = V[:, j]
    # map mesh bbox -> image alpha bbox (TripoSG frames the object like the cut-out)
    sx = (ab[2] - ab[0]) / max(u.max() - u.min(), 1e-6); sy = (ab[3] - ab[1]) / max(w.max() - w.min(), 1e-6)
    pu = ab[0] + (u - u.min()) * sx; pv = ab[3] - (w - w.min()) * sy
    return pu, pv
def iou(pu, pv):
    m = np.zeros((H, W), bool)
    iu = np.clip(pu.astype(int), 0, W - 1); iv = np.clip(pv.astype(int), 0, H - 1)
    m[iv, iu] = True
    # close the point splat
    from functools import reduce
    k = 3
    mm = m.copy()
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            mm |= np.roll(np.roll(m, dy, 0), dx, 1)
    return (mm & alpha).sum() / max((mm | alpha).sum(), 1)
best = max(((iou(*project(n, f)), n, f) for n in AX for f in (False, True)))
log['view'] = {'axis': best[1], 'flip': best[2], 'iou': round(float(best[0]), 3)}
print('VIEW', log['view'])
name, flip = best[1], best[2]
pu, pv = project(name, flip)
vdir = Vector(AX[name][2])                     # direction from camera into the scene

# ------------------------------------------------------------------ visibility + colour
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
bvh = BVHTree.FromBMesh(bm)
span = float(np.ptp(V, axis=0).max())
col = np.zeros((len(V), 3), np.float32); known = np.zeros(len(V), bool)
for k, v in enumerate(bm.verts):
    o = v.co - vdir * (span * 2.0)
    hit = bvh.ray_cast(o, vdir, span * 4.0)
    if hit[0] is not None and (hit[0] - v.co).length < span * 0.004:
        x, y = int(round(pu[k])), int(round(pv[k]))
        if 0 <= x < W and 0 <= y < H and px[y, x, 3] > 0.5:
            col[k] = rgb[y, x]; known[k] = True
log['visible_frac'] = round(float(known.mean()), 3)
# diffuse into hidden vertices
nbr = [[e.other_vert(v).index for e in v.link_edges] for v in bm.verts]
for it in range(400):
    unk = np.where(~known)[0]
    if not len(unk): break
    newly = []
    for k in unk:
        ks = [n for n in nbr[k] if known[n]]
        if ks:
            col[k] = col[ks].mean(0); newly.append(k)
    if not newly: break
    known[newly] = True
log['coloured_frac'] = round(float(known.mean()), 3)
bm.free()
ca = me.color_attributes.new('paint', 'FLOAT_COLOR', 'POINT')
srgb2lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
lin = srgb2lin(np.clip(col, 0, 1))
ca.data.foreach_set('color', np.concatenate([lin, np.ones((len(V), 1), np.float32)], 1).ravel())

# ------------------------------------------------------------------ orient: face -Y, feet on z=0, 1.75 m tall
# the view axis points into the scene; the character faces back along -vdir. Rotate so -vdir becomes -Y.
fwd = -vdir
ang = math.atan2(fwd.x, -fwd.y)                 # rotation about Z taking fwd onto -Y
ob.rotation_euler = (0, 0, -ang) if name in ('-X', '+X') else (0, 0, 0 if name == '-Y' else math.pi)
bpy.ops.object.transform_apply(rotation=True)
bb = np.array([v.co[:] for v in me.vertices])
s = HEIGHT / np.ptp(bb[:, 2])
ob.scale = (s, s, s); bpy.ops.object.transform_apply(scale=True)
bb = np.array([v.co[:] for v in me.vertices])
ob.location = (-(bb[:, 0].min() + bb[:, 0].max()) / 2, -(bb[:, 1].min() + bb[:, 1].max()) / 2, -bb[:, 2].min())
bpy.ops.object.transform_apply(location=True)

# ------------------------------------------------------------------ clean: voxel remesh closes holes and drops the
# marching-cubes noise (knit read as holes); colour survives via a data transfer from the original
if VOXEL:
    src = ob.copy(); src.data = ob.data.copy(); bpy.context.scene.collection.objects.link(src)
    r = ob.modifiers.new('remesh', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = VOXEL; r.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=r.name)
    if SMOOTH:
        sm = ob.modifiers.new('smooth', 'SMOOTH'); sm.factor = 0.5; sm.iterations = SMOOTH
        bpy.ops.object.modifier_apply(modifier=sm.name)
    me = ob.data
    if 'paint' not in me.color_attributes:
        me.color_attributes.new('paint', 'FLOAT_COLOR', 'POINT')
    dt = ob.modifiers.new('dt', 'DATA_TRANSFER'); dt.object = src
    dt.use_vert_data = True; dt.data_types_verts = {'COLOR_VERTEX'}; dt.vert_mapping = 'NEAREST'
    bpy.ops.object.modifier_apply(modifier=dt.name)
    bpy.data.objects.remove(src)
    log['faces_remeshed'] = len(me.polygons)

# ------------------------------------------------------------------ facet
if FACES and len(me.polygons) > FACES:
    d = ob.modifiers.new('decimate', 'DECIMATE'); d.ratio = FACES / len(me.polygons)
    bpy.ops.object.modifier_apply(modifier=d.name)
bm = bmesh.new(); bm.from_mesh(me)
lim = math.radians(SHARP)
for f in bm.faces: f.smooth = True
for e in bm.edges:
    e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim)
bm.to_mesh(me); bm.free()
log['faces_out'] = len(me.polygons)

m = bpy.data.materials.new('nils_paint'); m.use_nodes = True
nt = m.node_tree; b = nt.nodes['Principled BSDF']
attr = nt.nodes.new('ShaderNodeAttribute'); attr.attribute_name = 'paint'
nt.links.new(attr.outputs['Color'], b.inputs['Base Color'])
b.inputs['Roughness'].default_value = 0.62
me.materials.clear(); me.materials.append(m)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'nils_tsg.blend'))
json.dump(log, open(os.path.join(OUT, 'nils_tsg_log.json'), 'w'), indent=1)
print('LOG', log)
