# Progress

## 2026-08-15 — main

Initial repo: procedural Blender high-rise house generator.

Changes:
- `build_house.py` — generates the model. 20 × 14 m footprint, 4.0 m floor
  height, 3 open pilotis floors (columns + service core) carrying 12 occupied
  floors, 62.60 m to top of parapet. Per floor: 0.95 m spandrel / 0.30 m vent /
  1.50 m window / 0.30 m vent / 0.95 m spandrel, so the window is centred at
  mid-floor. Window and vent strips wrap all four facades at full width. Saves
  `.blend`, `.glb` and an EEVEE render into `out/`.
- `verify_house.py` — 29 geometry assertions over the saved `.blend`.
- `render_views.py` — front elevation, pilotis base, floor close-up.
- `README.md`, `.gitignore`.

Verification:
- Build ran clean under Blender 5.2.0 LTS; 8 objects, 6408 vertices.
- `verify_house.py`: 29/29 checks passed — every window 1.50 m and centred
  (offset 2.00 m in a 4.00 m floor), 12 window bands, glazing spans 99.1% of X
  and 100% of Y, all vent bands 0.30 m and flush above/below each window, no
  facade geometry below 12.0 m, structure from -0.30 m to 62.60 m.
- 4 renders written, all ~1.2 MB non-blank PNGs.

Remaining issues:
- Image files could not be viewed inside this session, so the renders were
  confirmed by geometry assertions and file-size checks rather than by eye.
  Worth a visual look at `out/preview.png` and `out/view_base_pilotis.png`.
