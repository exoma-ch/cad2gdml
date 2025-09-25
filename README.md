
This project is based on [GUIMesh3](https://github.com/MPintoSpace/GUIMesh3), originally developed by Marco Gui Alves Pinto. It is now a command line interface that converts STEP geometries to GDML format.

## Dependencies

You can build a containerized environment using Podman.

Build an image: 

```bash
podman build -t <imagename> .
```
Start a container with bind mount to your git repository:
```bash
podman run -it \
  --name <containername> \
  -v <pathto>/CADtoGeant4:/mnt/guimesh \
  <imagename>
  ```
  Re-enter the container:
  ```bash
  podman start -ai guimesh-container
  ```


## How to run

### Basic Usage
```bash
python GUIMeshCLI.py \
  --step "STEP files/<stepfile.step>" \
  --load-material "Materials/<material.txt>" \
  --load-props <properties.csv> \
  --output-dir gdml/
```

### Automatic World Size
The CLI now automatically calculates and sets the optimal world size based on your geometry's bounding box. No need to manually specify `--world-size` unless you want to override the automatic calculation.

When you load a STEP file, you'll see:
```
=== Geometry Analysis ===
Bounding box: 366.8mm x 380.0mm x 366.8mm
Center: (0.0, 150.0, 0.0) mm
Calculated world size: 0.51m x 0.53m x 0.51m
World dimensions automatically set to: 0.51m x 0.53m x 0.51m
==============================
```

### Single-Pass Workflow (Recommended)
Import STEP once, assign materials in-memory, and write GDML in a single command:

```bash
python src/GUIMeshCLI.py \
  --verbose \
  --step "data/STEPfiles/ring_radial_12_axial_1.step" \
  --assign-materials \
  --load-material "data/Materials/LYSO.txt" \
  --output-dir output/gdml/
```

### Multi-Pass Workflow (Legacy)
If you need to save/load properties as CSV:

```bash
# 1. Load STEP file and save properties (with automatic world size)
python src/GUIMeshCLI.py \
  --verbose \
  --step "data/STEPfiles/ring_radial_12_axial_1.step" \
  --save-props output/properties/properties.csv

# 2. Generate GDML with proper materials
python src/GUIMeshCLI.py \
  --verbose \
  --step "data/STEPfiles/ring_radial_12_axial_1.step" \
  --load-material "data/Materials/LYSO.txt" \
  --load-props output/properties/properties.csv \
  --output-dir output/gdml/
```
  
## Material Assignment

Materials are automatically assigned based on volume name patterns when using the `--assign-materials` flag. The assignment rules are defined in `material_mappings.json`:

- `_detector_lyso_*` → LYSO (custom material)
- `sipm_si*` → G4_Si (pure silicon)
- `dmod-base_al*` → G4_Al (aluminum)
- `pcb-sipm_pcb*` → G4_POLYETHYLENE (PCB material)
- `unit-cover_plastic*` → G4_POLYETHYLENE (plastic)

### Custom Material Mappings

You can customize material assignments by editing `material_mappings.json` or providing your own configuration file:

```bash
python src/GUIMeshCLI.py \
  --step "data/STEPfiles/your.step" \
  --assign-materials \
  --material-config "src/my_custom_mappings.json" \
  --load-material "data/Materials/LYSO.txt" \
  --output-dir output/gdml/
```

The JSON format allows you to:
- Define custom material patterns
- Add descriptions for each material
- Specify which materials require custom loading
- Set fallback materials for unmatched volumes

## Project Structure
```
/mnt/guimesh/
├── src/                          # Source code
│   ├── GUIMeshCLI.py            # Main CLI script
│   ├── GUIMesh.py               # Original GUI version
│   └── material_mappings.json   # Material configuration
├── libs/                        # Libraries
│   └── GUIMeshLibs/            # GUIMesh libraries
├── data/                        # Input data
│   ├── STEPfiles/              # STEP geometry files
│   └── Materials/              # Material definitions
├── output/                      # Generated outputs
│   ├── gdml/                   # GDML files
│   ├── properties/             # CSV property files
│   └── analysis/               # Analysis results
├── docs/                        # Documentation
│   └── Documents/              # User manual and guides
├── examples/                    # Example files
└── build/                       # Build artifacts
```

## Files description
* `src/GUIMeshCLI.py` - Main source code for command line interface
* `src/material_mappings.json` - JSON configuration file defining material assignment rules
* `docs/Documents/` - Folder with "GUIMesh User Manual.pdf", a guide on how to run GUIMesh
* `libs/GUIMeshLibs/` - folder containing libraries used in GUIMesh
* `data/Materials/` - folder which should be used to save materials in a database
* `data/STEPfiles/` - folder with STEP geometries used in all tests
* `output/gdml/` - folder for the gdml output
* `COPYING.txt` - License disclosure






## Licence  
Licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

See the `COPYING` file for license details.

