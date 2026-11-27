"""Last Theo step: lanky build (scale the whole rig about the feet: x/y 0.86, z 1.05) and theo_* names so Nils and
Theo can share a scene.  blender -b -P theo_finalize.py -- --blend <in> --out <out>"""
import sys
import bpy
argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
bpy.ops.wm.open_mainfile(filepath=arg('--blend'))
body = bpy.data.objects['nils_tsg']
body.scale = (0.86, 0.86, 1.05)
for o in list(bpy.data.objects):
    if o.name.startswith('nils_'): o.name = 'theo_' + o.name[5:]
    elif not o.name.startswith('theo_'): o.name = 'theo_' + o.name
for m in bpy.data.materials:
    if m.name.startswith('nils_'): m.name = 'theo_' + m.name[5:]
bpy.ops.wm.save_as_mainfile(filepath=arg('--out'))
print('THEO', sorted(o.name for o in bpy.data.objects)[:40])
