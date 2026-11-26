"""AnglerMind host "Captain Finn" v1: MakeHuman (MPFB 2) body, sculpted-fold clothes, groomed hair, face shapes, pose library.

Original design (Caesar picked the look, 2026-11-26; spec in tools/blender/host_v1.py and docs/styles/HOST.md):
a confident fishing guide, late thirties, about 1.84 m, athletic-heroic build, angular jaw, straight nose, short trimmed
copper-brown beard. Wraparound polarised sunglasses with a lake-blue mirror lens, sand bucket hat with an olive band and
two pinned lures, a long open rust waxed-cotton jacket, cream knit roll-neck, olive chest waders with braces, dark wader
boots, fingerless olive gloves, hands about 12 % oversized. Not modelled on any real person, actor or existing character.

Build (headless; keep Blender's user config inside D:\\CounterPhysical, MPFB 2.0.18 installed there):
  set BLENDER_USER_RESOURCES=D:\\CounterPhysical\\blender-user
  blender -b --factory-startup --python tools/blender/finn_v1.py -- --build [--preview] [--shots full,mcu,face,point,hold]
  -> assets/characters/finn.blend   (rig, body, clothes, materials; MPFB textures packed, CC0 fabric textures referenced
                                      relative to D:\\CounterPhysical\\assets-cc0\\textures)
  -> content/episodes/finn-lure-finder/previews/finn_v1_<shot>.jpg   (with --preview; Eevee, 1080x1920, AgX)

Episode renderer API (import this file inside Blender: sys.path.insert(0, 'tools/blender'); import finn_v1 as finn):
  load_finn(blend_path=None) -> rig      Appends the "Finn" collection from finn.blend (or builds him when there is no
                                         blend). Stands on z=0 at the origin, facing -Y, real-world metres.
                                         Move him with rig.location / rig.rotation_euler.
  POSES                                  Dict of body pose specs by name: neutral, hold_up, present, rod, phone_up,
                                         phone_present, box_out, box_hug, point_down, arms_wide, hand_on_chin.
  apply_pose(rig, name_a, name_b=None, mix=0.0, frame=None, idle=1.0)
                                         Poses the bones as POSES[name_a] blended toward name_b by mix (0..1, slerp per
                                         bone). frame drives a subtle breathing/weight-shift idle (idle scales it, 0 = off).
                                         Poses are solved once per rig from the specs and cached on the rig.
  set_face(rig, mouth='closed', open=None, brow=0.0, blink=0.0)
                                         mouth: closed | talk | shout | smirk. open 0..1 = jaw/mouth opening (lip-sync
                                         amplitude; default per mouth shape). brow -1 (down, stern) .. +1 (up, surprised).
  hand_socket(rig, side='R') -> bone name ('socket.R' / 'socket.L') for parenting props:
        prop.parent = rig; prop.parent_type = 'BONE'; prop.parent_bone = finn.hand_socket(rig, 'R')
        prop.matrix_parent_inverse.identity(); prop.location = offset; prop.rotation_euler = rot
      Socket frame (both hands): origin in the middle of the palm, about 1 cm off the palm skin; +Y runs along the
      fingers, +Z points out of the palm (palmar side), +X completes a right-handed frame. Sizes in metres.
      Expected local offsets for the props (what the pose library is built around):
        lure  (8-11 cm crankbait, pinched):  location (0.00, 0.08, 0.03), rotation (0, 0, 90 deg), lure long axis on X
        phone (7 x 15 cm):                   location (0.00, 0.03, 0.02), rotation (0, 0, 0), screen facing +Z (out of the
                                             palm), long side along +Y
        tackle box handle (box 30x18x16 cm): location (0.00, 0.045, 0.03), handle bar along X, box hangs toward -Z...
                                             for box_out/box_hug parent the box to socket.R and rest it on socket.L
        rod (cork grip, rod axis along -X for the right hand): location (0.0, 0.05, 0.03), rotation (0, 0, 0);
                                             the rod blank runs along the socket's +X/-X axis through the fist
  measure: FINN_HEIGHT = 1.84 (top of head, without hat)
"""
import bpy, bmesh, math, os, sys, random, time, argparse, json
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
ROOT = os.path.abspath(os.path.join(REPO, '..'))                       # D:\CounterPhysical
ASSETS = os.environ.get('FINN_ASSETS', os.path.join(ROOT, 'assets-cc0'))
TEX = os.path.join(ASSETS, 'textures')
BLEND = os.path.join(REPO, 'assets', 'characters', 'finn.blend')
PREVIEWS = os.path.join(REPO, 'content', 'episodes', 'finn-lure-finder', 'previews')
FINN_HEIGHT = 1.84
SOLE = 0.022                                                          # boot sole under the foot

COL = {
    'jacket': '#a4492a', 'hat': '#c8b48a', 'band': '#2c3520', 'lens': '#2f6f86', 'lureA': '#d7e04a', 'lureB': '#e2742e',
    'knit': '#e6dcc4', 'wader': '#3d4a2a', 'glove': '#47532f', 'boot': '#2b2119', 'brace': '#22261b', 'brass': '#b8904a',
    'frame': '#17191b', 'beard': '#7a4526', 'hair': '#5e3a22', 'cord': '#5a2a18', 'lining': '#4d5a34', 'sole': '#141210',
}


# ----------------------------------------------------------------------------------------------------------------- util
def lin(hexc):
    c = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def mpfb():
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    from bl_ext.user_default.mpfb.services.locationservice import LocationService
    return HumanService, TargetService, LocationService


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def band(x, a, b, soft):
    """1 inside [a, b], smooth falloff of width soft outside."""
    return smooth((x - a) / soft + 1) * smooth((b - x) / soft + 1)


def noise3(p, s=1.0, seed=0):
    from mathutils import noise
    return noise.noise(Vector((p.x * s + seed * 13.1, p.y * s - seed * 7.7, p.z * s + seed * 3.3)))


def set_active(o):
    for x in bpy.context.view_layer.objects: x.select_set(False)
    bpy.context.view_layer.objects.active = o; o.select_set(True)


def apply_mod(o, name):
    set_active(o); bpy.ops.object.modifier_apply(modifier=name)


def link(o, coll):
    for c in o.users_collection: c.objects.unlink(o)
    coll.objects.link(o)


# ------------------------------------------------------------------------------------------------------------ materials
def _img(path, noncolor=False):
    im = bpy.data.images.load(path, check_existing=True)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    return im


def _mean_lum(im):
    """1 / mean linear luminance of a texture, so any CC0 set modulates our costume colour around 1.0."""
    try:
        import numpy as np
        a = np.empty(len(im.pixels), dtype=np.float32); im.pixels.foreach_get(a)
        a = a.reshape(-1, 4)[::7, :3]
        lin_ = np.where(a > 0.04045, ((a + 0.055) / 1.055) ** 2.4, a / 12.92)
        y = float((lin_ @ np.array([0.2126, 0.7152, 0.0722])).mean())
        return 1.0 / max(0.03, y)
    except Exception as e:
        print('[finn] lum', e); return 2.0


def fabric(name, color, texset=None, scale=6.0, rough=(0.55, 0.85), sheen=0.0, coat=0.0, normal=0.6, ao=0.55,
           tint_mix=0.85, var=0.08, metal=0.0, spec=0.5, sss=0.0, lum=1.0):
    """Painted-PBR fabric: CC0 texture (box projected on the rest position, so it does not swim when posed) tinted to
    the costume colour, roughness remapped, normal map, cavity darkening from AO (darker creases) and a soft large-scale
    colour variation (hand-painted feel)."""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']
    b.inputs['Roughness'].default_value = rough[0]; b.inputs['Metallic'].default_value = metal
    b.inputs['Specular IOR Level'].default_value = spec
    if sheen: b.inputs['Sheen Weight'].default_value = sheen; b.inputs['Sheen Roughness'].default_value = 0.45
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.35
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = (0.6, 0.25, 0.12)
        b.inputs['Subsurface Scale'].default_value = 0.01
    base = Vector(lin(color))
    att = N.new('ShaderNodeAttribute'); att.attribute_name = 'finn_rest'; att.attribute_type = 'GEOMETRY'
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale, scale, scale)
    L.new(att.outputs['Vector'], mp.inputs['Vector'])
    # large-scale painted variation
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 3
    L.new(att.outputs['Vector'], nz.inputs['Vector'])
    vr = N.new('ShaderNodeMapRange'); vr.inputs['To Min'].default_value = 1 - var; vr.inputs['To Max'].default_value = 1 + var
    L.new(nz.outputs['Fac'], vr.inputs['Value'])
    col_out = None
    folder = os.path.join(TEX, texset) if texset else None
    files = os.listdir(folder) if folder and os.path.isdir(folder) else []

    def pick(*keys):
        for f in files:
            fl = f.lower()
            if any(k in fl for k in keys) and fl.endswith(('.jpg', '.png')): return os.path.join(folder, f)

    def tex(path, noncolor):
        t = N.new('ShaderNodeTexImage'); t.image = _img(path, noncolor); t.projection = 'BOX'; t.projection_blend = 0.35
        L.new(mp.outputs['Vector'], t.inputs['Vector']); return t
    tint = N.new('ShaderNodeRGB'); tint.outputs[0].default_value = (*base, 1)
    if pick('diff', 'albedo', 'color'):
        t = tex(pick('diff', 'albedo', 'color'), False)
        lum = lum * _mean_lum(t.image)
        bw = N.new('ShaderNodeRGBToBW'); L.new(t.outputs['Color'], bw.inputs['Color'])
        # texture luminance around 1.0 -> modulates the costume colour, keeps the hue exactly ours
        lv = N.new('ShaderNodeMath'); lv.operation = 'MULTIPLY'; lv.inputs[1].default_value = lum
        L.new(bw.outputs['Val'], lv.inputs[0])
        mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = tint_mix
        L.new(tint.outputs[0], mix.inputs[6])
        cm = N.new('ShaderNodeCombineColor'); L.new(lv.outputs[0], cm.inputs[0]); L.new(lv.outputs[0], cm.inputs[1]); L.new(lv.outputs[0], cm.inputs[2])
        L.new(cm.outputs[0], mix.inputs[7]); col_out = mix.outputs[2]
    else:
        col_out = tint.outputs[0]
    m1 = N.new('ShaderNodeMix'); m1.data_type = 'RGBA'; m1.blend_type = 'MULTIPLY'; m1.inputs['Factor'].default_value = 1.0
    L.new(col_out, m1.inputs[6]); cv = N.new('ShaderNodeCombineColor')
    for i in range(3): L.new(vr.outputs[0], cv.inputs[i])
    L.new(cv.outputs[0], m1.inputs[7]); col_out = m1.outputs[2]
    if ao:
        aon = N.new('ShaderNodeAmbientOcclusion'); aon.inputs['Distance'].default_value = 0.06; aon.samples = 8
        ar = N.new('ShaderNodeMapRange'); ar.inputs['To Min'].default_value = 1 - ao; ar.inputs['To Max'].default_value = 1.0
        L.new(aon.outputs['AO'], ar.inputs['Value'])
        m2 = N.new('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.blend_type = 'MULTIPLY'; m2.inputs['Factor'].default_value = 1.0
        ca = N.new('ShaderNodeCombineColor')
        for i in range(3): L.new(ar.outputs[0], ca.inputs[i])
        L.new(col_out, m2.inputs[6]); L.new(ca.outputs[0], m2.inputs[7]); col_out = m2.outputs[2]
    L.new(col_out, b.inputs['Base Color'])
    if pick('rough'):
        t = tex(pick('rough'), True)
        rr = N.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = rough[0]; rr.inputs['To Max'].default_value = rough[1]
        L.new(t.outputs['Color'], rr.inputs['Value']); L.new(rr.outputs[0], b.inputs['Roughness'])
    if pick('nor_gl', 'normalgl'):
        t = tex(pick('nor_gl', 'normalgl'), True)
        nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal
        L.new(t.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def simple(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, emit_s=0.0, spec=0.5, sss=0.0, alpha=1.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin(color), 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal; b.inputs['Specular IOR Level'].default_value = spec
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.08
    if sss: b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Scale'].default_value = 0.005
    if emit: b.inputs['Emission Color'].default_value = (*lin(emit), 1); b.inputs['Emission Strength'].default_value = emit_s
    return m


def lens_mat():
    """Polarised mirror lens: very glossy lake-blue metal with a thin-film edge, it throws the white glint."""
    m = bpy.data.materials.get('finn_lens')
    if m: return m
    m = bpy.data.materials.new('finn_lens'); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links
    b = N['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin(COL['lens']), 1); b.inputs['Metallic'].default_value = 0.92
    b.inputs['Roughness'].default_value = 0.035; b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.02
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = (*lin(COL['lens']), 1)
    mx.inputs[7].default_value = (*lin('#8fc3cf'), 1); L.new(lw.outputs['Facing'], mx.inputs['Factor'])
    L.new(mx.outputs[2], b.inputs['Base Color'])
    return m


def hair_mat(name, color, tip):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.42; b.inputs['Specular IOR Level'].default_value = 0.55
    b.inputs['Coat Weight'].default_value = 0.15
    hi = N.new('ShaderNodeHairInfo'); ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*[x * 0.55 for x in lin(color)], 1)
    ramp.color_ramp.elements[1].position = 0.6; ramp.color_ramp.elements[1].color = (*lin(color), 1)
    e = ramp.color_ramp.elements.new(1.0); e.color = (*lin(tip), 1)
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 400
    L.new(hi.outputs['Random'], nz.inputs['W']) if 'W' in nz.inputs else None
    mix = N.new('ShaderNodeMath'); mix.operation = 'MULTIPLY_ADD'; mix.inputs[1].default_value = 0.25
    L.new(hi.outputs['Random'], mix.inputs[0]); L.new(hi.outputs['Intercept'], mix.inputs[2])
    L.new(hi.outputs['Intercept'], ramp.inputs['Fac'])
    L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    return m


# ----------------------------------------------------------------------------------------------------------------- body
EXPR_UNITS = ['mouth-open', 'mouth-corner-puller', 'mouth-retraction', 'mouth-depression', 'mouth-elevation',
              'mouth-upward-retraction', 'mouth-parling', 'mouth-compression',
              'eyebrows-left-up', 'eyebrows-right-up', 'eyebrows-left-down', 'eyebrows-right-down',
              'eyebrows-left-inner-up', 'eyebrows-right-inner-up', 'eye-left-closure', 'eye-right-closure',
              'nose-left-elevation', 'nose-right-elevation']

DETAIL = {   # our own face and build: angular, strong jaw, straight nose, heroic torso, bigger hands
    'chin/chin-width-incr': 0.45, 'chin/chin-prominent-incr': 0.35, 'chin/chin-height-incr': 0.15, 'chin/chin-bones-incr': 0.5,
    'head/head-square': 0.55, 'head/head-scale-vert-incr': 0.08, 'head/head-angle-in': 0.1,
    'cheek/l-cheek-bones-incr': 0.45, 'cheek/r-cheek-bones-incr': 0.45, 'cheek/l-cheek-inner-decr': 0.3, 'cheek/r-cheek-inner-decr': 0.3,
    'nose/nose-hump-decr': 0.5, 'nose/nose-greek-incr': 0.25, 'nose/nose-point-width-decr': 0.2, 'nose/nose-scale-vert-incr': 0.15,
    'nose/nose-width1-decr': 0.15,
    'mouth/mouth-scale-horiz-incr': 0.2, 'mouth/mouth-lowerlip-volume-decr': 0.15, 'mouth/mouth-upperlip-volume-decr': 0.2,
    'eyebrows/eyebrows-trans-forward': 0.4, 'eyebrows/eyebrows-angle-down': 0.25,
    'forehead/forehead-trans-forward': 0.2, 'forehead/forehead-nubian-incr': 0.2,
    'neck/neck-scale-horiz-incr': 0.4, 'neck/neck-scale-depth-incr': 0.25,
    'torso/torso-vshape-incr': 0.3, 'torso/torso-muscle-pectoral-incr': 0.15, 'torso/measure-shoulder-dist-incr': 0.35,
    'torso/torso-muscle-dorsi-incr': 0.1, 'torso/measure-waist-circ-decr': 0.2,
    'hands/l-hand-scale-incr': 0.55, 'hands/r-hand-scale-incr': 0.55, 'hands/l-hand-fingers-diameter-incr': 0.3,
    'hands/r-hand-fingers-diameter-incr': 0.3,
}


def _macro(TS):
    m = TS.get_default_macro_info_dict()
    m.update(gender=1.0, age=0.62, muscle=0.66, weight=0.54, proportions=0.85, height=0.62)
    m['race'] = {'caucasian': 0.88, 'asian': 0.06, 'african': 0.06}
    return m


def _top(b):
    vg = b.vertex_groups['body'].index
    return max(v.co.z for v in b.data.vertices if any(g.group == vg for g in v.groups))


def build_body():
    HS, TS, LS = mpfb()
    tgt = os.path.join(LS.get_mpfb_data('targets'))
    m = _macro(TS)
    probe = HS.create_human(macro_detail_dict=m)
    for k, w in DETAIL.items():
        p = os.path.join(tgt, k + '.target.gz')
        if os.path.exists(p): TS.load_target(probe, p, weight=w)
        else: print('[finn] missing target', k)
    TS.bake_targets(probe); h = _top(probe)
    bpy.data.objects.remove(probe)
    s = 0.1 * FINN_HEIGHT / h
    b = HS.create_human(macro_detail_dict=m, scale=s)
    for k, w in DETAIL.items():
        p = os.path.join(tgt, k + '.target.gz')
        if os.path.exists(p): TS.load_target(b, p, weight=w)
    TS.bake_targets(b)
    b.shape_key_add(name='Basis')
    for u in EXPR_UNITS:
        TS.load_target(b, os.path.join(tgt, 'expression', 'units', 'caucasian', u + '.target.gz'), weight=0.0, name='x_' + u)
    b.name = 'finn_body'
    print('[finn] body height', round(_top(b), 3), 'scale', round(s, 4))
    rig = HS.add_builtin_rig(b, 'default')
    rig.name = 'finn_rig'; rig.data.name = 'finn_rig'
    ud = LS.get_user_data()
    for sub, typ in (('eyes/high-poly/high-poly.mhclo', 'Eyes'), ('teeth/teeth_base/teeth_base.mhclo', 'Teeth')):
        p = os.path.join(ud, sub)
        if os.path.exists(p):
            try:
                o = HS.add_mhclo_asset(p, b, asset_type=typ, subdiv_levels=1, material_type='MAKESKIN')
            except Exception as e:
                print('[finn] asset failed', sub, e)
    skin = os.path.join(ud, 'skins', 'middleage_caucasian_male', 'middleage_caucasian_male.mhmat')
    HS.set_character_skin(skin, b, skin_type='ENHANCED_SSS', material_instances=False)
    return b, rig


def strip_helpers(b):
    """Delete the MakeHuman helper geometry (tights, skirt, hair caps, joint cubes) once rig and assets are fitted."""
    vg = b.vertex_groups['body'].index
    bm = bmesh.new(); bm.from_mesh(b.data); dl = bm.verts.layers.deform.active
    kill = [v for v in bm.verts if v[dl].get(vg, 0.0) < 0.5]
    bmesh.ops.delete(bm, geom=kill, context='VERTS'); bm.to_mesh(b.data); bm.free()
    for md in list(b.modifiers):
        if md.type == 'MASK': b.modifiers.remove(md)
    for g in list(b.vertex_groups):
        if g.name.startswith(('joint-', 'helper-')) or g.name in ('HelperGeometry', 'JointCubes'): b.vertex_groups.remove(g)


class Body:
    """Rest-pose landmarks of the fitted body (metres, world, Finn facing -Y)."""
    def __init__(self, b, rig):
        self.b = b; self.rig = rig
        A = rig.data.bones
        self.p = {n: rig.matrix_world @ A[n].head_local for n in A.keys()}
        self.t = {n: rig.matrix_world @ A[n].tail_local for n in A.keys()}
        self.vg = {g.index: g.name for g in b.vertex_groups}
        self.bvh = BVHTree.FromObject(b, bpy.context.evaluated_depsgraph_get())
        self.eye = (self.p['eye.L'] + self.p['eye.R']) / 2
        self.head = self.p['head']
        vs = [b.matrix_world @ v.co for v in b.data.vertices]
        self.top = max(v.z for v in vs)
        lips = b.vertex_groups['lips'].index
        lv = [b.matrix_world @ v.co for v in b.data.vertices if any(g.group == lips and g.weight > 0.5 for g in v.groups)]
        self.lips = sum(lv, Vector()) / len(lv)
        self.lips_top = max(v.z for v in lv); self.lips_bot = min(v.z for v in lv)
        self.chin = self.t['jaw']
        # head surface front point (nose tip) by ray
        hit = self.bvh.ray_cast(Vector((0, -1.0, self.eye.z - 0.03)), Vector((0, 1, 0)))
        self.nose = hit[0]
        armg = {g.index for g in b.vertex_groups if g.name.startswith(('upperarm', 'lowerarm', 'wrist'))}
        vw = [sum(g.weight for g in v.groups if g.group in armg) for v in b.data.vertices]
        self.face_arm = [min(1.0, sum(vw[i] for i in p.vertices) / len(p.vertices)) for p in b.data.polygons]

    def arm_w(self, co):
        loc, nrm, idx, dist = self.bvh.find_nearest(co)
        return self.face_arm[idx] if idx is not None else 0.0

    def weights(self, v):
        return {self.vg[g.group]: g.weight for g in v.groups if g.group in self.vg}


def bone_sum(w, *prefixes):
    return sum(x for n, x in w.items() if n.startswith(prefixes))


# ------------------------------------------------------------------------------------------------------- hair (groomed)
def face_masks(B):
    """Vertex groups (weights) on the body for beard, moustache, brows and short back-and-sides hair."""
    b = B.b
    g_beard = b.vertex_groups.new(name='finn_beard'); g_mous = b.vertex_groups.new(name='finn_moustache')
    g_bl = b.vertex_groups.new(name='finn_brow_L'); g_br = b.vertex_groups.new(name='finn_brow_R')
    g_hair = b.vertex_groups.new(name='finn_hair')
    ears = b.vertex_groups['ears'].index; lips = b.vertex_groups['lips'].index; scalp = b.vertex_groups['scalp'].index
    E = B.eye; Lz = B.lips.z; head_y = B.head.y
    for v in b.data.vertices:
        co = b.matrix_world @ v.co
        gw = {g.group: g.weight for g in v.groups}
        if gw.get(ears, 0) > 0.2: continue
        if co.z < B.p['neck01'].z - 0.04 or co.z > B.top + 0.01: continue
        ax = abs(co.x); u = co.z - Lz; front = co.y < head_y - 0.005
        lipw = gw.get(lips, 0.0)
        w = 0.0
        if lipw < 0.15:
            # upper boundary: sideburn high at the ear, down the cheek to the mouth corner
            top = 0.015 + 0.95 * max(0.0, ax - 0.028)
            top = min(top, 0.075)
            up = smooth((top - u) / 0.008 + 0.5)
            # lower boundary: under the jaw onto the upper neck, a trimmed neckline
            neck_line = B.chin.z - 0.03 - 0.015 * smooth((ax - 0.02) / 0.05)
            lo = smooth((co.z - neck_line) / 0.01 + 0.5)
            back = smooth(((B.p['head'].y + 0.012) - co.y) / 0.01)          # stop in front of the ear
            w = up * lo * back * (1 - smooth(lipw * 6))
            if u > -0.005 and ax < 0.03:                                    # moustache zone -> its own system
                mw = band(u, 0.004, 0.024, 0.004) * (1 - smooth((ax - 0.026) / 0.01)) * (1 - smooth(lipw * 6))
                if mw > 0.02: g_mous.add([v.index], mw, 'REPLACE')
                w *= 0.0 if u > 0.004 else 1.0
            if w > 0.02: g_beard.add([v.index], w, 'REPLACE')
        # brows: arch above the eye sockets
        bz = E.z + 0.017 + 0.006 * math.sin(min(1, max(0, (ax - 0.012) / 0.05)) * math.pi) - 0.004 * smooth((ax - 0.045) / 0.02)
        if co.y < E.y + 0.03 and 0.01 < ax < 0.064:
            wb = band(co.z, bz - 0.005, bz + 0.004 - 0.003 * (ax - 0.01) / 0.05, 0.0025)
            wb *= 0.4 + 0.6 * (1 - smooth((ax - 0.04) / 0.025))
            if wb > 0.05: (g_bl if co.x > 0 else g_br).add([v.index], wb, 'REPLACE')
        # short hair, back and sides (the hat covers the crown)
        if gw.get(scalp, 0) > 0.3 and co.z < B.top - 0.02:
            hw = 1.0 - smooth((co.z - (E.z + 0.05)) / 0.03) * smooth(((B.head.y - 0.03) - co.y) / 0.03)
            if hw > 0.05: g_hair.add([v.index], hw, 'REPLACE')


def hair_system(b, name, group, count, length, mat, *, children=6, normal=0.4, down=0.0, side=0.0, fwd=0.0, root=0.06,
                tip=0.01, rand=0.15, clump=0.2, kink=0.0, seg=4, rough=0.003, child_radius=0.004, tang=0.0):
    md = b.modifiers.new(name, 'PARTICLE_SYSTEM'); ps = b.particle_systems[-1]; ps.name = name
    s = ps.settings; s.name = name; s.type = 'HAIR'; s.use_advanced_hair = True
    s.count = count; s.hair_step = seg; s.display_step = 3; s.render_step = 4
    s.emit_from = 'FACE'; s.use_emit_random = True; s.use_even_distribution = True
    # Blender hair length = |emission velocity| * 4: scale the direction mix so the strands are `length` long
    k = 0.25 * length / max(1e-6, math.sqrt(normal ** 2 + side ** 2 + fwd ** 2 + down ** 2))
    s.normal_factor = normal * k; s.object_align_factor = (side * k, fwd * k, -down * k); s.tangent_factor = tang * k
    s.factor_random = rand * k; s.brownian_factor = 0.0
    s.child_type = 'INTERPOLATED' if children else 'NONE'; s.child_percent = children; s.rendered_child_count = children
    s.child_radius = child_radius; s.clump_factor = clump; s.roughness_1 = rough; s.roughness_1_size = 1.0
    s.roughness_endpoint = rough * 0.5; s.kink = 'CURL' if kink else 'NO'
    if kink: s.kink_amplitude = kink; s.kink_frequency = 3
    s.root_radius = root; s.tip_radius = tip; s.radius_scale = 0.01; s.use_close_tip = True
    s.material_slot = mat.name
    ps.vertex_group_density = group; ps.vertex_group_length = group
    s.use_hair_bspline = True
    return ps


def groom(B):
    b = B.b
    face_masks(B)
    mb = hair_mat('finn_beard', '#5e321a', '#8a5230'); mh = hair_mat('finn_hairmat', COL['hair'], '#8a5a34')
    mbr = hair_mat('finn_brow', '#5a321c', '#7a4a2a')
    for m in (mb, mh, mbr): b.data.materials.append(m)
    hair_system(b, 'beard', 'finn_beard', 60000, 0.014, mb, children=0, normal=0.12, down=1.0, rand=0.08, clump=0.45,
                rough=0.0008, child_radius=0.003, root=0.055, tip=0.012)
    hair_system(b, 'moustache', 'finn_moustache', 9000, 0.013, mb, children=0, normal=0.5, down=0.6, fwd=-0.3, rand=0.08, clump=0.35,
                rough=0.001, child_radius=0.0025, root=0.05, tip=0.012)
    hair_system(b, 'brow_L', 'finn_brow_L', 1500, 0.0085, mbr, children=0, normal=0.25, side=0.75, rand=0.12, clump=0.3,
                rough=0.0008, child_radius=0.0018, root=0.08, tip=0.015)
    hair_system(b, 'brow_R', 'finn_brow_R', 1500, 0.0085, mbr, children=0, normal=0.25, side=-0.75, rand=0.12, clump=0.3,
                rough=0.0008, child_radius=0.0018, root=0.08, tip=0.015)
    hair_system(b, 'hair', 'finn_hair', 30000, 0.014, mh, children=0, normal=0.25, down=0.65, rand=0.15, clump=0.1,
                rough=0.002, child_radius=0.004, root=0.09, tip=0.02)
    # the particle systems must evaluate after the armature (they then follow the pose and the face shape keys)
    set_active(b)
    for md in [m for m in b.modifiers if m.type == 'PARTICLE_SYSTEM']:
        bpy.ops.object.modifier_move_to_index(modifier=md.name, index=len(b.modifiers) - 1)


# -------------------------------------------------------------------------------------------- garments from the body
def body_copy(B, name, keep_face, coll):
    """Copy of the body faces that pass keep_face(center, weights) with all bone weights (so it is rigged already)."""
    b = B.b
    me = b.data.copy(); me.name = name
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.matrix_world = b.matrix_world
    if me.shape_keys:
        set_active(o); o.active_shape_key_index = 0; bpy.ops.object.shape_key_remove(all=True)
    me.materials.clear()
    bm = bmesh.new(); bm.from_mesh(me); dl = bm.verts.layers.deform.active
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        w = {}
        for v in f.verts:
            for gi, x in v[dl].items():
                n = B.vg.get(gi)
                if n: w[n] = w.get(n, 0) + x / len(f.verts)
        if not keep_face(c, w): kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]; bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me); bm.free()
    for g in list(o.vertex_groups):
        if g.name.startswith('finn_') or g.name in ('lips', 'ears', 'scalp', 'fingernails', 'toenails', 'nipple', 'nippleTip', 'genitals', 'body', 'Left', 'Right', 'Mid'):
            o.vertex_groups.remove(g)
    return o


def subdivide(o, levels=1):
    md = o.modifiers.new('sub', 'SUBSURF'); md.levels = levels; md.render_levels = levels; md.quality = 2
    apply_mod(o, 'sub')


def store_rest(o):
    me = o.data
    a = me.attributes.get('finn_rest') or me.attributes.new('finn_rest', 'FLOAT_VECTOR', 'POINT')
    for i, v in enumerate(me.vertices): a.data[i].vector = o.matrix_world @ v.co


def bind(o, src, rig, coll=None, mode='POLYINTERP_NEAREST'):
    """Rig any extra geometry: transfer the bone weights from src (nearest surface), add the armature modifier."""
    set_active(o)
    for g in src.vertex_groups:
        if g.name not in o.vertex_groups and g.name in rig.data.bones: o.vertex_groups.new(name=g.name)
    md = o.modifiers.new('wt', 'DATA_TRANSFER'); md.object = src; md.use_vert_data = True
    md.data_types_verts = {'VGROUP_WEIGHTS'}; md.vert_mapping = mode
    md.layers_vgroup_select_src = 'ALL'; md.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.datalayout_transfer(modifier='wt')
    apply_mod(o, 'wt')
    arm(o, rig)


def arm(o, rig):
    for md in o.modifiers:
        if md.type == 'ARMATURE': return
    md = o.modifiers.new('rig', 'ARMATURE'); md.object = rig
    set_active(o); bpy.ops.object.modifier_move_to_index(modifier='rig', index=0)


def offset(o, fn):
    """Move every vertex along its normal by fn(world co, normal, weights) metres (sculpted folds live here)."""
    me = o.data; me.update()
    vg = {g.index: g.name for g in o.vertex_groups}
    for v in me.vertices:
        co = o.matrix_world @ v.co; n = (o.matrix_world.to_3x3() @ v.normal).normalized()
        w = {vg[g.group]: g.weight for g in v.groups if g.group in vg}
        d = fn(co, n, w)
        if isinstance(d, Vector): v.co = o.matrix_world.inverted() @ (co + d)
        else: v.co = o.matrix_world.inverted() @ (co + n * d)
    me.update()


def solidify(o, t, off=-1.0, rim=True):
    md = o.modifiers.new('thick', 'SOLIDIFY'); md.thickness = t; md.offset = off; md.use_rim = rim; md.use_even_offset = False
    return md


def shade(o, sub=1):
    for p in o.data.polygons: p.use_smooth = True
    if sub:
        md = o.modifiers.new('smooth', 'SUBSURF'); md.levels = sub; md.render_levels = sub


def fold_noise(co, s, seed, oct=2):
    v = 0.0; a = 1.0
    for k in range(oct):
        v += a * noise3(co, s * (2 ** k), seed + k); a *= 0.5
    return v


def _seg(p, a, b):
    ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return a + ab * t, t


def tube_push(B, co, tubes):
    """Push a point out to a tailored tube radius around the nearest limb segment (sleeves, trouser legs)."""
    best = None
    for a, b, ra, rb, wfn in tubes:
        q, t = _seg(co, a, b); d = (co - q).length
        if best is None or d < best[0]: best = (d, q, ra + (rb - ra) * t, wfn)
    d, q, r, wfn = best
    w = wfn(co)
    if w <= 0 or d >= r or d < 1e-6: return co
    return co + (co - q).normalized() * (r - d) * w


def relax(o, B, iters=12, factor=0.6, min_d=0.01, min_fn=None, keep_boundary=True, tubes=None):
    """Drape pass: smooth the garment (it stops following every muscle) while holding it at least min_d (or
    min_fn(co)) outside the body surface. This is the 'settle on the body' step before the folds are sculpted in."""
    me = o.data; bm = bmesh.new(); bm.from_mesh(me)
    mw = o.matrix_world; mi = mw.inverted()
    verts = [v for v in bm.verts if not (keep_boundary and v.is_boundary)]
    for it in range(iters):
        bmesh.ops.smooth_vert(bm, verts=verts, factor=factor, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        for v in bm.verts:
            co = mw @ v.co
            loc, nrm, idx, dist = B.bvh.find_nearest(co)
            if loc is None: continue
            d = min_fn(co) if min_fn else min_d
            side = (co - loc).dot(nrm)
            if side < d: co = co + nrm * (d - side)
            if tubes: co = tube_push(B, co, tubes)
            v.co = mi @ co
    bm.to_mesh(me); bm.free(); me.update()


def flatten_cuffs(o, B, t_off):
    """Square off a ragged sleeve/glove cuff: boundary verts near a wrist go onto a plane across the forearm."""
    me = o.data; bm = bmesh.new(); bm.from_mesh(me)
    for s in 'LR':
        w = B.p['wrist.' + s]; a = (w - B.p['lowerarm01.' + s]).normalized()
        for v in bm.verts:
            if v.is_boundary and (v.co - w).length < 0.09 and abs(((v.co - w) - a * (v.co - w).dot(a)).length) < 0.07:
                t = (v.co - w).dot(a)
                if abs(t - t_off) < 0.05: v.co -= a * (t - t_off)
    bm.to_mesh(me); bm.free()


def knit(B, coll, M):
    def keep(c, w):
        if c.z < B.p['pelvis.L'].z + 0.05: return False
        if bone_sum(w, 'head', 'jaw') > 0.25: return False
        if c.z > B.chin.z - 0.03: return False
        arms = bone_sum(w, 'lowerarm', 'wrist', 'finger', 'metacarpal')
        return arms < 0.3
    o = body_copy(B, 'finn_knit', keep, coll)
    subdivide(o, 1)
    neck_z = B.p['neck01'].z
    top_z = B.chin.z - 0.03

    def mind(co):
        t = (co.z - neck_z) / max(0.001, top_z - neck_z)
        return 0.004 + (0.013 * math.sin(max(0, min(1, t)) * math.pi * 0.8 + 0.4) if co.z > neck_z - 0.02 else 0.0)
    relax(o, B, 10, 0.5, min_fn=mind)

    def f(co, n, w):
        rib = 0.0009 * (0.5 + 0.5 * math.sin(math.atan2(co.x, co.y - B.head.y) * 150))   # vertical knit ribs
        d = rib + 0.0015 * (0.5 + 0.5 * fold_noise(co, 16, 3))
        if co.z > neck_z - 0.02:                                              # roll-neck: soft horizontal folds
            d += 0.002 * (0.5 + 0.5 * math.sin(co.z * 380 + 2 * noise3(co, 20, 4)))
        return d
    offset(o, f)
    store_rest(o); o.data.materials.append(M['knit']); shade(o, 1); solidify(o, 0.003)
    arm(o, B.rig)
    return o


def waders(B, coll, M):
    chest_front = B.p['spine01'].z - 0.02
    boot_top = B.p['lowerleg02.L'].z - 0.02

    def keep(c, w):
        if bone_sum(w, 'upperarm', 'lowerarm', 'wrist', 'finger', 'metacarpal', 'neck', 'head') > 0.35: return False
        if abs(c.x) > 0.19 and c.z > B.p['spine03'].z: return False
        if c.z < boot_top - 0.03: return False
        top = chest_front if c.y < B.p['spine02'].y else chest_front - 0.06
        return c.z < top
    o = body_copy(B, 'finn_waders', keep, coll)
    subdivide(o, 1)
    knee = B.p['lowerleg01.L'].z
    hip = B.p['upperleg01.L'].z

    def mind(co):
        crotch = band(co.z, hip - 0.24, hip - 0.02, 0.05) * (1 - smooth((abs(co.x) - 0.06) / 0.05))
        return 0.013 + 0.014 * smooth((hip - co.z) / 0.15) + 0.03 * crotch   # bib close, legs and seat baggy
    tubes = []
    for sd in 'LR':
        hp, kn, an = B.p['upperleg01.' + sd], B.p['lowerleg01.' + sd], B.p['foot.' + sd]
        legw = lambda co: smooth((hip - 0.05 - co.z) / 0.1)
        tubes += [(hp, kn, 0.11, 0.088, legw), (kn, an, 0.088, 0.074, legw)]
    relax(o, B, 28, 0.7, min_fn=mind, tubes=tubes)

    def f(co, n, w):
        leg = smooth((hip - co.z) / 0.12)
        d = 0.0
        d += 0.007 * band(co.z, boot_top, boot_top + 0.16, 0.04) * (0.5 + 0.5 * math.sin(co.z * 140 + 3 * noise3(co, 9, 1)))   # bunching over the boot
        d += 0.005 * band(co.z, knee - 0.07, knee + 0.09, 0.03) * max(0, math.sin(co.z * 110 + co.x * 40))                 # knee creases
        d += 0.004 * leg * (0.5 + 0.5 * math.sin((co.z * 28 + co.x * 22) + 2 * noise3(co, 6, 2)))                         # long drapes
        d += 0.0015 * (0.5 + 0.5 * fold_noise(co, 14, 4))
        return d
    offset(o, f)
    store_rest(o); o.data.materials.append(M['wader']); shade(o, 1); solidify(o, 0.004)
    arm(o, B.rig)
    return o


def boots(B, coll, M):
    top = B.p['lowerleg02.L'].z - 0.02

    def keep(c, w):
        return c.z < top and bone_sum(w, 'foot', 'toe', 'lowerleg') > 0.4
    o = body_copy(B, 'finn_boots', keep, coll)
    subdivide(o, 1)
    relax(o, B, 24, 0.7, min_fn=lambda co: 0.026 + 0.008 * band(co.z, top - 0.05, top, 0.02) + 0.006 * smooth((0.07 - co.z) / 0.04))

    def f(co, n, w):
        return 0.0025 * max(0.0, math.sin(co.z * 160)) * band(co.z, 0.12, top - 0.07, 0.02) + 0.001 * fold_noise(co, 30, 6)
    offset(o, f)
    for v in o.data.vertices:                      # flat sole under the foot
        if v.co.z < 0.015: v.co.z = 0.0
    store_rest(o); o.data.materials.append(M['boot']); shade(o, 1); solidify(o, 0.004)
    for s, side in ((1, 'L'), (-1, 'R')):          # lug sole slab
        ft = B.p['foot.' + side]; toe = B.t['foot.' + side]
        xs = [v.co.x for v in o.data.vertices if v.co.z < 0.02 and v.co.x * s > 0]
        ys = [v.co.y for v in o.data.vertices if v.co.z < 0.02 and v.co.x * s > 0]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        for v in bm.verts: v.co = Vector((v.co.x * (max(xs) - min(xs)) * 0.92, v.co.y * (max(ys) - min(ys)) * 0.96, v.co.z * SOLE))
        me = bpy.data.meshes.new('sole'); bm.to_mesh(me); bm.free()
        so = bpy.data.objects.new('finn_sole_' + side, me); coll.objects.link(so)
        so.location = (cx, cy, -SOLE * 0.5); so.data.materials.append(M['sole'])
        bv = so.modifiers.new('b', 'BEVEL'); bv.width = 0.008; bv.segments = 3
        bind(so, o, B.rig)
    arm(o, B.rig)
    return o


def gloves(B, coll, M):
    def keep(c, w):
        h = bone_sum(w, 'wrist', 'metacarpal', 'finger')
        if h + bone_sum(w, 'lowerarm02') < 0.5: return False
        if bone_sum(w, 'lowerarm02') > 0.6 and bone_sum(w, 'wrist') < 0.2: return False
        # fingerless: drop the middle and tip segments of every finger (and the thumb tip)
        if bone_sum(w, 'finger2-2', 'finger3-2', 'finger4-2', 'finger5-2', 'finger2-3', 'finger3-3', 'finger4-3', 'finger5-3', 'finger1-3') > 0.45:
            return False
        return True
    o = body_copy(B, 'finn_gloves', keep, coll)
    subdivide(o, 1)
    flatten_cuffs(o, B, -0.045)

    def f(co, n, w):
        d = 0.0022 + 0.003 * bone_sum(w, 'lowerarm', 'wrist')
        return d + 0.0005 * fold_noise(co, 60, 5)
    offset(o, f)
    store_rest(o); o.data.materials.append(M['glove']); shade(o, 1); solidify(o, 0.002)
    arm(o, B.rig)
    return o


def jacket(B, coll, M):
    """Long open waxed jacket: body copy of torso and sleeves, the skirt extruded from the hip loop to the knee,
    settled on the body (relax), then sculpted folds; open front, pocket flaps with brass snaps."""
    hip = B.p['upperleg01.L'].z + 0.02
    wrist = B.p['wrist.L']

    def keep(c, w):
        if c.z < hip: return False
        if bone_sum(w, 'neck', 'head', 'jaw') > 0.3: return False
        if bone_sum(w, 'wrist', 'finger', 'metacarpal') > 0.25: return False
        return True
    o = body_copy(B, 'finn_jacket', keep, coll)
    subdivide(o, 1)
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    ycut = B.p['spine03'].y - 0.03

    def half(z):
        t = (B.p['spine01'].z + 0.05 - z) / 0.5
        return 0.075 + 0.05 * smooth(t)
    knee = B.p['lowerleg01.L'].z - 0.04
    cy = B.p['spine05'].y
    bnd = [e for e in bm.edges if e.is_boundary and all(abs(v.co.z - hip) < 0.06 for v in e.verts)]
    rings = 10; cur = bnd
    for k in range(1, rings + 1):
        t = k / rings
        res = bmesh.ops.extrude_edge_only(bm, edges=cur)
        nv = [x for x in res['geom'] if isinstance(x, bmesh.types.BMVert)]
        for v in nv:
            r = Vector((v.co.x, v.co.y - cy, 0))
            grow = 1.0 + (0.03 + 0.05 * t) / max(0.12, r.length) / rings * 2.2
            v.co.x = r.x * grow; v.co.y = cy + r.y * grow; v.co.z = hip - (hip - knee) * t
        cur = [x for x in res['geom'] if isinstance(x, bmesh.types.BMEdge) and all(v in nv for v in x.verts)]
    kill = [f for f in bm.faces if f.calc_center_median().y < ycut and abs(f.calc_center_median().x) < half(f.calc_center_median().z)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]; bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me); bm.free()
    # skirt weights: blend the hip weights toward the leg weights below
    sk = o.vertex_groups.new(name='finn_skirt')
    for v in me.vertices:
        if v.co.z < hip - 0.01: sk.add([v.index], smooth((hip - v.co.z) / 0.15), 'REPLACE')
    md = o.modifiers.new('wt', 'DATA_TRANSFER'); md.object = B.b; md.use_vert_data = True
    md.data_types_verts = {'VGROUP_WEIGHTS'}; md.vert_mapping = 'POLYINTERP_NEAREST'
    md.layers_vgroup_select_src = 'ALL'; md.layers_vgroup_select_dst = 'NAME'; md.vertex_group = 'finn_skirt'; md.mix_factor = 0.6
    set_active(o); apply_mod(o, 'wt')

    def mind(co):
        if co.z < hip: return 0.04 + 0.05 * smooth((hip - co.z) / (hip - knee))
        armw = B.arm_w(co)
        return 0.03 - 0.012 * armw
    tubes = []
    for sd in 'LR':
        sh, el, wr = B.p['upperarm01.' + sd], B.p['lowerarm01.' + sd], B.p['wrist.' + sd]
        tubes += [(sh, el, 0.082, 0.07, lambda co: smooth((B.arm_w(co) - 0.3) / 0.4)),
                  (el, wr, 0.07, 0.058, lambda co: smooth((B.arm_w(co) - 0.3) / 0.4))]
    relax(o, B, 30, 0.7, min_fn=mind, keep_boundary=False, tubes=tubes)
    # straighten the front edges of the opening
    me = o.data; bm = bmesh.new(); bm.from_mesh(me)
    for v in bm.verts:
        if v.is_boundary and v.co.y < ycut + 0.03 and abs(v.co.x) < half(v.co.z) + 0.08 and v.co.z < B.p['neck01'].z - 0.04 and abs(v.co.x) < 0.2:
            v.co.x = math.copysign(half(v.co.z), v.co.x)
    bm.to_mesh(me); bm.free()
    flatten_cuffs(o, B, -0.03)
    elbow = B.p['lowerarm01.L']
    shoulder = B.p['upperarm01.L'].z

    def f(co, n, w):
        armw = bone_sum(w, 'upperarm', 'lowerarm', 'wrist')
        ang = math.atan2(co.x, co.y - cy)
        if co.z < hip:                                                   # skirt: hanging vertical folds, deeper at the hem
            t = (hip - co.z) / (hip - knee)
            d = (0.006 + 0.04 * t) * abs(math.sin(ang * 6 + 1.3 * noise3(co, 3, 7))) ** 0.7
            d += 0.004 * t * (0.5 + 0.5 * math.sin(ang * 21 + co.z * 4))
            return d
        d = 0.0
        if armw < 0.3:                                                   # torso: soft vertical drape below the chest
            d += 0.014 * band(co.z, hip, B.p['spine02'].z, 0.06) * abs(math.sin(ang * 7 + noise3(co, 4, 8))) ** 0.6
        else:                                                            # sleeves: elbow and wrist compression, twist folds
            ax = Vector((abs(co.x), co.y, co.z))
            de = (ax - elbow).length
            d += 0.013 * smooth(1 - de / 0.13) * max(0.0, math.sin(de * 140 + noise3(co, 9, 9) * 2.5))
            dw = (ax - wrist).length
            d += 0.011 * smooth(1 - dw / 0.16) * max(0.0, math.sin(dw * 170 + noise3(co, 11, 10) * 2))
            d += 0.012 * armw * abs(math.sin(co.z * 55 + abs(co.x) * 45 + 2 * noise3(co, 7, 11))) ** 0.6
        return d + 0.002 * (0.5 + 0.5 * fold_noise(co, 10, 12, 3))
    offset(o, f)
    store_rest(o)
    o.data.materials.append(M['jacket']); o.data.materials.append(M['lining'])
    shade(o, 1)
    sol = solidify(o, 0.007); sol.material_offset = 1; sol.material_offset_rim = 0
    arm(o, B.rig)
    flaps(B, o, coll, M)
    return o


def collar(B, coll, M, knit_o):
    """Standing corduroy collar: a clean band around the neck base, open at the front, flaring a little outward."""
    bvh = B.bvh
    nk = B.p['neck01']; c = Vector((0, nk.y + 0.005, 0))
    z0 = nk.z - 0.03; hgt = 0.05
    nu, nv = 48, 5
    bm = bmesh.new(); grid = []
    for j in range(nv + 1):
        row = []
        t = j / nv
        for i in range(nu + 1):
            a = math.radians(-155 + 310 * i / nu)                   # 0 = back, the gap is at the front
            d = Vector((math.sin(a), math.cos(a), 0))
            z = z0 + hgt * t - 0.012 * (1 - abs(math.cos(a / 2)))   # dips toward the front
            hit = bvh.ray_cast(Vector((c.x, c.y, z)) + d * 0.3, -d, 0.4)
            r = (hit[0] - Vector((c.x, c.y, z))).length if hit[0] else 0.075
            row.append((Vector((c.x, c.y, z)), d, min(r, 0.11) + 0.032 + 0.008 * t * t))
        rs = [x[2] for x in row]
        for _ in range(10): rs = [rs[0]] + [(rs[i - 1] + 2 * rs[i] + rs[i + 1]) / 4 for i in range(1, len(rs) - 1)] + [rs[-1]]
        row = [bm.verts.new(c0 + d0 * rv) for (c0, d0, _), rv in zip(row, rs)]
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    me = bpy.data.meshes.new('finn_collar'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('finn_collar', me); coll.objects.link(o); o.data.materials.append(M['cord'])
    for p in me.polygons: p.use_smooth = True
    store_rest(o)
    md = o.modifiers.new('t', 'SOLIDIFY'); md.thickness = 0.006; md.offset = 1
    md = o.modifiers.new('s', 'SUBSURF'); md.levels = 1; md.render_levels = 2
    bind(o, knit_o, B.rig)
    return o


def beard_shell(B, coll):
    """Painted beard base under the strands: a thin shell over the beard area that keeps the face shape keys (so it
    talks with the mouth), dark copper with soft alpha edges, so the trimmed beard reads dense at phone size."""
    b = B.b
    gb = b.vertex_groups['finn_beard'].index; gm = b.vertex_groups['finn_moustache'].index
    me = b.data.copy(); me.name = 'finn_beardshell'
    o = bpy.data.objects.new('finn_beardshell', me); coll.objects.link(o); o.matrix_world = b.matrix_world
    wv = {}
    for v in me.vertices:
        w = 0.0
        for g in v.groups:
            if g.group in (gb, gm): w = max(w, g.weight)
        wv[v.index] = w
    bm = bmesh.new(); bm.from_mesh(me)
    kill = [f for f in bm.faces if max(wv[v.index] for v in f.verts) < 0.05]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]; bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me); bm.free()
    me.materials.clear()
    for md in list(o.modifiers): o.modifiers.remove(md)
    # push every shape key out along the normals (shape keys are absolute positions)
    me.update()
    nrm = [v.normal.copy() for v in me.vertices]
    gbi = o.vertex_groups['finn_beard'].index; gmi = o.vertex_groups['finn_moustache'].index
    att = me.color_attributes.new('finn_beardw', 'FLOAT_COLOR', 'POINT')
    for v in me.vertices:
        w = max([g.weight for g in v.groups if g.group in (gbi, gmi)] or [0.0])
        att.data[v.index].color = (w, w, w, 1)
    if me.shape_keys:
        for kb in me.shape_keys.key_blocks:
            for i, d in enumerate(kb.data): d.co = d.co + nrm[i] * 0.0012
    else:
        for i, v in enumerate(me.vertices): v.co = v.co + nrm[i] * 0.0012
    m = bpy.data.materials.new('finn_beardbase'); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links
    m.surface_render_method = 'DITHERED'
    bsdf = N['Principled BSDF']; bsdf.inputs['Roughness'].default_value = 0.65
    ca = N.new('ShaderNodeAttribute'); ca.attribute_name = 'finn_beardw'
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 260; nz.inputs['Detail'].default_value = 4
    ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (*lin('#5a3019'), 1); ramp.color_ramp.elements[1].color = (*lin('#8a5230'), 1)
    L.new(nz.outputs['Fac'], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    # alpha = weight with a stubble break-up at the edge
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.05; mr.inputs['From Max'].default_value = 0.6
    L.new(ca.outputs['Fac'], mr.inputs['Value']); L.new(mr.outputs[0], bsdf.inputs['Alpha'])
    me.materials.append(m)
    for p in me.polygons: p.use_smooth = True
    arm(o, B.rig)
    return o


def _surface_patch(name, target, center, size, normal_hint, coll, mat, thick=0.004, curve=0.0, res=(8, 4)):
    """A flap shaped onto a surface: grid projected onto target (raycast along -normal_hint) and offset out."""
    dg = bpy.context.evaluated_depsgraph_get(); bvh = BVHTree.FromObject(target, dg)
    nh = Vector(normal_hint).normalized()
    up = Vector((0, 0, 1)); right = up.cross(nh).normalized()
    bm = bmesh.new(); grid = []
    for j in range(res[1] + 1):
        row = []
        for i in range(res[0] + 1):
            u = (i / res[0] - 0.5) * size[0]; vv = (j / res[1] - 0.5) * size[1]
            if j == 0: u *= 0.92                                     # flap tapers a little toward its edge
            p = Vector(center) + right * u + up * vv + nh * 0.2
            hit = bvh.ray_cast(p, -nh, 0.5)
            q = (hit[0] + hit[1].normalized() * 0.004) if hit[0] else p - nh * 0.2
            row.append(bm.verts.new(q))
        grid.append(row)
    for j in range(res[1]):
        for i in range(res[0]):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat)
    md = o.modifiers.new('t', 'SOLIDIFY'); md.thickness = thick; md.offset = 1
    md = o.modifiers.new('b', 'BEVEL'); md.width = 0.0015; md.segments = 2
    for p in o.data.polygons: p.use_smooth = True
    return o, bvh


def flaps(B, jk, coll, M):
    """Chest and hip pocket flaps with brass snaps, conformed to the jacket and rigged with its weights."""
    specs = []
    for s in (1, -1):
        specs.append((Vector((s * 0.115, -0.3, B.p['spine02'].z + 0.07)), (0.12, 0.05), Vector((0.25 * s, -1, 0.05))))
        specs.append((Vector((s * 0.16, -0.3, B.p['upperleg01.L'].z - 0.06)), (0.16, 0.06), Vector((0.35 * s, -1, 0.0))))
    for k, (c, sz, nh) in enumerate(specs):
        hit = BVHTree.FromObject(jk, bpy.context.evaluated_depsgraph_get()).ray_cast(c + nh.normalized() * 0.4, -nh.normalized(), 1.0)
        if not hit[0]: continue
        o, bvh = _surface_patch(f'finn_flap{k}', jk, hit[0], sz, nh, coll, M['jacket'], thick=0.004)
        store_rest(o); bind(o, jk, B.rig)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.0065, depth=0.004, vertices=20,
                                            location=hit[0] + hit[1].normalized() * 0.01 - Vector((0, 0, sz[1] * 0.18)))
        sn = bpy.context.active_object; sn.name = f'finn_snap{k}'
        sn.rotation_euler = hit[1].to_track_quat('Z', 'Y').to_euler(); link(sn, coll)
        sn.data.materials.append(M['brass']); bpy.ops.object.shade_smooth()
        bind(sn, jk, B.rig)


def braces(B, coll, M, knit_o):
    """Dark braces from the wader bib over the shoulders, brass clips at the front."""
    dg = bpy.context.evaluated_depsgraph_get(); bvh = BVHTree.FromObject(knit_o, dg)
    objs = []
    bib = B.p['spine01'].z - 0.02
    for s in (1, -1):
        pts = []
        path = [(s * 0.048, 'f', bib - 0.01), (s * 0.052, 'f', bib + 0.06), (s * 0.075, 'f', bib + 0.13), (s * 0.11, 'top', 0),
                (s * 0.095, 'b', bib + 0.14), (s * 0.06, 'b', bib + 0.0), (s * 0.035, 'b', bib - 0.07)]
        for x, side, z in path:
            if side == 'top':
                sh = B.p['shoulder01.' + ('L' if s > 0 else 'R')]
                o_, d_ = Vector((x, sh.y - 0.0, sh.z + 0.4)), Vector((0, 0, -1))
            else:
                o_, d_ = (Vector((x, -0.5, z)), Vector((0, 1, 0))) if side == 'f' else (Vector((x, 0.5, z)), Vector((0, -1, 0)))
            hit = bvh.ray_cast(o_, d_, 1.0)
            if hit[0]: pts.append(hit[0] + hit[1].normalized() * 0.004)
        cu = bpy.data.curves.new('brace', 'CURVE'); cu.dimensions = '3D'; sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
        sp.type = 'NURBS'; sp.order_u = 3; sp.use_endpoint_u = True; cu.resolution_u = 8
        prof = bpy.data.curves.new('brace_prof', 'CURVE'); ps = prof.splines.new('POLY'); ps.points.add(3)
        for i, (a, c) in enumerate(((-0.017, -0.0015), (0.017, -0.0015), (0.017, 0.0015), (-0.017, 0.0015))): ps.points[i].co = (a, c, 0, 1)
        ps.use_cyclic_u = True
        po = bpy.data.objects.new('brace_prof', prof); coll.objects.link(po)
        cu.bevel_mode = 'OBJECT'; cu.bevel_object = po; cu.use_fill_caps = True; cu.twist_mode = 'MINIMUM'
        co = bpy.data.objects.new('finn_brace', cu); coll.objects.link(co)
        set_active(co); bpy.ops.object.convert(target='MESH'); bo = bpy.context.active_object
        bpy.data.objects.remove(po)
        bo.data.materials.clear(); bo.data.materials.append(M['brace']); store_rest(bo)
        print('[finn] brace pts', len(pts), [tuple(round(x, 3) for x in p) for p in pts[:3]])
        bind(bo, knit_o, B.rig); objs.append(bo)
        # clip
        bpy.ops.mesh.primitive_cube_add(size=1, location=pts[0] + Vector((0, -0.006, 0.005)))
        cl = bpy.context.active_object; cl.name = 'finn_clip'; cl.scale = (0.024, 0.006, 0.03); link(cl, coll)
        bpy.ops.object.transform_apply(scale=True)
        bv = cl.modifiers.new('b', 'BEVEL'); bv.width = 0.003; bv.segments = 3
        cl.data.materials.append(M['brass']); bind(cl, knit_o, B.rig); objs.append(cl)
    return objs


# ----------------------------------------------------------------------------------------------- hat, glasses, lures
def head_bvh(B):
    return B.bvh


def head_ring(B, z, offset_out, n=64, tilt=0.0):
    """Ring around the head at height z (tilted front-up by tilt rad), offset_out metres outside the skin."""
    c = Vector((0, B.head.y - 0.005, z)); pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        d = Vector((math.sin(a), -math.cos(a), 0))
        zz = z + tilt * (-d.y) * 0.1
        o_ = Vector((c.x, c.y, zz)) + d * 0.4
        hit = B.bvh.ray_cast(o_, -d, 0.5)
        r = ((hit[0] - Vector((c.x, c.y, zz))).length if hit[0] else 0.09) + offset_out
        pts.append(Vector((c.x, c.y, zz)) + d * r)
    return pts


def hat(B, coll, M):
    """Sand canvas bucket hat: crown conformed to the head, sloped brim with stitched rings, olive band, 2 lures."""
    zb = B.eye.z + 0.052
    base = head_ring(B, zb, 0.010, 64, tilt=0.25)
    cen = sum(base, Vector()) / len(base)
    bm = bmesh.new(); rings = []
    # crown: from the base ring up to a softly domed top, slight taper, a dent across the top
    prof = [(0.0, 1.0), (0.025, 0.985), (0.05, 0.955), (0.07, 0.915), (0.082, 0.86), (0.09, 0.72), (0.094, 0.48), (0.096, 0.0)]
    top_z = B.top + 0.004
    for h, sc in prof:
        ring = []
        for p in base:
            q = cen + (p - cen) * sc
            z = p.z + (top_z - zb) * (h / prof[-1][0])
            z -= 0.006 * (1 - sc) * (1 + math.cos(math.atan2(p.x - cen.x, p.y - cen.y) * 2)) * (h > 0.07)
            ring.append(bm.verts.new((q.x, q.y, z)))
        rings.append(ring)
    # brim: out and down from the base, 6 cm wide, a rolled edge
    brim = [(0.004, -0.005), (0.02, -0.016), (0.035, -0.026), (0.05, -0.037), (0.06, -0.044), (0.064, -0.048), (0.064, -0.053)]
    brim_rings = []
    for wdt, dz in brim:
        ring = []
        for p in base:
            d = (p - cen); d.z = 0; d.normalize()
            ww = wdt * (1.0 - 0.12 * max(0, d.y))                     # a touch shorter at the back
            ring.append(bm.verts.new(p + d * ww + Vector((0, 0, dz))))
        brim_rings.append(ring)
    allr = list(reversed(rings[1:])) + [rings[0]] + brim_rings
    allr = list(reversed(allr))
    n = len(base)
    for r in range(len(allr) - 1):
        for i in range(n):
            bm.faces.new((allr[r][i], allr[r][(i + 1) % n], allr[r + 1][(i + 1) % n], allr[r + 1][i]))
    top_c = bm.verts.new(sum((v.co for v in rings[-1]), Vector()) / n)
    for i in range(n): bm.faces.new((rings[-1][i], rings[-1][(i + 1) % n], top_c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('finn_hat'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('finn_hat', me); coll.objects.link(o)
    o.data.materials.append(M['hat'])
    # stitched rings on the brim: shallow grooves
    for v in me.vertices:
        p = Vector(v.co); d = Vector((p.x - cen.x, p.y - cen.y, 0)).length
    for p in me.polygons: p.use_smooth = True
    md = o.modifiers.new('t', 'SOLIDIFY'); md.thickness = 0.003; md.offset = 1
    md = o.modifiers.new('s', 'SUBSURF'); md.levels = 2; md.render_levels = 2
    store_rest(o)
    # stitch lines on the brim and crown (thin dark tubes)
    parts = [o]
    stitch = simple('finn_stitch', '#8c7a55', 0.8)
    for ring_i, frac in ((1, None), (2, None), (3, None), (4, None)):
        w = brim[ring_i]
        pts = []
        for p in base[::2] + [base[0]]:
            d = (p - cen); d.z = 0; d.normalize(); ww = w[0] * (1.0 - 0.12 * max(0, d.y)) + 0.006
            pts.append(p + d * ww + Vector((0, 0, w[1] + 0.0035 - 0.003 * (ww / 0.06))))
        parts.append(_tube('finn_stitch', pts, 0.0009, coll, stitch))
    # olive band around the crown base
    bpts = []
    for hh in (0.004, 0.03):
        pass
    bm = bmesh.new(); r0 = []; r1 = []
    for p in base:
        d = (p - cen); d.z = 0; d.normalize()
        r0.append(bm.verts.new(p + d * 0.0035 + Vector((0, 0, 0.003))))
        r1.append(bm.verts.new(p + d * 0.0025 + Vector((0, 0, 0.026))))
    for i in range(n): bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
    me = bpy.data.meshes.new('finn_hatband'); bm.to_mesh(me); bm.free()
    bo = bpy.data.objects.new('finn_hatband', me); coll.objects.link(bo); bo.data.materials.append(M['band'])
    md = bo.modifiers.new('t', 'SOLIDIFY'); md.thickness = 0.002; md.offset = 1
    for p in me.polygons: p.use_smooth = True
    store_rest(bo); parts.append(bo)
    # lures pinned on the band (front-left and left side)
    for k, (ang, col, ln) in enumerate(((math.radians(32), M['lureA'], 0.052), (math.radians(78), M['lureB'], 0.044))):
        i = int(ang / (2 * math.pi) * n) % n
        p = base[i]; d = (p - cen); d.z = 0; d.normalize()
        parts += lure(f'finn_hatlure{k}', p + d * 0.008 + Vector((0, 0, 0.016)), d, col, ln, coll, M)
    return parts


def _tube(name, pts, r, coll, mat, cyclic=False):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
    sp.use_cyclic_u = cyclic; sp.type = 'NURBS'; sp.order_u = 3; sp.use_endpoint_u = not cyclic
    cu.bevel_depth = r; cu.bevel_resolution = 2; cu.resolution_u = 6; cu.use_fill_caps = True
    o = bpy.data.objects.new(name, cu); coll.objects.link(o); o.data.materials.append(mat)
    return o


def lure(name, pos, out, mat, length, coll, M):
    """Small crankbait: fat tapered body, clear lip, painted eye, two tiny treble hooks with split rings."""
    out = out.normalized(); fwd = Vector((0, 0, 1)).cross(out).normalized()   # body axis tangent to the band
    up = out.cross(fwd)
    parts = []
    bm = bmesh.new()
    segs = 16; rings = 10
    vs = []
    for j in range(rings + 1):
        t = j / rings
        prof = math.sin(math.pi * min(1, t * 1.05)) ** 0.7 * (1 - 0.35 * t)
        rr = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            q = pos + fwd * (t - 0.5) * length + out * math.cos(a) * 0.17 * length * prof * 0.75 + up * math.sin(a) * 0.17 * length * prof * 1.15
            rr.append(bm.verts.new(q))
        vs.append(rr)
    for j in range(rings):
        for i in range(segs):
            bm.faces.new((vs[j][i], vs[j][(i + 1) % segs], vs[j + 1][(i + 1) % segs], vs[j + 1][i]))
    for rr in (vs[0], vs[-1]):
        c = bm.verts.new(sum((v.co for v in rr), Vector()) / segs)
        for i in range(segs): bm.faces.new((rr[i], rr[(i + 1) % segs], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    md = o.modifiers.new('s', 'SUBSURF'); md.levels = 1; md.render_levels = 2
    parts.append(o)
    # lip
    bpy.ops.mesh.primitive_plane_add(size=1, location=pos - fwd * length * 0.55 - up * length * 0.06)
    lp = bpy.context.active_object; lp.name = name + '_lip'; lp.scale = (length * 0.12, length * 0.15, 1)
    lp.rotation_euler = (Matrix((fwd, out, up)).transposed() @ Matrix.Rotation(math.radians(60), 3, 'X')).to_euler()
    link(lp, coll); lp.data.materials.append(simple('finn_lip_clear', '#9fb3b8', 0.05, spec=0.8))
    sd = lp.modifiers.new('t', 'SOLIDIFY'); sd.thickness = 0.001; parts.append(lp)
    # eyes
    for s in (1, -1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=length * 0.045, segments=12, ring_count=8,
                                             location=pos - fwd * length * 0.3 + out * s * length * 0.1 + up * length * 0.03)
        e = bpy.context.active_object; e.name = name + '_eye'; link(e, coll); e.data.materials.append(simple('finn_lure_eye', '#111111', 0.1, coat=1))
        parts.append(e)
    # treble hooks under the belly and at the tail
    steel = M['steel']
    for t in (-0.05, 0.42):
        a = pos + fwd * t * length - up * length * 0.17
        parts.append(_tube(name + '_ring', [a, a - up * 0.004 + fwd * 0.002, a - up * 0.006], 0.0004, coll, steel))
        for k in range(3):
            ang = 2 * math.pi * k / 3
            dd = (out * math.cos(ang) + fwd * math.sin(ang)) * 0.0045
            b0 = a - up * 0.006
            pts = [b0, b0 - up * 0.008 + dd * 0.2, b0 - up * 0.012 + dd, b0 - up * 0.01 + dd * 1.6, b0 - up * 0.0065 + dd * 1.4]
            parts.append(_tube(name + '_hook', pts, 0.00045, coll, steel))
    return parts


def sunglasses(B, coll, M):
    """Wraparound shield: lens follows the face 15-18 mm out, from temple to temple, thin dark frame, temple arms."""
    E = B.eye; cy = B.head.y - 0.005
    lens_top = E.z + 0.021; lens_bot = E.z - 0.025
    nu, nv = 40, 10
    bm = bmesh.new(); grid = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            a = math.radians(-76 + 152 * i / nu)                          # around the head, 0 = straight ahead
            s = abs(math.degrees(a)) / 76
            top = lens_top + 0.002 * (1 - s) - 0.006 * s ** 2
            bot = lens_bot + 0.004 * s + 0.016 * s ** 2
            # nose bridge notch
            bot += 0.016 * math.exp(-(math.degrees(a) / 9) ** 2)
            z = bot + (top - bot) * (j / nv)
            d = Vector((math.sin(a), -math.cos(a), 0))
            hit = B.bvh.ray_cast(Vector((0, cy, z)) + d * 0.4, -d, 0.5)
            r = (hit[0] - Vector((0, cy, z))).length if hit[0] else 0.09
            # keep a smooth cylinder-like shield: distance from the brow ridge, not every bump of the face
            row.append((Vector((0, cy, z)), d, r + 0.013))
        # smooth the radii along the row so the shield is one clean curve
        rs = [x[2] for x in row]
        for _ in range(6): rs = [rs[0]] + [(rs[i - 1] + 2 * rs[i] + rs[i + 1]) / 4 for i in range(1, len(rs) - 1)] + [rs[-1]]
        row = [bm.verts.new(c0 + d0 * max(rv, 0.075)) for (c0, d0, _), rv in zip(row, rs)]
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    me = bpy.data.meshes.new('finn_lens'); bm.to_mesh(me); bm.free()
    lens = bpy.data.objects.new('finn_lens', me); coll.objects.link(lens); lens.data.materials.append(M['lens'])
    for p in me.polygons: p.use_smooth = True
    # smooth the shield (laplacian keeps the shape clean)
    md = lens.modifiers.new('t', 'SOLIDIFY'); md.thickness = 0.0022; md.offset = 1
    md = lens.modifiers.new('s', 'SUBSURF'); md.levels = 1; md.render_levels = 2
    parts = [lens]
    # frame along the top edge and the outer ends; temple arms back to the ears
    top = [grid[-1][i].co.copy() if False else None for i in range(0)]
    me_v = lens.data.vertices
    toprow = [me_v[(nv) * (nu + 1) + i].co.copy() for i in range(nu + 1)]
    botrow = [me_v[i].co.copy() for i in range(nu + 1)]
    fr = M['frame']
    parts.append(_tube('finn_frame_top', [p + Vector((0, 0, 0.0012)) for p in toprow], 0.0021, coll, fr))
    for side in (0, nu):
        pts = [botrow[side], (botrow[side] + toprow[side]) / 2, toprow[side]]
        parts.append(_tube('finn_frame_end', pts, 0.0022, coll, fr))
        end = toprow[side] - Vector((0, 0, 0.004)); sgn = 1 if end.x > 0 else -1
        ear = B.p['head'] + Vector((sgn * 0.078, 0.012, B.eye.z - B.p['head'].z + 0.008))
        mid = (end + ear) / 2 + Vector((sgn * 0.004, 0, 0.002))
        hook = ear + Vector((-sgn * 0.004, 0.022, -0.02))
        parts.append(_tube('finn_temple', [end, mid, ear, hook], 0.0018, coll, fr))
    # nose pads
    for s in (1, -1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0035, location=(s * 0.009, B.nose.y + 0.022, B.eye.z - 0.012))
        np_ = bpy.context.active_object; np_.name = 'finn_nosepad'; np_.scale = (0.5, 1, 1.4); link(np_, coll)
        np_.data.materials.append(simple('finn_pad', '#9aa3a6', 0.3)); parts.append(np_)
    return parts


def parent_to_bone(objs, rig, bone):
    bpy.context.view_layer.update()
    for o in objs:
        mw = o.matrix_world.copy()
        o.parent = rig; o.parent_type = 'BONE'; o.parent_bone = bone
        o.matrix_world = mw


def mouth_bag(B, coll):
    """Dark mouth interior behind the teeth so a shout reads as an open mouth, not a hole."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=24, ring_count=12, location=(0, B.lips.y + 0.032, B.lips.z - 0.006))
    o = bpy.context.active_object; o.name = 'finn_mouthbag'; o.scale = (0.024, 0.03, 0.022); link(o, coll)
    o.data.materials.append(simple('finn_mouth', '#3a1416', 0.7, spec=0.3))
    for p in o.data.polygons: p.use_smooth = True
    return o


# ------------------------------------------------------------------------------------------------------- face shapes
def derive_face_keys(b):
    """Half-face keys for the smirk from the symmetric expression units (left / right by x with a soft centre)."""
    kb = b.data.shape_keys.key_blocks; basis = kb['Basis']
    for src, dst in (('x_mouth-corner-puller', 'f_smile'), ('x_mouth-upward-retraction', 'f_upret'), ('x_nose-left-elevation', None)):
        if dst is None or src not in kb: continue
        for side, sgn in (('L', 1), ('R', -1)):
            k = b.shape_key_add(name=f'{dst}_{side}', from_mix=False)
            for i, v in enumerate(basis.data):
                w = smooth((sgn * v.co.x) / 0.012 + 0.5)
                k.data[i].co = v.co + (kb[src].data[i].co - v.co) * w
            k.value = 0.0


FACE = {   # mouth shapes -> shape key weights (per unit of `open` where marked) and jaw degrees at open=1
    'closed': {'jaw': 0.0, 'keys': {'x_mouth-compression': 0.15}},
    'talk': {'jaw': 9.0, 'open': 0.55, 'keys': {'x_mouth-open': 0.45, 'x_mouth-retraction': 0.12}},
    'shout': {'jaw': 21.0, 'open': 0.9, 'keys': {'x_mouth-open': 0.9, 'x_mouth-retraction': 0.45, 'x_mouth-upward-retraction': 0.25,
                                               'x_nose-left-elevation': 0.3, 'x_nose-right-elevation': 0.3}},
    'smirk': {'jaw': 1.5, 'open': 0.15, 'keys': {'f_smile_L': 0.85, 'f_upret_L': 0.35, 'x_mouth-compression': 0.25,
                                               'x_eyebrows-right-up': 0.0}},
}


def set_face(rig, mouth='closed', open=None, brow=0.0, blink=0.0):
    """Mouth shape, jaw opening (0..1, lip-sync amplitude), brows (-1 stern .. +1 raised), blink (0..1)."""
    bodies = _faces_of(rig)
    spec = FACE.get(mouth, FACE['closed'])
    o = spec.get('open', 0.0) if open is None else max(0.0, min(1.0, open))
    for body in bodies: _face_keys(body.data.shape_keys.key_blocks, spec, mouth, o, brow, blink)
    jaw = rig.pose.bones['jaw']
    rest = rig.get('finn_jaw_axis')
    ax = Vector(rest) if rest else Vector((1, 0, 0))
    jaw.rotation_mode = 'QUATERNION'
    jaw.rotation_quaternion = Quaternion(ax, math.radians(spec['jaw'] * o / max(0.01, spec.get('open', 1.0))) if spec['jaw'] else 0.0)


def _face_keys(kb, spec, mouth, o, brow, blink):
    for k in kb:
        if k.name.startswith(('x_', 'f_')): k.value = 0.0
    for name, w in spec['keys'].items():
        if name in kb:
            scale = o if name in ('x_mouth-open',) else 1.0
            kb[name].value = w * (scale if spec.get('open') else 1.0)
    if 'x_mouth-open' in kb and mouth in ('talk', 'shout'): kb['x_mouth-open'].value = spec['keys']['x_mouth-open'] * o / max(0.01, spec['open']) * spec['open']
    up = max(0.0, brow); dn = max(0.0, -brow)
    for side in ('left', 'right'):
        kb[f'x_eyebrows-{side}-up'].value = up * 0.9 + (0.25 if mouth == 'shout' else 0.0)
        kb[f'x_eyebrows-{side}-down'].value = dn * 0.9
        kb[f'x_eye-{side}-closure'].value = blink
    if mouth == 'smirk':                                             # one brow cocked
        kb['x_eyebrows-left-up'].value = min(1.0, kb['x_eyebrows-left-up'].value + 0.35)


def _faces_of(rig):
    out = [c for c in rig.children if c.type == 'MESH' and c.data.shape_keys and 'x_mouth-open' in c.data.shape_keys.key_blocks]
    if not out: raise RuntimeError('Finn body not found under the rig')
    return out


# ------------------------------------------------------------------------------------------------------- pose library
# A pose is a list of operations solved in order on the rest pose (A-pose), in Finn's own frame:
# +X = his left, -Y = forward (toward camera), +Z = up. Positions are offsets (m) from a bone's rest head.
#   ('rot', bone, axis, deg)                            rotate a bone (and its children) about a world axis
#   ('reach', side, (bone, offset), pole, fingers_dir, palm_dir)   2-bone IK wrist target + hand orientation
#   ('curl', side, {finger: deg}, spread)               flex fingers 1 (thumb) .. 5 at every joint
#   ('aim', bone, dir)                                  point a bone along a world direction
R_FIST = {1: 40, 2: 85, 3: 90, 4: 92, 5: 95}
RELAX = {1: 12, 2: 18, 3: 24, 4: 28, 5: 32}
PINCH = {1: 30, 2: 38, 3: 60, 4: 75, 5: 85}
POINT = {1: 45, 2: 2, 3: 95, 4: 98, 5: 100}
OPEN = {1: 4, 2: 6, 3: 8, 4: 10, 5: 12}
GRIP = {1: 50, 2: 70, 3: 75, 4: 78, 5: 82}
PHONE = {1: 22, 2: 30, 3: 38, 4: 45, 5: 52}

_ARMS_DOWN = [
    ('reach', 'L', ('upperleg01.L', (0.09, -0.05, -0.12)), (0.3, 1, 0), (0.05, -0.15, -1), (-1, 0.2, 0)),
    ('reach', 'R', ('upperleg01.R', (-0.09, -0.05, -0.12)), (-0.3, 1, 0), (-0.05, -0.15, -1), (1, 0.2, 0)),
    ('curl', 'L', RELAX, 4), ('curl', 'R', RELAX, 4),
]
_STANCE = [   # weight on his right leg, chest up, chin a touch up: confident
    ('rot', 'root', (0, 0, 1), -6), ('rot', 'spine04', (0, 1, 0), 1.5), ('rot', 'spine02', (1, 0, 0), -3),
    ('rot', 'upperleg01.L', (0, 1, 0), 3), ('rot', 'upperleg01.R', (0, 1, 0), 1), ('rot', 'neck01', (1, 0, 0), -2),
    ('rot', 'head', (1, 0, 0), -3),
]

POSES = {
    'neutral': _STANCE + _ARMS_DOWN,
    'hold_up': _STANCE + [
        ('reach', 'R', ('head', (-0.175, -0.10, -0.04)), (-1, 0.3, -0.6), (0.1, -0.25, 1), (0.25, -1, 0)),
        ('curl', 'R', PINCH, 2),
        ('reach', 'L', ('upperleg01.L', (0.09, -0.05, -0.12)), (0.3, 1, 0), (0.05, -0.15, -1), (-1, 0.2, 0)), ('curl', 'L', RELAX, 4),
        ('rot', 'head', (0, 1, 0), 4), ('rot', 'head', (0, 0, 1), -5),
    ],
    'present': _STANCE + [
        ('rot', 'spine03', (1, 0, 0), 6),
        ('reach', 'R', ('spine05', (-0.16, -0.36, 0.06)), (-1, 0.2, -0.4), (-0.2, -1, 0.05), (0, 0.05, 1)),
        ('reach', 'L', ('spine05', (0.16, -0.36, 0.06)), (1, 0.2, -0.4), (0.2, -1, 0.05), (0, 0.05, 1)),
        ('curl', 'L', OPEN, 10), ('curl', 'R', OPEN, 10), ('rot', 'head', (1, 0, 0), 6),
    ],
    'rod': _STANCE + [
        ('reach', 'R', ('spine05', (-0.05, -0.30, -0.02)), (-1, 0.4, -0.3), (0.6, -0.5, 0.1), (0.3, 0.1, 1)),
        ('reach', 'L', ('spine05', (0.10, -0.42, 0.10)), (1, 0.4, -0.3), (-0.5, -0.6, 0.2), (-0.2, 0.2, 1)),
        ('curl', 'R', GRIP, 0), ('curl', 'L', GRIP, 0),
    ],
    'phone_up': _STANCE + [
        ('reach', 'R', ('spine02', (-0.04, -0.30, 0.10)), (-1, 0.5, -0.5), (0.25, -0.3, 0.9), (0, 0.5, 0.5)),
        ('curl', 'R', PHONE, 4), ('rot', 'neck01', (1, 0, 0), 12), ('rot', 'head', (1, 0, 0), 14),
        ('reach', 'L', ('upperleg01.L', (0.09, -0.05, -0.12)), (0.3, 1, 0), (0.05, -0.15, -1), (-1, 0.2, 0)), ('curl', 'L', RELAX, 4),
    ],
    'phone_present': _STANCE + [
        ('reach', 'R', ('head', (-0.08, -0.40, -0.06)), (-1, 0.3, -0.5), (0.1, -0.15, 1), (0, -1, 0.05)),
        ('curl', 'R', PHONE, 4),
        ('reach', 'L', ('upperleg01.L', (0.09, -0.05, -0.12)), (0.3, 1, 0), (0.05, -0.15, -1), (-1, 0.2, 0)), ('curl', 'L', RELAX, 4),
        ('rot', 'head', (0, 0, 1), -4),
    ],
    'box_out': _STANCE + [
        ('rot', 'spine03', (1, 0, 0), 4),
        ('reach', 'R', ('spine02', (-0.17, -0.40, 0.02)), (-1, 0.3, -0.5), (0.1, -1, 0.0), (0.3, 0.0, 1)),
        ('reach', 'L', ('spine02', (0.17, -0.40, 0.02)), (1, 0.3, -0.5), (-0.1, -1, 0.0), (-0.3, 0.0, 1)),
        ('curl', 'R', GRIP, 0), ('curl', 'L', GRIP, 0),
    ],
    'box_hug': _STANCE + [
        ('reach', 'R', ('spine02', (-0.10, -0.26, -0.02)), (-1, 0.5, -0.5), (0.9, -0.2, 0.2), (0.1, -0.3, 1)),
        ('reach', 'L', ('spine02', (0.10, -0.26, 0.04)), (1, 0.5, -0.5), (-0.9, -0.2, 0.2), (-0.1, -0.3, 1)),
        ('curl', 'R', RELAX, 2), ('curl', 'L', RELAX, 2), ('rot', 'head', (0, 1, 0), 5),
    ],
    'point_down': _STANCE + [
        ('rot', 'spine03', (1, 0, 0), 5),
        ('reach', 'R', ('spine01', (-0.2, -0.5, -0.2)), (-1, 0.4, -0.3), (0.05, -0.35, -0.94), (0.15, 0.95, -0.2)),
        ('curl', 'R', POINT, 0),
        ('reach', 'L', ('upperleg01.L', (0.08, -0.07, -0.08)), (0.3, 1, 0), (0.05, -0.2, -1), (-1, 0.2, 0)), ('curl', 'L', RELAX, 4),
        ('rot', 'head', (1, 0, 0), 8),
    ],
    'arms_wide': _STANCE + [
        ('rot', 'spine03', (1, 0, 0), -6), ('rot', 'head', (1, 0, 0), -8),
        ('reach', 'R', ('shoulder01.R', (-0.58, -0.2, 0.22)), (0, 1, -0.4), (-1, -0.2, 0.4), (0, -0.6, 0.8)),
        ('reach', 'L', ('shoulder01.L', (0.58, -0.2, 0.22)), (0, 1, -0.4), (1, -0.2, 0.4), (0, -0.6, 0.8)),
        ('curl', 'L', OPEN, 14), ('curl', 'R', OPEN, 14),
    ],
    'hand_on_chin': _STANCE + [
        ('reach', 'R', ('head', (-0.03, -0.12, -0.115)), (-1, 0.0, -0.8), (0.3, 0.0, 1), (0.1, 1, 0.0)),
        ('curl', 'R', {1: 25, 2: 55, 3: 80, 4: 88, 5: 92}, 0),
        ('reach', 'L', ('spine05', (0.02, -0.22, 0.05)), (1, 0.3, -0.6), (-1, -0.1, 0.05), (0, 0.2, 1)),
        ('curl', 'L', RELAX, 2), ('rot', 'head', (0, 1, 0), -4), ('rot', 'head', (1, 0, 0), 4),
    ],
}

ARM = {s: dict(up1=f'upperarm01.{s}', up2=f'upperarm02.{s}', lo1=f'lowerarm01.{s}', lo2=f'lowerarm02.{s}', wr=f'wrist.{s}')
       for s in 'LR'}


def _world_rot(rig, pb, q):
    M = pb.matrix.copy(); h = M.translation.copy()
    pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ M
    bpy.context.view_layer.update()


def _ref(rig, ref):
    bone, off = ref
    return rig.data.bones[bone].head_local + Vector(off)


def _palm(rig, side):
    """Current (posed) finger direction and palmar normal of a hand, armature space."""
    loc = rig.get('finn_palm_' + side)
    pb = rig.pose.bones['wrist.' + side]
    R = pb.matrix.to_3x3()
    f = (R @ Vector(loc[0:3])).normalized(); p = (R @ Vector(loc[3:6])).normalized()
    return f, p


def _reach(rig, side, ref, pole, fdir, pdir):
    A = ARM[side]; P = rig.pose.bones
    sh = P[A['up1']].head.copy()
    l1 = (rig.data.bones[A['up1']].length + rig.data.bones[A['up2']].length)
    l2 = (rig.data.bones[A['lo1']].length + rig.data.bones[A['lo2']].length)
    target = _ref(rig, ref)
    # targets are authored relative to rest; follow the posed parent chain for spine/head references
    if ref[0] in P:
        pb = P[ref[0]]; rb = rig.data.bones[ref[0]]
        target = pb.matrix @ (rb.matrix_local.inverted() @ target)
    d = target - sh; dist = min(d.length, (l1 + l2) * 0.995); d.normalize()
    a = math.acos(max(-1, min(1, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist))))
    pole = Vector(pole).normalized(); pv = (pole - d * pole.dot(d)).normalized()
    elbow = sh + (d * math.cos(a) + pv * math.sin(a)) * l1
    wrist = sh + d * dist
    cur = P[A['up2']].tail - P[A['up1']].head
    _world_rot(rig, P[A['up1']], cur.rotation_difference(elbow - sh))
    cur = P[A['lo2']].tail - P[A['lo1']].head
    _world_rot(rig, P[A['lo1']], cur.rotation_difference(wrist - P[A['lo1']].head))
    _orient_hand(rig, side, Vector(fdir).normalized(), Vector(pdir).normalized())


def _orient_hand(rig, side, fdir, pdir):
    A = ARM[side]; P = rig.pose.bones
    pdir = (pdir - fdir * pdir.dot(fdir)).normalized()
    f, p = _palm(rig, side)
    Fc = Matrix((f, p, f.cross(p))).transposed(); Ft = Matrix((fdir, pdir, fdir.cross(pdir))).transposed()
    _world_rot(rig, P[A['wr']], (Ft @ Fc.transposed()).to_quaternion())
    # spread the forearm twist over the two forearm bones (no candy-wrapper wrist)
    ax = (P[A['lo2']].tail - P[A['lo1']].head).normalized()
    wq = P[A['wr']].matrix.to_quaternion(); lq = P[A['lo2']].matrix.to_quaternion()
    rel = lq.inverted() @ wq
    sw = rel.to_swing_twist('Y')[1]
    for b, frac in ((A['lo1'], 0.33), (A['lo2'], 0.33)):
        wsave = P[A['wr']].matrix.copy()
        _world_rot(rig, P[b], Quaternion(ax, sw * frac))
        P[A['wr']].matrix = wsave; bpy.context.view_layer.update()


def _curl(rig, side, degs, spread):
    P = rig.pose.bones
    f, p = _palm(rig, side)
    for k in range(1, 6):
        deg = degs.get(k, 0)
        for j in (1, 2, 3):
            pb = P[f'finger{k}-{j}.{side}']
            d = (pb.tail - pb.head).normalized()
            if k == 1:
                ax = d.cross(p).normalized(); deg_j = deg * (0.5 if j == 1 else 0.8)
            else:
                ax = d.cross(p).normalized(); deg_j = deg * (0.75 if j == 1 else 1.0 if j == 2 else 0.8)
            _world_rot(rig, pb, Quaternion(ax, math.radians(deg_j)))
        if spread and k > 1:
            pb = P[f'finger{k}-1.{side}']
            ax = p; sgn = (k - 3) * (1 if side == 'L' else -1)
            _world_rot(rig, pb, Quaternion(ax, math.radians(spread * 0.5 * sgn)))


def _rest(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def solve_pose(rig, name):
    _rest(rig)
    for op in POSES[name]:
        k = op[0]
        if k == 'rot':
            _world_rot(rig, rig.pose.bones[op[1]], Quaternion(Vector(op[2]).normalized(), math.radians(op[3])))
        elif k == 'aim':
            pb = rig.pose.bones[op[1]]
            _world_rot(rig, pb, (pb.tail - pb.head).rotation_difference(Vector(op[2])))
        elif k == 'reach':
            _reach(rig, *op[1:])
        elif k == 'curl':
            _curl(rig, op[1], op[2], op[3])
    out = {pb.name: tuple(pb.rotation_quaternion) for pb in rig.pose.bones
           if (Quaternion(pb.rotation_quaternion).angle > 1e-4) and pb.name != 'jaw'}
    return out


def _cache(rig):
    c = rig.get('finn_pose_cache')
    if c: return json.loads(c)
    jaw = dict(rig.pose.bones['jaw'].rotation_quaternion) if False else None
    res = {n: solve_pose(rig, n) for n in POSES}
    rig['finn_pose_cache'] = json.dumps(res)
    _rest(rig)
    return res


IDLE = {'spine03': ((1, 0, 0), 0.8), 'spine01': ((1, 0, 0), -0.5), 'clavicle.L': ((0, 1, 0), 0.6), 'clavicle.R': ((0, 1, 0), -0.6),
        'neck02': ((1, 0, 0), -0.3)}


def apply_pose(rig, name_a, name_b=None, mix=0.0, frame=None, idle=1.0):
    """Pose Finn as POSES[name_a] blended toward POSES[name_b] by mix, plus a breathing idle driven by frame."""
    C = _cache(rig)
    A = C[name_a]; Bp = C[name_b] if name_b else {}
    mix = max(0.0, min(1.0, mix)) if name_b else 0.0
    for pb in rig.pose.bones:
        if pb.name == 'jaw': continue
        pb.rotation_mode = 'QUATERNION'
        qa = Quaternion(A.get(pb.name, (1, 0, 0, 0)))
        q = qa.slerp(Quaternion(Bp.get(pb.name, (1, 0, 0, 0))), mix) if name_b else qa
        pb.rotation_quaternion = q
    if frame is not None and idle:
        fps = bpy.context.scene.render.fps or 24
        t = frame / fps
        br = math.sin(2 * math.pi * t / 4.2)
        sway = math.sin(2 * math.pi * t / 7.3 + 0.7)
        for bn, (axis, deg) in IDLE.items():
            pb = rig.pose.bones.get(bn)
            if pb: pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion(Vector(axis), math.radians(deg * br * idle))
        pb = rig.pose.bones.get('root')
        if pb: pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion(Vector((0, 1, 0)), math.radians(0.6 * sway * idle))


def hand_socket(rig, side='R'):
    """Bone name to parent props to (frame documented in the module docstring)."""
    return 'socket.' + ('R' if side.upper().startswith('R') else 'L')


def add_sockets(B):
    """Palm socket bones + the palm frame used by the pose solver, measured from the fitted hand."""
    rig = B.rig; b = B.b
    nails = b.vertex_groups['fingernails'].index
    set_active(rig); bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    info = {}
    for s in 'LR':
        mid = eb[f'finger3-1.{s}']; f3 = eb[f'finger3-3.{s}']
        fdir = (mid.tail - eb[f'wrist.{s}'].head).normalized()
        # back of the hand = the side the nails are on
        tip = f3.head; nv = [b.matrix_world @ v.co for v in b.data.vertices
                             if any(g.group == nails for g in v.groups) and ((b.matrix_world @ v.co) - tip).length < 0.03]
        nc = sum(nv, Vector()) / max(1, len(nv))
        axis_pt = f3.head + (f3.tail - f3.head) * max(0, min(1, (nc - f3.head).dot((f3.tail - f3.head).normalized()) / f3.length))
        dorsal = (nc - axis_pt); dorsal = (dorsal - fdir * dorsal.dot(fdir)).normalized()
        palmar = -dorsal
        centre = (eb[f'wrist.{s}'].tail + mid.head) / 2 + palmar * 0.012
        sk = eb.new('socket.' + s); sk.head = centre - fdir * 0.005; sk.tail = centre
        sk.align_roll(palmar); sk.parent = eb[f'wrist.{s}']; sk.use_deform = False
        wr = eb[f'wrist.{s}']
        Mw = wr.matrix.to_3x3().inverted()
        info[s] = list(Mw @ fdir) + list(Mw @ palmar)
    jaw = eb['jaw']
    bpy.ops.object.mode_set(mode='OBJECT')
    for s in 'LR': rig['finn_palm_' + s] = info[s]
    # jaw opening axis in the jaw bone's local frame: world +X (his left) opens the mouth
    jb = rig.data.bones['jaw']
    rig['finn_jaw_axis'] = list((jb.matrix_local.to_3x3().inverted() @ Vector((1, 0, 0))).normalized())


# ---------------------------------------------------------------------------------------------------------- assemble
def materials():
    M = {
        'jacket': fabric('finn_jacket', COL['jacket'], 'waxed-cotton-canvas/denim_fabric_04', scale=22, rough=(0.45, 0.8), sheen=0.1,
                         coat=0.08, normal=1.0, ao=0.6, var=0.18),
        'cord': fabric('finn_cord', COL['cord'], 'corduroy/ribbed_corduroy', scale=14, rough=(0.6, 0.9), sheen=0.4, normal=0.9, ao=0.5),
        'lining': fabric('finn_lining', COL['lining'], 'knit-wool/caban', scale=8, rough=(0.7, 0.95), ao=0.4),
        'knit': fabric('finn_knit', COL['knit'], 'knit-wool/knitted_fleece', scale=7, rough=(0.75, 1.0), sheen=0.5, normal=1.0, ao=0.55, var=0.05),
        'wader': fabric('finn_wader', COL['wader'], 'neoprene-rubber/scuba_suede', scale=6, rough=(0.42, 0.62), coat=0.08, normal=0.5, ao=0.6, var=0.08),
        'boot': fabric('finn_boot', COL['boot'], 'neoprene-rubber/Rubber004_1K-JPG', scale=5, rough=(0.35, 0.6), coat=0.1, normal=0.6, ao=0.5),
        'glove': fabric('finn_glove', COL['glove'], 'fleece/polar_fleece', scale=10, rough=(0.7, 0.95), sheen=0.3, normal=0.7, ao=0.5),
        'hat': fabric('finn_hat', COL['hat'], 'waxed-cotton-canvas/rough_linen', lum=0.78, scale=12, rough=(0.7, 0.95), sheen=0.2, normal=0.8, ao=0.5, var=0.06),
        'band': fabric('finn_band', COL['band'], 'leather/fabric_leather_02', scale=12, rough=(0.5, 0.7), normal=0.6, ao=0.3),
        'brace': fabric('finn_brace', COL['brace'], 'corduroy/ribbed_corduroy', scale=20, rough=(0.55, 0.8), normal=0.5, ao=0.3),
        'brass': simple('finn_brass', COL['brass'], 0.28, metal=1.0),
        'steel': simple('finn_steel', '#c4c8cc', 0.22, metal=1.0),
        'frame': simple('finn_frame', COL['frame'], 0.25, coat=0.6),
        'lens': lens_mat(),
        'lureA': simple('finn_lure_a', COL['lureA'], 0.25, coat=1.0), 'lureB': simple('finn_lure_b', COL['lureB'], 0.25, coat=1.0),
        'sole': simple('finn_sole', COL['sole'], 0.8),
    }
    return M


def tune_skin(b):
    """Push the MPFB skin a little toward painted game-engine skin: warmer, softer SSS, slightly less glossy."""
    for m in b.data.materials:
        if not m or not m.use_nodes: continue
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                if 'Subsurface Weight' in n.inputs and n.inputs['Subsurface Weight'].default_value > 0:
                    n.inputs['Subsurface Weight'].default_value = 0.35
                    n.inputs['Subsurface Radius'].default_value = (1.0, 0.35, 0.18)
            if n.type == 'GROUP':
                for i in n.inputs:
                    nm = i.name.lower()
                    if 'sss' in nm and 'weight' in nm and hasattr(i, 'default_value'): i.default_value = 0.35


def build():
    t0 = time.time()
    bpy.ops.wm.read_homefile(use_empty=True)
    coll = bpy.data.collections.new('Finn'); bpy.context.scene.collection.children.link(coll)
    b, rig = build_body()
    strip_helpers(b)
    for o in list(bpy.context.scene.objects):
        if o.type in ('MESH', 'ARMATURE'): link(o, coll)
    B = Body(b, rig)
    add_sockets(B)
    derive_face_keys(b)
    tune_skin(b)
    M = materials()
    print('[finn] body + rig', round(time.time() - t0, 1), 's')
    kn = knit(B, coll, M)
    collar(B, coll, M, kn)
    wd = waders(B, coll, M)
    bt = boots(B, coll, M)
    gl = gloves(B, coll, M)
    jk = jacket(B, coll, M)
    br = braces(B, coll, M, kn)
    print('[finn] clothes', round(time.time() - t0, 1), 's')
    head_parts = hat(B, coll, M) + sunglasses(B, coll, M) + [mouth_bag(B, coll)]
    parent_to_bone(head_parts, rig, 'head')
    groom(B)
    beard_shell(B, coll)
    for o in coll.objects:                       # every garment follows the rig object
        if o.type == 'MESH' and o.parent is None:
            mw = o.matrix_world.copy(); o.parent = rig; o.matrix_world = mw
    # boots carry a sole: lift the whole rig so the soles stand on z = 0
    rig.location.z = SOLE
    bpy.context.view_layer.update()
    print('[finn] built in', round(time.time() - t0, 1), 's')
    _cache(rig)
    return rig


def save(path=BLEND):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for im in bpy.data.images:
        if im.filepath and 'blender-user' in im.filepath.replace('\\', '/'):
            try: im.pack()
            except Exception as e: print('[finn] pack failed', im.name, e)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True, relative_remap=True)
    try:
        bpy.ops.file.make_paths_relative(); bpy.ops.wm.save_mainfile(compress=True)
    except Exception as e:
        print('[finn] relative paths', e)


def load_finn(blend_path=None):
    """Append Finn into the current scene and return his armature (z=0, origin, facing -Y)."""
    p = blend_path or BLEND
    if not os.path.exists(p):
        return build()
    with bpy.data.libraries.load(p, link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c == 'Finn']
    coll = dst.collections[0]
    bpy.context.scene.collection.children.link(coll)
    rig = next(o for o in coll.objects if o.type == 'ARMATURE')
    return rig


# ------------------------------------------------------------------------------------------------------------ preview
SHOTS = {   # name: pose, face, camera offset from Finn (m), look-at height above deck, lens mm
    'full': dict(pose='neutral', face=('smirk', None, 0.2), cam=(-1.0, -2.55, 1.05), look=0.98, lens=32),
    'mcu': dict(pose='present', face=('talk', 0.85, 0.35), cam=(-0.45, -1.55, 1.62), look=1.52, lens=40),
    'face': dict(pose='neutral', face=('talk', 0.6, 0.5), cam=(-0.3, -0.95, 1.8), look=1.68, lens=70),
    'point': dict(pose='point_down', face=('shout', 0.7, 0.6), cam=(-0.6, -2.35, 1.2), look=1.12, lens=35),
    'hold': dict(pose='hold_up', face=('talk', 0.7, 0.45), cam=(-0.3, -1.3, 1.66), look=1.62, lens=45),
}
FINN_AT = Vector((0.0, 5.6, 0.55))


def stage_preview():
    sys.path.insert(0, HERE)
    import finn_set
    bpy.context.scene.render.hair_type = 'STRAND'
    finn_set.build_set({'tex_dir': TEX, 'seed': 7, 'mist_low': 0.003, 'mist_high': 0.0005, 'sky': 0.55, 'sun': 7.5})
    sc = bpy.context.scene
    # preview grade on top of the set: a cooler, clearer dawn sky and blue-grey mist, so the warm key reads against it
    try:
        for n in sc.world.node_tree.nodes:
            if n.type == 'VALTORGB':
                n.color_ramp.elements[0].color = (*lin('#e8c49a'), 1); n.color_ramp.elements[1].color = (*lin('#5d7fa8'), 1)
                n.color_ramp.elements[0].position = 0.5; n.color_ramp.elements[1].position = 0.62
        for n in bpy.data.materials['mist'].node_tree.nodes:
            if n.type == 'PRINCIPLED_VOLUME': n.inputs['Color'].default_value = (*lin('#b4c2d0'), 1)
    except Exception as e:
        print('[finn] grade', e)
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, 100
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = -0.75
    try: sc.view_settings.look = 'AgX - Punchy'
    except Exception: pass
    ee = sc.eevee
    ee.taa_render_samples = 64
    for k, v in (('use_raytracing', True), ('use_shadows', True), ('volumetric_tile_size', '4'), ('volumetric_samples', 64),
                 ('use_volumetric_shadows', True), ('shadow_ray_count', 2), ('shadow_step_count', 8), ('use_gtao', True),
                 ('fast_gi_distance', 2.0)):
        try: setattr(ee, k, v)
        except Exception: pass
    try:
        ee.ray_tracing_options.resolution_scale = '1'
    except Exception: pass
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 85
    # cool fill from the front-left, small warm bounce from the deck, a soft glint light near the lens
    def area(name, color, energy, loc, size, target, spec=1.0, diff=1.0):
        l = bpy.data.lights.new(name, 'AREA'); l.color = lin(color); l.energy = energy; l.size = size
        l.specular_factor = spec; l.diffuse_factor = diff
        o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
    area('fill_cool', '#86a9de', 520, FINN_AT + Vector((-2.2, -2.6, 1.9)), 2.5, FINN_AT + Vector((0, 0, 1.3)), spec=0.5)
    area('bounce_warm', '#e8b98a', 40, FINN_AT + Vector((0.6, -1.0, 0.2)), 1.5, FINN_AT + Vector((0, 0, 1.0)), spec=0.0)
    area('rim_warm', '#ffbe7a', 900, FINN_AT + Vector((1.6, 1.8, 2.4)), 1.2, FINN_AT + Vector((0, 0, 1.4)), spec=1.0)
    area('glint', '#ffffff', 25, FINN_AT + Vector((-0.6, -1.6, 2.3)), 0.25, FINN_AT + Vector((0, 0, 1.75)), spec=1.0, diff=0.0)


def render_shots(rig, shots, out_dir=PREVIEWS, prefix='finn_v1_'):
    os.makedirs(out_dir, exist_ok=True)
    sc = bpy.context.scene
    cam = bpy.data.objects.get('preview_cam')
    if not cam:
        cd = bpy.data.cameras.new('preview_cam'); cam = bpy.data.objects.new('preview_cam', cd); sc.collection.objects.link(cam)
    sc.camera = cam
    times = {}
    lure_prop = None
    for name in shots:
        S = SHOTS[name]
        apply_pose(rig, S['pose'], frame=0)
        m, o, br = S['face']; set_face(rig, m, o, br)
        if lure_prop:
            for p in lure_prop: bpy.data.objects.remove(p)
            lure_prop = None
        if S['pose'] == 'hold_up':
            lure_prop = hand_lure(rig)
        tgt = FINN_AT + Vector((0, 0, S['look']))
        cam.location = FINN_AT + Vector(S['cam'])
        cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = S['lens']; cam.data.sensor_width = 36
        cam.data.dof.use_dof = S['lens'] >= 40
        cam.data.dof.focus_distance = (tgt - cam.location).length - 0.05; cam.data.dof.aperture_fstop = 2.8
        sc.render.filepath = os.path.join(out_dir, prefix + name + '.jpg')
        t = time.time(); bpy.ops.render.render(write_still=True); times[name] = round(time.time() - t, 1)
        print('[finn] rendered', name, times[name], 's', os.path.getsize(sc.render.filepath) // 1024, 'KB')
    return times


def hand_lure(rig):
    """A spare crankbait in the right hand for the hold-up pose (parented to the palm socket)."""
    coll = bpy.context.scene.collection
    M = {'steel': simple('finn_steel', '#c4c8cc', 0.22, metal=1.0)}
    parts = lure('hand_lure', Vector((0, 0, 0)), Vector((1, 0, 0)), simple('finn_lure_a', COL['lureA'], 0.25, coat=1.0), 0.11, coll, M)
    root = bpy.data.objects.new('hand_lure_root', None); coll.objects.link(root)
    for p in parts: p.parent = root
    root.parent = rig; root.parent_type = 'BONE'; root.parent_bone = hand_socket(rig, 'R')
    root.matrix_parent_inverse.identity()
    root.location = (0.0, 0.08, 0.03); root.rotation_euler = (0, 0, math.radians(90))
    return parts + [root]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', action='store_true'); ap.add_argument('--preview', action='store_true')
    ap.add_argument('--shots', default='full,mcu,face,point,hold'); ap.add_argument('--out', default=PREVIEWS)
    ap.add_argument('--prefix', default='finn_v1_'); ap.add_argument('--blend', default=BLEND)
    ap.add_argument('--res', type=int, default=100)
    a = ap.parse_args(argv)
    if a.build:
        rig = build(); save(a.blend)
    else:
        bpy.ops.wm.read_homefile(use_empty=True); rig = load_finn(a.blend)
    if a.preview:
        stage_preview(); bpy.context.scene.render.resolution_percentage = a.res
        rig.location = FINN_AT + Vector((0, 0, SOLE))
        times = render_shots(rig, a.shots.split(','), a.out, a.prefix)
        print('[finn] render times', json.dumps(times))


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
