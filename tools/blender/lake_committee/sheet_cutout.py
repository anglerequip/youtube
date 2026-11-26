import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
src = r'D:\CounterPhysical\wt-finn\content\characters\nils-brack\model_sheet.png'
im = Image.open(src).convert('RGB'); a = np.asarray(im).astype(np.float32)
rowbg = (a[:, :30].mean(axis=1) + a[:, -30:].mean(axis=1)) / 2
d = np.linalg.norm(a - rowbg[:, None, :], axis=2)
lab, n = ndimage.label(d < 16)
border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
fg = ~np.isin(lab, list(border))
H, W = fg.shape; yy, xx = np.mgrid[0:H, 0:W]
boots = ((xx >= 228) & (xx <= 448)) | ((xx >= 478) & (xx <= 785))
fg &= ~((yy > 1175) & ~boots)
fg &= ~((yy > 1125) & (xx > 430) & (xx < 482) & (d < 60)) & ~((yy > 1060) & (xx > 449) & (xx < 480) & (d < 70))

fg &= ~(yy > 1446)
fg = ndimage.binary_opening(fg, iterations=2); fg = ndimage.binary_fill_holes(fg)
lab2, n2 = ndimage.label(fg); sizes = ndimage.sum(fg, lab2, range(1, n2 + 1)); fg = lab2 == (np.argmax(sizes) + 1)
alpha = Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))
rgba = im.copy(); rgba.putalpha(alpha)
ys, xs = np.where(fg); x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
side = int(max(x1 - x0, y1 - y0) * 1.12)
sq = Image.new('RGBA', (side, side), (0, 0, 0, 0)); sq.paste(rgba.crop((x0, y0, x1 + 1, y1 + 1)), ((side - (x1 - x0)) // 2, (side - (y1 - y0)) // 2))
out = r'D:\CounterPhysical\lake-committee\assets\characters\nils_brack\v002\source'
sq.resize((1024, 1024), Image.LANCZOS).save(out + r'\nils_input_rgba.png')
for nm, c in (('white', (255, 255, 255)), ('grey', (127, 127, 127))):
    w = Image.new('RGB', sq.size, c); w.paste(sq, mask=sq.split()[3]); w.resize((1024, 1024), Image.LANCZOS).save(out + rf'\nils_input_{nm}.png')
print('bbox', x0, y0, x1, y1)
# head and shoulders close-up (cap to upper chest), for a higher-resolution face base
hb = (300, 17, 720, 330)
h = rgba.crop(hb); m = np.asarray(h.split()[3]).copy(); m[-6:, :] = 0
h.putalpha(Image.fromarray(m))
s2 = int(max(h.size) * 1.15); sq2 = Image.new('RGBA', (s2, s2), (0, 0, 0, 0)); sq2.paste(h, ((s2 - h.width) // 2, (s2 - h.height) // 2))
sq2.resize((1024, 1024), Image.LANCZOS).save(out + r'\nils_head_rgba.png')
