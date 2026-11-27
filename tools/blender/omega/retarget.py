"""Motion-capture retargeting (cycle 10, Caesar 27 Nov: "drastic improvements needed").

Source: Quaternius Universal Animation Library (CC0, copied to D:\\CounterPhysical\\assets-cc0\\anim): a humanoid
mannequin with 40+ captured actions (Idle_Loop, Idle_Talking_Loop, Sitting_Talking_Loop, PickUp_Table, Interact...).
Target: our character rigs (char_rig.py). Both face -Y with their left at +X.

Direction-copy retarget, per frame and per mapped bone, entirely in armature space (no depsgraph per bone):
  D  = R_src_pose * R_src_rest^-1                 the source bone's rotation from its own rest
  A  = rotation taking our rest bone direction onto the source rest direction (T-pose vs arms-down rests differ)
  Q  = D * A * R_tgt_rest                         our bone's posed armature-space rotation
  local = R_tgt_rest^-1 * R_parent_rest * (R_parent_pose)^-1 * Q     (Blender's pose composition, rotation part)
"""
import bpy
from mathutils import Quaternion, Matrix, Vector

MAP = {  # ours: source
    'hips': 'pelvis', 'spine': 'spine_01', 'chest': 'spine_03', 'neck': 'Head',
    'shoulder.L': 'clavicle_l', 'upper_arm.L': 'upperarm_l', 'forearm.L': 'lowerarm_l', 'hand.L': 'hand_l',
    'shoulder.R': 'clavicle_r', 'upper_arm.R': 'upperarm_r', 'forearm.R': 'lowerarm_r', 'hand.R': 'hand_r',
    'thigh.L': 'thigh_l', 'shin.L': 'calf_l', 'thigh.R': 'thigh_r', 'shin.R': 'calf_r',
}
ORDER = ['hips', 'spine', 'chest', 'neck', 'shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L',
         'shoulder.R', 'upper_arm.R', 'forearm.R', 'hand.R', 'thigh.L', 'shin.L', 'thigh.R', 'shin.R']


class Source:
    def __init__(self, glb, extra=()):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=glb)
        new = [o for o in bpy.data.objects if o not in before]
        self.arm = next(o for o in new if o.type == 'ARMATURE')
        for o in new:
            o.hide_render = True
        for g in extra:                       # more actions on the same skeleton (UAL2); its own objects are removed
            b2 = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=g)
            for o in [o for o in bpy.data.objects if o not in b2]:
                bpy.data.objects.remove(o)
        self.arm.animation_data_create()
        self.rest = {b.name: b.matrix_local.to_quaternion() for b in self.arm.data.bones}
        self.dirs = {b.name: (b.tail_local - b.head_local).normalized() for b in self.arm.data.bones}
        self.cache = {}

    def sample(self, action, t, fps):
        """Armature-space rotations of the mapped source bones at time t (s) of `action` (looped)."""
        act = bpy.data.actions[action]
        f0, f1 = act.frame_range
        length = (f1 - f0)
        fr = f0 + ((t * fps) % max(1.0, length))
        key = (action, round(fr * 4) / 4)
        if key in self.cache: return self.cache[key]
        self.arm.animation_data.action = act
        try:
            slot = act.slots[0] if hasattr(act, 'slots') and len(act.slots) else None
            if slot is not None: self.arm.animation_data.action_slot = slot
        except Exception:
            pass
        sc = bpy.context.scene
        sc.frame_set(int(fr), subframe=fr - int(fr))
        out = {n: self.arm.pose.bones[n].matrix.to_quaternion() for n in set(MAP.values())}
        self.cache[key] = out
        return out


def solve(src, rot_src, tgt_arm):
    """Local quaternions for our mapped bones from one sampled source frame."""
    bones = tgt_arm.data.bones
    posed = {}; local = {}
    for ours in ORDER:
        sn = MAP[ours]; b = bones[ours]
        R_tr = b.matrix_local.to_quaternion()
        D = rot_src[sn] @ src.rest[sn].inverted()
        tdir = (b.tail_local - b.head_local).normalized()
        A = tdir.rotation_difference(src.dirs[sn])
        Q = D @ A @ R_tr
        posed[ours] = Q
        if b.parent:
            R_pr = b.parent.matrix_local.to_quaternion()
            R_pp = posed.get(b.parent.name, _rest_pose(b.parent, posed))
            loc = R_tr.inverted() @ R_pr @ R_pp.inverted() @ Q
        else:
            loc = R_tr.inverted() @ Q
        local[ours] = loc
    return local


def _rest_pose(bone, posed):
    """Posed rotation of an unmapped bone that keeps its rest relation to its (possibly posed) parent."""
    if bone.parent is None: return bone.matrix_local.to_quaternion()
    R_pp = posed.get(bone.parent.name, _rest_pose(bone.parent, posed))
    return R_pp @ bone.parent.matrix_local.to_quaternion().inverted() @ bone.matrix_local.to_quaternion()


def blend(a, b, w):
    return {k: a[k].slerp(b[k], w) for k in a}
