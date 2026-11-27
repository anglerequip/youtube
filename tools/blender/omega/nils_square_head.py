"""Square the grafted head onto the body: the sheet shows Nils's head turned about 20 degrees, which the generator
keeps. A rig needs a neutral, straight head. Finds the head's mirror plane (yaw + offset) by a symmetry search, turns
the head about the neck so the plane is x = 0, and saves.

  blender -b -P tools/blender/omega/nils_square_head.py -- --blend <in.blend> --out <out.blend>"""
import math, sys
import bpy
import numpy as np
from mathutils import Matrix, Vector, kdtree
argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
bpy.ops.wm.open_mainfile(filepath=arg('--blend'))
head = bpy.data.objects['nils_head']

def sym(ob):
    mw = ob.matrix_world
    P = np.array([(mw @ v.co)[:] for v in ob.data.vertices]); P = P[(P[:, 2] > 1.44) & (P[:, 2] < 1.62)]
    P = P[::max(1, len(P) // 5000)]
    kd = kdtree.KDTree(len(P))
    for i, p in enumerate(P): kd.insert(p, i)
    kd.balance(); best = None
    for yaw in np.arange(-40, 40.5, 1):
        a = math.radians(yaw); n = np.array([math.cos(a), math.sin(a), 0])
        for off in np.arange(-0.05, 0.0501, 0.005):
            d = P @ n - off; R = P - 2 * d[:, None] * n
            err = np.mean([kd.find(r)[2] for r in R[::5]])
            if best is None or err < best[0]: best = (err, float(yaw), float(off))
    return best

e, yaw, off = sym(head); print('BEFORE', e, yaw, off)
pivot = Vector((0.0, -0.03, 1.42))
for sgn in (-1, 1):
    m0 = head.matrix_world.copy()
    head.matrix_world = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(sgn * yaw), 4, 'Z') @ Matrix.Translation(-pivot) @ m0
    bpy.context.view_layer.update()
    e2, y2, o2 = sym(head); print('TRY', sgn, e2, y2, o2)
    if abs(y2) < abs(yaw) / 2:
        head.matrix_world = Matrix.Translation((-o2, 0, 0)) @ head.matrix_world
        break
    head.matrix_world = m0
bpy.context.view_layer.update(); print('AFTER', sym(head))
bpy.ops.wm.save_as_mainfile(filepath=arg('--out'))
