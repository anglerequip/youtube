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
    lf = os.path.join(d, 'nils_v001_lit_fullbody.jpg')
    if os.path.exists(lf):
        im = Image.open(lf); th = im.resize((180, round(180 * im.height / im.width)), Image.LANCZOS)
        th.save(os.path.join(d, 'nils_v001_thumb180.png'))
        th.resize((720, round(720 * im.height / im.width)), Image.NEAREST).save(os.path.join(d, '_thumb180_x4.png'))


if __name__ == '__main__':
    main(sys.argv[1])
