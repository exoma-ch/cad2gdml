# GUIMeshCLI - Developer Documentation

This document provides information for developers who want to contribute to, modify, or extend GUIMeshCLI.

## Table of Contents

- [Development Setup](#development-setup)
  - [Creating New Container Image Versions](#creating-new-container-image-versions)
- [Project Architecture](#project-architecture)
- [Code Structure](#code-structure)
- [Key Components](#key-components)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Contributing](#contributing)
- [Technical Details](#technical-details)

## Development Setup

### Prerequisites

- **Podman**
- **Git**

**Note:** FreeCAD and all Python dependencies are automatically included in the container - no manual installation required.

### Containerized Development Environment

**Recommended approach:** All dependencies, including FreeCAD, are automatically installed in the container. No manual setup required.

```bash
# Build the development container
cd build/Podman
podman build -t cad2geant .

# Start container with your project mounted
podman run -it \
  --name guimesh-container \
  -v /path/to/CADtoGeant4:/mnt/guimesh \
  cad2geant

# Re-enter container
podman start -ai guimesh-container
```

Replace `/path/to/CADtoGeant4` with the absolute path to your cloned repository.

The container automatically includes:
- Python 3.11
- FreeCAD 1.0.1 (downloaded and extracted from AppImage during build)
- All Python dependencies from `build/Podman/requirements.txt`
- Properly configured environment variables (`PYTHONPATH`, `LD_LIBRARY_PATH`) for FreeCAD

Everything is set up automatically - just build and run the container.

### Creating New Container Image Versions

When you're ready to release a new version of the container image, follow these steps:

#### 1. Commit Your Changes

Make sure all your changes are committed:

```bash
git add .
git commit -m "Description of changes"
git push origin main
```

#### 2. Create a Git Tag

Create a git tag for the new version. Use semantic versioning (e.g., `v1.0.0`, `v1.1.0`, `v2.0.0`):

```bash
git tag -a v1.1.0 -m "Release version 1.1.0"
```

#### 3. Push the Tag

Push the tag to trigger the automated build:

```bash
git push origin v1.1.0
```

#### 4. Monitor the Build

The GitHub Actions workflow will automatically:
- Detect the tag push
- Build the container image
- Tag it with the version (e.g., `v1.1.0`, `1.1.0`, `1.1`, `1`)
- Push it to GitHub Container Registry at `ghcr.io/morepet/cadtogeant4/cadtogeant4`

You can monitor the build progress in the **Actions** tab of your GitHub repository.

#### 5. Verify the Image

Once the build completes, verify the image is available:

```bash
podman pull ghcr.io/morepet/cadtogeant4/cadtogeant4:v1.1.0
```


#### Updating an Existing Tag

If you need to update a tag to point to a newer commit:

```bash
# Delete the local tag
git tag -d v1.0.0

# Create a new tag pointing to current commit
git tag -a v1.0.0 -m "Release version 1.0.0"

# Delete the remote tag and push the new one
git push origin :refs/tags/v1.0.0
git push origin v1.0.0
```

**Note:** This will trigger a new build with the updated tag.

#### Manual Build (Local Testing)

If you want to build and tag an image locally for testing before pushing:

```bash
cd build/Podman

# Build with a specific tag
podman build -t cad2geant:v1.1.0 .

# Or with full registry path
podman build -t ghcr.io/morepet/cadtogeant4/cadtogeant4:v1.1.0 .

# Test the image locally
podman run -it --rm \
  -v /path/to/CADtoGeant4:/mnt/guimesh \
  cad2geant:v1.1.0
```

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

### Automated Testing with pytest

The project uses pytest for automated testing. To set up and run tests:

#### Setup

1. Create a virtual environment (recommended):
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows
```

2. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

#### Running Tests

Run all tests:
```bash
pytest
```

Run tests with verbose output:
```bash
pytest -v
```

Run a specific test file:
```bash
pytest tests/test_cli_no_step.py
```

Run a specific test:
```bash
pytest tests/test_cli_no_step.py::test_main_without_step_argument
```

#### Example Test

The test suite includes an example test (`tests/test_cli_no_step.py`) that verifies the program handles cases where the `--step` argument is not provided. This ensures the CLI fails gracefully when required inputs are missing.

#### Coverage Reports

Coverage reports are automatically generated when running tests. The current test coverage is **28%** for `GUIMeshCLI.py`, focusing on error handling and CLI argument parsing.

View coverage report:
```bash
# Coverage is automatically included in pytest output
pytest

# View detailed HTML coverage report
# Open htmlcov/index.html in your browser after running tests
```

For detailed coverage analysis, see `tests/COVERAGE_REPORT.md`.

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

