"""Picture metrics for HOST_RENDER_RULES 3 and 9: effective resolution (PSNR after halving and restoring),
high-frequency energy, colours per 1,000 px, mean gradient, on the top 70 % of each frame (captions excluded).
  python tools/look_metrics.py "out/<slug>/previews/*.png" ...   (one glob per set; compare at the same bitrate)"""
import numpy as np, glob, sys
from PIL import Image
def metr(path, crop_top=0.7):
    im = Image.open(path).convert('RGB'); w,h = im.size; im = im.crop((0,0,w,int(h*crop_top)))
    a = np.asarray(im).astype(np.float32)/255
    g = a.mean(2)
    res = {}
    for f in (2,3):
        sm = im.resize((w//f, int(h*crop_top)//f), Image.BICUBIC).resize(im.size, Image.BICUBIC)
        b = np.asarray(sm).astype(np.float32)/255
        mse = ((a-b)**2).mean(); res[f'psnr_x{f}'] = round(10*np.log10(1/mse),1)
    # high-frequency energy ratio
    F = np.abs(np.fft.fftshift(np.fft.fft2(g))); H,W = F.shape; yy,xx = np.ogrid[:H,:W]
    r = np.hypot((yy-H/2)/H,(xx-W/2)/W)
    res['hf'] = round(float(F[r>0.25].sum()/F.sum())*100,2)
    q = (np.asarray(im).astype(np.int32)//8).reshape(-1,3); res['colours/1k px'] = round(len(np.unique(q[:,0]*1024+q[:,1]*32+q[:,2]))/(q.shape[0]/1000),2)
    # edge sharpness: mean abs gradient
    res['grad'] = round(float(np.abs(np.diff(g,axis=1)).mean()*1000),1)
    return res
for pat in sys.argv[1:]:
    fs = sorted(glob.glob(pat)); R=[metr(f) for f in fs]
    print(pat[-45:], {k: round(np.mean([r[k] for r in R]),2) for k in R[0]})
