"""Render a rig under a test pose (arm gesture, lean, jaw open) to check skinning and the mouth.
  blender -b -P pose_test.py -- --blend <rig.blend> --out <png>"""
import math, os, sys
import bpy
from mathutils import Vector, Euler
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
kit.eevee_quality(sc, 32); kit.output(sc, 1080, 1350, 40)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); P = arm.name[:-3]
pb = arm.pose.bones
for b in pb: b.rotation_mode = 'XYZ'
pb['upper_arm.L'].rotation_euler = (math.radians(-55), 0, math.radians(25))
pb['forearm.L'].rotation_euler = (math.radians(-70), 0, 0)
pb['upper_arm.R'].rotation_euler = (math.radians(-15), 0, math.radians(-10))
pb['spine'].rotation_euler = (math.radians(8), 0, math.radians(-6))
pb['neck'].rotation_euler = (math.radians(-8), math.radians(10), 0)
head = bpy.data.objects[P + 'head']; head.data.shape_keys.key_blocks['jaw_open'].value = 0.8
bpy.data.objects[P + 'mouth'].scale = (1, 1, 0.8)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = kit.hexc('#3a3633'); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.4
kit.area('key', (2.2, -2.6, 3.2), (0, 0, 1.3), color='#fff1e0', power=900, size=0.8)
kit.area('rim', (-1.6, 2.4, 2.6), (0, 0, 1.4), color='#ffd2a0', power=700, size=0.6)
kit.camera('cam', (1.3, -3.4, 1.25), (0, 0, 1.05), lens=50)
sc.render.filepath = arg('--out'); bpy.ops.render.render(write_still=True)
kit.camera('cam2', (0.35, -1.1, 1.55), (0, 0, 1.5), lens=70)
sc.render.filepath = arg('--out').replace('.png', '_head.png'); bpy.ops.render.render(write_still=True)
