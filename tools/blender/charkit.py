"""Character finishing pass shared by every HOST character (Finn now, Nils Brack next).

Written after the 2026-11-26 audit of the rough Finn render against the One Bold Chemist references
(docs/styles/HOST_RENDER_RULES.md). Each function fixes one cause the audit found, and none of them is Finn-specific:
a character only has to name its layers, its beard shell (if any) and its rig.

  cull_covered(pairs, body)        inner garment layers lose the vertices an outer layer covers (game-character practice),
                                   so an inner layer can never poke through an outer one when the rig bends
  sculpted_beard(shell, ...)       particle beards turn into "sponge" at phone size in Eevee; replace them with a sculpted
                                   clump shell (bulk + flowing grooves) that still talks with the face shape keys
  macro_paint(materials)           detail at the scale the phone shows: cavity darkening, broad value breakup, edge
                                   lift. Real-scale weave and pores are invisible at 1080x1920 and read as flat clay
  grade(scene, preset)             the measured reference grade: mid-dark, contrasty, medium saturation

Run order in render_episode.py: load the character, then finish(rig, spec), then pose. Everything here is
non-destructive (modifiers, vertex groups, node additions), so the character's .blend is never changed.
"""
import math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


# ----------------------------------------------------------------------------------------------- garment layering
def _rest_bvh(o, solidify=False):
    """World-space BVH of an object's evaluated geometry with the rig in rest position."""
    off = [m for m in o.modifiers if m.type == 'SOLIDIFY' and m.show_viewport and not solidify]
    for m in off: m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(ev.matrix_world); ev.to_mesh_clear()
    for m in off: m.show_viewport = True
    t = BVHTree.FromBMesh(bm) if bm.faces else None
    bm.free()
    return t


def _rest_verts(o):
    """Rest-pose world positions of the object's own vertices (index-aligned with o.data.vertices), shape keys at basis."""
    keep = [(m, m.show_viewport) for m in o.modifiers]
    for m, _ in keep:
        if m.type != 'ARMATURE': m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    pts = [ev.matrix_world @ v.co for v in me.vertices] if len(me.vertices) == len(o.data.vertices) else \
          [o.matrix_world @ v.co for v in o.data.vertices]
    ev.to_mesh_clear()
    for m, s in keep: m.show_viewport = s
    return pts


def cull_covered(rig, pairs, body, reach_out=0.06, reach_in=0.015, erode=1, name='cull'):
    """Hide the parts of inner layers that an outer layer covers.

    pairs: [(outer_obj, inner_obj), ...]. For each inner vertex we look along the line away from the body (the
    garment's outward direction) up to reach_out, and back toward the body up to reach_in. If the outer layer is
    there, the vertex is covered. The covered set is eroded by `erode` rings so no gap opens at the outer layer's
    edge, then a MASK modifier (inverted, straight after the armature) removes it at render time.
    Returns {inner_name: hidden_vertex_count}.
    """
    pp = rig.data.pose_position; rig.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    body_bvh = _rest_bvh(body)
    out = {}
    hidden = {}
    for outer, inner in pairs:
        if outer is None or inner is None:
            continue
        obvh = _rest_bvh(outer, solidify=True)
        if obvh is None:
            continue
        pts = _rest_verts(inner)
        cov = hidden.setdefault(inner.name, set())
        for i, p in enumerate(pts):
            loc, nrm, _, d = body_bvh.find_nearest(p) if body_bvh else (None, None, None, None)
            n = (p - loc) if loc is not None and (p - loc).length > 1e-5 else (inner.matrix_world.to_3x3() @ inner.data.vertices[i].normal)
            n = n.normalized()
            if obvh.ray_cast(p - n * 0.001, n, reach_out)[0] is not None or obvh.ray_cast(p + n * 0.001, -n, reach_in)[0] is not None:
                cov.add(i)
    for iname, cov in hidden.items():
        inner = bpy.data.objects[iname]
        me = inner.data
        nb = [set() for _ in me.vertices]
        for e in me.edges:
            a, b = e.vertices; nb[a].add(b); nb[b].add(a)
        for _ in range(erode):                       # keep a ring of inner layer under the outer layer's edge
            cov = {i for i in cov if nb[i] <= cov}
        g = inner.vertex_groups.get(name) or inner.vertex_groups.new(name=name)
        g.add(list(cov), 1.0, 'REPLACE')
        md = inner.modifiers.get(name) or inner.modifiers.new(name, 'MASK')
        md.vertex_group = name; md.invert_vertex_group = True
        idx = next((k for k, m in enumerate(inner.modifiers) if m.type == 'ARMATURE'), -1) + 1
        with bpy.context.temp_override(object=inner):
            bpy.ops.object.modifier_move_to_index(modifier=name, index=idx)
        out[iname] = len(cov)
    rig.data.pose_position = pp
    bpy.context.view_layer.update()
    return out


# ------------------------------------------------------------------------------------------------- sculpted beard
def sculpted_beard(shell, body, systems=(), depth=0.004, groove=0.0, color=('#3e2112', '#7a4527', '#a8683c'),
                   weight_attr=None, groups=('finn_beard',)):
    """Turn a thin painted beard shell into a sculpted, clumped beard mass and switch the particle beard off.

    The shell keeps its shape keys and armature, so it still talks. Geometry: subdivided twice and pushed out along
    the normal by `depth` times the weight of `groups` (keep the moustache out of the bulk or it closes over the lips).
    Optional geometric grooves (`groove` > 0) swirl on MPFB UVs, so they stay off by default; the strand streaks are
    in the shader on Generated coordinates. At 1080x1920 this reads as a mass; 140k short strands read as sponge.
    """
    for o in (body,):
        for md in o.modifiers:
            if md.type == 'PARTICLE_SYSTEM' and md.name in systems:
                md.show_render = md.show_viewport = False
    # one group carrying the max of the listed weights
    w = shell.vertex_groups.get('beard_mass') or shell.vertex_groups.new(name='beard_mass')
    ids = [g.index for g in shell.vertex_groups if g.name in groups]
    for v in shell.data.vertices:
        ww = max([g.weight for g in v.groups if g.group in ids] or [0.0])
        if ww > 0: w.add([v.index], min(1.0, ww ** 0.6), 'REPLACE')
    sub = shell.modifiers.new('beard_sub', 'SUBSURF'); sub.levels = 2; sub.render_levels = 2
    bulk = shell.modifiers.new('beard_bulk', 'DISPLACE'); bulk.strength = depth; bulk.mid_level = 0.0
    bulk.vertex_group = 'beard_mass'; bulk.direction = 'NORMAL'
    if groove > 0:
        _grooves(shell, groove)
    for p in shell.data.polygons: p.use_smooth = True
    _beard_material(shell, color, weight_attr)
    return shell


def _grooves(shell, groove):
    tex = bpy.data.textures.get('beard_clumps') or bpy.data.textures.new('beard_clumps', 'WOOD')
    tex.wood_type = 'BANDNOISE'; tex.noise_basis_2 = 'SIN'; tex.turbulence = 9.0; tex.noise_scale = 0.06
    tex.noise_basis = 'ORIGINAL_PERLIN'
    gr = shell.modifiers.new('beard_grooves', 'DISPLACE'); gr.texture = tex; gr.texture_coords = 'UV'
    gr.strength = groove; gr.mid_level = 0.5; gr.vertex_group = 'beard_mass'; gr.direction = 'NORMAL'


def _beard_material(shell, color, weight_attr):
    m = bpy.data.materials.new(shell.name + '_sculpt'); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links
    try: m.surface_render_method = 'DITHERED'
    except Exception: pass
    bsdf = N['Principled BSDF']
    # Generated coordinates come from the undeformed mesh, so the strand streaks stay glued to the beard when he
    # talks or turns. Bands across X = vertical streaks (strands hang down).
    tc = N.new('ShaderNodeTexCoord')
    wave = N.new('ShaderNodeTexWave'); wave.wave_type = 'BANDS'; wave.bands_direction = 'X'
    wave.inputs['Scale'].default_value = 60.0; wave.inputs['Distortion'].default_value = 2.5
    wave.inputs['Detail'].default_value = 2.0; wave.inputs['Detail Scale'].default_value = 1.2
    L.new(tc.outputs['Generated'], wave.inputs['Vector'])
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.012
    mix = N.new('ShaderNodeMath'); mix.operation = 'MULTIPLY'
    L.new(wave.outputs['Fac'], mix.inputs[0]); L.new(ao.outputs['AO'], mix.inputs[1])
    ramp = N.new('ShaderNodeValToRGB')
    from finn_v1 import lin
    e = ramp.color_ramp.elements
    e[0].position = 0.05; e[0].color = (*lin(color[0]), 1)
    e[1].position = 0.95; e[1].color = (*lin(color[2]), 1)
    mid = e.new(0.5); mid.color = (*lin(color[1]), 1)
    L.new(mix.outputs[0], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.62
    for k, v in (('Sheen Weight', 0.6), ('Sheen Roughness', 0.35)):
        if k in bsdf.inputs: bsdf.inputs[k].default_value = v
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.35; bump.inputs['Distance'].default_value = 0.0008
    L.new(wave.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    # soft edge where the beard thins into the cheek (the shell's own weight attribute)
    if weight_attr:
        ca = N.new('ShaderNodeAttribute'); ca.attribute_name = weight_attr
        mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.08; mr.inputs['From Max'].default_value = 0.45
        L.new(ca.outputs['Fac'], mr.inputs['Value']); L.new(mr.outputs[0], bsdf.inputs['Alpha'])
    shell.data.materials.clear(); shell.data.materials.append(m)


# --------------------------------------------------------------------------------------------- macro paint pass
def macro_paint(materials, cavity=0.55, breakup=0.12, scale=2.2):
    """Add the detail a phone screen can show to every listed material: ambient-occlusion cavity darkening (seams,
    folds, armpits, under the brim), a broad low-frequency value breakup (wear and fading), both multiplied into
    Base Color in front of the Principled BSDF. Painted game characters carry exactly this in their diffuse maps."""
    done = 0
    for m in materials:
        if not m or not m.use_nodes or m.get('macro_painted'):
            continue
        nt = m.node_tree; N = nt.nodes; L = nt.links
        bsdf = next((n for n in N if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            continue
        sock = bsdf.inputs['Base Color']
        src = sock.links[0].from_socket if sock.is_linked else None
        base = N.new('ShaderNodeRGB'); base.outputs[0].default_value = sock.default_value
        ao = N.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.06; ao.only_local = False
        cav = N.new('ShaderNodeMapRange'); cav.inputs['From Min'].default_value = 0.0; cav.inputs['From Max'].default_value = 1.0
        cav.inputs['To Min'].default_value = 1.0 - cavity; cav.inputs['To Max'].default_value = 1.0
        L.new(ao.outputs['AO'], cav.inputs['Value'])
        tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 2.0
        L.new(tc.outputs['Object'], nz.inputs['Vector'])
        br = N.new('ShaderNodeMapRange'); br.inputs['To Min'].default_value = 1.0 - breakup; br.inputs['To Max'].default_value = 1.0 + breakup * 0.5
        L.new(nz.outputs['Fac'], br.inputs['Value'])
        k = N.new('ShaderNodeMath'); k.operation = 'MULTIPLY'
        L.new(cav.outputs[0], k.inputs[0]); L.new(br.outputs[0], k.inputs[1])
        mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
        L.new(src if src else base.outputs[0], mul.inputs['A'])
        L.new(k.outputs[0], mul.inputs['B'])
        L.new(mul.outputs['Result'], sock)
        m['macro_painted'] = 1; done += 1
    return done


# ---------------------------------------------------------------------------------------------------- the grade
GRADES = {
    # measured on the references (STYLE.md 4): mean luma 75-120, luma SD 43-67, saturation 0.34-0.48, warm key
    'host': dict(exposure=-1.05, look='AgX - High Contrast', saturation=1.18),
}


def grade(scene, preset='host'):
    g = GRADES[preset]
    vs = scene.view_settings
    vs.view_transform = 'AgX'; vs.exposure = g['exposure']
    try: vs.look = g['look']
    except Exception: pass
    # saturation through the compositor-free curve: scale chroma with a colour balance node is overkill; AgX
    # 'Punchy' is the built-in saturated look
    if g.get('saturation', 1.0) > 1.1:
        try: vs.look = 'AgX - Punchy'
        except Exception: pass
    return g


# ------------------------------------------------------------------------------------------------ one entry point
def finish(rig, spec):
    """spec: {'body': name, 'layers': [(outer, inner), ...], 'beard': {'shell': name, 'systems': [...], ...},
              'paint': [object names] or 'all'}. Returns a dict for the log."""
    objs = {o.name.split('.')[0] if o.name.count('.') == 1 and o.name.split('.')[1].isdigit() else o.name: o
            for o in rig.children_recursive if o.type == 'MESH'}
    rep = {}
    body = objs.get(spec['body'])
    if spec.get('layers'):
        rep['culled'] = cull_covered(rig, [(objs.get(a), objs.get(b)) for a, b in spec['layers']], body)
    bd = spec.get('beard')
    if bd and bd.get('mode') == 'remove':
        # the honest fallback for a strand beard that cannot read at phone size: no beard, keep the stubble layer
        for md in body.modifiers:
            if md.type == 'PARTICLE_SYSTEM' and md.name in bd.get('systems', ()):
                md.show_render = md.show_viewport = False
        sh = objs.get(bd.get('shell', ''))
        if sh: sh.hide_render = sh.hide_viewport = True
        rep['beard'] = 'removed'
    elif bd and objs.get(bd['shell']):
        bd = dict(bd); bd.pop('mode', None); sh = objs[bd.pop('shell')]
        sculpted_beard(sh, body, **bd); rep['beard'] = sh.name
    names = spec.get('paint')
    if names:
        mats = {m for o in objs.values() if names == 'all' or o.name in names for m in o.data.materials if m}
        mats = {m for m in mats if not m.name.endswith('_sculpt')}
        rep['painted'] = macro_paint(mats)
    return rep


# ------------------------------------------------------------------------------------------------ style audit
def style_audit(rig, min_thickness=0.005, max_subsurf=1, scan_dirs=('assets-cc0', 'textures', 'makehuman')):
    """The measurable parts of HOST_RENDER_RULES.md section 7 (stylised, never photoreal). Returns a list of
    violation strings; an empty list passes. Checks: particle/curve hair on the character, subdivision deeper than
    max_subsurf, garment (solidified) layers thinner than min_thickness, image textures loaded from photo/scan asset
    folders, skin-style pore or clearcoat inputs left on."""
    bad = []
    for o in rig.children_recursive:
        if o.type == 'CURVES':
            bad.append(f'{o.name}: curve hair (rule 8: sculpt hair as solid locks)')
        if o.type != 'MESH':
            continue
        for md in o.modifiers:
            if md.type == 'PARTICLE_SYSTEM' and md.show_render and md.particle_system.settings.type == 'HAIR':
                bad.append(f'{o.name}: particle hair "{md.name}" (rule 8)')
            if md.type == 'SUBSURF' and md.show_render and md.render_levels > max_subsurf:
                bad.append(f'{o.name}: subdivision level {md.render_levels} (rule 3: at most {max_subsurf})')
            if md.type == 'SOLIDIFY' and md.show_render and max(o.dimensions) > 0.1                     and abs(md.thickness) * max(o.scale) < min_thickness:     # garments, not lenses or small trims
                bad.append(f'{o.name}: {abs(md.thickness) * 1000:.1f} mm thick (rule 6: at least {min_thickness * 1000:.0f} mm)')
        for m in o.data.materials:
            if not m or not m.use_nodes:
                continue
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and any(s in n.image.filepath.replace(chr(92), '/').lower() for s in scan_dirs):
                    bad.append(f'{o.name}/{m.name}: scanned texture {n.image.name} (rule 9: paint it)')
                if n.type == 'GROUP':
                    for i in n.inputs:
                        if i.name == 'Pore strength' and i.default_value > 0:
                            bad.append(f'{o.name}/{m.name}: pores on (rule 9)')
                if n.type == 'BSDF_PRINCIPLED' and 'Coat Weight' in n.inputs and n.inputs['Coat Weight'].default_value > 0.05 \
                        and 'skin' in m.name.lower():
                    bad.append(f'{o.name}/{m.name}: clearcoat on skin (rule 11)')
    return sorted(set(bad))


# ------------------------------------------------------------------------------- audit 3: acting and the finish
def stylise_finish(scene, rig, body_name='finn_body', drop_systems=()):
    """Audit 3 ('still too realistic, no artsy look'): switch off the realism detail that survives on a phone as fine
    noise (skin pores and clearcoat, stubble strands) and render crisper edges (a narrower pixel filter). The
    references keep their detail at a coarser scale: they lose almost nothing when downscaled 2x (PSNR 45 dB against
    our 43 dB at the same bitrate) and carry a third less high-frequency energy (16-17 % against our 24 %)."""
    body = next((o for o in rig.children_recursive if o.name.startswith(body_name) and o.type == 'MESH'
                 and o.data.shape_keys), None)
    if body:
        for md in body.modifiers:
            if md.type == 'PARTICLE_SYSTEM' and md.name in drop_systems:
                md.show_render = md.show_viewport = False
        for m in body.data.materials:
            if not m or not m.use_nodes: continue
            for n in m.node_tree.nodes:
                if n.type == 'GROUP':
                    for i in n.inputs:
                        if i.name in ('Pore strength', 'Clearcoat'): i.default_value = 0.0
                        if i.name == 'Roughness': i.default_value = 0.68
    try: scene.render.filter_size = 0.8
    except Exception: pass


def apply_visemes(rig, api, v, vmap, mood='talk', brow=0.0, blink=0.0):
    """Drive the face from one frame of lipsync.visemes: reset the expression keys (api.set_face 'closed' keeps the
    brows and blink), add each viseme's shape keys by weight, a smile layer, the smirk on silent frames, and the jaw
    from the viseme's jaw amount scaled by the mood (a shout opens wider)."""
    from mathutils import Quaternion
    api.set_face(rig, mouth='closed', open=0.0, brow=brow, blink=blink)
    faces = [c for c in rig.children if c.type == 'MESH' and c.data.shape_keys and 'x_mouth-open' in c.data.shape_keys.key_blocks]
    vis = v['vis']; silent = vis.get('rest', 0.0) > 0.85
    for body in faces:
        kb = body.data.shape_keys.key_blocks
        if 'x_mouth-compression' in kb: kb['x_mouth-compression'].value = 0.0
        add = {}
        for name, w in vis.items():
            for key, val in vmap.get(name, {}).items():
                add[key] = add.get(key, 0.0) + val * w
        sm = v.get('smile', 0.0) * (0.3 if mood == 'shout' else 1.0)
        for key, val in vmap.get('_smile', {}).items():
            add[key] = add.get(key, 0.0) + val * sm
        if mood == 'smirk' and silent:
            add['f_smile_L'] = add.get('f_smile_L', 0.0) + 0.7; add['f_upret_L'] = add.get('f_upret_L', 0.0) + 0.3
        if mood == 'shout':
            add['x_mouth-upward-retraction'] = add.get('x_mouth-upward-retraction', 0.0) + 0.2 * v['jaw']
        for key, val in add.items():
            if key in kb: kb[key].value = max(0.0, min(1.0, val))
    deg = vmap.get('_jaw_deg', {}).get(mood, 10.0) * v['jaw']
    jaw = rig.pose.bones['jaw']; ax = rig.get('finn_jaw_axis') or (1, 0, 0)
    jaw.rotation_mode = 'QUATERNION'; jaw.rotation_quaternion = Quaternion(Vector(ax), math.radians(deg))


def talk_motion(rig, b, side='R', head='head', neck='neck02'):
    """Add one frame of lipsync.talk_layer on top of the posed rig: head nods and tilts (60 % head, 40 % neck) and
    the gesturing wrist beating with the accents. Rotations are multiplied onto the pose, so nothing accumulates."""
    from mathutils import Quaternion
    P = rig.pose.bones
    for bn, share in ((head, 0.6), (neck, 0.4)):
        pb = P.get(bn)
        if not pb: continue
        pb.rotation_mode = 'QUATERNION'
        q = (Quaternion((1, 0, 0), math.radians(b['head_pitch'] * share)) @
             Quaternion((0, 1, 0), math.radians(b['head_yaw'] * share)) @
             Quaternion((0, 0, 1), math.radians(b['head_roll'] * share)))
        pb.rotation_quaternion = pb.rotation_quaternion @ q
    wr = P.get(f'wrist.{side}')
    if wr:
        wr.rotation_mode = 'QUATERNION'
        wr.rotation_quaternion = wr.rotation_quaternion @ Quaternion((1, 0, 0), math.radians(b['wrist']))


def _finger_points(rig, side, k):
    P = rig.pose.bones; M = rig.matrix_world; pts = []
    for j in (2, 3):
        pb = P.get(f'finger{k}-{j}.{side}')
        if pb:
            pts += [M @ pb.head, M @ ((pb.head + pb.tail) / 2), M @ pb.tail]
    return pts


def contact_grip(rig, api, side, objs, step=3.0, max_deg=75.0, radius=0.009):
    """Curl each finger in small steps until it touches the held prop (finger joints within `radius` of the prop's
    surface: the glove's half-thickness), so a hand closes ON the prop instead of floating next to it or closing
    through it. Returns {finger: extra degrees}; the rig's finger rotations are restored, apply with apply_grip."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for o in objs:
        if o.type != 'MESH': continue
        ev = o.evaluated_get(dg); me = ev.to_mesh(); tmp = bmesh.new(); tmp.from_mesh(me); tmp.transform(ev.matrix_world)
        m2 = bpy.data.meshes.new('_grip'); tmp.to_mesh(m2); tmp.free(); bm.from_mesh(m2); bpy.data.meshes.remove(m2); ev.to_mesh_clear()
    if not bm.faces:
        bm.free(); return {}
    bvh = BVHTree.FromBMesh(bm); bm.free()
    P = rig.pose.bones
    names = [f'finger{k}-{j}.{side}' for k in range(1, 6) for j in (1, 2, 3)]
    saved = {n: P[n].rotation_quaternion.copy() for n in names if n in P}
    out = {}
    for k in range(1, 6):
        def dist():
            ds = [bvh.find_nearest(p)[3] for p in _finger_points(rig, side, k)]
            return min(d for d in ds if d is not None) if ds else 1.0
        d0 = dist()
        if d0 > 0.06 or d0 < radius:          # this finger is nowhere near the prop, or already on it
            out[k] = 0.0; continue
        tot = 0.0
        while tot < max_deg and dist() > radius:
            api._curl(rig, side, {k: step}, 0); tot += step
        out[k] = tot if dist() <= radius * 1.5 else 0.0     # never touched: leave the finger as posed, not clawed
    for n, q in saved.items():
        P[n].rotation_quaternion = q
    bpy.context.view_layer.update()
    return out


def _clean_fingers(rig, side):
    # api._curl writes pb.matrix, which leaves tiny scale/location residue in the bone; the per-frame pose resets
    # rotations only, so without this the residue compounds frame after frame (the fingers grew into giant tubes in
    # the first audit-3 test render)
    for pb in rig.pose.bones:
        if pb.name.startswith('finger') and pb.name.endswith('.' + side):
            pb.location = (0, 0, 0); pb.scale = (1, 1, 1)


def apply_grip(rig, api, side, grip):
    _clean_fingers(rig, side)
    if grip and any(grip.values()):
        api._curl(rig, side, {k: d for k, d in grip.items() if d}, 0)
        _clean_fingers(rig, side)
        bpy.context.view_layer.update()


def seat_prop(rig, side, root, objs, radius=0.01, step=0.002, floor=-0.01):
    """Slide a palm-socket prop toward the palm (socket -Z) until it is `radius` from the nearest finger or palm
    joint, so the hand has something to close on. The old placement lifted props clear of the palm by 3.5 cm to
    pass the clipping check, which is why they floated in front of open fingers. Returns the socket-space z."""
    P = rig.pose.bones; M = rig.matrix_world
    def joints():
        pts = []
        for k in range(1, 6):
            for j in (1, 2, 3):
                pb = P.get(f'finger{k}-{j}.{side}')
                if pb: pts += [M @ pb.head, M @ ((pb.head + pb.tail) / 2), M @ pb.tail]
        return pts
    def gap():
        bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new()
        for o in objs:
            if o.type != 'MESH': continue
            ev = o.evaluated_get(dg); me = ev.to_mesh(); t = bmesh.new(); t.from_mesh(me); t.transform(ev.matrix_world)
            m2 = bpy.data.meshes.new('_seat'); t.to_mesh(m2); t.free(); bm.from_mesh(m2); bpy.data.meshes.remove(m2); ev.to_mesh_clear()
        bvh = BVHTree.FromBMesh(bm); bm.free()
        return min(d for d in (bvh.find_nearest(p)[3] for p in joints()) if d is not None)
    z = root.location.z
    while z > floor and gap() > radius:
        z -= step; root.location.z = z
    return z


def pinch_place(rig, api, side, root, objs, tuck=(3, 4, 5), tuck_deg=55.0):
    """A small prop (lure, bottle cap, pen) held in a pinch: the other fingers fold out of the way, the prop's
    centre goes to the midpoint between the thumb tip and the index tip, then contact_grip closes thumb and index on
    it. Returns (z_offset_in_socket_space, grip) like seat_prop + contact_grip, with the location as a full vector."""
    P = rig.pose.bones; M = rig.matrix_world
    saved = {pb.name: pb.rotation_quaternion.copy() for pb in P if pb.name.startswith('finger') and pb.name.endswith('.' + side)}
    api._curl(rig, side, {k: tuck_deg for k in tuck}, 0)
    bpy.context.view_layer.update()
    T = M @ P[f'finger1-3.{side}'].tail; I = M @ P[f'finger2-3.{side}'].tail
    mw = root.matrix_world.copy(); mw.translation = (T + I) / 2 + (I - T).normalized().cross((M @ P[f'finger2-1.{side}'].head) - I).normalized() * 0.0
    root.matrix_world = mw; bpy.context.view_layer.update()
    loc = root.location.copy()
    for n, q in saved.items(): P[n].rotation_quaternion = q
    bpy.context.view_layer.update()
    api._curl(rig, side, {k: tuck_deg for k in tuck}, 0)
    g = contact_grip(rig, api, side, objs, radius=0.008)
    for n, q in saved.items(): P[n].rotation_quaternion = q
    bpy.context.view_layer.update()
    g = {k: (g.get(k, 0.0) if k in (1, 2) else 0.0) + (tuck_deg if k in tuck else 0.0) for k in range(1, 6)}
    return loc, g
