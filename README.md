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
    --load-materials data/Materials/MyMaterial.json \
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
- `--load-materials <file_or_dir>` — Load material definitions from a JSON file or directory (all `.json` files). Repeatable
- `--assign-materials <config.json>` — Assign materials to volumes by name pattern. Path is required; see `src/material_mappings/` for bundled configs
- `--extract-centers [filename]` — Extract LYSO crystal center coordinates and orientations (volumes whose name contains "lyso" or whose material is LYSO); writes both a CSV and an H5 file. Filename is auto-generated if omitted
- `--output-dir <dir>` — Output directory for GDML files
- `--world-size X Y Z` — World volume dimensions in meters (default: auto from bounding box + 10% margin)
- `--center-geometry` — Translate geometry so its bounding box center is at the origin; saves the applied translation to `geometry_transform.json`
- `--dump-parts <output_file>` — Write all part labels from the STEP file to a text file (one per line) and exit
- `--verbose` — Detailed progress output

### Outputs

- `mother.gdml` — Top-level GDML file (world + includes)
- `Volumes/*.gdml` — Per-volume GDML files
- `<name>.csv` + `<name>.h5` — LYSO crystal centers and orientations (when using `--extract-centers`)
- `geometry_transform.json` — Applied translation (when using `--center-geometry`)

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
| `window_quartz_03` | `quartz` | custom (requires `--load-materials`) |

### Material mapping file (`src/material_mappings/<domain>.json`)

```json
{
  "material_mappings": {
    "copper": {
      "material": "G4_Cu",
      "description": "Copper",
      "requires_custom": false
    },
    "quartz": {
      "material": "SiO2",
      "description": "Fused silica",
      "requires_custom": true
    }
  },
  "world_material": "Vacuum"
}
```

- `material`: Geant4 material name — `G4_*` for NIST materials, or a custom name
- `requires_custom: true`: material must also be loaded with `--load-materials`
- `world_material` (optional): the **name** of a material to fill the world volume. The named material must be loaded via `--load-materials` (`data/Materials/Vacuum.json` and `data/Materials/Vacuum_ref.json` ship with the repo). Omit to use the legacy hardcoded `Vacuum` block. Use `Vacuum_ref` whenever the GDML will be loaded into [g4ring](gPET-sim/g4ring/src/DetectorConstruction.cpp), which creates its own C++-side material called `Vacuum` and would otherwise duplicate-name-collide.

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

Save material files under `data/Materials/` and load at runtime:

```bash
--load-materials data/Materials/SiO2.json   # single file
--load-materials data/Materials/            # all .json files in directory
```

## License

Licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html). See `COPYING.txt` for details.
