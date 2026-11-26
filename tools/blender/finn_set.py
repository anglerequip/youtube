"""Dawn lake jetty set for the AnglerMind HOST ads (docs/styles/HOST.md), Blender.

build_set(opts) makes: a weathered wooden jetty running out into a misty lake, the lake (glossy, rippled), a reedy
bank with stones, conifer silhouettes on the far shore fading into ground fog, a low warm sun with a cool sky fill,
and a volume of mist for light shafts. Warm key, cool fill (HOST.md 3). Everything procedural; textures come from
D:\\CounterPhysical\\assets-cc0\\textures when `tex_dir` is given (CC0), otherwise procedural shaders.
Coordinates: z up, the jetty runs along +y out over the water, its deck top at z = 0.55, the bank at y < 0.
"""
import bpy, bmesh, math, os, random
from mathutils import Vector

DECK_Z = 0.55


def _lin(hexc):
    c = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def _mat(name, color, rough=0.6, metal=0.0, noise=0.0, noise_scale=6.0, bump=0.0, tex=None, tex_dir=None, uv_scale=1.0):
    """Principled material; optional colour noise (painted variation), bump, or a CC0 texture set folder."""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*_lin(color), 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    folder = None
    if tex and tex_dir:
        cand = os.path.join(tex_dir, tex)
        if os.path.isdir(cand):
            subs = [os.path.join(cand, d) for d in sorted(os.listdir(cand)) if os.path.isdir(os.path.join(cand, d))]
            folder = subs[0] if subs else cand
    if folder:
        files = os.listdir(folder)
        def pick(*keys):
            for f in files:
                fl = f.lower()
                if any(k in fl for k in keys) and fl.endswith(('.png', '.jpg', '.jpeg')): return os.path.join(folder, f)
        tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (uv_scale, uv_scale, uv_scale); nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
        col = pick('color', 'albedo', 'diff', 'basecolor')
        if col:
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(col); t.projection = 'BOX'; t.projection_blend = 0.3
            nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 0.85
            mix.inputs[6].default_value = (*[min(1.0, x * 2.2) for x in _lin(color)], 1)
            nt.links.new(t.outputs['Color'], mix.inputs[7]); nt.links.new(mix.outputs[2], b.inputs['Base Color'])
        nrm = pick('normalgl', 'nor_gl', 'normal', 'nrm')
        if nrm:
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(nrm); t.image.colorspace_settings.name = 'Non-Color'
            t.projection = 'BOX'; t.projection_blend = 0.3; nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
            nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.8
            nt.links.new(t.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
        rg = pick('rough')
        if rg:
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(rg); t.image.colorspace_settings.name = 'Non-Color'
            t.projection = 'BOX'; t.projection_blend = 0.3; nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
            nt.links.new(t.outputs['Color'], b.inputs['Roughness'])
        return m
    if noise:
        tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = noise_scale; nz.inputs['Detail'].default_value = 8; nz.inputs['Roughness'].default_value = 0.6
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        c = _lin(color)
        ramp.color_ramp.elements[0].color = (*[x * (1 - noise) for x in c], 1)
        ramp.color_ramp.elements[1].color = (*[min(1, x * (1 + noise)) for x in c], 1)
        nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
        if bump:
            bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump
            nt.links.new(nz.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def _obj(name, bm, mat, smooth=False, coll=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth
    o = bpy.data.objects.new(name, me); (coll or bpy.context.scene.collection).objects.link(o)
    if mat: me.materials.append(mat)
    return o


def _box(name, size, loc, mat, rot=(0, 0, 0), bevel=0.0, coll=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    o = _obj(name, bm, mat, False, coll); o.location = loc; o.rotation_euler = rot
    if bevel:
        bv = o.modifiers.new('bev', 'BEVEL'); bv.width = bevel; bv.segments = 2; bv.limit_method = 'ANGLE'
    return o


def _cyl(name, r, h, loc, mat, seg=24, rot=(0, 0, 0), coll=None):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h)
    o = _obj(name, bm, mat, True, coll); o.location = loc; o.rotation_euler = rot
    return o


def jetty(M, rnd, length=9.0, width=1.6):
    """Planked jetty on posts: planks of slightly different tone/height, two stringers, posts with rope."""
    objs = []
    n = int(length / 0.16)
    for k in range(n):
        y = -0.8 + k * 0.16
        m = M['plank'][rnd.randrange(len(M['plank']))]
        o = _box('plank', (width + rnd.uniform(-0.04, 0.04), 0.145, 0.04), (rnd.uniform(-0.015, 0.015), y, DECK_Z - 0.02 + rnd.uniform(-0.006, 0.004)), m,
                 rot=(rnd.uniform(-0.01, 0.01), rnd.uniform(-0.012, 0.012), rnd.uniform(-0.01, 0.01)), bevel=0.006)
        objs.append(o)
    for s in (-1, 1):
        objs.append(_box('stringer', (0.08, length, 0.16), (s * (width / 2 - 0.12), -0.8 + length / 2, DECK_Z - 0.13), M['post']))
    for k in range(int(length / 1.8) + 1):
        y = -0.6 + k * 1.8
        for s in (-1, 1):
            h = DECK_Z + 1.4 + (0.45 if k % 2 == 0 else 0.0)
            o = _cyl('post', 0.085, h, (s * (width / 2 + 0.02), y, DECK_Z + (0.45 if k % 2 == 0 else 0.0) - h / 2 + 0.0), M['post'], 20)
            o.rotation_euler = (rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), 0); objs.append(o)
            if k % 2 == 0:
                bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.088, radius2=0.03, depth=0.05)
                cap = _obj('post_cap', bm, M['post'], True); cap.location = (s * (width / 2 + 0.02), y, DECK_Z + 0.47); objs.append(cap)
                tor = bpy.data.meshes.new('rope')
                bm = bmesh.new(); bmesh.ops.create_circle(bm, segments=32, radius=0.1)
                # rope coil: torus via a curve would be nicer; a thick ring is enough at phone size
                bpy.ops.mesh.primitive_torus_add(major_radius=0.098, minor_radius=0.016, major_segments=32, minor_segments=12,
                                                 location=(s * (width / 2 + 0.02), y, DECK_Z + 0.3))
                r = bpy.context.active_object; r.name = 'rope'; r.data.materials.append(M['rope']); objs.append(r)
    return objs


def water(M, size=400):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    o = _obj('lake', bm, M['water']); o.location = (0, 0, 0.0)
    return o


def bank(M, rnd):
    """The near bank: a gentle muddy-grass slope behind the jetty root (y < 0), reeds, a few stones."""
    objs = []
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=80, y_segments=40, size=1.0)
    for v in bm.verts:
        x, y = v.co.x * 30, v.co.y * 10 - 10          # y from -20 to 0
        z = 0.65 * (1 / (1 + math.exp((y + 0.6) * 2.2))) - 0.25 + 0.06 * math.sin(x * 0.7) * math.cos(y * 0.9)
        v.co = Vector((x, y, z))
    o = _obj('bank', bm, M['ground'], True); objs.append(o)
    for k in range(260):
        x = rnd.uniform(-9, 9)
        if abs(x) < 1.1 and rnd.random() < 0.85: continue
        y = rnd.uniform(-1.2, 1.6)
        h = rnd.uniform(0.7, 1.6)
        lean = Vector((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.1, 0.15), 1)).normalized()
        bm = bmesh.new()
        base = Vector((x, y, -0.05)); w = rnd.uniform(0.008, 0.014)
        side = Vector((1, 0, 0)) if abs(lean.x) < 0.9 else Vector((0, 1, 0))
        n = 6
        verts = []
        for j in range(n + 1):
            t = j / n
            p = base + lean * h * t + Vector((0.06 * t * t * math.copysign(1, lean.x), 0, 0))
            ww = w * (1 - t) + 0.001
            verts.append((bm.verts.new(p - side * ww), bm.verts.new(p + side * ww)))
        for j in range(n): bm.faces.new((verts[j][0], verts[j][1], verts[j + 1][1], verts[j + 1][0]))
        o = _obj('reed', bm, M['reed'] if rnd.random() < 0.7 else M['reed_dry'], True); objs.append(o)
        if rnd.random() < 0.25:                    # cattail head
            p = base + lean * h * 0.86
            c = _cyl('cattail', 0.018, 0.14, p, M['cattail'], 12); c.rotation_euler = lean.to_track_quat('Z', 'Y').to_euler(); objs.append(c)
    for k in range(40):
        x = rnd.uniform(-6, 6); y = rnd.uniform(-1.6, 0.4)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=rnd.uniform(0.08, 0.3), location=(x, y, -0.05))
        s = bpy.context.active_object; s.name = 'stone'; s.scale = (1, rnd.uniform(0.7, 1.2), rnd.uniform(0.4, 0.7))
        s.data.materials.append(M['stone']); objs.append(s)
    return objs


def far_shore(M, rnd):
    """Far shore 70-110 m out: low hills and rows of conifer cones; the fog makes them layered silhouettes."""
    objs = []
    for row, (dist, n) in enumerate(((70, 60), (95, 70), (130, 80))):
        bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=60, y_segments=4, size=1.0)
        for v in bm.verts:
            x = v.co.x * 160; yy = dist + (v.co.y + 1) * 15
            z = (v.co.y + 1) * (4 + row * 3) * (0.6 + 0.4 * math.sin(x * 0.03 + row)) - 0.3
            v.co = Vector((x, yy, z))
        objs.append(_obj('hill', bm, M['forest'], True))
        for k in range(n):
            x = rnd.uniform(-150, 150); y = dist + rnd.uniform(0, 6)
            h = rnd.uniform(6, 13)
            bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=h * 0.22, radius2=0.0, depth=h)
            o = _obj('conifer', bm, M['forest']); o.location = (x, y, h / 2 - 0.5 + (row * 1.5)); objs.append(o)
    return objs


def light_and_world(opts):
    """Low warm sun behind-left (rim light and long shafts in the mist), cool sky dome, mist volume."""
    sc = bpy.context.scene
    w = bpy.data.worlds.new('dawn'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    sky = nt.nodes.new('ShaderNodeTexGradient'); sky.gradient_type = 'LINEAR'
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, math.radians(-90), 0)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], sky.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.5; ramp.color_ramp.elements[0].color = (*_lin('#e9c9a0'), 1)   # warm horizon
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (*_lin('#6f86a3'), 1)  # cool zenith
    nt.links.new(sky.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = opts.get('sky', 0.9)
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = opts.get('sun', 3.6); sun.color = _lin('#ffc58a'); sun.angle = math.radians(2.0)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(90 - opts.get('sun_elev', 9)), 0, math.radians(opts.get('sun_az', 200)))
    # the sun disc itself low over the far shore
    bpy.ops.mesh.primitive_uv_sphere_add(radius=6, location=(-60, 160, 14))
    d = bpy.context.active_object; d.name = 'sun_disc'
    md = bpy.data.materials.new('sun_disc'); md.use_nodes = True; e = md.node_tree.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*_lin('#ffd7a0'), 1); e.inputs['Strength'].default_value = 18
    md.node_tree.links.new(e.outputs[0], md.node_tree.nodes['Material Output'].inputs['Surface']); d.data.materials.append(md)
    # mist: a big box with volume scatter, denser low over the water (height gradient)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 60, 6)); mist = bpy.context.active_object; mist.name = 'mist'
    mist.scale = (240, 200, 14)
    mv = bpy.data.materials.new('mist'); mv.use_nodes = True; mt = mv.node_tree
    mt.nodes.remove(mt.nodes['Principled BSDF'])
    vol = mt.nodes.new('ShaderNodeVolumePrincipled'); vol.inputs['Color'].default_value = (*_lin('#c9cdd2'), 1)
    vol.inputs['Anisotropy'].default_value = 0.55
    tc2 = mt.nodes.new('ShaderNodeTexCoord'); sep = mt.nodes.new('ShaderNodeSeparateXYZ')
    mt.links.new(tc2.outputs['Generated'], sep.inputs['Vector'])
    cr = mt.nodes.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.42; cr.inputs['From Max'].default_value = 0.6
    cr.inputs['To Min'].default_value = opts.get('mist_low', 0.03); cr.inputs['To Max'].default_value = opts.get('mist_high', 0.004)
    mt.links.new(sep.outputs['Z'], cr.inputs['Value']); mt.links.new(cr.outputs['Result'], vol.inputs['Density'])
    mt.links.new(vol.outputs['Volume'], mt.nodes['Material Output'].inputs['Volume']); mist.data.materials.append(mv)
    return so


def materials(tex_dir=None):
    M = {}
    M['plank'] = [_mat(f'plank{k}', c, 0.8, noise=0.25, noise_scale=40, bump=0.25, tex='wood_planks', tex_dir=tex_dir, uv_scale=1.5)
                  for k, c in enumerate(('#8a7356', '#7b6650', '#94805f', '#6f5d48'))]
    M['post'] = _mat('post', '#4f4333', 0.85, noise=0.3, noise_scale=20, bump=0.3, tex='wood_planks', tex_dir=tex_dir)
    M['rope'] = _mat('rope', '#a8916a', 0.9, noise=0.2, noise_scale=80, bump=0.4, tex='rope', tex_dir=tex_dir, uv_scale=8)
    M['ground'] = _mat('ground', '#4d4a2c', 0.95, noise=0.35, noise_scale=3, bump=0.2, tex='mossy_ground', tex_dir=tex_dir, uv_scale=0.4)
    M['reed'] = _mat('reed', '#7c7a3a', 0.7, noise=0.15)
    M['reed_dry'] = _mat('reed_dry', '#a8925c', 0.7, noise=0.15)
    M['cattail'] = _mat('cattail', '#4a2e1c', 0.8)
    M['stone'] = _mat('stone', '#6b6a63', 0.75, noise=0.3, noise_scale=8, bump=0.3, tex='wet_rocks', tex_dir=tex_dir)
    M['forest'] = _mat('forest', '#27311f', 0.95)
    w = bpy.data.materials.new('water'); w.use_nodes = True; nt = w.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*_lin('#2a3a3c'), 1); b.inputs['Roughness'].default_value = 0.06
    b.inputs['IOR'].default_value = 1.33
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 6
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 3, 1)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.08; bp.inputs['Distance'].default_value = 0.02
    nt.links.new(nz.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    M['water'] = w
    return M


def build_set(opts=None):
    opts = opts or {}
    rnd = random.Random(opts.get('seed', 7))
    M = materials(opts.get('tex_dir'))
    objs = jetty(M, rnd) + [water(M)] + bank(M, rnd) + far_shore(M, rnd)
    sun = light_and_world(opts)
    return {'M': M, 'objs': objs, 'sun': sun}
