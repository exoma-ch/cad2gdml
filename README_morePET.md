# CADtoGeant4 – morePET Workflow

This document covers the morePET-specific usage of GUIMeshCLI. For general setup, flags, and material format, see `README.md`.

## Context

morePET is a PET scanner project. This converter is used to turn the CAD model of the scanner into a Geant4 simulation geometry. The typical CAD assembly contains LYSO scintillator crystals, SiPM sensors, aluminum structural parts, and various fasteners. The converter produces:

- GDML geometry files for Geant4
- Crystal center coordinates and orientations (CSV + H5) for simulation analysis

## CAD Naming Convention

Name parts in the CAD assembly so that the material is identifiable from the name. Current mappings in `src/material_mappings.json`:

| Name contains | Material |
|---|---|
| `lyso` | LYSO (custom, load with `--load-materials`) |
| `sipm` | `G4_Si` |
| `alu` or `aluminum` | `G4_Al` |
| `carbon` | `G4_C` |
| `steel` or `stainless` | `G4_STAINLESS-STEEL` |
| `pcb` or `plastic` | `G4_POLYETHYLENE` |

Parts that don't match any pattern get the fallback material. Run `--dump-parts` on a new STEP file to check part names before converting.

## Typical Workflow

```bash
# 1. Inspect part names
podman run --rm -v /path/to/CADtoGeant4:/mnt/guimesh cadtogeant4:slim \
  python3 src/GUIMeshCLI.py \
    --step data/STEPfiles/ring_12x1.step \
    --dump-parts output/parts.txt

# 2. Convert with material assignment and crystal extraction
podman run --rm -v /path/to/CADtoGeant4:/mnt/guimesh cadtogeant4:slim \
  python3 src/GUIMeshCLI.py \
    --step data/STEPfiles/ring_12x1.step \
    --load-materials data/Materials/ \
    --assign-materials \
    --extract-centers output/analysis/crystals \
    --center-geometry \
    --output-dir output/gdml/ \
    --verbose
```

## Crystal Center Extraction (`--extract-centers`)

For each volume whose name matches the `lyso` pattern, the tool extracts:

- `center_x/y/z` — bounding box center in mm, in the CAD frame (or post-translation if `--center-geometry` is used).
- `dir_x/y/z` — unit vector along the crystal's long axis, in the same frame, sign-canonicalized so opposite-pointing crystals share a direction.

> **Strong assumption (no fallback):** each LYSO volume must be a clean parallelepiped tessellating to 8 vertices, with one unambiguously longest edge — typically the radial/depth direction of a PET crystal. Volumes that don't satisfy this are skipped with a warning.

`dir_*` is derived from the tessellated vertices (no spherical-coordinate convention baked in); see [README_DEV.md](README_DEV.md#crystal-orientation-algorithm) for the algorithm. Downstream consumers that need azimuth/elevation derive them from `dir_*` against whichever scanner axial axis they use.

Output files: `<name>.csv` and `<name>.h5`, both containing the same data.

## Geometry Centering (`--center-geometry`)

For a ring geometry, the CAD origin is typically not at the scanner center. `--center-geometry` translates the entire assembly so its bounding box center is at (0, 0, 0). This:

- Reduces world volume size (better simulation performance)
- Places the scanner center at the Geant4 origin as expected

The applied translation is saved to `geometry_transform.json`. Crystal coordinates in the output CSV/H5 are already in the centered coordinate system. To recover original CAD coordinates, subtract the translation:

```
CAD_coord = centered_coord - translation_mm
```

## LYSO Material Definition

LYSO is a custom material; it must be loaded explicitly. Definition in `data/Materials/LYSO.json`:

```json
{
  "name": "LYSO",
  "density": 7.1,
  "elements": [
    {"name": "G4_Lu", "fraction": 0.7143},
    {"name": "G4_Y",  "fraction": 0.0403},
    {"name": "G4_Si", "fraction": 0.0637},
    {"name": "G4_O",  "fraction": 0.1814},
    {"name": "G4_Ce", "fraction": 0.0003}
  ]
}
```

Load the whole `data/Materials/` directory to get all custom materials in one flag:

```bash
--load-materials data/Materials/
```

## Reference STEP Files

| File | Description |
|---|---|
| `data/STEPfiles/ring_radial_12_axial_1.step` | Small ring (12 crystals, 1 axial layer) — fast for testing |
| `data/STEPfiles/ring34x1_yup.step` | Larger ring with full crystal array |
