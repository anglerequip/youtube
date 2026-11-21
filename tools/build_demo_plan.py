"""Plan for the BUILD effects showcase (renderer/scenes/build3d.js). Not an episode.

    python tools/build_demo_plan.py out/build-demo/plan.json
    node renderer/render.mjs --scene build3d --plan out/build-demo/plan.json --out out/build-demo/visual.mp4
"""
import json
import sys

FPS, T, W, H = 30, 13.0, 720, 1280
fx = dict(wind0=3.0, wind1=7.5, freeze0=3.2, freeze1=6.0, shrink0=6.2, shrink1=7.4, shatter=9.4)
L = 'blizzard'
shots = [
    dict(start=0, end=3.0, pos0=[2.6, 1.1, 3.6], pos1=[2.2, 1.0, 3.1], look0=[0, 0.45, 0], lighting=L),
    dict(start=3.0, end=6.1, pos0=[1.5, 0.85, 2.6], pos1=[1.35, 0.8, 2.3], look0=[0, 0.42, 0], lighting=L),
    dict(start=6.1, end=8.6, pos0=[-1.4, 0.8, 1.9], pos1=[-1.25, 0.75, 1.7], look0=[0, 0.35, 0], lighting=L),
    dict(start=8.6, end=10.6, pos0=[0.0, 0.6, 2.2], pos1=[0.0, 0.62, 2.0], look0=[0, 0.3, 0], lighting=L),
    dict(type='orbit', start=10.6, end=T, center=[0, 0.3, 0], r0=4.2, r1=4.6, h0=1.8, h1=2.1, az0=20, az1=45,
         look0=[0, 0.3, 0], lighting=L),
]
O = [
    dict(type='callout', start=0.6, end=2.9, at=[0.28, 0.62, 0.1], text='HEAT SOURCE', dx=-0.18, dy=-0.12),
    dict(type='pill', start=1.2, end=2.9, text='WARM', icon='check', xy=[0.5, 0.2]),
    dict(type='gauge', start=3.3, end=6.0, at=[0.32, 0.95, 0], label='BODY HEAT', **{'from': 0.85}, to=0.18,
         color0='#e8813a', color1='#4fb3e8'),
    dict(type='pill', start=4.2, end=6.0, text='FREEZING', icon='snow', xy=[0.5, 0.2]),
    dict(type='arrows', start=6.3, end=7.6, at=[0, 0.36, 0], mode='in', r=0.075),
    dict(type='dim', start=7.0, end=8.5, a=[-0.42, 0.0, 0.35], b=[-0.42, 0.58, 0.35], text='0.6 M'),
    dict(type='ring', start=8.7, end=9.4, at=[0, 0.3, 0], r=0.07),
    dict(type='xmark', start=8.9, end=9.45, at=[0, 0.3, 0], r=0.03),
    dict(type='flash', start=9.35, end=9.65, peak=0.85),
    dict(type='tint', start=10.6, end=T, color='#0b1530', alpha=0.28),
    dict(type='pill', start=11.0, end=T, text='-50°', icon='snow', xy=[0.5, 0.2]),
]
plan = dict(W=W, H=H, fps=FPS, n_frames=int(T * FPS), seed=5, shots=shots, fx=fx, overlays=O)
out = sys.argv[1] if len(sys.argv) > 1 else 'plan.json'
json.dump(plan, open(out, 'w'), indent=1)
print(out)
