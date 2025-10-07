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
- [World Size Configuration](#world-size-configuration)
  - [Automatic World Size Calculation](#automatic-world-size-calculation)
  - [Manual World Size Setting](#manual-world-size-setting)
  - [World Size Options](#world-size-options)
  - [Example Output](#example-output)
- [Material Assignment](#material-assignment)
  - [How Material Assignment Works](#how-material-assignment-works)
  - [Material Mappings Configuration](#material-mappings-configuration)
  - [Material Assignment Examples](#material-assignment-examples)
  - [Customizing Material Mappings](#customizing-material-mappings)
  - [Material Assignment Process](#material-assignment-process)
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

## World Size Configuration

The system automatically calculates the world size based on the geometry's bounding box, but you can also set it manually for specific simulation requirements.

### Automatic World Size Calculation

By default, the system automatically calculates the world size:

```bash
# Automatic world size (recommended)
python3 src/GUIMeshCLI.py \
  --step "data/STEPfiles/ring_radial_12_axial_1.step" \
  --load-material "data/Materials/LYSO.txt" \
  --assign-materials \
  --output-dir output/gdml/
```

The system will:
1. Analyze the geometry's bounding box
2. Add a 10% margin for safety
3. Display the calculated world dimensions
4. Use these dimensions in the generated GDML files

### Manual World Size Setting

For specific simulation requirements, you can set custom world dimensions:

```bash
# Set custom world size (in meters)
python3 src/GUIMeshCLI.py \
  --step "data/STEPfiles/ring_radial_12_axial_1.step" \
  --load-material "data/Materials/LYSO.txt" \
  --assign-materials \
  --world-size 1.0 1.0 1.0 \
  --output-dir output/gdml/
```

### World Size Options

- **Automatic**: `--world-size auto` (default) - Calculates based on geometry
- **Custom**: `--world-size <x> <y> <z>` - Set specific dimensions in meters
- **Cubic**: `--world-size 2.0` - Creates a 2m × 2m × 2m cubic world

### Example Output

```
=== Geometry Analysis ===
Bounding box: 366.8mm x 380.0mm x 366.8mm
Center: (0.0, 150.0, 0.0) mm
Calculated world size: 0.51m x 0.53m x 0.51m
World dimensions automatically set to: 0.51m x 0.53m x 0.51m
```

## Material Assignment

The system automatically assigns materials to volumes based on their names using pattern matching rules defined in `src/material_mappings.json`. This allows for flexible and customizable material assignment without modifying the code.

### How Material Assignment Works

1. **Volume Name Analysis**: The system examines each volume's name for specific keywords
2. **Pattern Matching**: Keywords are matched against the material mappings configuration
3. **Material Assignment**: The corresponding Geant4 material is assigned to the volume
4. **Custom Material Loading**: Materials marked as `requires_custom: true` are loaded from external files

### Material Mappings Configuration

The material assignment rules are defined in `src/material_mappings.json`:

```json
{
  "material_mappings": {
    "lyso": {
      "material": "LYSO",
      "description": "Custom LYSO scintillator material",
      "requires_custom": true
    },
    "sipm": {
      "material": "G4_Si",
      "description": "Pure silicon for Silicon Photomultiplier",
      "requires_custom": false
    },
    "pcb": {
      "material": "G4_POLYETHYLENE",
      "description": "PCB material (fiberglass/epoxy composite approximation)",
      "requires_custom": false
    },
    "aluminum": {
      "material": "G4_Al",
      "description": "Aluminum material",
      "requires_custom": false
    }
  },
  "fallback_material": {
    "material": "G4_Si",
    "description": "Default fallback material",
    "requires_custom": false
  },
  "version": "1.0",
  "description": "Material assignment rules for GUIMeshCLI"
}
```

### Material Assignment Examples

**Volume Name Patterns:**
- `_detector_lyso_*` → *image.png*LYSO** (custom material, requires `--load-material`)
- `sipm_si*` → **G4_Si** (pure silicon)
- `dmod-base_al*` → **G4_Al** (aluminum)
- `pcb-sipm_pcb*` → **G4_POLYETHYLENE** (PCB material)
- `unit-cover_plastic*` → **G4_POLYETHYLENE** (plastic)

**Custom Material Loading:**
```bash
# Load custom LYSO material properties
python3 src/GUIMeshCLI.py \
  --step "data/STEPfiles/ring_radial_12_axial_1.step" \
  --load-material "data/Materials/LYSO.txt" \
  --assign-materials \
  --output-dir output/gdml/
```

### Customizing Material Mappings

You can customize material assignments by editing `material_mappings.json`:

**Adding New Materials:**
```json
{
  "material_mappings": {
    "tungsten": {
      "material": "G4_W",
      "description": "Tungsten material",
      "requires_custom": false
    },
    "lead": {
      "material": "G4_Pb",
      "description": "Lead shielding material",
      "requires_custom": false
    }
  }
}
```

**Custom Material Properties:**
For materials with `"requires_custom": true`, create a material file (e.g., `data/Materials/CUSTOM_MATERIAL.txt`) with Geant4 material definitions and load it using `--load-material`.

### Material Assignment Process

1. **Volume Scanning**: System scans all volumes in the STEP file
2. **Name Pattern Matching**: Volume names are checked against material mappings
3. **Material Assignment**: Matching volumes are assigned the corresponding Geant4 material
4. **Custom Material Loading**: Custom materials are loaded from external files
5. **GDML Generation**: Materials are included in the generated GDML files

**Assignment Summary Example:**
```
Material assignments summary:
  LYSO: 1728 volumes
  G4_Si: 336 volumes
  G4_Al: 12 volumes
  G4_POLYETHYLENE: 12 volumes
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

**Method 1: Direct Edge Vector Analysis (Default)**
- **Best for**: 8-vertex rectangular crystals
- **How it works**: Analyzes edge vectors to find the main crystal axis
- **Advantage**: More accurate for rectangular geometries

**Method 2: PCA Analysis (Alternative)**
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

**Direct Edge Vector Analysis (Default):**
1. **Edge Vector Collection**: Collect all edge vectors from the crystal vertices
```python
# Check all possible edge combinations (8 choose 2 = 28 combinations)
for i in range(len(vertices)):
    for j in range(i+1, len(vertices)):
        edge_vector = [vertices[j][k] - vertices[i][k] for k in range(3)]
        edge_length = math.sqrt(sum(v**2 for v in edge_vector))
        edge_vectors.append(edge_vector)
        edge_lengths.append(edge_length)
```

2. **Main Axis Identification**: Find the longest edge with exactly 3 parallel edges (parallelepiped property)
```python
# For each edge, count how many other edges are parallel to it
for i, edge_vec in enumerate(edge_vectors):
    edge_len = edge_lengths[i]
    if edge_len <= 0:  # Skip zero-length edges
        continue
        
    # Normalize this edge
    normalized_edge = [v / edge_len for v in edge_vec]
    
    # Count how many other edges are parallel to this direction
    parallel_count = 0
    for j, other_edge in enumerate(edge_vectors):
        if i != j and edge_lengths[j] > 0:  # Don't skip any edges, just zero-length ones
            other_normalized = [v / other_len for v in other_edge]
            # Calculate alignment (dot product)
            alignment = abs(sum(normalized_edge[k] * other_normalized[k] for k in range(3)))
            if alignment > 0.99:  # Nearly parallel (accounting for floating-point precision)
                parallel_count += 1
    
    # For a parallelepiped, we expect exactly 3 parallel edges (plus itself = 4 total)
    # Among edges with 3 parallel edges, choose the longest one
    if parallel_count == 3:
        if parallel_count > max_parallel_count or (parallel_count == max_parallel_count and edge_len > longest_edge_length):
            max_parallel_count = parallel_count
            longest_edge_length = edge_len
            main_axis_vector = normalized_edge
```

3. **Azimuth Calculation**: `azimuth = atan2(main_axis[2], main_axis[0])`
4. **Elevation Calculation**: `elevation = atan2(main_axis[1], sqrt(main_axis[0]² + main_axis[2]²))`
```python
# Calculate azimuth angle (rotation in XZ plane)
azimuth_angle = math.degrees(math.atan2(main_axis_vector[2], main_axis_vector[0]))

# Calculate elevation angle (tilt relative to XZ plane)
elevation_angle = math.degrees(math.atan2(main_axis_vector[1], 
                                        math.sqrt(main_axis_vector[0]**2 + main_axis_vector[2]**2)))
```

**PCA Analysis (Alternative):**
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
