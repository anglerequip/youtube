"""Burn HOST-style captions into finished frames and mux the mix (venv Python).

  python captions.py <finished_frames_dir> <timeline.json> <mix.wav> <out.mp4> [--fps 24]

HOST.md: white, sentence-case words as spoken, thin grey outline + soft shadow, up to 4 words, centred at about 64 %
of the 9:16 height, no highlight, no animation. Groups follow the word timings (a group holds until the next starts)."""
import glob, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

src, tl_path, mix, out = sys.argv[1:5]
FPS = 24
START = int(sys.argv[sys.argv.index('--start') + 1]) if '--start' in sys.argv else 1   # first frame of a clip
TL = json.load(open(tl_path))
FONT = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 92)       # reviewer c2: regular grotesk, ~7 % height

groups = []
for L in TL['lines']:
    ws = [(w['w'], w['s'] + L['start'], w['e'] + L['start']) for w in L['words']]
    # 'www .anglermind .com' -> one token
    merged = []
    for w in ws:
        if merged and w[0].startswith('.'):
            merged[-1] = (merged[-1][0] + w[0], merged[-1][1], w[2])
        elif merged and w[0].startswith('-'):
            merged[-1] = (merged[-1][0] + w[0], merged[-1][1], w[2])
        else:
            merged.append(w)
    merged = [(m[0].replace('www.', ''), m[1], m[2]) for m in merged]
    # phrase-aware groups (reviewer c4): break at punctuation, at most 6 words per group
    chunks, cur = [], []
    for m_ in merged:
        cur.append(m_)
        if m_[0][-1:] in ',.?!' or len(cur) == 6: chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    for g in chunks:
        txt = ' '.join(x[0] for x in g)
        for a, b in (('Angler Mind', 'AnglerMind'), ('sign up', 'sign-up'), ("that's free.", "that's free?"), ('drop -offs', 'drop-offs'),
                     ('lure finder', 'Lure Finder'), ('all of these.', 'all of these?'), ('Cloudy bit windy.', 'Cloudy? Bit windy?'),
                     ('depends what', 'Depends. What'), ('weather doing.', 'weather doing?'), ('AnglerMind .com', 'anglermind.com'), ('AnglerMind.com', 'anglermind.com'), ('doing.', 'doing?')):
            txt = txt.replace(a, b)
        groups.append((g[0][1] - 0.05, g[-1][2] + 0.15, txt))
for k in range(len(groups) - 1):          # never overlap: a group ends when the next begins
    s, e, t = groups[k]; groups[k] = (s, min(e, groups[k + 1][0]), t)

frames = sorted(glob.glob(os.path.join(src, '*.png')))
cap_dir = os.path.join(src, '..', 'captioned'); os.makedirs(cap_dir, exist_ok=True)
for k, f in enumerate(frames):
    t = (k + START - 1) / FPS
    im = Image.open(f).convert('RGB')
    txt = next((g[2] for g in groups if g[0] <= t < g[1]), None)
    if txt:
        W, H = im.size
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        words = txt.split(); lines_ = [words[0]]
        for wd in words[1:]:
            test = lines_[-1] + ' ' + wd
            if d.textbbox((0, 0), test, font=FONT)[2] > W * 0.88: lines_.append(wd)
            else: lines_[-1] = test
        txt = '\n'.join(lines_)
        bb = d.multiline_textbbox((0, 0), txt, font=FONT, align='center', spacing=4); tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x, y = (W - tw) / 2, H * 0.74 - th / 2
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
        ds.multiline_text((x + 3, y + 5), txt, font=FONT, fill=(0, 0, 0, 235), align='center', spacing=4, stroke_width=6, stroke_fill=(0, 0, 0, 150))
        sh = sh.filter(ImageFilter.GaussianBlur(9))
        d.multiline_text((x, y), txt, font=FONT, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(30, 30, 30, 255), align='center', spacing=4)
        im = Image.alpha_composite(Image.alpha_composite(im.convert('RGBA'), sh), lay).convert('RGB')
    im.save(os.path.join(cap_dir, f'f{k + 1:04d}.png'))
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(cap_dir, 'f%04d.png'), '-ss', str((START - 1) / FPS), '-i', mix,
                '-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart', out], check=True)
print('WROTE', out, len(frames), 'frames', len(groups), 'caption groups')
