"""Turnaround + head close-up of a Nils asset under one 45-degree key, rim and weak fill (rule 7.12).

  blender -b -P tools/blender/omega/nils_preview.py -- --blend <nils.blend> --out <dir> [--clay] [--pct 50]
Writes <out>/turn_{front,tq,side,back}[_clay].png and head_{front,tq}[_clay].png."""
import math, os, sys
import bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit

argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
BLEND, OUT, CLAY, PCT = arg('--blend'), arg('--out'), '--clay' in argv, int(arg('--pct', '50'))
K = float(arg('--k', '1.0'))   # size of the asset relative to a 1.75 m figure (head-only assets: 0.3)
os.makedirs(OUT, exist_ok=True)

sc = kit.reset(); kit.eevee_quality(sc, 48); kit.output(sc, 1080, 1350, PCT)
with bpy.data.libraries.load(BLEND, link=False) as (src, dst):
    dst.objects = list(src.objects)
for o in dst.objects:
    kit.link(o)
    if CLAY and o.type == 'MESH':
        o.data.materials.clear(); o.data.materials.append(kit.flat('clay', '#b9b1a6', rough=0.7))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = kit.hexc('#3a3633')
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35
bpy.ops.mesh.primitive_plane_add(size=20); fl = bpy.context.active_object
fl.data.materials.append(kit.flat('floor', '#4a4440', rough=0.9))
kit.area('key', (2.2, -2.6, 3.2), (0, 0, 1.3), color='#fff1e0', power=900, size=0.8)
kit.area('rim', (-1.6, 2.4, 2.6), (0, 0, 1.4), color='#ffd2a0', power=700, size=0.6)
kit.area('fill', (-3.0, -2.0, 1.5), (0, 0, 1.0), color='#a9c0dc', power=120, size=3.0)

tag = '_clay' if CLAY else ''
for name, yaw in (('front', 0), ('tq', 35), ('side', 90), ('back', 180)):
    a = math.radians(yaw)
    d = Vector((math.sin(a), -math.cos(a), 0))
    kit.camera('cam_' + name, tuple(d * 6.0 * K + Vector((0, 0, 0.95 * K))), (0, 0, 0.88 * K), lens=50)
    sc.render.filepath = os.path.join(OUT, f'turn_{name}{tag}.png'); bpy.ops.render.render(write_still=True)
for name, yaw in (('front', 0), ('tq', 30)):
    a = math.radians(yaw)
    d = Vector((math.sin(a), -math.cos(a), 0))
    kit.camera('hcam_' + name, tuple(d * 1.5 * (K if K < 1 else 1) + Vector((0, 0, 1.55 if K == 1 else 0.33 * K / 0.3 * 0.9))), (0, 0, 1.55 if K == 1 else 0.33 * K / 0.3 * 0.9), lens=70)
    sc.render.filepath = os.path.join(OUT, f'head_{name}{tag}.png'); bpy.ops.render.render(write_still=True)
print('DONE')
