"""Head close-ups at jaw 0 / 0.35 / 0.6 to check lips and mouth.  blender -b -P mouth_test.py -- --blend <rig> --out <png>"""
import math, os, sys
import bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
bpy.ops.wm.open_mainfile(filepath=arg('--blend'))
sc = bpy.context.scene
for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try: sc.render.engine = eng; break
    except TypeError: pass
kit.eevee_quality(sc, 32); kit.output(sc, 800, 800, 50)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); P = arm.name[:-3]
head = bpy.data.objects[P + 'head']; kb = head.data.shape_keys.key_blocks
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = kit.hexc('#6b6560'); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
mw = arm.matrix_world
hp = mw @ Vector((0, -0.1, 1.5))
kit.area('key', tuple(mw @ Vector((0.8, -1.2, 2.0))), tuple(hp), color='#fff1e0', power=200, size=0.6)
kit.camera('cam', tuple(mw @ Vector((0.18, -0.75, 1.52))), tuple(mw @ Vector((0, -0.15, 1.5))), lens=85)
for j in (0.0, 0.35, 0.6):
    kb['jaw_open'].value = j
    import anim_skit; anim_skit.set_bone(arm, 'jaw', pitch=13 * j)
    bpy.data.objects[P + 'mouth'].scale = (1, 1, 0.06 + 1.35 * j)
    sc.render.filepath = arg('--out').replace('.png', f'_{int(j*100)}.png'); bpy.ops.render.render(write_still=True)
