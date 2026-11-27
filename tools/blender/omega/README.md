# OMEGA Blender kit (Nils Brack, Lake Committee set)

Built 2026-11-27 for Caesar's Project Omega milestones 3-5. Blender 5.2, Eevee, run headless:
`B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"`; `$B -b -P <script> -- <args>`.

## Nils from the model sheet (order matters)
1. `lake_committee/sheet_cutout.py` cut-outs -> `lake_committee/triposg_nils.py` (TripoSG, own venv under
   `D:\CounterPhysical\ai`): body candidate `A_body_s42`, head close-up candidate `E_head_s7_d8` (seed 7, guidance 5,
   octree depth 8: clean planes; the depth-9 head was noisy and full of holes).
2. `nils_from_mesh.py` per candidate: view axis by silhouette IoU, sheet colours projected onto visible vertices and
   diffused, voxel remesh (body 6 mm, head 3 mm at 0.5 m scale), light smooth, decimate. Body `--faces 80000`.
3. `nils_graft_head.py`: registers the head on the body by front-silhouette search, cuts both at 1.415 m.
4. `nils_square_head.py`: the sheet's head is turned ~22 degrees; a mirror-plane search straightens it.
5. `nils_paint.py`: clean painted regions (cap, skin, nose, lip, hair, shirt, knit, bib, boot...). Zones are geometric
   (anatomy/garment layout of the sheet); colour only decides inside a zone. Cap gets knit ribs.
6. `nils_facet.py`: planar dissolve that never crosses a material border (body 14 deg, head 5 deg) -> the sheet's
   flat garment panels with clean region edges.
7. `nils_face.py`: rig-ready parts by raycast onto the head/body: eyes (gaze), upper lids (rest -12 deg = half-lidded,
   +38 = closed), sculpted brow locks and sideburns, braces with brass buckles, bib hem, the float on his left strap.
8. `nils_preview.py` turnaround/head checks. `D:\CounterPhysical\research\omega\nils\rebuild.sh <lid> <tag> 14 5`
   reruns 5-8.

## Set, shots, finish
- `kit.py`: bevelled blocks, lathes with sharp plane borders, painted materials (tones + cavity + roughness levels,
  wood grain, knit ribs), sunset sky with painted sun glow, camera-only sky + cooler ambient, bounded haze box.
- `calib_m3.py --shot prop|wide|portrait|desk|anim [--nils <blend>]`; `anim_m5.py` is the 6 s acting test.
- `post.py`: Lanczos 2x + highlight bloom + vignette; on a frames folder it also encodes H.264.

## Gotchas
- Eevee world volume absorbs the sky: haze lives in a bounded box (`fog_box`).
- `Mesh.set_sharpness_by_angle` is not in 5.2: sharp edges are set in bmesh.
- diffusers >= 0.33 dropped `normalization.LayerNorm`; TripoSG modules must be imported before `from_pretrained`.
- BRIA RMBG-1.4 is non-commercial: never loaded (inputs carry their own alpha).
