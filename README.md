# CAD2Geant4: STEP to GDML Converter

Converts CAD geometry (STEP format) to GDML for use in Geant4 Monte Carlo simulations. Based on [GUIMesh3](https://github.com/MPintoSpace/GUIMesh3).

**How it works:** You name your CAD parts so that the material is identifiable from the name — e.g., `bracket_alu`, `crystal_lyso`, `housing_carbon`. The tool reads those names, matches them against a configurable pattern file (`src/material_mappings.json`), and assigns Geant4 materials automatically. If you don't know the names in an existing STEP file, use `--dump-parts` to list them before writing your mappings.

## Setup

### 1. Clone this repository

```bash
git clone <repository-url>
cd CADtoGeant4
```

### 2. Build the slim container image

```bash
cd build/Podman
podman build -f Containerfile.slim -t cadtogeant4:slim .
```

All dependencies (FreeCAD, Python packages) are bundled in the container — no manual installation required.

### 3. Run a conversion

```bash
podman run --rm \
  -v /path/to/CADtoGeant4:/mnt/guimesh \
  cadtogeant4:slim \
  python3 src/GUIMeshCLI.py \
    --step data/STEPfiles/your_geometry.step \
    --load-materials data/Materials/MyMaterial.json \
    --assign-materials \
    --output-dir output/gdml/ \
    --verbose
```

Replace `/path/to/CADtoGeant4` with the absolute path to your cloned repository. The container mounts it at `/mnt/guimesh`; all paths in the examples below are relative to that root.

## Usage

### Flags

- `--step <file>` — **Required.** Input STEP file to convert
- `--load-materials <file_or_dir>` — Load material definitions from a JSON file or directory (all `.json` files). Repeatable
- `--assign-materials [config.json]` — Assign materials to volumes by name pattern. Uses `src/material_mappings.json` by default, or pass a custom file
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
  cadtogeant4:slim \
  python3 src/GUIMeshCLI.py \
    --step data/STEPfiles/your_geometry.step \
    --dump-parts output/parts.txt
```

Open `parts.txt`, identify the naming patterns (e.g., `_alu`, `_lyso`, `_carbon`), then write `src/material_mappings.json` accordingly.

## Materials

### Naming parts in your CAD model

The tool assigns materials by matching substrings in volume names (case-insensitive, first match wins). Name your CAD parts so the material is embedded in the name:

| Part name example | Pattern matched | Material assigned |
|---|---|---|
| `cavity_copper_01` | `copper` | `G4_Cu` |
| `shield_aluminum` | `aluminum` | `G4_Al` |
| `window_quartz_03` | `quartz` | custom (requires `--load-materials`) |

### Material mapping file (`src/material_mappings.json`)

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
  }
}
```

- `material`: Geant4 material name — `G4_*` for NIST materials, or a custom name
- `requires_custom: true`: material must also be loaded with `--load-materials`

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
