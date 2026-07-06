# CAD2Geant4: STEP to GDML Converter

Converts CAD geometry (STEP format) to GDML for use in Geant4 Monte Carlo simulations. Based on [GUIMesh3](https://github.com/MPintoSpace/GUIMesh3).

**How it works:** You name your CAD parts so that the material is identifiable from the name — e.g., `bracket_alu`, `crystal_lyso`, `housing_carbon`. The tool reads those names, matches them against a configurable pattern file, and assigns Geant4 materials automatically. If you don't know the names in an existing STEP file, use `--dump-parts` to list them before writing your mappings.

## Setup

### 1. Clone this repository

```bash
git clone <repository-url>
cd CADtoGeant4
```

### 2. Get the container image

**Pull from Docker Hub (recommended):**

```bash
podman pull docker.io/pipsin/cad2geant4:latest
```

All dependencies (FreeCAD, Python packages) are bundled in the image — no manual installation required.

**Or build locally:**

```bash
cd build/Podman
podman build -f Containerfile.slim -t docker.io/pipsin/cad2geant4:latest .
```

### 3. Run a conversion

```bash
podman run --rm \
  -v /path/to/CADtoGeant4:/mnt/guimesh \
  docker.io/pipsin/cad2geant4:latest \
  python3 src/GUIMeshCLI.py \
    --step data/STEPfiles/your_geometry.step \
    --assign-materials src/material_mappings/<config>.json \
    --output-dir output/gdml/ \
    --verbose
```

Replace `/path/to/CADtoGeant4` with the absolute path to your cloned repository. The container mounts it at `/mnt/guimesh`; all paths in the examples below are relative to that root.

### Working with files outside the repo

The container can only see what you explicitly bind-mount with `-v`. Files outside `/path/to/CADtoGeant4` (or whatever you mounted) are invisible — passing a path the container can't reach produces a "file not found" error, not a permission error, which can be confusing.

Two ways to handle inputs/outputs that don't live in the repo:

**(a) Copy them into the repo first.** Drop your STEP file into `data/STEPfiles/` and write outputs to `output/`. Simplest, no extra flags.

**(b) Bind-mount the external location too.** Add another `-v` flag and reference the in-container path in the CLI args:

```bash
podman run --rm \
  -v /path/to/CADtoGeant4:/mnt/guimesh \
  -v /home/me/cad_projects:/data \
  docker.io/pipsin/cad2geant4:latest \
  python3 src/GUIMeshCLI.py \
    --step /data/some_geometry.step \
    --output-dir /data/gdml_out/ \
    --assign-materials src/material_mappings/<config>.json
```

The container sees `/home/me/cad_projects` as `/data`, so `--step /data/some_geometry.step` resolves correctly. Outputs written to `/data/gdml_out/` land in `/home/me/cad_projects/gdml_out/` on the host.

A common mistake: passing host paths (`--step /home/me/foo.step`) without mounting the parent directory — the container sees no such file. The error message will say "file not found" rather than "not mounted", so check your `-v` flags first when this happens.

## Usage

### Flags

- `--step <file>` — **Required.** Input STEP file to convert
- `--assign-materials <config.json>` — Assign materials to volumes by name pattern. Path is required; see `src/material_mappings/` for bundled configs. Custom material JSON files referenced by `path` fields in the mapping are auto-loaded
- `--extract-centers [filename]` — Write the crystal map (H5) for every LYSO volume. Schema below. Volumes that aren't clean 8-vertex parallelepipeds are skipped with a warning. Filename is auto-generated if omitted
- `--output-dir <dir>` — Output directory for GDML files
- `--world-size X Y Z` — World volume dimensions in meters (default: auto from bounding box + 10% margin)
- `--center-geometry` — Translate geometry so its bounding box center is at the origin; saves the applied translation to `geometry_transform.json`
- `--add-copynumbers [prefix]` — Emit `name`/`copynumber` attributes on crystal `<physvol>` tags in `mother.gdml`, taking the number from the `<prefix><N>` volume label (default prefix `_detector_lyso_`). Downstream tools (e.g. gPET-sim's g4ring readout) key on this copy number; using this flag makes the exported GDML directly usable with no separate post-processing step
- `--dump-parts <output_file>` — Write all part labels from the STEP file to a text file (one per line) and exit
- `--verbose` — Detailed progress output

### Outputs

- `mother.gdml` — Top-level GDML file (world + includes)
- `Volumes/*.gdml` — Per-volume GDML files
- `<name>.h5` — Crystal map (when using `--extract-centers`)
- `geometry_transform.json` — Applied translation (when using `--center-geometry`)

### Crystal map (`<name>.h5`)

Per-crystal datasets (one row per LYSO volume):

| Field | Type | Source |
|---|---|---|
| `crystal_id` | int32 | parsed from the volume name (regex) |
| `volume_name` | bytes | original CAD label |
| `center_x/y/z` | float64, mm | bounding-box center, in CAD frame (post-translation if `--center-geometry`) |
| `dir_x/y/z` | float64, unit | the longest of the three principal edges of the tessellated parallelepiped, sign-canonicalized |

File-level attrs (one per file, identical for every crystal):

| Attr | Type | Source |
|---|---|---|
| `scanner_axial_axis` | `'x' \| 'y' \| 'z'` | world axis with smallest mean(`dir²`) — the axis the long axes avoid |
| `crystal_size_radial_mm` | float64 | length of the long edge |
| `crystal_size_axial_mm` | float64 | transverse edge whose direction is most parallel to `scanner_axial_axis` |
| `crystal_size_tangential_mm` | float64 | the remaining transverse edge |

## Discovering part names

If you don't know the part names in your STEP file, dump them first:

```bash
podman run --rm \
  -v /path/to/CADtoGeant4:/mnt/guimesh \
  docker.io/pipsin/cad2geant4:latest \
  python3 src/GUIMeshCLI.py \
    --step data/STEPfiles/your_geometry.step \
    --dump-parts output/parts.txt
```

Open `parts.txt`, identify the naming patterns (e.g., `_alu`, `_lyso`, `_carbon`), then either reuse one of the bundled configs in `src/material_mappings/` or add a new one alongside.

## Materials

### Naming parts in your CAD model

The tool assigns materials by matching substrings in volume names (case-insensitive, first match wins). Name your CAD parts so the material is embedded in the name:

| Part name example | Pattern matched | Material assigned |
|---|---|---|
| `cavity_copper_01` | `copper` | `G4_Cu` |
| `shield_aluminum` | `aluminum` | `G4_Al` |
| `window_quartz_03` | `quartz` | custom (loaded from `path` in mapping JSON) |

### Material mapping file (`src/material_mappings/<domain>.json`)

```json
{
  "material_mappings": {
    "copper": {
      "material": "G4_Cu",
      "description": "Copper"
    },
    "quartz": {
      "material": "SiO2",
      "path": "../../data/Materials/SiO2.json",
      "description": "Fused silica"
    }
  },
  "world_material": {
    "name": "Vacuum",
    "path": "../../data/Materials/Vacuum.json"
  }
}
```

- `material`: Geant4 material name — `G4_*` for NIST materials, or a custom name
- `path` (optional): path to a custom material JSON definition. Resolved **relative to this mapping file**. Entries without `path` are assumed to be NIST built-ins (no loading needed). The script auto-loads every referenced path; no separate flag is required.
- `world_material` (optional): object with `name` (the material to fill the world volume) and an optional `path` to its JSON definition. Omit to use the legacy hardcoded `Vacuum` block. Use `Vacuum_ref` whenever the GDML will be loaded into [g4ring](gPET-sim/g4ring/src/DetectorConstruction.cpp), which creates its own C++-side material called `Vacuum` and would otherwise duplicate-name-collide.

### Custom material definition

```json
{
  "name": "SiO2",
  "density": 2.2,
  "elements": [
    {"name": "G4_Si", "fraction": 0.467},
    {"name": "G4_O",  "fraction": 0.533}
  ]
}
```

- `density` in g/cm³; `fraction` values must sum to 1.0
- Element names follow the Geant4 NIST convention (`G4_Si`, `G4_O`, `G4_Lu`, etc.)

Save material files under `data/Materials/` and reference them from your mapping JSON via the `path` field; the script loads them automatically when `--assign-materials` runs.

## License

Licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html). See `COPYING.txt` for details.
