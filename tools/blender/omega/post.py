"""OMEGA finish (run with the project venv Python, which has PIL/numpy/scipy):

  python tools/blender/omega/post.py <raw.png> [--scale 2] [--bloom 0.35]      -> <name>.jpg next to it
  python tools/blender/omega/post.py <frames_dir> --video <out.mp4> [--fps 24]  -> finished frames + H.264

Rule 9.1: render at 50 % and upscale with Lanczos. Then a soft bloom from the brightest areas only (emissive and
sun-lit edges, never a wash over the subject) and a gentle vignette."""
import glob, os, subprocess, sys
import numpy as np
from PIL import Image
from scipy import ndimage

args = sys.argv[2:]
def opt(n, d):
    return type(d)(args[args.index(n) + 1]) if n in args else d
SCALE, BLOOM, THRESH, VIG = opt('--scale', 2.0), opt('--bloom', 0.35), opt('--thresh', 0.80), opt('--vignette', 0.22)


def finish(src):
    im = Image.open(src).convert('RGB')
    im = im.resize((int(im.width * SCALE), int(im.height * SCALE)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    hi = a * np.clip((lum - THRESH) / (1 - THRESH), 0, 1)[..., None]
    glow = np.zeros_like(a)
    for s, w in ((a.shape[1] * 0.006, 0.5), (a.shape[1] * 0.02, 0.35), (a.shape[1] * 0.05, 0.25)):
        glow += w * np.stack([ndimage.gaussian_filter(hi[..., c], s) for c in range(3)], -1)
    a = 1 - (1 - a) * (1 - np.clip(glow * BLOOM * 2, 0, 1))          # screen blend
    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
    a *= (1 - VIG * np.clip(r - 0.35, 0, 1) ** 1.5 / 0.65 ** 1.5)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


src = sys.argv[1]
if os.path.isdir(src):
    out = opt('--video', os.path.join(src, '..', 'clip.mp4')); fps = opt('--fps', 24)
    fin = os.path.join(src, '..', 'finished'); os.makedirs(fin, exist_ok=True)
    frames = sorted(glob.glob(os.path.join(src, '*.png')))
    for k, f in enumerate(frames):
        finish(f).save(os.path.join(fin, f'f{k + 1:04d}.png'))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', os.path.join(fin, 'f%04d.png'),
                    '-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out],
                   check=True)
    print('WROTE', out, len(frames), 'frames')
else:
    out = src.replace('_raw.png', '.jpg')
    finish(src).save(out, quality=93)
    print('WROTE', out, Image.open(out).size)
