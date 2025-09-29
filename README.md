# GUIMeshCLI - STEP to GDML Converter with Crystal Analysis

This project is based on [GUIMesh3](https://github.com/MPintoSpace/GUIMesh3), originally developed by Marco Gui Alves Pinto. It is now a command line interface that converts STEP geometries to GDML format.

## Table of Contents

- [Primary Purpose](#primary-purpose)
- [Quick Start](#quick-start)
  - [Basic STEP to GDML Conversion](#basic-step-to-gdml-conversion)
  - [Extract Crystal Data for Geant4 Simulation](#extract-crystal-data-for-geant4-simulation)
  - [Visualize Crystal Geometry](#visualize-crystal-geometry)
- [Complete Workflow](#complete-workflow)
  - [For Geant4 Simulation Setup](#for-geant4-simulation-setup)
  - [Output Files](#output-files)
  - [Command Line Options](#command-line-options)
- [Technical Details](#technical-details)
  - [How Crystal Centers and Orientations Are Calculated](#how-crystal-centers-and-orientations-are-calculated)
  - [Visualization Tool](#visualization-tool)
- [Dependencies](#dependencies)
- [Project Structure](#project-structure)
- [Files Description](#files-description)
- [License](#license)

## Primary Purpose

**Main Function**: Convert STEP CAD files to GDML format for Geant4 simulations, including automatic material assignment based on part names.

**Secondary Feature**: Extract crystal center coordinates and orientations for detector simulation setup.

## Quick Start

### Basic STEP to GDML Conversion

```bash
# Convert STEP file to GDML with material assignment
python3 src/GUIMeshCLI.py \
  --step "data/STEPfiles/ring_radial_12_axial_1.step" \
  --load-material "data/Materials/LYSO.txt" \
  --assign-materials \
  --output-dir output/gdml/
```

### Extract Crystal Data for Geant4 Simulation

```bash
# Extract crystal centers and orientations for simulation setup
python3 src/GUIMeshCLI.py \
  --step "data/STEPfiles/ring_radial_12_axial_1.step" \
  --load-material "data/Materials/LYSO.txt" \
  --assign-materials \
  --extract-centers output/analysis/crystal_lookup.csv \
  --output-dir output/analysis/
```

### Visualize Crystal Geometry

```bash
# Generate visualizations from crystal data
cd output/analysis
python3 plot_scanner_with_crystals.py
```

**Visualization Features:**
- **3D Scanner View**: Shows crystal orientations as oriented sticks
- **Orthogonal Plane Views**: Top (XZ), Side (XY), and Front (YZ) projections  
- **Orientation Group Analysis**: Groups crystals by azimuth angle for pattern analysis
- **Debug Views**: Single crystal per group for easier debugging

**Output Files:**
- `scanner_with_crystals.png` - Main scanner visualization
- `all_orientation_groups_combined.png` - Separate plots for each orientation group
- `all_orientation_groups_superimposed.png` - All groups overlaid
- `debug_single_crystals_per_group.png` - Debug view with one crystal per group

## Complete Workflow

### For Geant4 Simulation Setup

1. **Convert STEP to GDML with materials**
2. **Extract crystal lookup table** 
3. **Visualize geometry for verification**

```bash
# Step 1: Convert STEP to GDML
python3 src/GUIMeshCLI.py \
  --step "data/STEPfiles/ring_radial_12_axial_1.step" \
  --load-material "data/Materials/LYSO.txt" \
  --assign-materials \
  --output-dir output/gdml/

# Step 2: Extract crystal data for simulation
python3 src/GUIMeshCLI.py \
  --step "data/STEPfiles/ring_radial_12_axial_1.step" \
  --load-material "data/Materials/LYSO.txt" \
  --assign-materials \
  --extract-centers output/analysis/crystal_lookup.csv \
  --output-dir output/analysis/

# Step 3: Visualize for verification
cd output/analysis
python3 plot_scanner_with_crystals.py
```

### Output Files

**GDML Files (for Geant4):**
- `mother.gdml` - Main GDML file with material assignments
- `Volumes/` - Directory with individual volume GDML files

**Crystal Lookup Table (CSV format):**
- `crystal_lookup.csv` - Crystal ID, center coordinates, and orientation angles
- **Columns**: `crystal_id`, `volume_name`, `center_x`, `center_y`, `center_z`, `azimuth_angle`, `elevation_angle`
- **Purpose**: Provides crystal positions and orientations for Geant4 simulation setup

**Visualization Files:**
- `scanner_with_crystals.png` - Main scanner visualization with crystal orientations
- `all_orientation_groups_combined.png` - Separate plots for each orientation group
- `all_orientation_groups_superimposed.png` - All groups overlaid on same plots
- `debug_single_crystals_per_group.png` - Debug view with one crystal per group

### Command Line Options

```bash
# Basic extraction (auto-generated filename)
python3 src/GUIMeshCLI.py --step <step_file> --output-dir <output_dir> --extract-centers

# Specify custom CSV filename
python3 src/GUIMeshCLI.py --step <step_file> --output-dir <output_dir> --extract-centers <filename.csv>

# With verbose output (shows detailed progress)
python3 src/GUIMeshCLI.py --step <step_file> --output-dir <output_dir> --extract-centers --verbose

# Use PCA analysis instead of Direct Edge Vector (default)
python3 src/GUIMeshCLI.py --step <step_file> --output-dir <output_dir> --extract-centers --use-pca

# Show help
python3 src/GUIMeshCLI.py --help
```

## Technical Details

### How Crystal Centers and Orientations Are Calculated

The system extracts crystal center coordinates and 3D orientations using geometric analysis of the tessellated 3D shapes. This creates a lookup table for Geant4 simulations.

#### Center Calculation

**Method**: Bounding box center calculation
```python
# Get bounding box of the crystal volume
bbox = obj.VolumeCAD.Shape.BoundBox
center_x = (bbox.XMin + bbox.XMax) / 2
center_y = (bbox.YMin + bbox.YMax) / 2  
center_z = (bbox.ZMin + bbox.ZMax) / 2
```

#### Orientation Calculation

The system offers **two methods** for extracting crystal orientations:

**Method 1: Direct Edge Vector Analysis (Default - Recommended)**
- **Best for**: 8-vertex rectangular crystals
- **How it works**: Analyzes edge vectors to find the main crystal axis
- **Advantage**: More accurate for rectangular geometries

**Method 2: PCA Analysis**
- **Best for**: General 3D shapes with many vertices
- **How it works**: Uses Principal Component Analysis on vertex distribution
- **Advantage**: Robust statistical method

#### Detailed Implementation

**Geometric Data Extraction:**
```python
# Get tessellated vertices from the 3D crystal shape
triangles = obj.VolumeCAD.Shape.tessellate(precision)
vertices = triangles[0]  # All 3D vertices of the crystal

# Extract coordinates
x_coords = [v[0] for v in vertices]
y_coords = [v[1] for v in vertices] 
z_coords = [v[2] for v in vertices]
```

**Direct Edge Vector Analysis:**
1. **Edge Vector Collection**: Collect all edge vectors from the crystal vertices
2. **Main Axis Identification**: Find the direction with strongest edge alignment
3. **Azimuth Calculation**: `azimuth = atan2(main_axis[2], main_axis[0])`
4. **Elevation Calculation**: `elevation = atan2(main_axis[1], sqrt(main_axis[0]² + main_axis[2]²))`

**PCA Analysis:**
1. **Covariance Matrix**: Calculate covariance matrix from vertex distribution
2. **Principal Components**: Find eigenvectors of the covariance matrix
3. **Azimuth Calculation**: `azimuth = atan2(2 * xz_cov, xx_var - zz_var) / 2`
4. **Elevation Calculation**: `elevation = atan2(2 * xy_cov, xx_var - yy_var) / 2`

**Angle Normalization:**
- **Azimuth**: Normalized to 0-180° (opposite directions grouped together)
- **Elevation**: Normalized to 0-360° (0° and 360° grouped together)
- **Rounding**: Angles rounded to 1 decimal place to avoid floating-point precision issues

### Visualization Tool

The `plot_scanner_with_crystals.py` script provides comprehensive visualization of the crystal geometry:

**Features:**
- **Automatic CSV Detection**: Finds and uses the correct CSV file automatically
- **3D Crystal Representation**: Shows crystals as oriented sticks (20mm length)
- **Multiple View Angles**: Top (XZ), Side (XY), and Front (YZ) projections
- **Orientation Grouping**: Groups crystals by azimuth angle for pattern analysis
- **Debug Views**: Single crystal per group for detailed inspection

**Usage:**
```bash
cd output/analysis
python3 plot_scanner_with_crystals.py
```

**Output Files:**
- `scanner_with_crystals.png` - Main scanner visualization with crystal orientations
- `all_orientation_groups_combined.png` - Separate plots for each orientation group
- `all_orientation_groups_superimposed.png` - All groups overlaid on same plots
- `debug_single_crystals_per_group.png` - Debug view with one crystal per group

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
│   └── analysis/               # Analysis results and visualizations
│       ├── plot_scanner_with_crystals.py    # Main visualization script
│       ├── lyso_crystal_centers_3d_angles_*.csv  # Crystal data files
│       ├── mother.gdml         # Generated GDML file
│       ├── Volumes/            # Individual volume GDML files
│       └── *.png               # Visualization images
├── docs/                        # Documentation
│   └── Documents/              # User manual and guides
├── examples/                    # Example files
└── build/                       # Build artifacts
```

## Files Description
* `src/GUIMeshCLI.py` - Main source code for command line interface
* `src/material_mappings.json` - JSON configuration file defining material assignment rules
* `docs/Documents/` - Folder with "GUIMesh User Manual.pdf", a guide on how to run GUIMesh
* `libs/GUIMeshLibs/` - folder containing libraries used in GUIMesh
* `data/Materials/` - folder which should be used to save materials in a database
* `data/STEPfiles/` - folder with STEP geometries used in all tests
* `output/gdml/` - folder for the gdml output
* `COPYING.txt` - License disclosure

## License  
Licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

See the `COPYING` file for license details.
