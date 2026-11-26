"""Compose the Nils stage-1 review images with the system Python (Blender's Python has no PIL).

  python tools/blender/lake_committee/compose.py <previews_dir>
Reads the renders nils_build.py leaves there (_clay_clay.png + _guides_clay.json, _turn_*.png,
nils_v001_lit_fullbody.jpg) and writes nils_v001_match_clay.jpg (sheet | clay with guide lines at the same height),
nils_v001_turnaround_clay.jpg, nils_v001_thumb180.png (+ a 4x enlargement to look at)."""
import json, os, sys
from PIL import Image, ImageDraw


def main(d):
    g = json.load(open(os.path.join(d, '_guides_clay.json')))
    here = os.path.dirname(os.path.abspath(__file__))
    sheet = os.path.join(here, '..', '..', '..', 'content', 'characters', 'nils-brack', 'model_sheet.png')
    A = Image.open(sheet).convert('RGB'); B = Image.open(g['render']).convert('RGB').resize(A.size)
    W, H = A.size; out = Image.new('RGB', (W * 2 + 20, H), 'white'); out.paste(A, (0, 0)); out.paste(B, (W + 20, 0))
    dr = ImageDraw.Draw(out); rows = []
    for k, (name, ys) in enumerate(g['sheet_guides'].items()):
        yr = g['guides'][name] * H / g['res'][1]
        col = (255, 70, 70) if k % 2 else (70, 200, 255)
        dr.line([(0, ys), (W, ys)], fill=col, width=2); dr.line([(W + 20, yr), (2 * W + 20, yr)], fill=col, width=2)
        dr.text((6, ys - 14), name, fill=col); dr.text((W + 26, yr - 14), f'{name} {yr - ys:+.0f}px', fill=col)
        rows.append((name, round(yr - ys)))
    out.save(os.path.join(d, 'nils_v001_match_clay.jpg'), quality=90)
    print('guide offsets (render - sheet, px):', rows)
    t = [os.path.join(d, f'_turn_{n}.png') for n in ('front', 'three_quarter', 'side', 'back')]
    if all(os.path.exists(p) for p in t):
        ims = [Image.open(p).convert('RGB') for p in t]
        w, h = ims[0].size; s = Image.new('RGB', (w * 4, h)); [s.paste(im, (i * w, 0)) for i, im in enumerate(ims)]
        s.save(os.path.join(d, 'nils_v001_turnaround_clay.jpg'), quality=90)
    look = os.path.join(d, '_look')
    if os.path.isdir(look) and os.listdir(look):
        import subprocess
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '24', '-i', os.path.join(look, 'f%04d.png'), '-c:v', 'libx264',
                        '-crf', '18', '-pix_fmt', 'yuv420p', os.path.join(d, 'nils_v001_look_test.mp4')], check=True)
    lf = os.path.join(d, 'nils_v001_lit_fullbody.jpg')
    if os.path.exists(lf):
        im = Image.open(lf); th = im.resize((180, round(180 * im.height / im.width)), Image.LANCZOS)
        th.save(os.path.join(d, 'nils_v001_thumb180.png'))
        th.resize((720, round(720 * im.height / im.width)), Image.NEAREST).save(os.path.join(d, '_thumb180_x4.png'))


def head(d):
    """Head close-up: the sheet's head region beside the same region of the 3x clay render (aligned on the eyes)."""
    g = json.load(open(os.path.join(d, '_guides_head.json')))
    here = os.path.dirname(os.path.abspath(__file__))
    A = Image.open(os.path.join(here, '..', '..', '..', 'content', 'characters', 'nils-brack', 'model_sheet.png')).convert('RGB')
    B = Image.open(g['render']).convert('RGB')
    k = B.width / A.width                                   # 3x
    box = (300, 20, 720, 400)
    dy = g['guides']['eyes'] / k * (A.height / (g['res'][1])) - g['sheet_guides']['eyes'] if False else 0
    ey_r = g['guides']['eyes'] * B.height / g['res'][1]; ey_s = g['sheet_guides']['eyes'] * k
    off = ey_r - ey_s
    a = A.crop(box).resize(((box[2] - box[0]) * 2, (box[3] - box[1]) * 2), Image.LANCZOS)
    b = B.crop((box[0] * k, box[1] * k + off, box[2] * k, box[3] * k + off)).resize(a.size, Image.LANCZOS)
    out = Image.new('RGB', (a.width * 2 + 10, a.height), 'white'); out.paste(a, (0, 0)); out.paste(b, (a.width + 10, 0))
    out.save(os.path.join(d, 'nils_v001_head_match_clay.jpg'), quality=90)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == 'headviews':
        ims = [Image.open(os.path.join(sys.argv[1], f'_head_{n}.png')).convert('RGB') for n in ('front', 'tq', 'side')]
        o = Image.new('RGB', (640 * 3, 640)); [o.paste(im, (i * 640, 0)) for i, im in enumerate(ims)]
        o.save(os.path.join(sys.argv[1], '_headviews.jpg'), quality=88); sys.exit()
    if len(sys.argv) > 2 and sys.argv[2] == 'head':
        head(sys.argv[1]); sys.exit()
    main(sys.argv[1])
