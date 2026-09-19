# Highrise House

A procedural Blender model of a high-rise residential complex composed of two independently configured apartment towers, a continuous curved glass podium, open pilotis levels, sky gardens, and landscaped roofs. The project explores facade rhythm, public space, structure, and lighting at the scale of a dense vertical development.

![Current Blender view](docs/images/highrise-current-view.png)

The image above captures the current Blender working view. The images below are rendered from the same saved `.blend` scene.

## Project Overview

| Item | Specification |
| --- | ---: |
| Towers | 2 |
| Existing tower | 76 × 40 m; approximately 193.94 m to the core top |
| Adjacent tower | 84 × 40 m; approximately 269.94 m to the core top |
| Clear gap between towers | 30 m |
| Typical floor-to-floor height | 4 m |
| Residential facade module | 4 × 1.5 m window module |
| Podium depth | 60 m |
| Render engine | Blender EEVEE |

## Design Features

- **Twin residential towers:** each tower keeps its own height, room-module count, and service-core configuration, producing an asymmetrical skyline.
- **Continuous curved podium:** the podium extends beneath both towers and across the connector, using a smooth 120-degree central arc rather than disconnected rectangular wings.
- **Open public base:** pilotis lift the towers above a permeable ground level, while elevated galleries, guardrails, and planted terraces form a continuous public edge.
- **Horizontal facade rhythm:** pale stone bands, dark metal mullions, and neutral clear glass create long ribbon elevations. Windows, ventilation bands, and wall surfaces remain flush on one facade plane.
- **Sky gardens and refuge floors:** double-height openings combine vertical screens, planting, balustrades, exposed cores, and perimeter structure.
- **Landscaped roofs:** low planting and perimeter screens terminate both tower and podium volumes.
- **Legible structure:** twin service cores continue through each tower, with exposed trusses and outrigger elements marking the taller tower's sky-garden levels.
- **Layered lighting:** deterministic warm and cool room lights create a scattered, star-like pattern behind the glazing, while dense circular fixtures illuminate the podium soffits and pilotis arcades.

## Main Views

| Ground-Up Twin-Tower View | Ground-Up Podium Corner |
| --- | --- |
| ![Ground-up view between the illuminated towers](out/view_ground_up.png) | ![Ground-up view across the illuminated podium](out/view_ground_up_wide.png) |
| The camera sits at ground level and looks steeply upward between both towers, emphasizing their height and scattered interior lights. | A second ground-level camera looks upward from the podium corner, placing the illuminated soffit, pilotis, and both towers in the same frame. |

| Podium and Pilotis | Sky Garden |
| --- | --- |
| ![Podium and pilotis](docs/images/highrise-podium.png) | ![Sky garden](docs/images/highrise-sky-garden.png) |
| A close view of the open base, columns, public galleries, guardrails, and illuminated podium underside. | The double-height planted refuge level, vertical screen, glazing, and structural frame. |

| Facade Detail |
| --- |
| ![Facade detail](docs/images/highrise-facade-detail.png) |
| Clear glazing, ventilation strips, horizontal spandrels, mullions, and the varied interior-light modules seen at close range. |

## The Stack

A second, independent procedural study in this repository: an image-led approximation of MVRDV's *The Stack* competition proposal, built by `build_the_stack.py`. It is a slender 115 × 40 m slab rising to 298.8 m, read as a vertical stack of horizontal neighbourhood bands — a double-height retail hall, garden, diagrid, fin and masonry bands. Its identity is the public route up the middle: two service cores run the long axis and, between them, one continuous chain of escalators climbs from the ground hall to the planted roof, stopping at four sky-garden plazas. In the retail hall the chain is a rectangular helix — a run on each face of the ring at a real escalator pitch, so from above it reads as a 回 that spirals up — kept on the ring floor beside the atrium opening, never across the draughty void. Each plaza is the same two-storey volume — a planted garden deck at the bottom, with the chunky Abeno Harukas-style chevron belt truss rising from that deck and spanning both storeys to the ceiling — and both storeys are wrapped by a folded glass screen: a vertical sawtooth in plan whose outer folds sit on the shared facade plane and whose inner folds are drawn back, so the layer reads as a folding screen and never stands proud of the envelope, with the truss reading through the glass. The garden and its trees grow up through the truss toward the ceiling two storeys above: a vertical mall wrapped in a vertical forest. The fourth plaza sits in the middle of the apartment band, between its two offset voids. Those two voids are ventilation openings either side of the centreline, each as wide as half the span between the cores so it runs from its core to the centreline; each is centred on one of the core's chunky X-brace bays, so the brace reads in the vertical middle of the opening — the taller lower vent stands free in the brick band with a few storeys of wall below it, while the upper one opens down onto the garden roof of the mid-apartment refuge. The public escalator interlocks big ~30° diagonal flights across the office shaft — two of them crossing over the centre — then reverts to a plain one-plane switchback through the apartment band above. The apartment band is pierced by the two offset voids, each against a core, rather than by a bridge.

Generated and iterated procedurally with **DeepSeek 4.1**.

| Whole building | Apartment curtain wall |
| --- | --- |
| ![The Stack, whole building](docs/images/stack-preview.png) | ![The Stack, apartment curtain wall](docs/images/stack-facade.png) |

| Apartment void | Refuge sky garden |
| --- | --- |
| ![The Stack, apartment void](docs/images/stack-void.png) | ![The Stack, refuge sky garden](docs/images/stack-refuge-garden.png) |

| Retail base |
| --- |
| ![The Stack, retail base](docs/images/stack-base.png) |

### Reference

The generator is an image-led approximation of MVRDV's competition proposal; the
original design (© MVRDV, [mvrdv.com/projects/340/the-stack](https://mvrdv.com/projects/340/the-stack))
is kept here for comparison:

| MVRDV reference — aerial (photo 16064) | MVRDV reference — atrium escalators |
| --- | --- |
| ![The Stack reference, aerial](docs/images/stack-mvrdv-aerial.jpg) | ![The Stack reference, atrium escalators](docs/images/stack-mvrdv-atrium.jpg) |

Build, render the review views and validate it with:

```bash
blender --background --factory-startup --python-exit-code 1 --python build_the_stack.py
blender --background --factory-startup --python-exit-code 1 --python build_the_stack.py -- --views preview facade garden void base
blender --background --factory-startup --python-exit-code 1 --python verify_the_stack.py -- out/the_stack.blend
blender --background --factory-startup --python-exit-code 1 --python check_stack_zfight.py -- out/the_stack.blend
```

### Export The Stack for the Browser

The web viewer loads a binary glTF file (`.glb`), not the editable Blender file and not OBJ. The export script opens the source `.blend` in memory, merges static mesh objects that share one material, and writes a browser-ready GLB without saving changes back to the source scene:

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python export_the_stack.py -- \
  --profile architectural \
  --compression meshopt \
  --report out/the_stack_web_report.json \
  --source out/the_stack.blend \
  --output web/assets/the_stack.glb

npm run optimize:web -- \
  web/assets/the_stack.glb \
  web/assets/the_stack.optimized.glb \
  --compress meshopt
```

The browser loads `web/assets/the_stack.optimized.glb`. Material merging is enabled by default because browser performance is more sensitive to draw calls than to this model's triangle count. It preserves the geometry, floor slabs, and triangle count; it only reduces the number of independent mesh primitives. Blender EEVEE glass node graphs are translated on the in-memory export copy to glTF transmission/IOR/specular/clearcoat properties so the browser keeps the source glass's transparency and reflection semantics. The `.blend` file is never saved by the exporter. To export without this web optimization:

```bash
blender --background --factory-startup --python export_the_stack.py -- \
  --no-merge-materials
```

To leave all Blender material node graphs untouched during export, add:

```bash
--preserve-materials
```

The current The Stack web assets are approximately:

```text
Blender-export GLB:  2.80 MB / 20 meshes
Final optimized GLB: 1.64 MB / 11 meshes
Triangles:           198,860
Meshopt:             EXT_meshopt_compression
```

The original editable scene remains `out/the_stack.blend`. The web asset is loaded by `web/index.html` through Three.js's `GLTFLoader` with `MeshoptDecoder`. The exporter supports `--profile static`, `--profile animated`, and `--profile architectural`; animated exports do not merge meshes. It also accepts `--compression draco`, `--compression meshopt`, `--compression none`, `--report`, `--no-merge-materials`, and `--preserve-materials`. LOD is intentionally not applied automatically because generic geometric decimation can damage glass, floors, instances, and animation semantics; runtime resolution and on-demand rendering are enabled in the viewer instead.

## Repository Structure

```text
build_house.py       # Procedural generation of the residential towers and podium
build_office.py      # Separate procedural office-tower study
materials.py         # Stone, glass, metal, lighting, and planting materials
render_views.py      # Batch rendering of presentation views
verify_house.py      # Geometry, facade-module, and scene validation
floor_plan.py        # Floor-plan output
open_in_blender.py   # Opens the scene in Material Preview
export_the_stack.py  # Browser-oriented GLB export and optimization report
package.json         # glTF Transform post-processing command
view.sh              # Convenience command for opening the saved Blender scene
out/                 # Local build products; ignored by Git
web/                 # Three.js viewer and web assets
docs/images/         # Images displayed in this README
```

## Usage

Blender 5.x is required. The project is currently developed with Blender 5.2.0 LTS.

### Build the Scene

```bash
blender --background --factory-startup --python build_house.py
```

The build writes the following files to `out/`:

- `highrise_house.blend`: the complete editable scene
- `highrise_house.glb`: a glTF export for web and other DCC viewers
- `preview.png`: the overall preview render

Append `--no-render` to generate the model without rendering the preview.

### Open the Scene

```bash
./view.sh
```

This opens `out/highrise_house.blend` and switches the 3D viewport to Material Preview. Blender's default Solid mode ignores the project materials and otherwise displays the model as a flat grey mass.

### Render Presentation Views

```bash
blender --background --factory-startup --python render_views.py -- out/highrise_house.blend
```

The renderer writes all views to `out/`, including two reproducible ground-level upward views. The README images are repository snapshots stored in `docs/images/`, allowing GitHub to display the project without relying on external release assets.

### Run Validation

```bash
blender --background --factory-startup --python verify_house.py -- out/highrise_house.blend
```

The verifier checks tower dimensions, floor and window modules, glazing, service cores, sky gardens, podium continuity, pilotis clearance, and saved viewport settings. The current saved scene includes later three-level podium and truss-height adjustments, so several older assertions still report baseline mismatches and need to be synchronized with the latest design.

## Parametric Model

Key dimensions are derived from window count, floor height, and residential-group count instead of being assembled as fixed masses. Adding one 4 m module to a long facade increases the corresponding tower width by exactly 4 m. Changing the residential group count updates the floors, core tops, sky-garden positions, and camera framing together.

The two residential tower configurations are defined by the `configure_tower()` calls in `build_house.py`:

```python
configure_tower(2, 18, core_column_bays=2)  # Existing tower
configure_tower(3, 20, core_column_bays=3)  # Adjacent tower
```

Materials are centralized in `materials.py`. The default palette combines warm pale stone, neutral transparent glass, dark anodized metal, and subdued green planting. Interior depth comes from discrete ceiling fixtures with deterministic warm, cool, and off states rather than a uniformly emissive surface placed behind the glazing.

## Current Status

The current scene is saved as `out/highrise_house.blend`. The README imagery has been captured and rendered from that scene, including the two ground-level upward views. Scene building and batch rendering are reproducible; validation runs successfully but still contains several podium and truss assertions based on an earlier scene baseline.
