"""Gesture check: rest, explain, shrug, point; plus a face close-up.  blender -b -P pose_test2.py -- --blend <rig> --out <dir>"""
import math, os, sys
import bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import kit
from anim_skit import set_bone
argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
bpy.ops.wm.open_mainfile(filepath=arg('--blend')); OUT = arg('--out'); os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try: sc.render.engine = eng; break
    except TypeError: pass
kit.eevee_quality(sc, 32); kit.output(sc, 1080, 1350, 40)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = kit.hexc('#6b6560'); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
mw = arm.matrix_world
kit.area('key', tuple(mw @ Vector((1.5, -2.2, 2.6))), tuple(mw @ Vector((0, 0, 1.2))), color='#fff1e0', power=700, size=0.8)
kit.area('rim', tuple(mw @ Vector((-1.4, 2.0, 2.4))), tuple(mw @ Vector((0, 0, 1.4))), color='#a8d8ff', power=500, size=0.6)
POSES = {
 'tp': {'upper_arm.R': (-60, 0, 0)}, 'ty': {'upper_arm.R': (0, -60, 0)}, 'tr': {'upper_arm.R': (0, 0, -60)}, 'tf': {'forearm.R': (-60, 0, 0)},
 'rest': {},
 'explain': {'upper_arm.L': (-40, 0, -15), 'forearm.L': (-70, 0, 0), 'hand.L': (-10, 0, 0), 'upper_arm.R': (-10, 0, 8), 'forearm.R': (-25, 0, 0)},
 'shrug': {'upper_arm.L': (-15, 0, -28), 'forearm.L': (-80, 25, 0), 'upper_arm.R': (-15, 0, 28), 'forearm.R': (-80, -25, 0),
           'shoulder.L': (0, 0, -12), 'shoulder.R': (0, 0, 12), 'neck': (0, 0, 8)},
 'point': {'upper_arm.R': (-75, 0, 10), 'forearm.R': (-10, 0, 0), 'neck': (0, -10, 0)},
}
kit.camera('cam', tuple(mw @ Vector((1.8, -2.8, 1.3))), tuple(mw @ Vector((0, 0, 1.0))), lens=45)
for name, p in POSES.items():
    for b in arm.pose.bones: set_bone(arm, b.name, 0, 0, 0)
    for b, (pp, yy, rr) in p.items(): set_bone(arm, b, pp, yy, rr)
    sc.render.filepath = os.path.join(OUT, f'pose_{name}.png'); bpy.ops.render.render(write_still=True)
for b in arm.pose.bones: set_bone(arm, b.name, 0, 0, 0)
kit.camera('cam2', tuple(mw @ Vector((0.25, -1.05, 1.56))), tuple(mw @ Vector((0, -0.1, 1.53))), lens=70)
sc.render.filepath = os.path.join(OUT, 'face.png'); bpy.ops.render.render(write_still=True)
