"""Cut the painted Nils into flat planes: planar (dissolve) decimation that never crosses a material border, so the
garments break into the big faceted panels of the model sheet while region edges stay clean (rule 7.3, 'high poly
but blocky'). Head and body get their own angle.

  blender -b -P tools/blender/omega/nils_facet.py -- --blend <in> --out <out> [--body 7] [--head 4]"""
import math, sys
import bpy
argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
bpy.ops.wm.open_mainfile(filepath=arg('--blend'))
for name, ang in (('nils_tsg', float(arg('--body', '7'))), ('nils_head', float(arg('--head', '4')))):
    ob = bpy.data.objects.get(name)
    if not ob or ang <= 0: continue
    n0 = len(ob.data.polygons)
    bpy.context.view_layer.objects.active = ob
    d = ob.modifiers.new('planar', 'DECIMATE'); d.decimate_type = 'DISSOLVE'; d.angle_limit = math.radians(ang)
    d.delimit = {'MATERIAL'}
    bpy.ops.object.modifier_apply(modifier=d.name)
    t = ob.modifiers.new('tri', 'TRIANGULATE'); bpy.ops.object.modifier_apply(modifier=t.name)
    # flat planes, sharp borders: every face its own plane (the head keeps smooth shading inside its planes)
    for p in ob.data.polygons: p.use_smooth = name == 'nils_head'
    print('FACET', name, n0, '->', len(ob.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=arg('--out'))
