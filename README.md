
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
  - [Detailed Implementation](#detailed-implementation)
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
- **Debug Views**: Single crystal per group for detailed inspection

**Output Files:**
- `scanner_with_crystals.png` - Main scanner visualization
- `all_orientation_groups_combined.png` - Separate plots for each orientation group
- `all_orientation_groups_superimposed.png` - All groups overlaid
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

#### Detailed Implementation

#### 1. **Geometric Data Extraction**
```python
# Get tessellated vertices from the 3D crystal shape
triangles = obj.VolumeCAD.Shape.tessellate(precision)
vertices = triangles[0]  # All 3D vertices of the crystal

# Extract coordinates
x_coords = [v[0] for v in vertices]
y_coords = [v[1] for v in vertices] 
z_coords = [v[2] for v in vertices]
```

#### 2. **Azimuth Angle Calculation (0° to 360°)**
The azimuth angle represents the **horizontal rotation in the XZ plane**:
```python
# Calculate covariance matrix for XZ plane
xx_var = sum((x - x_mean)**2 for x in x_coords) / len(x_coords)
zz_var = sum((z - z_mean)**2 for z in z_coords) / len(z_coords)
xz_cov = sum((x - x_mean) * (z - z_mean) for x, z in zip(x_coords, z_coords)) / len(x_coords)

# Calculate azimuth angle using principal component analysis
azimuth_angle = math.degrees(math.atan2(2 * xz_cov, xx_var - zz_var) / 2)
```

**Azimuth Angle Interpretation:**
- **0°**: Points along **+X axis**
- **90°**: Points along **+Z axis**
- **180°**: Points along **-X axis**
- **270°**: Points along **-Z axis**

#### 3. **Elevation Angle Calculation (0° to 360°)**
The elevation angle represents the **tilt of the crystal normal relative to the XZ plane**:
```python
# Calculate covariance matrix for XY plane
yy_var = sum((y - y_mean)**2 for y in y_coords) / len(y_coords)
xy_cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_coords, y_coords)) / len(x_coords)

# Calculate elevation angle
elevation_angle = math.degrees(math.atan2(2 * xy_cov, xx_var - yy_var) / 2)
```

**Elevation Angle Interpretation:**
- **0° or 360°**: Crystal normal is **parallel to XZ plane** (horizontal)
- **90°**: Crystal normal is **perpendicular to XZ plane** (vertical, pointing up)
- **270°**: Crystal normal is **perpendicular to XZ plane** (vertical, pointing down)

### How Crystals Are Visualized

The visualization system creates **oriented sticks** representing crystal orientations in three orthogonal views:

#### 1. **Top View (XZ plane)** - Looking down from above
```python
# Calculate stick endpoints in XZ plane
dx = (stick_length/2) * math.cos(azimuth_rad)
dz = (stick_length/2) * math.sin(azimuth_rad)
```
- Shows horizontal crystal orientations
- Azimuth 270° crystals appear as **horizontal lines** pointing along -Z axis

#### 2. **Side View (XY plane)** - Looking from the side
```python
# Calculate stick endpoints in XY plane using both angles
dx = (stick_length/2) * math.cos(azimuth_rad) * math.cos(elevation_rad)
dy = (stick_length/2) * math.sin(elevation_rad)
```
- Shows vertical crystal orientations
- Azimuth 270° crystals with elevation 0° appear as **points** (horizontal crystals)
- Azimuth 270° crystals with elevation 90° appear as **vertical lines** (vertical crystals)

#### 3. **Front View (YZ plane)** - Looking from the front
```python
# Calculate stick endpoints in YZ plane using both angles
dz = (stick_length/2) * math.sin(azimuth_rad) * math.cos(elevation_rad)
dy = (stick_length/2) * math.sin(elevation_rad)
```
- Shows crystal orientations in the YZ plane
- Combines both azimuth and elevation information

### **Expected Results for Ring Scanners**

For a **12-sided ring scanner**:
- **6 azimuth groups**: 0°, 30°, 60°, 270°, 300°, 330° (30° intervals)
- **288 crystals per group** (1728 total ÷ 6 groups)
- **Mixed elevation angles**: Some horizontal (0°/360°), some vertical (90°/270°)

This creates a **modular scanner design** where crystals are organized in specific angular patterns, not all pointing radially outward.

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

## Crystal Center Extraction and Analysis

GUIMeshCLI can extract the center coordinates of LYSO crystals from your geometry and provide detailed analysis tools for visualization and pattern detection.

### How Crystal Centers are Found

The crystal center extraction process:

1. **Material Filtering**: Only volumes with material name "LYSO" are processed
2. **Bounding Box Calculation**: For each LYSO crystal, the geometric bounding box is calculated using FreeCAD's `Shape.BoundBox` property
3. **Center Calculation**: The center coordinates are computed as the midpoint of the bounding box
4. **CSV Export**: Results are saved to a CSV with columns: `crystal_id`, `volume_name`, `center_x`, `center_y`, `center_z`, `orientation_angle`

**Core Implementation** (from `src/GUIMeshCLI.py`):

```python
def extract_crystal_centers(self, output_file=None):
    """Extract center coordinates of LYSO crystals only and optionally save to CSV"""
    crystal_centers = []
    lyso_count = 0
    
    for i, obj in enumerate(self.list_of_objects):
        try:
            # Get material name
            material_name = obj.VolumeMaterial.Name if obj.VolumeMaterial else "Unknown"
            
            # Only process LYSO crystals
            if material_name != "LYSO":
                continue
            
            lyso_count += 1
            
            # Get the bounding box of the volume
            bbox = obj.VolumeCAD.Shape.BoundBox
            
            # Calculate center coordinates
            center_x = (bbox.XMin + bbox.XMax) / 2.0
            center_y = (bbox.YMin + bbox.YMax) / 2.0
            center_z = (bbox.ZMin + bbox.ZMax) / 2.0
            
            crystal_info = {
                'crystal_id': lyso_count,
                'center_x': center_x,
                'center_y': center_y,
                'center_z': center_z
            }
            
            crystal_centers.append(crystal_info)
            
        except Exception as e:
            print(f"Warning: Could not process volume {i+1}: {str(e)}")
            continue
    
    # Save to CSV if requested
    if output_file:
        import csv
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['crystal_id', 'center_x', 'center_y', 'center_z']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for crystal in crystal_centers:
                writer.writerow(crystal)
        
        print(f"Crystal centers saved to: {output_file}")
```

**Key Steps**:
- **Material Filtering**: `if material_name != "LYSO": continue`
- **Bounding Box**: `bbox = obj.VolumeCAD.Shape.BoundBox`
- **Center Calculation**: `center_x = (bbox.XMin + bbox.XMax) / 2.0`
- **Crystal ID Extraction**: Uses regex patterns to extract numbers from volume names
- **Duplicate Detection**: Stops execution if duplicate or missing crystal numbers found
- **CSV Export**: Uses Python's `csv.DictWriter` for clean output

**Error Handling**:
- **Missing Numbers**: Stops if volume name contains no extractable number (except `_detector_lyso_`)
- **Duplicate Numbers**: Stops if same crystal ID appears in multiple volume names
- **Clear Error Messages**: Provides specific guidance on how to fix naming issues

### Extracting Crystal Centers

Use the `--extract-centers` flag to extract crystal coordinates:

```bash
python3 src/GUIMeshCLI.py \
  --step "data/STEPfiles/ring_radial_12_axial_1.step" \
  --load-material "data/Materials/LYSO.txt" \
  --assign-materials \
  --extract-centers output/analysis/lyso_crystal_centers.csv \
  --output-dir output/analysis/
```

This will:
- Load the STEP file and assign materials
- Extract center coordinates and orientations of all LYSO crystals
- Save a CSV with crystal ID, volume name, coordinates, and orientation angles
- Generate GDML output files

### Analysis Tools

The analysis tools are located in `output/analysis/` and provide both visual and statistical analysis:

#### 3D Visualization
```bash
cd output/analysis
python plot_crystal_centers_simple.py lyso_crystal_centers.csv
```

This generates:
- **`crystal_centers_overview.png`**: 3D scatter plot with XY/XZ/YZ projections
- **`crystal_centers_layers.png`**: Layer-by-layer analysis showing crystal distribution

#### Pattern Analysis
```bash
cd output/analysis
python analyze_crystal_patterns.py lyso_crystal_centers.csv
```

This provides:
- **Distribution Statistics**: X/Y/Z ranges and spans
- **Layer Analysis**: Number of layers and crystals per layer
- **Pattern Detection**: Regular spacing analysis
- **Geometry Summary**: Detector type and dimensions

### Example Output

**CSV Format** (`lyso_crystal_centers.csv`):
```csv
crystal_id,volume_name,center_x,center_y,center_z,orientation_angle
0,_detector_lyso_,70.0138864196027,8.499999999999568,125.41760851410854,60.83
1,_detector_lyso_001,66.41988099389741,24.999999999998998,127.49260851410853,62.48
2,_detector_lyso_002,70.0138864196027,19.499999999999197,125.41760851410854,60.83
...
```

**Analysis Results**:
```
=== Crystal Distribution Statistics ===
Total crystals: 1728
X range: -143.62 to 143.62 mm (span: 287.24 mm)
Y range: 3.00 to 47.00 mm (span: 44.00 mm)
Z range: -143.62 to 143.62 mm (span: 287.24 mm)

=== Layer Analysis ===
Found 9 Y layers:
  Layer 1: Y = 3.0 mm, 192 crystals
  Layer 2: Y = 8.5 mm, 192 crystals
  ...
```

### Use Cases

- **Geometry Verification**: Visual inspection of crystal placement
- **Pattern Analysis**: Detection of regular arrays and spacing
- **Quality Control**: Verification of detector geometry
- **Simulation Setup**: Coordinate data for Geant4 simulations

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

### Key Features

- **Automatic CSV Detection**: The visualization script automatically finds and uses the correct CSV file
- **Clean Output Structure**: All files are organized in the `output/analysis/` directory
- **Two Analysis Methods**: Choose between Direct Edge Vector (recommended) or PCA analysis
- **Complete 3D Orientation**: Extracts both azimuth and elevation angles for full crystal orientation
- **Multiple Visualizations**: Generates comprehensive plots for analysis and debugging

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

