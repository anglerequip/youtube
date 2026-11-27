"""Theo, the beginner: a second original character derived from the same sculpt so he shares Nils's art style
(same proportion language, planes and finish) but reads as a different, younger person.

  blender -b -P tools/blender/omega/theo_morph.py -- --blend <graft_E_sq.blend> --out <theo_graft.blend>

Changes here: a smaller, straighter nose,
a softer brow ridge, a smaller, rounder chin. The lanky build (x/y 0.86, z 1.05) and the theo_* names are applied last (theo_finalize.py), after paint and parts."""
import sys
import bpy
import numpy as np
argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
bpy.ops.wm.open_mainfile(filepath=arg('--blend'))
head = bpy.data.objects['nils_head']; body = bpy.data.objects['nils_tsg']
bpy.context.view_layer.update()

def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

mw = np.array(head.matrix_world); inv = np.linalg.inv(mw)
V = np.array([v.co[:] for v in head.data.vertices]); W = V @ mw[:3, :3].T + mw[:3, 3]
x, y, z = W[:, 0].copy(), W[:, 1].copy(), W[:, 2].copy()
ax = np.abs(x)
# nose: pull toward the face plane and up (shorter, straighter, less droop)
nose = smoothstep(0.045, 0.02, ax) * smoothstep(1.47, 1.5, z) * smoothstep(1.6, 1.575, z) * smoothstep(-0.17, -0.19, y)
face_y = -0.188
y = y + (face_y - y) * 0.45 * nose * (y < face_y)
z = z + 0.006 * nose * smoothstep(1.52, 1.49, z)
# brow ridge: softer (pushed back 5 mm)
brow = smoothstep(1.565, 1.58, z) * smoothstep(1.61, 1.595, z) * smoothstep(-0.16, -0.18, y) * smoothstep(0.1, 0.06, ax)
y = y + 0.005 * brow
# chin and jaw: smaller and rounder (narrower, pulled back)
chin = smoothstep(1.47, 1.43, z) * smoothstep(-0.1, -0.15, y)
y = y + (0.012 * chin)
x = x * (1 - 0.08 * smoothstep(1.48, 1.42, z) * smoothstep(-0.06, -0.12, y))
Wn = np.stack([x, y, z], 1)
Vn = (Wn - mw[:3, 3]) @ np.linalg.inv(mw[:3, :3]).T
head.data.vertices.foreach_set('co', Vn.ravel()); head.data.update()

print('THEO morphed')
bpy.ops.wm.save_as_mainfile(filepath=arg('--out'))
