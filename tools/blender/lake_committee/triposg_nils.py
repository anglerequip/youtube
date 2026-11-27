"""Image-to-3D sculpt base for Nils with TripoSG (VAST-AI-Research, MIT code and weights; see
content/characters/nils-brack/SOURCES.md). Runs in its own venv under D:\\CounterPhysical\\ai; nothing outside
D:\\CounterPhysical is written (HF/torch/pip caches go to D:\\CounterPhysical\\ai-cache).

  set HF_HOME=D:\\CounterPhysical\\ai-cache\\hf & set TORCH_HOME=D:\\CounterPhysical\\ai-cache\\torch
  D:\\CounterPhysical\\ai\\venv-triposg\\Scripts\\python.exe tools/blender/lake_committee/triposg_nils.py
      [--repo D:\\CounterPhysical\\ai\\TripoSG] [--out <lake-committee>/assets/characters/nils_brack/v002/source]

Inputs are the model sheet cut out by hand-tuned colour keying (nils_input_rgba.png, full body; nils_head_rgba.png,
head close-up): they carry their own alpha, so TripoSG's bundled background remover (BRIA RMBG-1.4, non-commercial)
is never loaded. The marching cubes run through scikit-image (hierarchical decoder) because the flash decoder needs
the compiled `diso` package. Writes one .glb per candidate plus candidates.json (seed, steps, guidance, timings)."""
import argparse, json, os, sys, time

ap = argparse.ArgumentParser()
ap.add_argument('--repo', default=r'D:\CounterPhysical\ai\TripoSG')
ap.add_argument('--weights', default=r'D:\CounterPhysical\ai\weights\TripoSG')
ap.add_argument('--out', default=r'D:\CounterPhysical\lake-committee\assets\characters\nils_brack\v002\source')
ap.add_argument('--only', default='')
a = ap.parse_args()
sys.path.insert(0, a.repo); sys.path.insert(0, os.path.join(a.repo, 'scripts'))

import numpy as np
import torch
from huggingface_hub import snapshot_download
import diffusers.models.normalization as _dn   # diffusers >= 0.33 dropped this alias; TripoSG still imports it
if not hasattr(_dn, 'LayerNorm'): _dn.LayerNorm = torch.nn.LayerNorm
from triposg.pipelines.pipeline_triposg import TripoSGPipeline
import triposg.schedulers.scheduling_rectified_flow, triposg.models.autoencoders, triposg.models.transformers  # diffusers loads only imported modules
from image_process import prepare_image
import trimesh

if not os.path.exists(os.path.join(a.weights, 'model_index.json')):
    snapshot_download(repo_id='VAST-AI/TripoSG', local_dir=a.weights)
pipe = TripoSGPipeline.from_pretrained(a.weights).to('cuda', torch.float16)

CANDIDATES = [   # name, input, seed, steps, guidance, hierarchical depth
    ('A_body_s42', 'nils_input_rgba.png', 42, 50, 7.0, 9),
    ('B_body_s7', 'nils_input_rgba.png', 7, 50, 7.0, 9),
    ('C_body_s42_g5', 'nils_input_rgba.png', 42, 60, 5.0, 9),
    ('D_head_s42', 'nils_head_rgba.png', 42, 50, 7.0, 9),
    ('E_head_s7_d8', 'nils_head_rgba.png', 7, 50, 5.0, 8),
    ('F_head_s11_d8', 'nils_head_rgba.png', 11, 60, 4.0, 8),
]
log = []
for name, src, seed, steps, g, depth in CANDIDATES:
    if a.only and a.only not in name:
        continue
    t = time.time()
    img = prepare_image(os.path.join(a.out, src), bg_color=np.array([1.0, 1.0, 1.0]), rmbg_net=None)
    img.save(os.path.join(a.out, f'{name}_prepared.png'))
    out = pipe(image=img, generator=torch.Generator(device='cuda').manual_seed(seed), num_inference_steps=steps,
               guidance_scale=g, use_flash_decoder=False, dense_octree_depth=8, hierarchical_octree_depth=depth)
    v, f = out.samples[0]
    mesh = trimesh.Trimesh(vertices=v.astype(np.float32), faces=np.ascontiguousarray(f))
    mesh.export(os.path.join(a.out, f'{name}.glb'))
    rec = dict(name=name, input=src, seed=seed, steps=steps, guidance=g, octree_depth=depth, verts=int(len(v)), faces=int(len(f)),
               seconds=round(time.time() - t, 1), peak_vram_gb=round(torch.cuda.max_memory_allocated() / 2 ** 30, 2))
    print(rec, flush=True); log.append(rec)
    torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
json.dump(log, open(os.path.join(a.out, 'candidates.json'), 'a' if a.only else 'w'), indent=1)
