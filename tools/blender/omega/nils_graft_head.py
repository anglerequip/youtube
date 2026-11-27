"""Replace the body mesh's head with a separately generated, higher-resolution head (both from the same model sheet).

  blender -b -P tools/blender/omega/nils_graft_head.py -- --body <body.blend> --head <head.blend> --out <graft.blend>
        [--cut 1.415]

The head asset (nils_from_mesh.py on the head close-up) is registered onto the body's head by a brute-force search
over scale and offset that maximises the overlap of their front silhouettes above the cut line; depth is aligned by
the mean of the head region. Body vertices above the cut are deleted; the collar hides the seam. Writes the result
with the head as its own object 'nils_head' parented to the body."""
import sys
import bpy, bmesh
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
CUT = float(arg('--cut', '1.415'))

bpy.ops.wm.open_mainfile(filepath=arg('--body'))
body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('nils'))
with bpy.data.libraries.load(arg('--head'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith('nils')]
head = dst.objects[0]; bpy.context.scene.collection.objects.link(head); head.name = 'nils_head'

B = np.array([v.co[:] for v in body.data.vertices]); Hv = np.array([v.co[:] for v in head.data.vertices])
G = 160
def sil(P, box):
    x0, z0, x1, z1 = box
    m = np.zeros((G, G), bool)
    i = ((P[:, 0] - x0) / (x1 - x0) * (G - 1)).astype(int); j = ((P[:, 2] - z0) / (z1 - z0) * (G - 1)).astype(int)
    ok = (i >= 0) & (i < G) & (j >= 0) & (j < G); m[j[ok], i[ok]] = True
    k = 2; mm = m.copy()
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            mm |= np.roll(np.roll(m, dy, 0), dx, 1)
    return mm
bh = B[B[:, 2] > CUT]
box = (bh[:, 0].min() - 0.05, CUT, bh[:, 0].max() + 0.05, bh[:, 2].max() + 0.03)
target = sil(bh, box)
best = (-1, None)
top = Hv[:, 2].max()
for s in np.linspace(0.45, 0.85, 41):
    P = Hv * s
    for tz in np.linspace(-0.04, 0.04, 17):
        dz = bh[:, 2].max() - P[:, 2].max() + tz
        for tx in np.linspace(-0.03, 0.03, 13):
            Q = P + np.array([tx, 0, dz])
            q = Q[Q[:, 2] > CUT]
            if not len(q): continue
            m = sil(q, box)
            iou = (m & target).sum() / max((m | target).sum(), 1)
            if iou > best[0]: best = (iou, (s, tx, dz))
iou, (s, tx, dz) = best
P = Hv * s + np.array([tx, 0, dz])
ty = bh[:, 1].mean() - P[P[:, 2] > CUT][:, 1].mean()
print('GRAFT', dict(iou=round(float(iou), 3), scale=round(float(s), 3), tx=round(float(tx), 4), dz=round(float(dz), 4), ty=round(float(ty), 4)))
head.matrix_world = Matrix.Translation((tx, ty, dz)) @ Matrix.Scale(s, 4)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT'); head.select_set(True); bpy.context.view_layer.objects.active = head
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# trim the head asset below the cut (its shoulders) and the body above it
for ob, keep_below in ((head, False), (body, True)):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    lim = CUT - (0.0 if keep_below else 0.02)     # the head keeps a 2 cm skirt into the collar
    dead = [v for v in bm.verts if (v.co.z > CUT if keep_below else v.co.z < lim)]
    bmesh.ops.delete(bm, geom=dead, context='VERTS'); bm.to_mesh(ob.data); bm.free()
head.parent = body; head.matrix_parent_inverse = body.matrix_world.inverted()
bpy.ops.wm.save_as_mainfile(filepath=arg('--out'))
