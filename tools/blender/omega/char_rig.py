"""Rig Nils or Theo for acting (motion study 2026-11-27: the whole body must act, not just the head).

  blender -b -P tools/blender/omega/char_rig.py -- --blend <nils_v002.blend | theo_v001.blend> --out <rigged.blend>

- Armature (root, hips, spine, chest, neck, shoulders, upper arms, forearms, hands, thighs, shins) in the body's own
  space (Nils proportions; Theo is the same rig under his lanky object scale). Body skinned with automatic weights.
- The head, face parts and hair go rigid on the neck bone; braces, buckles, hem, zip, float on the chest bone.
- Mouth: a 'jaw_open' shape key on the head (lower face swings about a hinge in front of the ears) plus a mouth
  object (dark interior and an upper-teeth strip) that opens with it, and 'wide' / 'round' keys on the corners, so
  lipsync.visemes can drive AA/EE/OO/MBP shapes.
Prefix (nils_/theo_) is detected from the body object's name."""
import math, sys
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
sys.path_insert = None
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit

argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
bpy.ops.wm.open_mainfile(filepath=arg('--blend'))
body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith('_tsg'))
P = body.name[:-3]                                     # 'nils_' or 'theo_'
head = bpy.data.objects[P + 'head']
bpy.context.view_layer.update()

# ------------------------------------------------------------------ armature in the body's local space
B = {  # name: (head, tail, parent)
    'root': ((0, 0, 0), (0, 0.2, 0), None),
    'hips': ((0, 0, 0.95), (0, 0, 1.12), 'root'),
    'spine': ((0, 0, 1.12), (0, 0, 1.28), 'hips'),
    'chest': ((0, 0, 1.28), (0, -0.02, 1.41), 'spine'),
    'neck': ((0, -0.03, 1.41), (0, -0.03, 1.56), 'chest'),
    'jaw': ((0, -0.02, 1.50), (0, -0.12, 1.47), 'neck'),
}
for s, n in ((1, 'L'), (-1, 'R')):
    B[f'shoulder.{n}'] = ((s * 0.06, 0.0, 1.35), (s * 0.25, 0.01, 1.34), 'chest')
    B[f'upper_arm.{n}'] = ((s * 0.25, 0.01, 1.34), (s * 0.345, 0.02, 1.07), f'shoulder.{n}')
    B[f'forearm.{n}'] = ((s * 0.345, 0.02, 1.07), (s * 0.335, -0.015, 0.83), f'upper_arm.{n}')
    B[f'hand.{n}'] = ((s * 0.335, -0.015, 0.83), (s * 0.325, -0.03, 0.64), f'forearm.{n}')
    B[f'thigh.{n}'] = ((s * 0.12, 0.0, 0.95), (s * 0.13, 0.0, 0.5), 'hips')
    B[f'shin.{n}'] = ((s * 0.13, 0.0, 0.5), (s * 0.13, 0.02, 0.1), f'thigh.{n}')
ad = bpy.data.armatures.new(P + 'rig'); arm = bpy.data.objects.new(P + 'rig', ad); kit.link(arm)
arm.matrix_world = body.matrix_world.copy()
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t, par) in B.items():
    eb = ad.edit_bones.new(name); eb.head, eb.tail = h, t
    if par: eb.parent = ad.edit_bones[par]; eb.use_connect = False
    eb.use_deform = name not in ('root', 'neck', 'jaw')
bpy.ops.object.mode_set(mode='OBJECT')

# rigid parts first (so the automatic weights only see the body)
def to_bone(o, bone):
    """Bone-parent keeping the object's current world placement in the rest pose (the bone frame is its tail)."""
    bpy.context.view_layer.update()
    mw = o.matrix_world.copy()
    b = ad.bones[bone]
    o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = bone
    o.matrix_parent_inverse = (arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
    o.matrix_basis = mw
for o in list(bpy.data.objects):
    if o.parent != body: continue
    n = o.name[len(P):] if o.name.startswith(P) else o.name
    if n.startswith(('head', 'eye_', 'lid_', 'brow_', 'sideburn_', 'fringe', 'glasses', 'price_tag', 'tag_')):
        to_bone(o, 'neck')
    else:
        to_bone(o, 'chest')

# body skin
mwb = body.matrix_world.copy()
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_NAME')        # empty groups; weights are written below
body.matrix_world = mwb
how = 'geometric'
# geometric weights: the generated body has its arms touching the torso, so heat weights bleed arm into chest (the
# first pose test tore the chest). Classify by position instead, with 3-4 cm blends at every joint.
Vb = np.array([v.co[:] for v in body.data.vertices]); bx, by, bz = Vb[:, 0], Vb[:, 1], Vb[:, 2]; ax_ = np.abs(bx)
def ss(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
armness = np.where(bz > 0.86, ss(0.235, 0.27, ax_), ss(0.215, 0.245, ax_)) * ss(0.56, 0.6, bz) * ss(1.42, 1.36, bz)
shoulder_blend = ss(1.24, 1.32, bz) * ss(0.17, 0.26, ax_)               # deltoid: shared by chest and upper arm
legs = ss(0.98, 0.9, bz) * (1 - armness)
torso = np.clip(1 - armness - legs, 0, 1)
W_ = {}
W_['hips'] = torso * ss(1.16, 1.06, bz)
W_['spine'] = torso * ss(1.06, 1.16, bz) * ss(1.32, 1.24, bz)
W_['chest'] = torso * ss(1.24, 1.32, bz) * (1 - 0.5 * shoulder_blend)
up = armness * ss(1.03, 1.11, bz); fo = armness * ss(1.11, 1.03, bz) * ss(0.79, 0.87, bz); ha = armness * ss(0.87, 0.79, bz)
for n, sgn in (('L', 1), ('R', -1)):
    side = (bx * sgn) > 0
    W_[f'upper_arm.{n}'] = (up + torso * 0.5 * shoulder_blend) * side
    W_[f'forearm.{n}'] = fo * side; W_[f'hand.{n}'] = ha * side
    W_[f'thigh.{n}'] = legs * ss(0.46, 0.54, bz) * side
    W_[f'shin.{n}'] = legs * ss(0.54, 0.46, bz) * side
tot = sum(W_.values()) + 1e-6
for name, w in W_.items():
    vg = body.vertex_groups.get(name) or body.vertex_groups.new(name=name)
    w = w / tot
    idx = np.where(w > 0.002)[0]
    for i in idx: vg.add([int(i)], float(w[i]), 'REPLACE')
print('SKIN', how, len(body.vertex_groups), 'groups')

# ------------------------------------------------------------------ mouth: jaw key, corner keys, mouth object
mw = np.array(head.matrix_world); inv = np.linalg.inv(mw)
V = np.array([v.co[:] for v in head.data.vertices]); W = V @ mw[:3, :3].T + mw[:3, 3]
# body-local (Nils units) coordinates of the head vertices
bl = np.array(body.matrix_world.inverted())
L_ = W @ bl[:3, :3].T + bl[:3, 3]
x, y, z = L_[:, 0], L_[:, 1], L_[:, 2]
MZ = float(arg('--mouthz', '1.482'))
def sstep(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
if not head.data.shape_keys: head.shape_key_add(name='Basis')
jaw_w = sstep(MZ + 0.004, MZ - 0.004, z) * sstep(-0.02, -0.09, y) * sstep(0.12, 0.08, np.abs(x)) * sstep(1.38, 1.41, z)
hinge = np.array([0.0, -0.02, 1.50])
def make_key(name, newL):
    k = head.shape_key_add(name=name, from_mix=False)
    Wn = newL @ np.linalg.inv(bl[:3, :3]).T + (np.array(body.matrix_world)[:3, 3])
    Wn = (np.array(body.matrix_world)[:3, :3] @ newL.T).T + np.array(body.matrix_world)[:3, 3]
    Vn = (Wn - mw[:3, 3]) @ np.linalg.inv(mw[:3, :3]).T
    k.data.foreach_set('co', Vn.ravel()); return k
ang = math.radians(13)
rel = L_ - hinge
ry = rel[:, 1] * math.cos(ang) - rel[:, 2] * math.sin(ang); rz = rel[:, 1] * math.sin(ang) + rel[:, 2] * math.cos(ang)
jl = L_.copy(); jl[:, 1] = L_[:, 1] + (hinge[1] + ry - L_[:, 1]) * jaw_w; jl[:, 2] = L_[:, 2] + (hinge[2] + rz - L_[:, 2]) * jaw_w
make_key('jaw_open', jl)
corner = sstep(0.012, 0.03, np.abs(x)) * sstep(0.055, 0.04, np.abs(x)) * sstep(MZ + 0.018, MZ + 0.004, z) * sstep(MZ - 0.02, MZ - 0.006, z) * sstep(-0.12, -0.16, y)
wl = L_.copy(); wl[:, 0] += np.sign(x) * 0.007 * corner; wl[:, 2] += 0.002 * corner
make_key('wide', wl)
rl = L_.copy(); rl[:, 0] -= np.sign(x) * 0.008 * corner; rl[:, 1] -= 0.004 * sstep(0.04, 0.0, np.abs(x)) * sstep(MZ + 0.015, MZ, z) * sstep(MZ - 0.015, MZ, z) * sstep(-0.14, -0.17, y)
make_key('round', rl)

# mouth object: a dark interior lens with an upper-teeth strip, sitting in the mouth line; it opens (scale z) with
# the jaw; its root is on the neck bone so it follows the head
from mathutils.bvhtree import BVHTree
_bm = bmesh.new(); _bm.from_mesh(head.data); _bm.transform(head.matrix_world); HB = BVHTree.FromBMesh(_bm)
mwB = body.matrix_world
mpos_l = Vector((0.0, -0.3, MZ))
h = HB.ray_cast(mwB @ Vector((0, -1.0, MZ)), (mwB.to_3x3() @ Vector((0, 1, 0))).normalized(), 3.0)
front = h[0] if h[0] else mwB @ Vector((0, -0.19, MZ))
mroot = bpy.data.objects.new(P + 'mouth', None); kit.link(mroot)
mroot.location = front + (mwB.to_3x3() @ Vector((0, -0.002, 0.0015)))   # top edge just under the upper lip
mroot.rotation_euler = mwB.to_euler()
INT = kit.flat(P + 'mouth_in', '#1a0806', rough=0.8); TEETH = kit.flat(P + 'teeth', '#e6dfd0', rough=0.35)
TONGUE = kit.flat(P + 'tongue', '#8a3a33', rough=0.6)
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0)
for v in bm.verts: v.co = Vector((v.co.x * 0.023, v.co.y * 0.009, (v.co.z - 1.0) * 0.014))   # hangs down from its origin
cav = kit.from_bm(P + 'mouth_cavity', bm, INT, smooth_angle=89); cav.parent = mroot
tb = kit.box(P + 'teeth_top', (0.03, 0.004, 0.005), (0, -0.003, -0.0035), mat=TEETH, bev=0.0012); tb.parent = mroot
tg = kit.box(P + 'tongue', (0.024, 0.006, 0.006), (0, 0.002, -0.021), mat=TONGUE, bev=0.002); tg.parent = mroot
mroot.scale = (1, 1, 0.02)
to_bone(mroot, 'neck')

# lips (Caesar, 27 Nov: "like they have no lips"): sculpted upper and lower lip that frame the dark mouth. The upper
# lip is rigid on the head; the lower lip rides a jaw pivot that turns with the jaw_open key (same hinge, 13 deg).
LIPM = kit.painted(P + 'lips', ['#5e2620', '#74322a', '#874034'] if P == 'nils_' else ['#8a3c34', '#a04a40', '#b2584c'],
                   rough=0.42, scale=30.0, cavity=0.35, cavity_dist=0.006)
fwd = (mwB.to_3x3() @ Vector((0, 1, 0))).normalized()
def surf_local(xl, zl):
    hh = HB.ray_cast(mwB @ Vector((xl, -1.0, zl)), fwd, 3.0)
    return (mwB.inverted() @ hh[0]).y if hh[0] else -0.19
def lip(name, zc, hz0, hy0, out, droop):
    Wd = 0.028; n = 15; m = 8
    bm = bmesh.new(); rings = []
    for k in range(n):
        u = -1 + 2 * k / (n - 1); xl = u * Wd
        taper = max(0.18, 1 - 0.75 * u * u)
        z0 = zc + droop * (u * u)                          # corners turn slightly down (Nils) or up
        ys = surf_local(xl, z0) - out * taper
        ring = []
        for j in range(m):
            a = 2 * math.pi * j / m
            ring.append(bm.verts.new(mwB @ Vector((xl, ys + hy0 * taper * math.cos(a) * (0.6 if math.cos(a) > 0 else 1.0),
                                                  z0 + hz0 * taper * math.sin(a)))))
        rings.append(ring)
    for a_, b_ in zip(rings, rings[1:]):
        for j in range(m):
            jj = (j + 1) % m
            bm.faces.new((a_[j], a_[jj], b_[jj], b_[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit.from_bm(name, bm, LIPM, smooth_angle=70)
droop = -0.0015 if P == 'nils_' else 0.0008
up_l = lip(P + 'lip_upper', MZ + 0.0045, 0.0052, 0.0055, 0.0035, droop)
lo_l = lip(P + 'lip_lower', MZ - 0.006, 0.0065, 0.0062, 0.005, droop)
to_bone(up_l, 'neck')
to_bone(lo_l, 'jaw')
bpy.ops.wm.save_as_mainfile(filepath=arg('--out'))
print('RIG', P, 'bones', len(ad.bones), 'keys', [k.name for k in head.data.shape_keys.key_blocks])
