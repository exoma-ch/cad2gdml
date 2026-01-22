# Geometry Centering Feature

## Overview

The geometry centering feature allows you to optionally translate and center the geometry's bounding box at the origin (0, 0, 0). This minimizes the world volume size and transforms all crystal center coordinates to the centered coordinate system.

## Feature Description

### Without Centering (Default Behavior)

- **Preserves original CAD coordinates**: Geometry maintains its original position relative to the CAD origin
- **World size calculation**: Uses maximum extent from origin in each axis (ensures geometry is fully contained even if not centered)
- **Crystal coordinates**: Reported in original CAD coordinate system
- **World position**: Always at (0, 0, 0) m

### With Centering (`--center-geometry`)

- **Translates geometry**: Moves the bounding box center to (0, 0, 0)
- **Minimal world size**: Uses bounding box dimensions + margin (smaller than non-centered mode)
- **Transformed crystal coordinates**: All crystal centers are automatically transformed to the centered coordinate system
- **Transformation tracking**: Translation information is saved for reference

## Key Differences

| Aspect | Without `--center-geometry` | With `--center-geometry` |
|--------|----------------------------|--------------------------|
| **World Size** | Based on max extent from origin | Based on bounding box dimensions |
| **World Position** | (0, 0, 0) m | (0, 0, 0) m (geometry translated) |
| **Crystal Coordinates** | Original CAD coordinates | Transformed (centered) coordinates |
| **World Volume** | Larger (accommodates off-center geometry) | Smaller (optimized for centered geometry) |
| **Coordinate System** | Original CAD | Centered at origin |

## Usage

### Basic Command (Without Centering)

```bash
python3 src/GUIMeshCLI.py \
  --step STEPfiles/ring_12x1_irene.step \
  --assign-materials \
  --output-dir output/test_no_center
```

### With Centering Enabled

```bash
python3 src/GUIMeshCLI.py \
  --step STEPfiles/ring_12x1_irene.step \
  --assign-materials \
  --center-geometry \
  --output-dir output/test_centered
```

## Output Files

### Transformation Information

When `--center-geometry` is used, a `geometry_transform.json` file is created in the output directory:

```json
{
  "geometry_centered": true,
  "translation_mm": {
    "x": -150.5,
    "y": -200.3,
    "z": -75.2
  },
  "translation_m": {
    "x": -0.1505,
    "y": -0.2003,
    "z": -0.0752
  },
  "description": "Geometry has been translated to center the bounding box at (0, 0, 0). Crystal center coordinates in output files are in the transformed (centered) coordinate system. To convert back to original CAD coordinates, subtract the translation values (translation_mm)."
}
```

### GDML Comments

The `mother.gdml` file includes transformation information as XML comments:

```xml
<!--
  Geometry Transformation Information:
  Geometry has been translated to center the bounding box at (0, 0, 0).
  Translation applied to geometry: (-0.150500, -0.200300, -0.075200) m
  Translation in mm: (-150.500, -200.300, -75.200) mm
  Crystal center coordinates in output files are in the transformed (centered) coordinate system.
  To convert back to original CAD coordinates, subtract the translation values.
  For detailed transformation information, see geometry_transform.json in the output directory.
-->
```

## Testing the Feature

### Running Tests in Container

1. **Start the container** (if not already running):

```bash
# Build the container (if needed)
cd build/Podman
podman build -t cad2geant .

# Start container with repository mounted
podman run -it \
  --name guimesh-container \
  -v /path/to/CADtoGeant4:/mnt/guimesh \
  cad2geant

# Or re-enter existing container
podman start -ai guimesh-container
```

2. **Inside the container**, navigate to the mounted directory:

```bash
cd /mnt/guimesh
```

### Test Procedure

#### Test 1: Without Centering

```bash
python3 src/GUIMeshCLI.py \
  --step STEPfiles/ring_12x1_irene.step \
  --assign-materials \
  --output-dir output/test_no_center \
  --verbose
```

**What to observe:**
- Check the "Geometry Analysis" output section
- Note the "Geometry center" coordinates (will be non-zero if geometry is off-center)
- Note the "World size" - should be larger to accommodate off-center geometry
- Check that `geometry_transform.json` shows `"geometry_centered": false`
- Crystal center coordinates in CSV/H5 files are in original CAD coordinates

#### Test 2: With Centering

```bash
python3 src/GUIMeshCLI.py \
  --step STEPfiles/ring_12x1_irene.step \
  --assign-materials \
  --center-geometry \
  --output-dir output/test_centered \
  --verbose
```

**What to observe:**
- Check the "Geometry Analysis (CENTERING MODE)" output section
- Note the "Original geometry center" coordinates
- Note the "Translation to center" values
- Note the "World size" - should be smaller (optimized)
- Check that `geometry_transform.json` shows `"geometry_centered": true` with translation values
- Crystal center coordinates in CSV/H5 files are in transformed (centered) coordinates

### Comparing Results

#### Compare World Sizes

```bash
# Check world dimensions in both outputs
grep "World size" output/test_no_center/*.gdml output/test_centered/*.gdml
```

The centered version should have a smaller world size.

#### Compare Geometry Centers

```bash
# Check transformation info
cat output/test_centered/geometry_transform.json
```

#### Compare Crystal Coordinates

```bash
# Extract first few crystal centers from both outputs
head -5 output/test_no_center/*.csv
head -5 output/test_centered/*.csv
```

The coordinates should differ by the translation amount.

#### Verify GDML Transformation

```bash
# Check the geometry_offset in mother.gdml
grep "geometry_offset" output/test_no_center/mother.gdml
grep "geometry_offset" output/test_centered/mother.gdml
```

- **Without centering**: `geometry_offset` should be `(0, 0, 0)`
- **With centering**: `geometry_offset` should be the negative of the translation (in meters)

### Expected Output Differences

#### Console Output (Without Centering)

```
=== Geometry Analysis ===
Bounding box: 300.0mm x 400.0mm x 150.0mm
Extents from origin: X [50.0, 350.0] mm, Y [100.0, 500.0] mm, Z [25.0, 175.0] mm
Geometry center: (200.0, 300.0, 100.0) mm
World size: 0.74m x 1.05m x 0.37m
World position: (0.000, 0.000, 0.000) m (CAD origin preserved)
```

#### Console Output (With Centering)

```
=== Geometry Analysis (CENTERING MODE) ===
Bounding box: 300.0mm x 400.0mm x 150.0mm
Extents from origin: X [50.0, 350.0] mm, Y [100.0, 500.0] mm, Z [25.0, 175.0] mm
Original geometry center: (200.0, 300.0, 100.0) mm
Translation to center: (-200.0, -300.0, -100.0) mm
World size: 0.32m x 0.42m x 0.16m
World position: will be set to translation (geometry centered at origin)
```

## Coordinate System Conversion

### Converting from Centered to Original CAD Coordinates

If you have crystal coordinates from the centered output and need original CAD coordinates:

```python
import json

# Load transformation info
with open('output/test_centered/geometry_transform.json') as f:
    transform = json.load(f)

translation_mm = transform['translation_mm']

# Convert centered coordinates to CAD coordinates
centered_x, centered_y, centered_z = 10.5, 20.3, 15.7  # Example centered coordinates

cad_x = centered_x - translation_mm['x']  # Subtract (not add) because translation is negative
cad_y = centered_y - translation_mm['y']
cad_z = centered_z - translation_mm['z']
```

### Converting from Original CAD to Centered Coordinates

```python
# Convert CAD coordinates to centered coordinates
cad_x, cad_y, cad_z = 210.5, 320.3, 115.7  # Example CAD coordinates

centered_x = cad_x + translation_mm['x']  # Add translation
centered_y = cad_y + translation_mm['y']
centered_z = cad_z + translation_mm['z']
```

## Use Cases

### When to Use Centering

- **Minimize world size**: Reduces simulation volume for better performance
- **Standardized coordinates**: All geometries centered at origin for easier comparison
- **Optimized simulations**: Smaller world volumes reduce memory and computation

### When NOT to Use Centering

- **Preserve CAD coordinates**: When you need exact original coordinate values
- **Coordinate matching**: When coordinates must match other CAD-derived data
- **Legacy compatibility**: When existing analysis tools expect original coordinates

## Implementation Details

### Translation Calculation

The translation is calculated as the negative of the bounding box center:

```python
center_x = (min_x + max_x) / 2.0
center_y = (min_y + max_y) / 2.0
center_z = (min_z + max_z) / 2.0

translation = [-center_x, -center_y, -center_z]  # mm
```

### GDML Transformation

In the GDML file, the transformation is applied via the `geometry_offset` position:

```xml
<position name="geometry_offset" x="-0.200" y="-0.300" z="-0.100" unit="m"/>
```

This offset is applied to all geometry volumes when they are placed in the world.

### Crystal Center Transformation

Crystal centers are transformed during extraction:

```python
if translation is not None:
    center_x = center_x + translation[0]
    center_y = center_y + translation[1]
    center_z = center_z + translation[2]
```

## Troubleshooting

### Issue: World size is the same in both modes

**Possible cause**: Geometry is already centered at origin
**Solution**: Check the geometry center coordinates - if they're close to (0, 0, 0), the difference will be minimal

### Issue: Crystal coordinates don't match expected values

**Possible cause**: Forgetting to account for coordinate system transformation
**Solution**: Check `geometry_transform.json` and apply the conversion formula

### Issue: GDML file shows wrong transformation

**Possible cause**: Translation sign confusion
**Solution**: Remember that `geometry_offset` in GDML is the negative of `world_pos`, which is the negative of the translation

## References

- Main README: `README.md`
- Developer Documentation: `README_DEV.md`
- Test Documentation: `tests/README.md`
