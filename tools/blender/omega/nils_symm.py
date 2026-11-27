"""Face fix (Caesar, 27 Nov: "his face is way too disfigured"): the generated head is lopsided (one eye socket deeper,
a crooked nose, uneven cheeks). Mirror the cleaner half across the face's centre plane (x = 0 after squaring) and
pull the nose back toward the face a little, keeping the long wedge the model sheet asks for.
  blender -b -P nils_symm.py -- --blend <graft_E_sq.blend> --out <same or new> [--side X|-X] [--nose 0.85]"""
import sys
import bpy, bmesh
import numpy as np
argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
bpy.ops.wm.open_mainfile(filepath=arg('--blend'))
head = bpy.data.objects['nils_head']; body = bpy.data.objects['nils_tsg']
mw = head.matrix_world.copy(); head.parent = None; head.matrix_world = mw
bpy.ops.object.select_all(action='DESELECT'); head.select_set(True); bpy.context.view_layer.objects.active = head
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bm = bmesh.new(); bm.from_mesh(head.data)
bmesh.ops.symmetrize(bm, input=bm.verts[:] + bm.edges[:] + bm.faces[:], direction=arg('--side', 'X'), dist=0.0005)
k = float(arg('--nose', '0.85'))
for v in bm.verts:
    x, y, z = v.co
    if abs(x) < 0.045 and 1.47 < z < 1.6 and y < -0.17:
        w = max(0.0, min(1.0, (-0.17 - y) / 0.02)) * max(0.0, 1 - abs(x) / 0.045)
        v.co.y = -0.17 + (y + 0.17) * (1 - (1 - k) * w)
bm.to_mesh(head.data); bm.free()
head.parent = body; head.matrix_parent_inverse = body.matrix_world.inverted()
bpy.ops.wm.save_as_mainfile(filepath=arg('--out'))
print('SYMM done', len(head.data.vertices))
