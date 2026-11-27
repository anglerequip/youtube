"""Calm the face: the generator carves fine wrinkles and pits into the skin, which read as bug-like texture at phone
size (Caesar, 27 Nov). Smooth the face region of the head (weighted, feathered) so the big planes stay (brow ridge,
nose wedge, cheek, chin block) and the fine noise goes.

  blender -b -P tools/blender/omega/nils_smooth_face.py -- --blend <in> --out <out> [--iters 25] [--factor 0.7]"""
import sys
import bpy
import numpy as np
argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
bpy.ops.wm.open_mainfile(filepath=arg('--blend'))
head = bpy.data.objects['nils_head']; me = head.data
mw = np.array(head.matrix_world)
V = np.array([v.co[:] for v in me.vertices]); W = V @ mw[:3, :3].T + mw[:3, 3]
x, y, z = W[:, 0], W[:, 1], W[:, 2]
# face mask: below the cap line, in front of the ears; feathered edges; the nose ridge and brow keep some detail
w = np.clip((1.595 - z) / 0.02, 0, 1) * np.clip((z - 1.40) / 0.02, 0, 1) * np.clip((-0.02 - y) / 0.04, 0, 1)
vg = head.vertex_groups.new(name='face_smooth')
for i, wi in enumerate(w):
    if wi > 0.001: vg.add([i], float(wi), 'REPLACE')
bpy.context.view_layer.objects.active = head
for it, (fac, n) in enumerate(((float(arg('--factor', '0.7')), int(arg('--iters', '25'))),)):
    m = head.modifiers.new('calm', 'SMOOTH'); m.iterations = n; m.factor = fac; m.vertex_group = 'face_smooth'
    bpy.ops.object.modifier_apply(modifier=m.name)
print('SMOOTHED', int((w > 0.001).sum()), 'verts')
bpy.ops.wm.save_as_mainfile(filepath=arg('--out'))
