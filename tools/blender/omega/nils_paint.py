"""Repaint a projected Nils mesh in clean, designed material regions (rule 7.9: paint the colour, don't scan it).

  blender -b -P tools/blender/omega/nils_paint.py -- --blend <nils_tsg.blend> --out <nils_painted.blend>

Each vertex's projected sheet colour is classified to the nearest entry of the Nils palette (chroma-weighted so the
sheet's baked shading doesn't flip a shadowed shirt into a boot), labels are majority-filtered over the mesh, and every
face gets the material of its region. The region materials are painted (kit.painted): 2-3 tones, cavity, roughness
levels per rule 7.10. The model-sheet colours stay the authority; the sheet's baked light is dropped."""
import os, sys
import bpy, bmesh
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit

argv = sys.argv[sys.argv.index('--') + 1:]
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d
SRC, OUT = arg('--blend'), arg('--out')

# region: (sheet sample sRGB for classification, paint tones, roughness, metal)
PAL = {
    'cap':    ('#a84a26', ['#7f2c12', '#a03c1a', '#b9501f'], 0.88, 0.0),
    'skin':   ('#b98068', ['#985a40', '#b26f4f', '#c78866'], 0.62, 0.0),
    'nose':   ('#c0705a', ['#a85a3e', '#c26b4a', '#d4805c'], 0.55, 0.0),
    'hair':   ('#8a8682', ['#6b6866', '#8d8985', '#a9a49e'], 0.75, 0.0),
    'shirt':  ('#38434c', ['#27313a', '#36424c', '#46525c'], 0.78, 0.0),
    'bib':    ('#615f2c', ['#46441d', '#5e5c29', '#77733a'], 0.62, 0.0),
    'knit':   ('#5a3e2c', ['#3f2a1c', '#563a28', '#6b4a33'], 0.9, 0.0),
    'strap':  ('#4a3122', ['#33200f', '#4b2f1c', '#61402a'], 0.4, 0.0),
    'brass':  ('#9c7f45', ['#6e5422', '#a07c3a', '#c9a55c'], 0.25, 1.0),
    'boot':   ('#36312e', ['#23201e', '#34302d', '#48413c'], 0.55, 0.0),
    'red':    ('#a8261d', ['#8a1a12', '#b2261b', '#c93a26'], 0.25, 0.0),
    'ivory':  ('#d2c6a6', ['#bfb08b', '#d9ccaa', '#e8dec2'], 0.3, 0.0),
}
NAMES = list(PAL)

def to_lab(rgb):
    """sRGB (0-1) -> approximate CIELAB."""
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)

bpy.ops.wm.open_mainfile(filepath=SRC)
MATS = {}
for n in NAMES:
    _, tones, rough, metal = PAL[n]
    MATS[n] = kit.painted('nils_' + n, tones, rough=rough, metal=metal, scale=3.0, cavity=0.5,
                          cavity_dist=0.03, rough_var=0.06)
for ob in [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('nils') and 'paint' in o.data.color_attributes]:
    bpy.context.view_layer.update(); mw = np.array(ob.matrix_world)
    me = ob.data
    ca = me.color_attributes['paint']
    lin = np.array([c.color[:3] for c in ca.data], np.float32)
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, 1), 1 / 2.4) - 0.055)
    lab = to_lab(srgb)
    ref = to_lab(np.array([[int(PAL[n][0][i:i + 2], 16) / 255 for i in (1, 3, 5)] for n in NAMES]))
    w = np.array([0.45, 1.3, 1.3])                 # lightness matters less than hue: the sheet's light is baked in
    d = (((lab[:, None, :] - ref[None]) * w) ** 2).sum(-1)
    V = np.array([v.co[:] for v in me.vertices]); V = V @ mw[:3, :3].T + mw[:3, 3]; x, y, z = V[:, 0], V[:, 1], V[:, 2]
    zz = z                 # rules are written for a 1.75 m Nils facing -Y (his left = +X)
    ax = np.abs(x)
    # allowed labels per zone (anatomy and garment layout from the model sheet); colour picks within them
    allowed = np.zeros((len(V), len(NAMES)), bool)
    def allow(mask, *names):
        for n in names: allowed[mask, NAMES.index(n)] = True
    cap = zz > 1.59 - 0.08 * y
    head = (zz > 1.43) & ~cap
    collar = (zz > 1.36) & (zz <= 1.43)
    torso = (zz > 1.0) & (zz <= 1.36) & (ax < 0.25)
    arm = (zz > 0.84) & (zz <= 1.36) & (ax >= 0.25)
    hand = (zz > 0.52) & (zz <= 0.86) & (ax >= 0.235)
    legs = (zz > 0.34) & (zz <= 1.0) & ~hand
    boot = zz <= 0.34
    front = y < -0.02
    ear = head & (ax > 0.112) & (y > -0.08) & (y < 0.03) & (zz > 1.47) & (zz < 1.57)
    hair = head & ~ear & ((y > 0.035) & (zz < 1.585) | ((ax > 0.10) & (ax < 0.13) & (y > -0.10) & (y < -0.065) & (zz > 1.50) & (zz < 1.578)))
    browz = head & (zz > 1.572) & (zz < 1.607) & (ax > 0.01) & (ax < 0.085) & (y < -0.172)
    nosez = head & (ax < 0.026) & (zz > 1.493) & (zz < 1.572) & (y < -0.198)
    bibm = torso & front & (ax < 0.2) & (zz < 1.24)
    strap = torso & front & (ax > 0.065) & (ax < 0.15) & (zz >= 1.2) & (zz < 1.36)
    buckle = strap & (zz < 1.27) & (ax > 0.09) & (ax < 0.13)
    backw = torso & ~front & (zz < 1.06)
    allow(cap, 'cap'); allow(head & ~hair & ~browz & ~nosez, 'skin'); allow(hair | browz, 'hair'); allow(nosez, 'nose'); allow(collar & ~strap & ~((ax < 0.05) & front), 'shirt')
    allow(collar & (ax < 0.05) & front, 'knit')
    allow(torso & ~bibm & ~strap & ~backw, 'shirt'); allow(bibm | backw, 'bib'); allow(strap & ~buckle, 'strap'); allow(buckle, 'brass')
    allow(arm, 'shirt'); allow(hand, 'skin'); allow(legs, 'bib'); allow(boot, 'boot')
    flt = (x > 0.1) & (x < 0.3) & (y < -0.05) & (zz > 1.05) & (zz < 1.32)
    # the float is a separate prop (nils_face.py), not painted onto the bib
    allowed[~allowed.any(1), NAMES.index('shirt')] = True
    d = np.where(allowed, d, 1e12)
    lab_id = d.argmin(1)

    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    nbr = [[e.other_vert(v).index for e in v.link_edges] for v in bm.verts]
    for it in range(int(arg('--filter', '7'))):
        new = lab_id.copy()
        for k, ns in enumerate(nbr):
            if ns:
                vals = np.bincount(lab_id[ns + [k]], minlength=len(NAMES))
                new[k] = vals.argmax()
        lab_id = new
    me.materials.clear()
    for n in NAMES:
        me.materials.append(MATS[n])
    for f in bm.faces:
        f.material_index = int(np.bincount(lab_id[[v.index for v in f.verts]], minlength=len(NAMES)).argmax())
    bm.to_mesh(me); bm.free()
    counts = {n: int((lab_id == i).sum()) for i, n in enumerate(NAMES)}
    print('REGIONS', counts)

bpy.ops.wm.save_as_mainfile(filepath=OUT)
