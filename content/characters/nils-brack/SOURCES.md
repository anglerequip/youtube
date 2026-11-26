# Sources and licences: Nils Brack

## Design
- `model_sheet.png`: Caesar's approved design for Nils (the authority for face, proportions, clothes, materials).

## Image-to-3D sculpt base (v002, unfinished, paused 2026-11-27)
Chosen model: **TripoSG** (VAST-AI-Research), single image to 3D mesh.
- Code: https://github.com/VAST-AI-Research/TripoSG, commit `fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c`.
  Licence: **MIT** (read from the repository's `LICENSE` file, "MIT License, Copyright (c) 2025 VAST-AI-Research
  and contributors"). Commercial use allowed.
- Weights: Hugging Face `VAST-AI/TripoSG`, model card licence **MIT**, not gated. Not downloaded yet: the pause
  came before the first run finished.
- Local patch: `triposg/inference_utils.py` imports `diso` (a compiled CUDA extension) only if present. The
  generation uses the hierarchical decoder with scikit-image marching cubes instead, because the PC has no
  CUDA toolkit or C++ compiler.
- **Not used: BRIA RMBG-1.4.** TripoSG's bundled background remover is non-commercial ("Commercial use is subject
  to a commercial agreement with BRIA"). Our inputs are cut out of the model sheet by colour keying instead
  (`tools/blender/lake_committee/sheet_cutout.py`). They carry their own alpha, so TripoSG never loads RMBG.

Rejected candidates and why:
- Hunyuan3D: its licence excludes the EU.
- InstantMesh: its Zero123++ weights are CC-BY-NC 4.0 (non-commercial).
- TRELLIS / TRELLIS.2 (MIT): need 16-24 GB VRAM and compiled CUDA extensions (spconv, kaolin, nvdiffrast, ...).
- Stable Fast 3D / SPAR3D: Stability Community Licence (free only under US$1M revenue), gated weights, and they
  need a C++/CUDA toolchain to install.
- TripoSR (MIT): installable, but blobby low-resolution geometry. Kept as the fallback.

## Where things live (all on Caesar's PC, under D:\CounterPhysical, nothing in git except scripts)
- `D:\CounterPhysical\ai\TripoSG` (code), `D:\CounterPhysical\ai\venv-triposg` (Python 3.12 venv:
  torch 2.6.0+cu124, diffusers 0.32.2, transformers 4.48.3, scikit-image, trimesh, pymeshlab).
- Caches: `D:\CounterPhysical\ai-cache` (pip, Hugging Face, torch). Weights go to `D:\CounterPhysical\ai\weights\TripoSG`.
- Inputs and generated meshes: `D:\CounterPhysical\lake-committee\assets\characters\nils_brack\v002\source\`.
