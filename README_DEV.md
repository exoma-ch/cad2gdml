# GUIMeshCLI - Developer Documentation

This document provides information for developers who want to contribute to, modify, or extend GUIMeshCLI.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Code Structure](#code-structure)
- [Key Components](#key-components)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Contributing](#contributing)
- [Technical Details](#technical-details)

## Development Setup

### Prerequisites

- **Podman** or **Docker** (for containerized development - recommended)
- **Git**

**Note:** FreeCAD and all Python dependencies are automatically included in the container - no manual installation required.

### Containerized Development Environment

**Recommended approach:** All dependencies, including FreeCAD, are automatically installed in the container. No manual setup required.

```bash
# Build the development container
cd build/Podman
podman build -t guimesh-dev .

# Start container with your project mounted
podman run -it \
  --name guimesh-dev \
  -v /path/to/guimesh:/mnt/guimesh \
  guimesh-dev

# Re-enter container
podman start -ai guimesh-dev
```

The container automatically includes:
- Python 3.11
- FreeCAD 1.0.1 (downloaded and extracted from AppImage during build)
- All Python dependencies from `build/Podman/requirements.txt`
- Properly configured environment variables (`PYTHONPATH`, `LD_LIBRARY_PATH`) for FreeCAD

Everything is set up automatically - just build and run the container.

## Project Architecture

### High-Level Overview

```
┌─────────────────┐
│  GUIMeshCLI.py  │  Main CLI entry point
└────────┬────────┘
         │
         ├──► LoadOP.py          (STEP file loading)
         ├──► Materials.py       (Material management)
         ├──► Volumes.py         (Volume data structures)
         ├──► WriteGDML.py      (GDML file generation)
         └──► CrystalCenters.py  (Crystal analysis)
```

### Data Flow

1. **Input**: STEP file → `LoadOP.Load_STEP_File()`
2. **Processing**: 
   - Material loading → `Materials.Load_Material_JSON()`
   - Material assignment → `GUIMeshCLI.assign_materials_from_names()`
   - Crystal extraction → `CrystalCenters.extract_crystal_centers()`
3. **Output**: GDML files → `WriteGDML.CreateMother()` and `WriteGDML.CreateGDML()`

## Code Structure

### Main Components

#### `src/GUIMeshCLI.py`
Main CLI application and orchestration logic.

**Key Classes:**
- `GUIMeshCLI`: Main application class
  - `load_step_file()`: Loads and processes STEP files
  - `load_materials()`: Loads material definitions
  - `assign_materials_from_names()`: Assigns materials based on patterns
  - `extract_crystal_centers()`: Extracts crystal geometry data
  - `write_gdml()`: Generates GDML output files
  - `auto_set_world_size()`: Calculates optimal world dimensions

**Key Functions:**
- `main()`: CLI argument parsing and workflow orchestration

#### `libs/GUIMeshLibs/`

**LoadOP.py**
- `Load_STEP_File()`: Loads STEP files using FreeCAD
- Handles FreeCAD document management
- Returns list of Volume objects

**Materials.py**
- `Load_Elements()`: Loads Geant4 standard elements
- `Load_Material_JSON()`: Loads custom materials from JSON
- `Load_Materials_From_Dir()`: Batch loads materials from directory
- Material data structures and validation

**Volumes.py**
- `Volume` class: Core data structure for geometry volumes
  - `VolumeCAD`: FreeCAD object reference
  - `VolumeMaterial`: Assigned material
  - `VolumeMMD`: Mesh precision
  - `VolumeGDMLoption`: Write flag

**WriteGDML.py**
- `CreateMother()`: Generates main GDML file
- `CreateGDML()`: Generates individual volume GDML files
- `normalize_base_volumes()`: Post-processes volume files

**CrystalCenters.py**
- `extract_crystal_centers()`: Extracts crystal center coordinates and orientations
- Uses geometric analysis of tessellated shapes
- Implements Direct Edge Vector Analysis for orientation calculation

### Configuration Files

#### `src/material_mappings.json`
JSON configuration for material assignment rules:
```json
{
  "material_mappings": {
    "pattern": {
      "material": "MaterialName",
      "description": "Description",
      "requires_custom": true/false
    }
  },
  "fallback_material": {...},
  "version": "1.0"
}
```

## Key Components

### Material Assignment System

**Pattern Matching:**
- Volume names are lowercased and checked against patterns
- First matching pattern wins
- Patterns are simple substring matches (case-insensitive)

**Custom Materials:**
- Materials with `requires_custom: true` must be loaded via `--load-materials`
- Custom materials are defined in JSON format (see `data/Materials/` for examples)

**Material Loading:**
- Supports single files: `--load-materials file.json`
- Supports directories: `--load-materials dir/` (loads all `.json` files)
- Multiple `--load-materials` flags can be used

### Crystal Center Extraction

**Algorithm:**
1. **Center Calculation**: Bounding box center of each crystal volume
2. **Orientation Calculation**: Direct Edge Vector Analysis
   - Collects all edge vectors from tessellated vertices
   - Identifies longest edge with exactly 3 parallel edges (parallelepiped property)
   - Calculates azimuth and elevation angles from main axis vector

**Output Format (CSV, h5):**
- `crystal_id`: Unique identifier
- `volume_name`: Original volume name from STEP file
- `center_x`, `center_y`, `center_z`: Center coordinates (mm)
- `azimuth_angle`: Rotation in XZ plane (degrees, 0-180°)
- `elevation_angle`: Tilt relative to XZ plane (degrees, 0-360°)

### World Size Calculation

**Automatic Mode:**
1. Calculates bounding box of all loaded volumes
2. Adds 10% margin on each side
3. Converts from mm to meters
4. Sets world position to geometry center

**Manual Mode:**
- User specifies dimensions: `--world-size X Y Z`
- Dimensions in meters
- World position defaults to origin (0, 0, 0)

## Development Workflow

### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed

3. **Test your changes:**
   ```bash
   # Test with a sample STEP file
   python3 src/GUIMeshCLI.py \
     --step data/STEPfiles/test.step \
     --load-materials data/Materials/LYSO.json \
     --assign-materials \
     --output-dir output/test/
   ```

4. **Check for errors:**
   - Run with `--verbose` flag to see detailed output
   - Verify GDML output is valid
   - Test material assignment logic

5. **Commit and push:**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin feature/your-feature-name
   ```

### Code Style Guidelines

- **Python**: Follow PEP 8 style guide
- **Naming**: Use descriptive names, camelCase for classes, snake_case for functions
- **Comments**: Document complex algorithms and non-obvious logic
- **Error Handling**: Use try-except blocks, provide meaningful error messages
- **Logging**: Use `print()` for user-facing messages, consider logging module for debug info

### Adding New Features

**Adding a new material pattern:**
1. Edit `src/material_mappings.json`
2. Add new pattern entry
3. Test with volumes matching the pattern

**Adding a new CLI option:**
1. Add argument to `argparse` in `main()`
2. Implement logic in `GUIMeshCLI` class
3. Update user documentation

**Adding a new library module:**
1. Create new file in `libs/GUIMeshLibs/`
2. Add to `__init__.py` if needed
3. Import in `GUIMeshCLI.py`

## Testing

### Manual Testing

**Test STEP file loading:**
```bash
python3 src/GUIMeshCLI.py \
  --step data/STEPfiles/ring_radial_12_axial_1.step \
  --verbose
```

**Test material assignment:**
```bash
python3 src/GUIMeshCLI.py \
  --step data/STEPfiles/ring_radial_12_axial_1.step \
  --load-materials data/Materials/LYSO.json \
  --assign-materials \
  --verbose
```

**Test crystal extraction:**
```bash
python3 src/GUIMeshCLI.py \
  --step data/STEPfiles/ring_radial_12_axial_1.step \
  --load-materials data/Materials/LYSO.json \
  --assign-materials \
  --extract-centers output/test/test.csv \
  --output-dir output/test/ \
  --verbose
```

**Test GDML generation:**
```bash
python3 src/GUIMeshCLI.py \
  --step data/STEPfiles/ring_radial_12_axial_1.step \
  --load-materials data/Materials/LYSO.json \
  --assign-materials \
  --output-dir output/test/
```

### Test Files

Use files in `data/STEPfiles/` for testing:
- `ring_radial_12_axial_1.step` - Small test geometry
- `ring34x1_yup.step` - Larger geometry with crystals
- Other ring geometries for various configurations

## Contributing

### Before Contributing

1. **Check existing issues**: Look for similar issues or feature requests
2. **Discuss major changes**: Open an issue to discuss significant changes
3. **Follow the license**: All contributions must be compatible with GPL v3.0

### Contribution Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Update documentation
6. Submit a pull request

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Changes are tested
- [ ] Documentation is updated
- [ ] No breaking changes (or clearly documented)
- [ ] Error handling is appropriate
- [ ] Comments explain complex logic

## Technical Details

### FreeCAD Integration

**FreeCAD Path Configuration:**
- Default: `/usr/local/bin/squashfs-root/usr/lib`
- Can be modified in `GUIMeshCLI.py` line 42

**FreeCAD Modules Used:**
- `FreeCAD`: Core FreeCAD functionality
- `Import`: STEP file import
- `Part`: Geometry operations
- `Draft`: Additional geometry tools

**FreeCAD Document Management:**
- Documents are created and managed by `LoadOP.Load_STEP_File()`
- Objects are extracted from FreeCAD document
- FreeCAD document is closed after processing

### GDML Format

**Structure:**
- `mother.gdml`: Main file with world definition and material includes
- `Volumes/*.gdml`: Individual volume files referenced by mother file

**Material Definitions:**
- Standard Geant4 materials: `G4_Si`, `G4_Al`, etc.
- Custom materials: Defined in JSON, included in GDML

**Volume Definitions:**
- Tessellated shapes (triangular meshes)
- Material assignments
- Position and rotation information

### Crystal Orientation Algorithm

**Direct Edge Vector Analysis:**

1. **Vertex Collection**: Extract all vertices from tessellated shape
2. **Edge Vector Generation**: Calculate all possible edge vectors (n choose 2)
3. **Parallel Edge Detection**: For each edge, count parallel edges
4. **Main Axis Selection**: Choose longest edge with exactly 3 parallel edges
5. **Angle Calculation**:
   - Azimuth: `atan2(z, x)` - rotation in XZ plane
   - Elevation: `atan2(y, sqrt(x² + z²))` - tilt from XZ plane

**Why This Method:**
- Works well for rectangular parallelepiped crystals
- More accurate than PCA for regular geometries
- Handles edge cases better than simple bounding box analysis

### Performance Considerations

**Large STEP Files:**
- Processing time scales with number of volumes
- Tessellation is the most time-consuming step
- Consider using `--verbose` to monitor progress

**Memory Usage:**
- FreeCAD loads entire STEP file into memory
- Large geometries may require significant RAM
- Containerized environment helps isolate resource usage

**Optimization Opportunities:**
- Parallel volume processing (not currently implemented)
- Caching of tessellated shapes
- Incremental GDML writing for very large geometries

## Troubleshooting Development Issues

**FreeCAD Import Errors:**
- Check `PYTHONPATH` and `LD_LIBRARY_PATH` environment variables
- Verify FreeCAD AppImage is properly extracted
- Check FreeCAD version compatibility

**Material Loading Issues:**
- Validate JSON syntax in material files
- Check material name matches between mappings and loaded materials
- Verify file paths are correct

**GDML Generation Errors:**
- Check that all volumes have assigned materials
- Verify world size is appropriate for geometry
- Check for invalid geometry (self-intersections, etc.)

**Crystal Extraction Issues:**
- Ensure volumes are properly tessellated
- Check that crystal volumes are rectangular parallelepipeds
- Use `--verbose` to see detailed extraction process

## Additional Resources

- **FreeCAD Documentation**: https://www.freecad.org/
- **GDML Specification**: https://gdml.web.cern.ch/GDML/
- **Geant4 Documentation**: https://geant4.web.cern.ch/
- **Original GUIMesh3**: https://github.com/MPintoSpace/GUIMesh3

## License

This project is licensed under the GNU General Public License v3.0. See `COPYING.txt` for details.

All contributions must be compatible with this license.

