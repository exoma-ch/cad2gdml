
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

### Complete Workflow Example
```bash
# 1. Load STEP file and save properties (with automatic world size)
python GUIMeshCLI.py \
  --verbose \
  --step "STEP files/ring_radial_12_axial_1.step" \
  --save-props properties.csv

# 2. Assign materials based on volume names
python assign_materials.py properties.csv properties-with-materials.csv

# 3. Generate GDML with proper materials
python GUIMeshCLI.py \
  --verbose \
  --step "STEP files/ring_radial_12_axial_1.step" \
  --load-material "Materials/LYSO.txt" \
  --load-props properties-with-materials.csv \
  --output-dir gdml_output/
```
  
## Material Assignment

The `assign_materials.py` script automatically assigns materials based on volume names:

- `_detector_lyso_*` → LYSO (custom material)
- `sipm_si*` → G4_Si (pure silicon)
- `dmod-base_al*` → G4_Al (aluminum)
- `pcb-sipm_pcb*` → G4_POLYETHYLENE (PCB material)
- `unit-cover_plastic*` → G4_POLYETHYLENE (plastic)

Usage:
```bash
python assign_materials.py input_properties.csv output_properties.csv
```

## Files description
* `GUIMeshCLI.py` - Main source code for command line interface - for our purposes (GUIMesh.py - original source code for GUI)
* `assign_materials.py` - Script to automatically assign materials based on volume names
* `calculate_world_size.py` - Standalone script to calculate optimal world size (now integrated into main CLI)
* `Documents/` - Folder with "GUIMesh User Manual.pdf", a guide on how to run GUIMesh found in the Documents directory
* `GUIMeshLibs/` - folder containing libraries used in GUIMesh
* `Materials/` - folder which should be used to save materials in a database
* `STEP Files/` - folder with STEP geometries used in all tests
* `gdml/` - folder for the gdml output
* `COPYING` - License disclosure






## Licence  
Licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

See the `COPYING` file for license details.

