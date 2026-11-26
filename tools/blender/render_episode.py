"""Render a HOST-style episode (Captain Finn) from its plan.json with Blender Eevee.

  blender -b --python tools/blender/render_episode.py -- --plan out/<slug>/plan.json --episode content/episodes/<slug>
          --out out/<slug>/frames [--stills 0.0,2.5,...] [--from F --to F] [--scale 1.0] [--samples 32]

factory/production.py (renderer: blender) calls this. The plan (content/episodes/<slug>/plan.py) lists shots (camera
from/to, target, lens, focus, f-stop, roll), Finn's pose keys, lip-sync amplitude per frame, blinks, which prop is
in his hand when, and what the phone screen shows. This file builds the set (finn_set.py), loads Finn
(finn_v1.py), makes the props, and renders frame by frame. Frames: <out>/f00000.png ...
"""
import bpy, bmesh, math, os, sys, json, argparse, random
from mathutils import Vector, Euler, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import finn_set

FONT_DIR = os.path.join(ROOT, 'assets', 'fonts')


# ---------------------------------------------------------------- helpers
def ease(u):
    u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return [x + (y - x) * u for x, y in zip(a, b)]


def emission_mat(name, img_path, strength=1.6):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(img_path); tex.extension = 'CLIP'
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = strength
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.05
    mix = nt.nodes.new('ShaderNodeMixShader'); mix.inputs['Fac'].default_value = 0.08
    nt.links.new(tex.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs[0], mix.inputs[1]); nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    m['tex'] = tex.name
    return m


# ---------------------------------------------------------------- phone screen pages (real Lure Finder output)
def screen_pages(plan, outdir):
    """Draw the phone screen pages with PIL in AnglerMind's own colours (docs/BRAND.md). The content is the real
    Lure Finder result captured 2026-11-26 (content/episodes/finn-lure-finder/ref/tool_output.md)."""
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(outdir, exist_ok=True)
    W, H = 720, 1480
    olive, cream, sand, rust, ink, lake = '#52652c', '#faf7ea', '#f2edd9', '#b6552a', '#232b1c', '#4c7680'
    def F(sz, w='SemiBold'):
        p = os.path.join(FONT_DIR, f'Inter-{w}.ttf')
        return ImageFont.truetype(p if os.path.exists(p) else os.path.join(FONT_DIR, 'Poppins-SemiBold.ttf'), sz)
    def base(title):
        im = Image.new('RGB', (W, H), sand); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 150], fill=cream); d.text((40, 70), 'AnglerMind', font=F(40), fill=olive)
        d.text((40, 190), 'LURE FINDER', font=F(26), fill=rust); d.text((40, 230), title, font=F(46), fill=ink)
        return im, d
    pages = {}
    cond = next(s for s in plan['screen'] if s['page'] == 'conditions')
    chips = [('Fish', ['Northern pike', 'Perch', 'Zander']), ('Time of day', ['Dawn / dusk', 'Daytime', 'Night']),
             ('Sky', ['Sunny', 'Overcast', 'Rain']), ('Water', ['Clear', 'Stained / tea', 'Murky'])]
    for k in range(len(cond['taps']) + 1):
        im, d = base('What should I tie on?')
        y = 330
        for label, opts in chips:
            d.text((40, y), label.upper(), font=F(24), fill='#6b6a55'); y += 44; x = 40
            for o in opts:
                on = o in cond['taps'][:k]
                w = d.textlength(o, font=F(30)) + 48
                d.rounded_rectangle([x, y, x + w, y + 70], 18, fill=olive if on else cream, outline=olive, width=3)
                d.text((x + 24, y + 18), o, font=F(30), fill=cream if on else ink); x += w + 16
            y += 110
        d.rounded_rectangle([40, H - 200, W - 40, H - 110], 24, fill=olive); d.text((W / 2 - 150, H - 180), 'Show my lure  >', font=F(36), fill=cream)
        p = os.path.join(outdir, f'cond{k}.png'); im.save(p); pages[f'cond{k}'] = p
    im, d = base('Your lure for Northern pike')
    d.rounded_rectangle([30, 330, W - 30, 1100], 28, fill=cream, outline=rust, width=4)
    d.rounded_rectangle([60, 370, 250, 420], 12, fill=rust); d.text((78, 380), 'TOP PICK', font=F(28), fill=cream)
    d.rounded_rectangle([W - 270, 370, W - 60, 420], 12, fill='#dfe3cf'); d.text((W - 250, 380), '9/10 MATCH', font=F(28), fill=olive)
    # the lure drawing: a jointed minnow silhouette
    d.ellipse([110, 480, 360, 600], fill='#c9ccd2'); d.ellipse([340, 485, 600, 595], fill='#c9ccd2')
    d.rectangle([110, 520, 600, 545], fill='#2b2f36'); d.ellipse([140, 515, 165, 540], fill='#1b1d1f')
    d.text((60, 650), 'Rapala Jointed J11', font=F(44), fill=ink); d.text((60, 710), 'Jerkbait · 11 cm · 9 g · Floating', font=F(28, 'Medium'), fill='#55574a')
    d.text((60, 790), 'Picked from', font=F(30, 'Medium'), fill='#55574a')
    d.text((60, 830), '756', font=F(150), fill=rust); d.text((60, 1010), 'real lure models', font=F(36), fill=ink)
    p = os.path.join(outdir, 'result.png'); im.save(p); pages['result'] = p
    im, d = base('Colour for murky water')
    d.rounded_rectangle([30, 330, W - 30, 1180], 28, fill=cream, outline=rust, width=4)
    for i, c in enumerate(('#3d7a2a', '#e2742e', '#d7e04a')):                      # firetiger: green over orange, chartreuse belly
        d.rectangle([90, 400 + i * 70, W - 90, 470 + i * 70], fill=c)
    for k in range(6): d.polygon([(130 + k * 85, 400), (165 + k * 85, 400), (150 + k * 85, 520), (115 + k * 85, 520)], fill='#1f3a14')
    d.text((60, 640), 'Firetiger', font=F(56), fill=ink)
    d.rounded_rectangle([60, 720, 360, 770], 12, fill=rust); d.text((78, 728), 'CONFIDENT CALL', font=F(28), fill=cream)
    d.text((60, 800), 'Hard contrast that holds its shape', font=F(30, 'Medium'), fill='#55574a')
    d.text((60, 840), 'in coloured water.', font=F(30, 'Medium'), fill='#55574a')
    d.text((60, 920), '4,627', font=F(150), fill=rust); d.text((60, 1100), 'factory colourways', font=F(36), fill=ink)
    p = os.path.join(outdir, 'colour.png'); im.save(p); pages['colour'] = p
    return pages


# ---------------------------------------------------------------- props
def make_phone(M):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * 0.074, v.co.y * 0.0085, v.co.z * 0.155))
    body = finn_set._obj('phone', bm, M['phone_body'], True)
    bv = body.modifiers.new('bev', 'BEVEL'); bv.width = 0.009; bv.segments = 6
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts: v.co = Vector((v.co.x * 0.068, -0.0044, v.co.y * 0.148))
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops: l[uv].uv = (l.vert.co.x / 0.068 + 0.5, l.vert.co.z / 0.148 + 0.5)
    scr = finn_set._obj('phone_screen', bm, None, False); scr.parent = body
    return body, scr


def make_lure(M, color='#d7e04a', length=0.11):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=1.0)
    o = bpy.context.active_object; o.name = 'lure'; o.scale = (length / 2, 0.012, 0.016)
    o.data.materials.append(finn_set._mat('lure_' + color, color, 0.25))
    for p in o.data.polygons: p.use_smooth = True
    for s in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.0045, location=(length * 0.33, s * 0.011, 0.004))
        e = bpy.context.active_object; e.data.materials.append(M['ink']); e.parent = o; e.matrix_parent_inverse = o.matrix_world.inverted()
    return o


def make_box(M, rnd):
    """Open tackle box: green plastic body, lid hinged open, two cantilever trays full of bright lures."""
    root = bpy.data.objects.new('tackle_box', None); bpy.context.scene.collection.objects.link(root)
    parts = []
    def box(name, size, loc, mat, rot=(0, 0, 0)):
        o = finn_set._box(name, size, loc, mat, rot, bevel=0.004); o.parent = root; parts.append(o); return o
    box('tb_body', (0.42, 0.24, 0.16), (0, 0, 0.08), M['box'])
    box('tb_lid', (0.42, 0.012, 0.24), (0, 0.13, 0.28), M['box'], rot=(math.radians(-12), 0, 0))
    for k, (dy, dz) in enumerate(((-0.07, 0.2), (0.06, 0.22))):
        box(f'tb_tray{k}', (0.4, 0.11, 0.03), (0, dy, dz), M['tray'])
        for i in range(6):
            for j in range(2):
                c = rnd.choice(['#d7e04a', '#e2742e', '#c92a2e', '#f2f0e6', '#3d7a2a', '#e8b81c', '#8fa6c8', '#e85a8f'])
                bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1.0,
                                                     location=(-0.17 + i * 0.068, dy - 0.025 + j * 0.05, dz + 0.022))
                l = bpy.context.active_object; l.scale = (0.026, 0.009, 0.009); l.rotation_euler = (0, 0, rnd.uniform(-0.3, 0.3))
                l.data.materials.append(finn_set._mat('lure_' + c, c, 0.25)); l.parent = root; parts.append(l)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.05, minor_radius=0.008, location=(0, 0, 0.175), rotation=(math.radians(90), 0, 0))
    h = bpy.context.active_object; h.data.materials.append(M['tray']); h.parent = root
    return root


def make_rod(M):
    pts = [(0, 0, -0.35), (0, 0, 0.0), (0, 0, 1.2), (0, 0, 2.3)]
    cu = bpy.data.curves.new('rod', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 1.0; cu.bevel_resolution = 4
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, q, r in zip(sp.points, pts, (0.016, 0.012, 0.006, 0.0025)): p.co = (*q, 1); p.radius = r
    o = bpy.data.objects.new('rod', cu); bpy.context.scene.collection.objects.link(o); cu.materials.append(M['rod'])
    return o


def make_pike(M):
    """A northern pike's head and shoulders: long olive body, pale bean spots, flat duck-bill snout."""
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        L = 0.45 if x > 0 else 0.35
        snout = max(0.0, x) ** 2
        v.co = Vector((x * L, y * 0.06 * (1 - 0.55 * snout), z * 0.075 * (1 - 0.6 * snout) + (0.01 * snout if z > 0 else -0.004 * snout)))
    o = finn_set._obj('pike', bm, M['pike'], True)
    for s in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.012, location=(0.25, s * 0.035, 0.03))
        e = bpy.context.active_object; e.data.materials.append(M['pike_eye']); e.parent = o
    return o


def prop_materials():
    M = {}
    M['phone_body'] = finn_set._mat('phone_body', '#1d2024', 0.3, metal=0.6)
    M['ink'] = finn_set._mat('ink', '#101214', 0.3)
    M['box'] = finn_set._mat('box', '#3f5a3a', 0.45, noise=0.1)
    M['tray'] = finn_set._mat('tray', '#d9d2b8', 0.5)
    M['rod'] = finn_set._mat('rod', '#20262a', 0.25, metal=0.2)
    pk = bpy.data.materials.new('pike'); pk.use_nodes = True; nt = pk.node_tree; b = nt.nodes['Principled BSDF']
    vo = nt.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 28
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 2.4, 2.4)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], vo.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.12
    ramp.color_ramp.elements[0].color = (*finn_set._lin('#d6d29a'), 1); ramp.color_ramp.elements[1].position = 0.16
    ramp.color_ramp.elements[1].color = (*finn_set._lin('#4a5a2a'), 1)
    nt.links.new(vo.outputs['Distance'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.25; M['pike'] = pk
    M['pike_eye'] = finn_set._mat('pike_eye', '#d4a93a', 0.1)
    return M


def attach(prop, rig, bone, local=(0, 0, 0), rot=(0, 0, 0)):
    prop.parent = rig; prop.parent_type = 'BONE'; prop.parent_bone = bone
    prop.location = local; prop.rotation_euler = rot


# ---------------------------------------------------------------- main
def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True); ap.add_argument('--episode', default=''); ap.add_argument('--out', required=True)
    ap.add_argument('--stills', default=''); ap.add_argument('--from', dest='f0', type=int, default=0); ap.add_argument('--to', dest='f1', type=int, default=-1)
    ap.add_argument('--scale', type=float, default=float(os.environ.get('RENDER_SCALE', '1.0')))
    ap.add_argument('--samples', type=int, default=int(os.environ.get('RENDER_SAMPLES', '48')))
    ap.add_argument('--engine', default=os.environ.get('RENDER_ENGINE', 'EEVEE'))
    ap.add_argument('--tex', default=os.environ.get('CC0_TEXTURES', r'D:\CounterPhysical\assets-cc0\textures'))
    ap.add_argument('--finn', default=os.environ.get('FINN_BLEND', os.path.join(ROOT, 'assets', 'characters', 'finn.blend')))
    A = ap.parse_args(argv)
    plan = json.load(open(A.plan))
    os.makedirs(A.out, exist_ok=True)
    rnd = random.Random(11)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    S = finn_set.build_set({'tex_dir': A.tex if os.path.isdir(A.tex) else None, 'sun_az': 200, 'sun_elev': 9})
    M = prop_materials()

    # Finn
    try:
        import finn_v1
        rig = finn_v1.load_finn(A.finn if os.path.exists(A.finn) else None)
        api = finn_v1
    except ImportError:
        import host_v1
        rig = host_v1.build_host(); api = None
    fp = plan['finn']['pos']; rig.location = fp; rig.rotation_euler = (0, 0, plan['finn'].get('yaw', 0.0))
    sock = (lambda s: api.hand_socket(rig, s)) if api else (lambda s: f'hand_{"R" if s == "R" else "L"}')

    # props
    pages = screen_pages(plan, os.path.join(A.out, '_screen'))
    phone, scr = make_phone(M)
    scr_mats = {k: emission_mat('scr_' + k, p) for k, p in pages.items()}
    scr.data.materials.append(scr_mats['cond0'])
    attach(phone, rig, sock('R'), (0.0, 0.0, 0.09), (math.radians(90), 0, 0))
    lure = make_lure(M); attach(lure, rig, sock('R'), (0.0, 0.0, 0.08), (0, math.radians(90), 0))
    rod = make_rod(M); attach(rod, rig, sock('R'), (0, 0, 0.05), (math.radians(-60), 0, 0))
    box = make_box(M, rnd); bx = plan['box']; box.location = bx; box.rotation_euler = (0, 0, math.radians(15))
    pike = make_pike(M); pk = plan['pike_at']; pike.rotation_euler = (0, math.radians(-8), math.radians(-115)); pike.scale = (0.75, 0.75, 0.75)

    # render settings
    try: sc.render.engine = 'BLENDER_EEVEE' if A.engine.upper().startswith('EEVEE') else 'CYCLES'
    except TypeError: sc.render.engine = 'BLENDER_EEVEE_NEXT'
    if sc.render.engine == 'CYCLES':
        sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
            for d in prefs.devices: d.use = True
            sc.cycles.device = 'GPU'
        except Exception: pass
    else:
        ee = sc.eevee
        for k, v in (('taa_render_samples', A.samples), ('use_raytracing', True), ('use_shadows', True), ('volumetric_tile_size', '4'),
                     ('volumetric_samples', 96), ('use_volumetric_shadows', True), ('volumetric_end', 300.0), ('use_gtao', True), ('use_bloom', True)):
            try: setattr(ee, k, v)
            except Exception: pass
    sc.render.resolution_x = int(plan['W'] * A.scale); sc.render.resolution_y = int(plan['H'] * A.scale)
    sc.render.fps = plan['fps']; sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError: pass
    cam_data = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_data); sc.collection.objects.link(cam); sc.camera = cam
    cam_data.sensor_width = 36; cam_data.clip_start = 0.02; cam_data.clip_end = 1000; cam_data.dof.use_dof = True

    shots = plan['shots']; keys = plan['keys']; fps = plan['fps']; talk = plan['talk']; props = plan['props']
    cond = next(s for s in plan['screen'] if s['page'] == 'conditions')
    in_any = lambda t, spans: any(a <= t < b for a, b in spans)

    def pose_frame(i):
        t = i / fps
        sh = next((s for s in shots if s['start'] <= t < s['end']), shots[-1])
        u = ease((t - sh['start']) / max(0.01, sh['end'] - sh['start']))
        p = Vector(lerp(sh['cam0'], sh['cam1'], u)); tg = Vector(lerp(sh['tgt0'], sh['tgt1'], u))
        tr = sh.get('track')
        if tr:                       # follow a prop: the camera keeps its offset from the planned target
            pose_props(i, t)
            bpy.context.view_layer.update()
            obj = {'phone': phone, 'box': box, 'pike': pike, 'lure': lure}[tr]
            w = obj.matrix_world.translation.copy()
            p = w + (p - tg); tg = w; sh = dict(sh, focus=list(w))
        drift = Vector((0.004 * math.sin(t * 0.9), 0.003 * math.sin(t * 0.7 + 1), 0.004 * math.sin(t * 1.1 + 2)))
        cam.location = p + drift
        q = (tg - cam.location).to_track_quat('-Z', 'Y'); cam.rotation_euler = q.to_euler()
        cam.rotation_euler.rotate_axis('Z', math.radians(sh.get('roll', 0)))
        cam_data.lens = sh['lens']
        cam_data.dof.focus_distance = (Vector(sh['focus']) - cam.location).length; cam_data.dof.aperture_fstop = sh.get('fstop', 2.8)
        # Finn's pose: blend from the previous key into the current one over 0.35 s
        k = max([j for j, kk in enumerate(keys) if kk['t'] <= t] or [0])
        cur = keys[k]; prev = keys[k - 1] if k else cur
        mix = ease((t - cur['t']) / 0.35)
        a = talk[min(i, len(talk) - 1)]
        blink = 1.0 if any(0 <= t - b < 0.12 for b in plan['blinks']) else 0.0
        if api:
            api.apply_pose(rig, prev['pose'], cur['pose'], mix)
            api.set_face(rig, mouth=cur.get('mouth', 'talk'), open=a * (1.4 if cur.get('mouth') == 'shout' else 1.0),
                         brow=cur.get('brow', 0.0), blink=blink)
        pose_props(i, t)
        bpy.context.view_layer.update()

    def pose_props(i, t):
        lure.hide_render = not in_any(t, props['lure_hand'])
        rod.hide_render = not in_any(t, props['rod'])
        phone.hide_render = not in_any(t, props['phone'])
        page = 'cond0'
        for s in plan['screen']:
            if t >= s['t']: page = s['page']
        if page == 'conditions':
            n_t = sum(1 for tt in cond['tap_times'] if t >= tt); page = f'cond{n_t}'
        scr.data.materials[0] = scr_mats.get(page, scr_mats['cond0'])
        if in_any(t, props['box_in_hands']):
            box.parent = rig; box.parent_type = 'BONE'; box.parent_bone = sock('R'); box.location = (0.15, 0.0, 0.12)
        else:
            box.parent = None; box.location = bx
        t0, t1 = props['pike']
        if t0 <= t < t1 + 0.6:
            h = math.sin(math.pi * min(1.0, (t - t0) / (t1 - t0 + 0.6)))
            pike.hide_render = False; pike.location = (pk[0], pk[1], -0.07 + 0.075 * h)
        else:
            pike.hide_render = True

    n = plan['n_frames']
    if A.stills:
        frames = [min(n - 1, int(float(x) * fps)) for x in A.stills.split(',')]
        names = [f'still_{float(x):05.1f}.png' for x in A.stills.split(',')]
    else:
        f1 = n if A.f1 < 0 else min(n, A.f1)
        frames = list(range(A.f0, f1)); names = [f'f{i:05d}.png' for i in frames]
    for i, nm in zip(frames, names):
        path = os.path.join(A.out, nm)
        if not A.stills and os.path.exists(path): continue          # resumable
        pose_frame(i); sc.frame_set(i)
        sc.render.filepath = path; bpy.ops.render.render(write_still=True)
        print('frame', i, flush=True)


if __name__ == '__main__':
    main()
