"""Retarget check: a UAL action on our rig at 4 times.  blender -b -P mocap_test.py -- --blend <rig> --action <name> --out <dir>"""
import math, os, sys
import bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit, retarget
argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
bpy.ops.wm.open_mainfile(filepath=arg('--blend')); OUT = arg('--out'); os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try: sc.render.engine = eng; break
    except TypeError: pass
kit.eevee_quality(sc, 24); kit.output(sc, 1080, 1350, 30)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
src = retarget.Source(r'D:\CounterPhysical\assets-cc0\anim\UAL1_Standard.glb', [r'D:\CounterPhysical\assets-cc0\anim\UAL2_Standard.glb'])
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = kit.hexc('#6b6560'); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
kit.area('key', (1.5, -2.2, 2.6), (0, 0, 1.2), color='#fff1e0', power=700, size=0.8)
kit.camera('cam', (1.2, -3.3, 1.3), (0, 0, 0.95), lens=40)
TS = [float(x) for x in arg('--times', '0.3,1.2,2.1,3.0').split(',')]
for k, t in enumerate(TS):
    loc = retarget.solve(src, src.sample(arg('--action', 'Idle_Talking_Loop'), t, 30), arm)
    for n, q in loc.items():
        pb = arm.pose.bones[n]; pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = q
    sc.frame_set(1)
    sc.render.filepath = os.path.join(OUT, f'm{k}.png'); bpy.ops.render.render(write_still=True)
print('MOCAP ok')
