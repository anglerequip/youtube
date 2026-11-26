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
