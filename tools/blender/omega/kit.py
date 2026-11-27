"""OMEGA Blender kit: shared builders for the stylised 'high-poly but blocky' look (HOST_RENDER_RULES 0, 7, 9).

Everything here is built in Blender from scratch (no external assets). Run inside Blender 5.2:
  blender -b -P tools/blender/omega/calib_m3.py -- --shot prop
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, Euler


# ----------------------------------------------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            sc.render.engine = eng; break
        except TypeError:
            continue
    return sc


def eevee_quality(sc, samples=96):
    e = sc.eevee
    for k, v in (('taa_render_samples', samples), ('use_shadows', True), ('use_raytracing', True),
                 ('shadow_ray_count', 2), ('shadow_step_count', 8), ('use_volumetric_shadows', True),
                 ('volumetric_tile_size', '4'), ('volumetric_samples', 96), ('volumetric_end', 120.0),
                 ('fast_gi_method', 'GLOBAL_ILLUMINATION'), ('use_fast_gi', True)):
        try: setattr(e, k, v)
        except Exception: pass
    try:
        e.ray_tracing_method = 'SCREEN'
        e.ray_tracing_options.resolution_scale = '1'
    except Exception: pass
    sc.render.filter_size = 0.8                       # crisp polygon edges (rule 9.4)
    vs = sc.view_settings
    vs.view_transform = 'AgX'
    try: vs.look = 'AgX - Punchy'
    except Exception: pass


def output(sc, w=1080, h=1920, pct=50):
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, pct
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '16'


# ----------------------------------------------------------------------------------------------------- mesh helpers
def link(o, coll=None):
    (coll or bpy.context.scene.collection).objects.link(o)
    return o


def from_bm(name, bm, mat=None, smooth_angle=35.0):
    me = bpy.data.meshes.new(name)
    if smooth_angle is not None:
        # smooth inside a plane, hard at the plane borders (rule 7.3): edges sharper than smooth_angle stay faceted
        lim = math.radians(smooth_angle)
        for f in bm.faces: f.smooth = True
        for e in bm.edges:
            e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    if mat: me.materials.append(mat)
    return link(o)


def bevel(o, width=0.01, segs=2, angle=40.0, profile=0.6):
    m = o.modifiers.new('bevel', 'BEVEL')
    m.width, m.segments, m.profile = width, segs, profile
    m.limit_method = 'ANGLE'; m.angle_limit = math.radians(angle)
    m.harden_normals = False
    return m


def box(name, size, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, bev=0.01, segs=2, jitter=0.0, seed=0):
    """A bevelled block. jitter nudges the vertices so nothing is machine-perfect (hand-built miniature)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if jitter:
        r = random.Random(seed)
        for v in bm.verts:
            v.co += Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))) * jitter
    o = from_bm(name, bm, mat)
    o.location, o.rotation_euler = loc, rot
    if bev: bevel(o, bev, segs)
    return o


def cyl(name, r, h, loc=(0, 0, 0), rot=(0, 0, 0), seg=24, mat=None, bev=0.006, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    o = from_bm(name, bm, mat)
    o.location, o.rotation_euler = loc, rot
    if bev: bevel(o, bev, 2)
    return o


def lathe(name, profile, seg=32, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, angle=35.0):
    """profile: [(radius, z), ...] bottom to top. Closed at both ends when radius 0."""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = from_bm(name, bm, mat, smooth_angle=angle)
    o.location, o.rotation_euler = loc, rot
    return o


def text_mesh(name, body, size, loc, rot, mat, extrude=0.0004, align='CENTER', font_bold=True):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size
    cu.align_x = align; cu.align_y = 'CENTER'; cu.extrude = extrude
    try:
        if font_bold:
            cu.font = bpy.data.fonts.load(r'C:\Windows\Fonts\arialbd.ttf', check_existing=True)
    except Exception: pass
    o = bpy.data.objects.new(name, cu); link(o)
    o.location, o.rotation_euler = loc, rot
    o.data.materials.append(mat)
    return o


# ----------------------------------------------------------------------------------------------------- materials
def _nodes(m):
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    return nt, bsdf


def hexc(h, a=1.0):
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, a)


def painted(name, tones, rough=0.7, metal=0.0, scale=1.6, cavity=0.55, cavity_dist=0.06, rough_var=0.08,
            spec=0.5, stripes=None, coat=0.0, grain_axis='Y', ribs=None):
    """A painted (not scanned) material: 2-3 tones blended by large-scale noise (value breakup over 10-30 cm),
    darker in cavities (AO node), roughness varied gently with the same noise. `stripes` (scale, strength) adds
    long grain bands along local X for wood."""
    m = bpy.data.materials.new(name)
    nt, b = _nodes(m); N, L = nt.nodes, nt.links
    tc = N.new('ShaderNodeTexCoord')
    noise = N.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 2.0; noise.inputs['Roughness'].default_value = 0.45
    L.new(tc.outputs['Object'], noise.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.3, hexc(tones[0])
    cr.elements[1].position, cr.elements[1].color = 0.7, hexc(tones[-1])
    if len(tones) > 2:
        e = cr.elements.new(0.5); e.color = hexc(tones[1])
    fac = noise.outputs['Fac']
    if stripes:
        # wood grain: a noise stretched along the board (grain_axis), lightly distorted, mixed under the breakup
        gm = N.new('ShaderNodeMapping')
        gm.inputs['Scale'].default_value = {'X': (0.06, 1.0, 1.0), 'Y': (1.0, 0.06, 1.0), 'Z': (1.0, 1.0, 0.06)}[grain_axis]
        L.new(tc.outputs['Object'], gm.inputs['Vector'])
        gn = N.new('ShaderNodeTexNoise'); gn.inputs['Scale'].default_value = stripes[0]
        gn.inputs['Detail'].default_value = 3.0; gn.inputs['Distortion'].default_value = 0.4
        L.new(gm.outputs['Vector'], gn.inputs['Vector'])
        gc = N.new('ShaderNodeMapRange'); gc.inputs['From Min'].default_value = 0.38; gc.inputs['From Max'].default_value = 0.62
        L.new(gn.outputs['Fac'], gc.inputs['Value'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'FLOAT'; mx.inputs['Factor'].default_value = stripes[1]
        L.new(fac, mx.inputs['A']); L.new(gc.outputs['Result'], mx.inputs['B']); fac = mx.outputs['Result']
    L.new(fac, ramp.inputs['Fac'])
    col = ramp.outputs['Color']
    if cavity:
        ao = N.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = cavity_dist
        try: ao.only_local = True
        except Exception: pass
        L.new(col, ao.inputs['Color'])
        dark = N.new('ShaderNodeMix'); dark.data_type = 'RGBA'; dark.blend_type = 'MULTIPLY'
        inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
        L.new(ao.outputs['AO'], inv.inputs[1])
        sc = N.new('ShaderNodeMath'); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = cavity
        L.new(inv.outputs[0], sc.inputs[0])
        L.new(sc.outputs[0], dark.inputs['Factor'])
        L.new(col, dark.inputs['A']); dark.inputs['B'].default_value = (0.08, 0.05, 0.04, 1)
        col = dark.outputs['Result']
    L.new(col, b.inputs['Base Color'])
    rr = N.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = rough - rough_var
    rr.inputs['To Max'].default_value = rough + rough_var
    L.new(noise.outputs['Fac'], rr.inputs['Value']); L.new(rr.outputs['Result'], b.inputs['Roughness'])
    b.inputs['Metallic'].default_value = metal
    try: b.inputs['Specular IOR Level'].default_value = spec
    except Exception: pass
    if coat:
        b.inputs['Coat Weight'].default_value = coat
    if ribs:
        # knit ribs: count ribs around a vertical axis through `center` (world), as a bump (count, strength, center)
        count, strength, center = ribs
        geo = N.new('ShaderNodeNewGeometry')
        sub = N.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = center
        L.new(geo.outputs['Position'], sub.inputs[0])
        grad = N.new('ShaderNodeTexGradient'); grad.gradient_type = 'RADIAL'
        L.new(sub.outputs['Vector'], grad.inputs['Vector'])
        mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = count * 6.2832
        L.new(grad.outputs['Fac'], mul.inputs[0])
        sn = N.new('ShaderNodeMath'); sn.operation = 'SINE'; L.new(mul.outputs[0], sn.inputs[0])
        ab = N.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; L.new(sn.outputs[0], ab.inputs[0])
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = strength; bp.inputs['Distance'].default_value = 0.004
        L.new(ab.outputs[0], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
        dk = N.new('ShaderNodeMix'); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'; dk.inputs['Factor'].default_value = 0.35
        L.new(b.inputs['Base Color'].links[0].from_socket, dk.inputs['A'])
        ramp2 = N.new('ShaderNodeValToRGB'); ramp2.color_ramp.elements[0].color = (0.55, 0.55, 0.55, 1)
        L.new(ab.outputs[0], ramp2.inputs['Fac']); L.new(ramp2.outputs['Color'], dk.inputs['B'])
        L.new(dk.outputs['Result'], b.inputs['Base Color'])
    return m


def flat(name, color, rough=0.5, metal=0.0, emit=None, emit_strength=0.0, alpha=1.0, transmission=0.0, ior=1.45):
    m = bpy.data.materials.new(name)
    nt, b = _nodes(m)
    b.inputs['Base Color'].default_value = hexc(color)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = hexc(emit); b.inputs['Emission Strength'].default_value = emit_strength
    if transmission:
        b.inputs['Transmission Weight'].default_value = transmission; b.inputs['IOR'].default_value = ior
    return m


def water(name='water'):
    """Stylised lake: dark, glossy, broad ripples (no fine noise), reflects the sky and the rim light."""
    m = bpy.data.materials.new(name)
    nt, b = _nodes(m); N, L = nt.nodes, nt.links
    b.inputs['Base Color'].default_value = hexc('#0f1d1c')
    b.inputs['Roughness'].default_value = 0.06
    try: b.inputs['Specular IOR Level'].default_value = 0.6
    except Exception: pass
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 3.0, 1.0)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'
    wv.inputs['Scale'].default_value = 0.9; wv.inputs['Distortion'].default_value = 4.0; wv.inputs['Detail'].default_value = 1.0
    L.new(mp.outputs['Vector'], wv.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.12; bump.inputs['Distance'].default_value = 0.05
    L.new(wv.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


# ----------------------------------------------------------------------------------------------------- world, lights
def sky_world(top='#1d3346', mid='#c9764a', horizon='#f0b070', strength=1.0, fog_density=0.012, fog_color='#d9a27a',
              fog_aniso=0.55, ambient=None, sun_dir=None, sun_color='#ffcf8a', fog_box=((0, 20, 6), (90, 90, 16))):
    """Painted sunset gradient + a world volume for depth haze and light shafts."""
    w = bpy.data.worlds.new('sky'); bpy.context.scene.world = w
    w.use_nodes = True; nt = w.node_tree; N, L = nt.nodes, nt.links
    bg = N.get('Background'); out = N.get('World Output')
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ')
    L.new(tc.outputs['Generated'], sep.inputs['Vector'])
    # Generated z on the world is the view direction z in [-1,1]: map to [0,1]
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -0.15; mr.inputs['From Max'].default_value = 0.6
    L.new(sep.outputs['Z'], mr.inputs['Value'])
    ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, hexc(horizon)
    cr.elements[1].position, cr.elements[1].color = 1.0, hexc(top)
    e = cr.elements.new(0.3); e.color = hexc(mid)
    L.new(mr.outputs['Result'], ramp.inputs['Fac'])
    col = ramp.outputs['Color']
    if sun_dir is not None:
        # a painted sun glow: (dot(view, sun) ^ k) in a warm colour, added over the gradient
        nrm = N.new('ShaderNodeVectorMath'); nrm.operation = 'NORMALIZE'
        L.new(tc.outputs['Generated'], nrm.inputs[0])
        dot = N.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'; dot.inputs[1].default_value = tuple(sun_dir)
        L.new(nrm.outputs['Vector'], dot.inputs[0])
        cl = N.new('ShaderNodeMath'); cl.operation = 'MAXIMUM'; cl.inputs[1].default_value = 0.0
        L.new(dot.outputs['Value'], cl.inputs[0])
        for k, (pw, amt) in enumerate(((5.0, 0.3), (60.0, 1.2), (2500.0, 30.0))):
            pp = N.new('ShaderNodeMath'); pp.operation = 'POWER'; pp.inputs[1].default_value = pw
            L.new(cl.outputs[0], pp.inputs[0])
            sc_ = N.new('ShaderNodeMath'); sc_.operation = 'MULTIPLY'; sc_.inputs[1].default_value = amt
            L.new(pp.outputs[0], sc_.inputs[0])
            ad = N.new('ShaderNodeMix'); ad.data_type = 'RGBA'; ad.blend_type = 'ADD'
            L.new(sc_.outputs[0], ad.inputs['Factor']); L.new(col, ad.inputs['A'])
            ad.inputs['B'].default_value = hexc(sun_color)
            col = ad.outputs['Result']
    L.new(col, bg.inputs['Color']); bg.inputs['Strength'].default_value = strength
    if ambient:
        # the camera sees the painted gradient; everything else is lit by a cooler, dimmer sky so the shadows go
        # blue-teal against the warm sun (warm/cool separation, rule 3)
        lp = N.new('ShaderNodeLightPath'); amb = N.new('ShaderNodeBackground')
        amb.inputs['Color'].default_value = hexc(ambient[0]); amb.inputs['Strength'].default_value = ambient[1]
        mix = N.new('ShaderNodeMixShader')
        L.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac'])
        L.new(amb.outputs['Background'], mix.inputs[1]); L.new(bg.outputs['Background'], mix.inputs[2])
        L.new(mix.outputs['Shader'], out.inputs['Surface'])
    if fog_density and fog_box:
        # Eevee treats a world volume as infinite and absorbs the sky behind it, so the haze lives in a bounded box
        bpy.ops.mesh.primitive_cube_add(size=1, location=fog_box[0]); fb = bpy.context.active_object
        fb.name = 'haze'; fb.scale = fog_box[1]
        fm = bpy.data.materials.new('haze'); fm.use_nodes = True; fnt = fm.node_tree
        fnt.nodes.remove(fnt.nodes['Principled BSDF'])
        v = fnt.nodes.new('ShaderNodeVolumePrincipled')
        v.inputs['Color'].default_value = hexc(fog_color); v.inputs['Density'].default_value = fog_density
        v.inputs['Anisotropy'].default_value = fog_aniso
        fnt.links.new(v.outputs['Volume'], fnt.nodes['Material Output'].inputs['Volume'])
        fb.data.materials.append(fm)
    elif fog_density:
        vol = N.new('ShaderNodeVolumePrincipled')
        vol.inputs['Color'].default_value = hexc(fog_color)
        vol.inputs['Density'].default_value = fog_density
        vol.inputs['Anisotropy'].default_value = fog_aniso
        L.new(vol.outputs['Volume'], out.inputs['Volume'])
    return w


def sun(name, rot_deg, color='#ffb46b', strength=4.0, angle=1.5):
    d = bpy.data.lights.new(name, 'SUN'); d.color = hexc(color)[:3]; d.energy = strength
    d.angle = math.radians(angle)
    try: d.volume_factor = 1.0
    except Exception: pass
    o = bpy.data.objects.new(name, d); link(o)
    o.rotation_euler = [math.radians(a) for a in rot_deg]
    return o


def area(name, loc, target, color='#ffffff', power=300.0, size=1.0, shape='DISK', vol=0.0):
    d = bpy.data.lights.new(name, 'AREA'); d.color = hexc(color)[:3]; d.energy = power
    d.shape = shape; d.size = size
    try: d.volume_factor = vol
    except Exception: pass
    o = bpy.data.objects.new(name, d); link(o); o.location = loc
    aim(o, target)
    return o


def point(name, loc, color='#ffb060', power=30.0, radius=0.03):
    d = bpy.data.lights.new(name, 'POINT'); d.color = hexc(color)[:3]; d.energy = power; d.shadow_soft_size = radius
    o = bpy.data.objects.new(name, d); link(o); o.location = loc
    return o


def aim(o, target):
    v = Vector(target) - o.location
    o.rotation_euler = v.to_track_quat('-Z', 'Y').to_euler()


def camera(name, loc, target, lens=50.0, fstop=None, focus=None, sensor=36.0):
    c = bpy.data.cameras.new(name); c.lens = lens; c.sensor_width = sensor; c.sensor_fit = 'HORIZONTAL'
    o = bpy.data.objects.new(name, c); link(o); o.location = loc
    aim(o, target)
    if fstop:
        c.dof.use_dof = True; c.dof.aperture_fstop = fstop
        c.dof.focus_distance = focus if focus else (Vector(target) - Vector(loc)).length
    bpy.context.scene.camera = o
    return o


def asset(p):
    """Local Windows path on Caesar's PC; with OMEGA_ROOT set (cloud render), the same file in the repo bundle
    assets/omega: textures/<set>/..., anim/<glb>, and loose images by file name."""
    r = os.environ.get('OMEGA_ROOT')
    if not r: return p
    q = p.replace('\\', '/')
    if '/textures' in q: return os.path.join(r, 'textures' + q.split('/textures', 1)[1])
    return os.path.join(r, 'anim' if q.endswith('.glb') else '', os.path.basename(q))


TEX_ROOT = asset(r'D:\CounterPhysical\assets-cc0\textures')


def tex_material(name, set_name, scale=1.0, tint=None, rough_add=0.15, normal=0.35, saturation=1.0, flat=None, detail=1.0):
    """A matte game-style material from a CC0 PBR set (ambientCG): colour, roughness and a soft normal, box-projected
    in object space (no UVs needed). Cycle 1-2 audits: the references carry painted game textures on every surface."""
    import os
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links; b = N['Principled BSDF']
    base = os.path.join(TEX_ROOT, set_name, set_name)
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale, scale, scale)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    def img(suffix, noncolor):
        p = base + suffix
        if not os.path.exists(p): return None
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(p, check_existing=True)
        n.projection = 'BOX'; n.projection_blend = 0.25
        if noncolor: n.image.colorspace_settings.name = 'Non-Color'
        L.new(mp.outputs['Vector'], n.inputs['Vector']); return n
    c = img('_Color.jpg', False); r = img('_Roughness.jpg', True); nrm = img('_NormalGL.jpg', True)
    col = c.outputs['Color']
    if tint or saturation != 1.0:
        hs = N.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = saturation
        L.new(col, hs.inputs['Color']); col = hs.outputs['Color']
        if tint:
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
            L.new(col, mx.inputs['A']); mx.inputs['B'].default_value = hexc(tint); col = mx.outputs['Result']
    if flat:                                  # cycle 3 review: photo textures read as 'realistic Blender'; keep the
        lum = N.new('ShaderNodeRGBToBW'); L.new(col, lum.inputs['Color'])          # texture only as a value modulation
        mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.15; mr.inputs['From Max'].default_value = 0.6
        mr.inputs['To Min'].default_value = 1.0 - 0.35 * detail; mr.inputs['To Max'].default_value = 1.0 + 0.12 * detail
        L.new(lum.outputs['Val'], mr.inputs['Value'])
        mx2 = N.new('ShaderNodeMix'); mx2.data_type = 'RGBA'; mx2.blend_type = 'MULTIPLY'; mx2.inputs['Factor'].default_value = 1.0
        mx2.inputs['A'].default_value = hexc(flat); L.new(mr.outputs['Result'], mx2.inputs['B'])
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.0; L.new(tc.outputs['Object'], nz.inputs['Vector'])
        mr2 = N.new('ShaderNodeMapRange'); mr2.inputs['To Min'].default_value = 0.9; mr2.inputs['To Max'].default_value = 1.08
        L.new(nz.outputs['Fac'], mr2.inputs['Value'])
        mx3 = N.new('ShaderNodeMix'); mx3.data_type = 'RGBA'; mx3.blend_type = 'MULTIPLY'; mx3.inputs['Factor'].default_value = 1.0
        L.new(mx2.outputs['Result'], mx3.inputs['A']); L.new(mr2.outputs['Result'], mx3.inputs['B'])
        col = mx3.outputs['Result']
    L.new(col, b.inputs['Base Color'])
    if r:
        ad = N.new('ShaderNodeMath'); ad.operation = 'ADD'; ad.inputs[1].default_value = rough_add; ad.use_clamp = True
        L.new(r.outputs['Color'], ad.inputs[0]); L.new(ad.outputs[0], b.inputs['Roughness'])
    if nrm:
        nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal
        L.new(nrm.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], b.inputs['Normal'])
    try: b.inputs['Specular IOR Level'].default_value = 0.2
    except Exception: pass
    return m
