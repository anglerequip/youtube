"""Phone screen pages for render_episode.py, drawn with PIL in AnglerMind's colours (docs/BRAND.md).

Runs inside Blender when its Python has PIL, otherwise render_episode.py calls this file with the system Python:
  python tools/blender/screen_pages.py <plan.json> <out_dir>      -> writes the PNGs and <out_dir>/pages.json
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_DIR = os.path.join(ROOT, 'assets', 'fonts')


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



if __name__ == '__main__':
    plan = json.load(open(sys.argv[1]))
    pages = screen_pages(plan, sys.argv[2])
    json.dump(pages, open(os.path.join(sys.argv[2], 'pages.json'), 'w'))
