# Analysis Folder - Coordinate System Normalization

## Overview

This folder contains visualization scripts for crystal geometry data. The plotting scripts automatically handle different coordinate system conventions to ensure consistent visualizations regardless of the input coordinate system.

## Coordinate System Conventions

The system supports two coordinate conventions:

- **yup convention**: Standard coordinate system where y and z are not swapped
- **noyup convention**: Coordinate system where y and z are swapped (and one is negated)

## Automatic Normalization

The `plot_scanner_with_crystals.py` script automatically detects and normalizes coordinate systems to ensure plots are consistent regardless of which convention the input CSV file uses.

### Detection Method

The script detects the coordinate convention by checking which coordinate has a mean near zero:

- If `mean_y ≈ 0` and `mean_z ≠ 0` → Detected as **yup convention** (needs transformation)
  - In yup: y values are distributed around 0, z values have non-zero mean
- If `mean_y ≠ 0` and `mean_z ≈ 0` → Detected as **noyup convention** (already correct, used as canonical)
  - In noyup: y values have non-zero mean, z values are distributed around 0

The detection uses a tolerance of 1.0 mm to determine if a mean is "near zero".

### Transformation

When yup convention is detected, coordinates are automatically transformed to noyup convention:

```python
y_noyup = -z_yup  # Swap and negate
z_noyup = y_yup   # Swap
```

### Elevation Angle Normalization

Elevation angles are normalized so that 0° and 360° are treated as equivalent:

```python
elevation = elevation % 360.0
if elevation == 360.0:
    elevation = 0.0
```

## Important Notes

⚠️ **This normalization approach is specific to the current geometry** (34x1 crystal detector configuration). The detection heuristics are based on the characteristic coordinate value distributions of this particular geometry.

For other geometries:
- The mean-based detection (checking which coordinate has mean ≈ 0) may not reliably distinguish coordinate conventions if both coordinates have non-zero means or both are centered around zero
- The transformation formula may need adjustment
- Manual coordinate system specification may be required
- One must be aware that this approach might fail for future geometries with different coordinate distributions

## Usage

The normalization happens automatically when reading CSV files:

```python
from plot_scanner_with_crystals import read_crystal_data

# Both files will produce identical plots after normalization
crystals_yup = read_crystal_data('34x1crystalcenters_yup.csv')
crystals_noyup = read_crystal_data('34x1crystalcenters_noyup.csv')
```

## Files

- `plot_scanner_with_crystals.py` - Main plotting script with coordinate normalization
- `34x1crystalcenters_yup.csv` - Crystal data in yup convention
- `34x1crystalcenters_noyup.csv` - Crystal data in noyup convention

## Output Files

- `all_orientation_groups_superimposed.png` - All orientation groups overlaid
- `all_orientation_groups_combined.png` - Separate plots for each orientation group
- `scanner_with_crystals.png` - Main scanner visualization
- `debug_single_crystals_per_group.png` - Debug view with one crystal per group
- `y_vs_radial_angle.png` - Y position vs radial angle plot

