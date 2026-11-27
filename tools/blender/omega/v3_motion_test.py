"""Short motion test of the v3 characters with native motion capture (no retargeting): both characters side by side
in a plain warm room, talking idle, then a close-up. blender -b -P v3_motion_test.py -- --dir <v3 dir> --out <dir>"""
import math, os, sys
import bpy
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit
argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None): return argv[argv.index(n) + 1] if n in argv else d
D = arg('--dir'); OUT = arg('--out'); os.makedirs(OUT, exist_ok=True)
sc = kit.reset(); kit.eevee_quality(sc, 32); kit.output(sc, pct=50)
try: sc.view_settings.look = 'AgX - Punchy'
except Exception: pass
def load(p):
    with bpy.data.libraries.load(p, link=False) as (src, dst): dst.objects = list(src.objects)
    for o in dst.objects:
        if o: kit.link(o)
load(os.path.join(D, 'nils_v3.blend')); load(os.path.join(D, 'theo_v3.blend'))
for o in list(bpy.data.objects):
    if o.type == 'CAMERA' or o.type == 'LIGHT' or o.name.startswith('Plane'): bpy.data.objects.remove(o)
nils = bpy.data.objects['nils_rig']; theo = bpy.data.objects['theo_rig']
for a, loc, yaw in ((nils, (0.45, 0, 0), -35), (theo, (-0.45, -0.05, 0), 40)):
    a.location = loc; a.rotation_mode = 'XYZ'; a.rotation_euler = (0, 0, math.radians(yaw))
for g in ('UAL1_Standard.glb', 'UAL2_Standard.glb'):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=kit.asset('D:\\CounterPhysical\\assets-cc0\\anim\\' + g))
    for o in [o for o in bpy.data.objects if o not in before]: bpy.data.objects.remove(o)
def play(a, name, start=1):
    ac = bpy.data.actions[name]; a.animation_data_create(); a.animation_data.action = ac
    try: a.animation_data.action_slot = ac.slots[0]
    except Exception: pass
play(nils, 'Idle_Talking_Loop'); play(theo, 'Idle_Loop')
# a warm plain room
W = kit.flat('wall', '#b98a5e', rough=0.9); Fm = kit.flat('floorm', '#7a5a3e', rough=0.85)
kit.box('floor', (6, 6, 0.04), (0, 0, -0.02), mat=Fm, bev=0); kit.box('wall', (6, 0.04, 3), (0, 1.5, 1.5), mat=W, bev=0)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = kit.hexc('#8fb4c8'); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.5
kit.sun('sun', (55, 0, 200), color='#ffd8a8', strength=3.5, angle=2.0)
kit.area('key', (-1.2, -2.0, 2.4), (0, 0, 1.3), color='#ffe6c8', power=300, size=1.0)
kit.area('rim', (1.2, 1.2, 2.2), (0, 0, 1.4), color='#a8d8f0', power=300, size=0.6)
FPS = 24; N = 96; sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, N
c1 = kit.camera('wide', (0.1, -3.0, 1.35), (0, 0, 1.05), lens=32, fstop=6.0, focus=3.0)
c2 = kit.camera('cu', (0.05, -1.25, 1.75), (0.45, 0, 1.72), lens=55, fstop=3.0, focus=1.3)
for f, c in ((1, c1), (49, c2)):
    m = sc.timeline_markers.new('c', frame=f); m.camera = c
for f in range(1, 49, 2):
    c1.location = Vector((0.1, -3.0, 1.35)) + Vector((0, 0.35, -0.05)) * (f / 48); c1.keyframe_insert('location', frame=f)
sc.camera = c1
sc.render.filepath = os.path.join(OUT, 'f'); bpy.ops.render.render(animation=True)
