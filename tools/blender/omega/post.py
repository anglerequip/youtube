"""OMEGA still finish (run with the project venv Python, which has PIL/numpy/scipy):

  python tools/blender/omega/post.py <raw.png> [--scale 2] [--bloom 0.35]

Rule 9.1: render at 50 % and upscale with Lanczos. Then a soft bloom from the brightest areas only (emissive and
sun-lit edges, never a wash over the subject) and a gentle vignette. Writes <name>.jpg next to the raw file."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

src = sys.argv[1]
args = sys.argv[2:]
def opt(n, d):
    return float(args[args.index(n) + 1]) if n in args else d
scale, bloom, thresh, vig = opt('--scale', 2), opt('--bloom', 0.35), opt('--thresh', 0.80), opt('--vignette', 0.22)

im = Image.open(src).convert('RGB')
im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
a = np.asarray(im).astype(np.float32) / 255.0
lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
mask = np.clip((lum - thresh) / (1 - thresh), 0, 1)[..., None]
hi = a * mask
glow = np.zeros_like(a)
for s, w in ((a.shape[1] * 0.006, 0.5), (a.shape[1] * 0.02, 0.35), (a.shape[1] * 0.05, 0.25)):
    glow += w * np.stack([ndimage.gaussian_filter(hi[..., c], s) for c in range(3)], -1)
a = 1 - (1 - a) * (1 - np.clip(glow * bloom * 2, 0, 1))          # screen blend
h, w = lum.shape
yy, xx = np.mgrid[0:h, 0:w]
r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
a *= (1 - vig * np.clip(r - 0.35, 0, 1) ** 1.5 / 0.65 ** 1.5)[..., None]
out = src.replace('_raw.png', '.jpg')
Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out, quality=93)
print('WROTE', out, Image.open(out).size)
