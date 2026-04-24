#!/usr/bin/env python3


""" # Show help
python GUIMeshCLI.py --help

# Single-pass (recommended): load STEP once, assign materials, write GDML
python GUIMeshCLI.py --step STEPfiles/your.step --assign-materials --load-materials Materials/LYSO.json --output-dir gdml_output/ """

#########################################################################################################
#    GUIMeshCLI v1                                                                                      #
#    Command-line version of GUIMesh                                                                     #
#                                                                                                       #
#    Copyright (c) 2018  Marco Gui Alves Pinto mail:mgpinto11@gmail.com                                 #
#    Modified for CLI version                                                                           #
#                                                                                                       #
#    This program is free software: you can redistribute it and/or modify                               #
#    it under the terms of the GNU General Public License as published by                               #
#    the Free Software Foundation, either version 3 of the License, or                                  #
#    (at your option) any later version.                                                                #
#                                                                                                       #
#    This program is distributed in the hope that it will be useful,                                    #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of                                     #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                                      #
#    GNU General Public License for more details.                                                       #
#                                                                                                       #
#    You should have received a copy of the GNU General Public License                                  #
#    along with this program.  If not, see <https://www.gnu.org/licenses/>                              #
#                                                                                                       #
#########################################################################################################

import sys
import os
import argparse
from pathlib import Path
import time
import threading
import json

# Add FreeCAD path
#sys.path.append('/home/irene/dev/Programs/squashfs-root/usr/lib')
sys.path.append('/usr/local/bin/squashfs-root/usr/lib')
# Add PySide2 from FreeCAD's site-packages (needed for Draft module)
# Use current Python version to find the correct site-packages path
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
pyside_path = f'/usr/local/bin/squashfs-root/usr/lib/python{python_version}/site-packages'
if pyside_path not in sys.path:
    sys.path.insert(0, pyside_path)


try:
    import FreeCAD
    import Import
    import FreeCADGui
    import Draft
    import Part
except ImportError:
    print("Error: FreeCAD not found. Please ensure FreeCAD is installed and the path is correct.")
    sys.exit(1)

try:
    # Add libs directory to path for imports
    libs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
    sys.path.insert(0, libs_path)
    
    from GUIMeshLibs import Materials
    from GUIMeshLibs import Volumes
    from GUIMeshLibs import LoadOP
    from GUIMeshLibs import WriteGDML
    from GUIMeshLibs import CrystalCenters
except ImportError:
    print("Error: Could not load GUIMesh libraries. Please check if the folder libs/GUIMeshLibs exists and if the files are there.")
    sys.exit(1)

class GUIMeshCLI:
    def __init__(self):
        self.world_dimensions = [1.0, 1.0, 1.0]  # in meters
        self.world_position = [0.0, 0.0, 0.0]  # World box center position in meters
        self.list_of_objects = []
        self.Element_List = Materials.Load_Elements()
        self.Material_List = []
        self.file_status = 0
        self.verbose = False
        self.vertex_counts = []  # Track vertex counts for statistics
        self.center_geometry = False  # Flag to enable geometry centering
        self.geometry_translation = [0.0, 0.0, 0.0]  # Translation to center geometry (in mm, CAD coordinates)

    def load_materials(self, material_path):
        """Load material(s) from a file or directory
        
        Args:
            material_path: Path to a JSON material file or directory containing JSON material files
        
        Returns:
            bool: True if at least one material was loaded successfully, False otherwise
        """
        path = Path(material_path).resolve()
        
        if not path.exists():
            print(f"Error: Path '{material_path}' not found.")
            return False
        
        # If it's a directory, load all JSON files from it
        if path.is_dir():
            new_materials = Materials.Load_Materials_From_Dir(str(path))
            if new_materials == 0:
                print("No materials loaded from directory.")
                return False
        # If it's a file, load it
        elif path.is_file():
            # Check file extension
            if path.suffix.lower() != '.json':
                print(f"Error: Material file must be in JSON format (.json), got '{path.suffix}'")
                return False
            
            new_material = Materials.Load_Material_JSON(str(path))
            if new_material == 0:
                return False
            new_materials = [new_material]
        else:
            print(f"Error: '{material_path}' is neither a file nor a directory.")
            return False
        
        # Check for duplicates and add to Material_List
        loaded_count = 0
        skipped_count = 0
        for new_material in new_materials:
            # Check for duplicate names
            is_duplicate = False
            for mat in self.Material_List + self.Element_List:
                if mat.Name == new_material.Name:
                    print(f"Warning: Material '{new_material.Name}' already exists, skipping.")
                    skipped_count += 1
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                self.Material_List.append(new_material)
                loaded_count += 1
        
        if loaded_count > 0:
            if path.is_dir():
                print(f"Loaded {loaded_count} materials from {material_path}")
            else:
                print(f"Successfully loaded material '{new_materials[0].Name}'")
        if skipped_count > 0:
            print(f"Skipped {skipped_count} duplicate materials")
        
        return loaded_count > 0

    def load_step_file(self, step_file):
        """Load a STEP file and process its contents"""
        if not os.path.exists(step_file):
            print(f"Error: File {step_file} does not exist")
            return False

        if not step_file.lower().endswith(('.step', '.stp')):
            print("Error: File must be a STEP file (.step or .stp)")
            return False

        try:
            start_time = time.time()
            
            # Use LoadOP to load the STEP file (progress output is handled inside Load_STEP_File)
            list_of_objects = LoadOP.Load_STEP_File(self.file_status, self.Element_List[13], path_to_file=step_file)
            
            if list_of_objects == 0:
                print("Error: Failed to load STEP file")
                return False
            
            elapsed = time.time() - start_time
            self.list_of_objects = list_of_objects
            self.file_status = 1
            
            print(f"\n{'='*60}")
            print(f"STEP file import completed in {elapsed:.1f} seconds")
            print(f"Total volumes loaded: {len(self.list_of_objects)}")
            print(f"{'='*60}\n")
            
            # Calculate and set optimal world size
            self.auto_set_world_size()
            return True

        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return False

    def check_material_mappings_file(self, config_file="material_mappings.json"):
        """Check if material mappings file exists. Returns the full path if found, None otherwise."""
        config_path = Path(config_file)
        if config_path.exists():
            return str(config_path)

        # Try relative to script directory (src/)
        script_dir = Path(__file__).parent
        config_path = script_dir / config_file
        if config_path.exists():
            return str(config_path)
        
        return None

    def load_material_mappings(self, config_file="material_mappings.json"):
        """Load material assignment rules from JSON configuration file."""
        config_path = self.check_material_mappings_file(config_file)
        if config_path is None:
            raise FileNotFoundError(f"Material mappings file '{config_file}' not found. Please create the file or specify a valid path.")
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            print(f"Loaded material mappings from {config_path}")
            if 'description' in config:
                print(f"  {config['description']}")
            if 'version' in config:
                print(f"  Version: {config['version']}")
            
            return config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing material mappings file '{config_path}': {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Error loading material mappings from '{config_path}': {str(e)}")

    def assign_materials_from_names(self, config_file="material_mappings.json"):
        """Assign materials to volumes based on their label/name patterns using JSON configuration."""
        if not self.list_of_objects:
            print("Error: No volumes loaded to assign materials")
            return False

        # Load material mappings from JSON
        try:
            config = self.load_material_mappings(config_file)
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            print(f"ERROR: {str(e)}")
            return False
        
        mappings = config.get("material_mappings", {})
        
        if not mappings:
            print("Error: No material mappings found in configuration file.")
            return False

        def choose_material_name(label_lower: str) -> tuple:
            """Return (material_name, description, requires_custom) for a given label."""
            for pattern, mapping in mappings.items():
                if pattern in label_lower:
                    return (mapping["material"], mapping["description"], mapping.get("requires_custom", False))
            
            # No match found
            return (None, None, False)

        # Build quick lookup for available materials/elements
        name_to_material = {}
        for ele in self.Element_List:
            name_to_material[ele.Name] = ele
        for mat in self.Material_List:
            name_to_material[mat.Name] = mat

        assignments_count = {}
        custom_materials_needed = set()
        unmatched_volumes = []
        missing_materials = {}  # Track missing materials: {material_name: [volume_labels]}

        for obj in self.list_of_objects:
            label_lower = str(obj.VolumeCAD.Label).lower()
            mat_name, description, requires_custom = choose_material_name(label_lower)
            
            # Check if no pattern matched
            if mat_name is None:
                unmatched_volumes.append(obj.VolumeCAD.Label)
                continue
            
            if requires_custom:
                custom_materials_needed.add(mat_name)
            
            mat_obj = name_to_material.get(mat_name)
            if mat_obj is None:
                # Track missing materials
                if mat_name not in missing_materials:
                    missing_materials[mat_name] = []
                missing_materials[mat_name].append(obj.VolumeCAD.Label)
                continue
            obj.VolumeMaterial = mat_obj
            assignments_count[mat_name] = assignments_count.get(mat_name, 0) + 1

        if assignments_count:
            print("Material assignments summary:")
            for k, v in sorted(assignments_count.items(), key=lambda x: (-x[1], x[0])):
                print(f"  {k}: {v} volumes")
        
        # Check for missing required materials first (most critical error)
        if missing_materials:
            print(f"\nERROR: Required materials not found. {len(missing_materials)} material(s) need to be loaded:")
            for mat_name, volume_labels in sorted(missing_materials.items()):
                print(f"  - Material '{mat_name}' (required for {len(volume_labels)} volume(s))")
                # Show first few volumes that need this material
                examples = volume_labels[:5]
                for vol in examples:
                    print(f"      • {vol}")
                if len(volume_labels) > 5:
                    print(f"      ... and {len(volume_labels) - 5} more")
            print(f"\nTo fix this:")
            print(f"  1. Load the missing material(s) using --load-materials")
            print(f"     Example: --load-materials data/Materials/{list(missing_materials.keys())[0]}.json")
            if len(missing_materials) > 1:
                print(f"     (You may need multiple --load-materials flags for multiple materials)")
            return False
        
        if unmatched_volumes:
            print(f"\n ERROR: {len(unmatched_volumes)} volumes have no matching material pattern:")
            # Show first few examples
            examples = unmatched_volumes[:10]
            for example in examples:
                print(f"  - {example}")
            if len(unmatched_volumes) > 10:
                print(f"  ... and {len(unmatched_volumes) - 10} more")
            print(f"\nTo fix this:")
            print(f"  1. Add patterns to the material mappings file for these volume names")
            print(f"  2. Check that volume names match the patterns in the material mappings file")
            return False
        
        if not assignments_count:
            print("No materials were assigned.")
            return False
        
        return True

    def dump_part_list(self, output_file):
        """Write all volume labels from the loaded STEP file to a plain-text file, one per line."""
        if not self.list_of_objects:
            print("Error: No volumes loaded")
            return False

        labels = [str(obj.VolumeCAD.Label) for obj in self.list_of_objects]

        try:
            with open(output_file, 'w') as f:
                for label in labels:
                    f.write(label + '\n')
            print(f"Wrote {len(labels)} part labels to {output_file}")
            return True
        except Exception as e:
            print(f"Error writing part list: {str(e)}")
            return False

    def extract_crystal_centers(self, output_file=None):
        """Extract center coordinates of LYSO crystals only and optionally save to CSV"""
        # Apply translation if geometry centering is enabled
        translation = self.geometry_translation if self.center_geometry else None
        crystal_centers, success = CrystalCenters.extract_crystal_centers(
            list_of_objects=self.list_of_objects,
            verbose=self.verbose,
            output_file=output_file,
            output_dir=getattr(self, 'output_dir', None),
            vertex_counts=self.vertex_counts,
            translation=translation
        )
        
        return success

    def auto_set_world_size(self):
        """Calculate optimal world size based on geometry bounding box and ask for confirmation"""
        if not self.list_of_objects:
            return
        
        try:
            # Calculate bounding box for all loaded objects (in mm, CAD coordinates)
            min_x = min_y = min_z = float('inf')
            max_x = max_y = max_z = float('-inf')
            
            for obj in self.list_of_objects:
                try:
                    bbox = obj.VolumeCAD.Shape.BoundBox
                    min_x = min(min_x, bbox.XMin)
                    min_y = min(min_y, bbox.YMin)
                    min_z = min(min_z, bbox.ZMin)
                    max_x = max(max_x, bbox.XMax)
                    max_y = max(max_y, bbox.YMax)
                    max_z = max(max_z, bbox.ZMax)
                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Could not process {obj.VolumeCAD.Label}: {str(e)}")
                    continue
            
            # Calculate dimensions
            width = max_x - min_x   # X extent of geometry (mm)
            height = max_y - min_y  # Y extent of geometry (mm)
            depth = max_z - min_z   # Z extent of geometry (mm)
            
            # Calculate geometry center (in mm)
            center_x = min_x + width / 2.0
            center_y = min_y + height / 2.0
            center_z = min_z + depth / 2.0

            if self.center_geometry:
                # CENTERING MODE: Translate geometry to center it at origin
                # Translation is negative of center to move center to (0,0,0)
                self.geometry_translation = [-center_x, -center_y, -center_z]  # mm
                
                # After translation, geometry will be centered at origin
                # World size is just the bounding box dimensions + margin
                margin = 0.05  # 5% margin
                world_x = width * (1.0 + margin) / 1000.0  # meters
                world_y = height * (1.0 + margin) / 1000.0  # meters
                world_z = depth * (1.0 + margin) / 1000.0  # meters
                
                # World position will be set to translation (in meters) when writing GDML
                # This applies the translation to center the geometry
                
                print(f"\n=== Geometry Analysis (CENTERING MODE) ===")
                print(f"Bounding box: {width:.1f}mm x {height:.1f}mm x {depth:.1f}mm")
                print(f"Extents from origin: X [{min_x:.1f}, {max_x:.1f}] mm, "
                      f"Y [{min_y:.1f}, {max_y:.1f}] mm, "
                      f"Z [{min_z:.1f}, {max_z:.1f}] mm")
                print(f"Original geometry center: ({center_x:.1f}, {center_y:.1f}, {center_z:.1f}) mm")
                print(f"Translation to center: ({self.geometry_translation[0]:.1f}, "
                      f"{self.geometry_translation[1]:.1f}, {self.geometry_translation[2]:.1f}) mm")
                print(f"World size: {world_x:.2f}m x {world_y:.2f}m x {world_z:.2f}m")
                print("World position: will be set to translation (geometry centered at origin)")
                print("=" * 30)
            else:
                # NON-CENTERING MODE: Preserve CAD coordinates
                # IMPORTANT:
                # The world volume is centered at the CAD origin (0, 0, 0) to preserve
                # the original coordinates, but the geometry itself might NOT be
                # centered at the origin. If we only use the width/height/depth,
                # a geometry that lives mostly on one side of the origin could stick
                # out of the world box.
                #
                # To avoid that, we compute the maximum distance from the origin
                # to the geometry in each axis and size the world so that the
                # half‑length is large enough to contain the most distant point
                # (plus a margin).
                #
                # Example: geometry Y goes from 0 mm to 600 mm.
                #   - height = 600 mm
                #   - max_extent_y = max(|0|, |600|) = 600 mm
                #   - world half‑length in Y ≥ max_extent_y * (1 + margin)
                #   - world full length in Y = 2 * half‑length
                #
                # This keeps the world centered at 0 while still containing
                # geometries that are not centered around the origin.

                max_extent_x = max(abs(min_x), abs(max_x))  # mm
                max_extent_y = max(abs(min_y), abs(max_y))  # mm
                max_extent_z = max(abs(min_z), abs(max_z))  # mm

                # World size: large enough half‑length to contain the furthest
                # point from the origin, plus a relative margin.
                margin = 0.05  # 5% margin on the half‑length
                half_x = max_extent_x * (1.0 + margin)  # mm
                half_y = max_extent_y * (1.0 + margin)  # mm
                half_z = max_extent_z * (1.0 + margin)  # mm

                # Convert to full lengths in meters for GDML world box (G4Box x,y,z are full lengths)
                world_x = 2.0 * half_x / 1000.0
                world_y = 2.0 * half_y / 1000.0
                world_z = 2.0 * half_z / 1000.0
                
                # Reset translation (no centering)
                self.geometry_translation = [0.0, 0.0, 0.0]
                
                print(f"\n=== Geometry Analysis ===")
                print(f"Bounding box: {width:.1f}mm x {height:.1f}mm x {depth:.1f}mm")
                print(f"Extents from origin: X [{min_x:.1f}, {max_x:.1f}] mm, "
                      f"Y [{min_y:.1f}, {max_y:.1f}] mm, "
                      f"Z [{min_z:.1f}, {max_z:.1f}] mm")
                print(f"Geometry center: ({center_x:.1f}, {center_y:.1f}, {center_z:.1f}) mm")
                print(f"World size: {world_x:.2f}m x {world_y:.2f}m x {world_z:.2f}m")
                print("World position: (0.000, 0.000, 0.000) m (CAD origin preserved)")
            
            # Set the calculated world size
            self.world_dimensions = [world_x, world_y, world_z]
            print(f"World dimensions automatically set to: {world_x:.2f}m x {world_y:.2f}m x {world_z:.2f}m")
            print("=" * 30)
            
        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not calculate world size: {str(e)}")
            print("Using default world size: 1.0m x 1.0m x 1.0m")

    def set_world_size(self, x, y, z):
        """Set the world dimensions"""
        try:
            x = float(x)
            y = float(y)
            z = float(z)
            if x <= 0 or y <= 0 or z <= 0:
                print("Error: Dimensions must be positive numbers")
                return False
            self.world_dimensions = [x, y, z]
            print(f"World dimensions set to: {x}m x {y}m x {z}m")
            return True
        except ValueError:
            print("Error: Dimensions must be valid numbers")
            return False

    def write_gdml(self, output_dir):
        """Write GDML files"""
        if not self.list_of_objects:
            print("Error: No volumes to mesh")
            return False

        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            volumes_path = output_path / "Volumes"
            volumes_path.mkdir(exist_ok=True)

            # Apply translation to world_position if centering is enabled
            # WriteGDML.CreateMother uses -world_pos for geometry_offset, so we need to negate
            # Convert from mm to meters
            if self.center_geometry:
                world_pos = [-self.geometry_translation[0] / 1000.0,
                           -self.geometry_translation[1] / 1000.0,
                           -self.geometry_translation[2] / 1000.0]
            else:
                world_pos = self.world_position

            WriteGDML.CreateMother(str(output_path), self.list_of_objects, self.world_dimensions, world_pos)
            
            for i, obj in enumerate(self.list_of_objects, 1):
                if obj.VolumeGDMLoption == 1:
                    WriteGDML.CreateGDML(obj, i, str(output_path))

            # Normalize base volumes at the end (keeping original names)
            WriteGDML.normalize_base_volumes(str(volumes_path))

            # Save transformation info to JSON file
            if self.center_geometry:
                # Note: world_pos is negated version of translation (due to WriteGDML logic)
                # The actual translation applied is geometry_translation
                transform_info = {
                    "geometry_centered": True,
                    "translation_mm": {
                        "x": self.geometry_translation[0],
                        "y": self.geometry_translation[1],
                        "z": self.geometry_translation[2]
                    },
                    "translation_m": {
                        "x": self.geometry_translation[0] / 1000.0,
                        "y": self.geometry_translation[1] / 1000.0,
                        "z": self.geometry_translation[2] / 1000.0
                    },
                    "description": "Geometry has been translated to center the bounding box at (0, 0, 0). "
                                 "Crystal center coordinates in output files are in the transformed (centered) coordinate system. "
                                 "To convert back to original CAD coordinates, subtract the translation values (translation_mm)."
                }
            else:
                transform_info = {
                    "geometry_centered": False,
                    "translation_mm": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "translation_m": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "description": "Geometry uses original CAD coordinates (no translation applied)."
                }
            
            transform_file = output_path / "geometry_transform.json"
            with open(transform_file, 'w') as f:
                json.dump(transform_info, f, indent=2)
            print(f"Transformation info saved to {transform_file}")

            print(f"GDML files written to {output_dir}")
            return True

        except Exception as e:
            print(f"Error writing GDML files: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='GUIMeshCLI - Command line interface for converting STEP files to GDML')
    
    parser.add_argument('--step', help='Input STEP file path')
    parser.add_argument('--world-size', nargs=3, type=float, metavar=('X', 'Y', 'Z'),
                      help='World dimensions in meters (X Y Z)')
    parser.add_argument('--output-dir', help='Output directory for GDML files')
    parser.add_argument('--load-materials', action='append', help='Load material(s) from a JSON file or directory containing JSON files. Can be used multiple times.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging and progress messages')
    parser.add_argument('--assign-materials', nargs='?', const='material_mappings.json', default=None, help='Assign materials based on volume name patterns. Optionally specify JSON config file (default: material_mappings.json)')
    parser.add_argument('--extract-centers', nargs='?', const=True, help='Extract crystal center coordinates and save to CSV file. Optionally specify output filename.')
    parser.add_argument('--center-geometry', action='store_true', help='Translate and center geometry at origin (0,0,0) by centering the bounding box. This minimizes world size and transforms crystal coordinates.')
    parser.add_argument('--dump-parts', metavar='OUTPUT_FILE', help='Load STEP file and write all part labels to a plain-text file (one per line), then exit. Useful for discovering part names before writing material_mappings.json.')
    
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    mesh = GUIMeshCLI()
    mesh.verbose = bool(args.verbose)
    mesh.center_geometry = bool(args.center_geometry)
    
    # Set output directory for files
    mesh.output_dir = args.output_dir

    # --dump-parts requires a STEP file
    if args.dump_parts and not args.step:
        print("Error: --dump-parts requires --step")
        return

    # Check material mappings file BEFORE loading STEP file (if --assign-materials is used)
    if args.assign_materials:
        config_file = args.assign_materials
        if mesh.check_material_mappings_file(config_file) is None:
            print(f"   ERROR: Material mappings file '{config_file}' not found.")
            print(f"   Please create the file or specify a valid path.")
            print(f"   The file should be located in the current directory or in src/ directory.")
            return

    if args.step:
        if not mesh.load_step_file(args.step):
            return

    if args.dump_parts:
        mesh.dump_part_list(args.dump_parts)
        return

    if args.world_size:
        if not mesh.set_world_size(*args.world_size):
            return

    if args.load_materials:
        for material_path in args.load_materials:
            if not mesh.load_materials(material_path):
                return

    # Material assignment based on volume name patterns
    if args.assign_materials:
        if not mesh.assign_materials_from_names(args.assign_materials):
            return

    # Extract crystal centers if requested
    if args.extract_centers:
        if not mesh.extract_crystal_centers(args.extract_centers):
            return

    if args.output_dir:
        if not mesh.write_gdml(args.output_dir):
            return

if __name__ == '__main__':
    main() 




