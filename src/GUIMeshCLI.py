#!/usr/bin/env python3


""" # Show help
python GUIMeshCLI.py --help

# Single-pass (recommended): load STEP once, assign materials, write GDML
python GUIMeshCLI.py --step STEPfiles/your.step --assign-materials --load-material Materials/LYSO.txt --output-dir gdml_output/

# Optional: save properties to CSV (for auditing)
python GUIMeshCLI.py --step STEPfiles/your.step --assign-materials --save-props props.csv --output-dir gdml_output/ """

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
    from GUIMeshLibs import MaterialManager
    from GUIMeshLibs import WriteGDML
except ImportError:
    print("Error: Could not load GUIMesh libraries. Please check if the folder libs/GUIMeshLibs exists and if the files are there.")
    sys.exit(1)

class GUIMeshCLI:
    def __init__(self):
        self.world_dimensions = [1.0, 1.0, 1.0]  # in meters
        self.list_of_objects = []
        self.Element_List = Materials.Load_Elements()
        self.Material_List = []
        self.file_status = 0
        self.verbose = False

    def load_custom_material(self, material_file):
        """Load a custom material from a file"""
        if not os.path.exists(material_file):
            print(f"Error: Material file {material_file} not found.")
            return False

        new_material = Materials.Load_Material(material_file)
        if new_material == 0:
            print(f"Error: Could not load material from {material_file}.")
            return False

        # Check for duplicate names
        for mat in self.Material_List + self.Element_List:
            if mat.Name == new_material.Name:
                print(f"Error: Material name '{new_material.Name}' already exists.")
                return False
        
        self.Material_List.append(new_material)
        print(f"Successfully loaded material '{new_material.Name}'")
        return True

    def load_step_file(self, step_file):
        """Load a STEP file and process its contents"""
        if not os.path.exists(step_file):
            print(f"Error: File {step_file} does not exist")
            return False

        if not step_file.lower().endswith(('.step', '.stp')):
            print("Error: File must be a STEP file (.step or .stp)")
            return False

        try:
            if self.verbose:
                print(f"Starting STEP import: {step_file}")
                print("Note: Large STEP files may take several minutes to import...")
            start_time = time.time()
            
            if self.file_status:
                FreeCAD.closeDocument("Unnamed")
                print("Previous document closed")

            FreeCAD.newDocument("Unnamed")
            FreeCAD.setActiveDocument("Unnamed")
            
            # This is the blocking call - no way to show progress during import
            Import.insert(step_file, "Unnamed")
            
            elapsed = time.time() - start_time
            print(f"File read successfully in {elapsed:.1f}s")
            
            self.list_of_objects = []
            all_objs = FreeCAD.ActiveDocument.Objects
            part_objs = [obj for obj in all_objs if obj.TypeId == "Part::Feature"]
            total_parts = len(part_objs)
            if self.verbose:
                print(f"Found {total_parts} solid parts in {len(all_objs)} total objects")
            for idx, obj in enumerate(part_objs, start=1):
                try:
                    obj.Label = obj.Label.replace(" ", "_")
                    obj.Label = obj.Label.replace(".", "_")
                    obj.Label = obj.Label.replace("---", "_")
                    self.list_of_objects.append(Volumes.Volume(obj, self.Element_List[13], 0.1, 1))
                    #print(f"Added object: {obj.Label}")
                except Exception as e:
                    if self.verbose:
                        print(f"Error processing part {idx}: {obj.Label} - {str(e)}")
                    continue
                if self.verbose and (idx % 500 == 0 or idx == total_parts):
                    print(f"Processed {idx}/{total_parts} parts")
            
            self.file_status = 1
            print(f"Loaded {len(self.list_of_objects)} objects from STEP file")
            
            # Calculate and set optimal world size
            self.auto_set_world_size()
            return True

        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return False

    def load_material_mappings(self, config_file="material_mappings.json"):
        """Load material assignment rules from JSON configuration file."""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                # Try relative to script directory (src/)
                script_dir = Path(__file__).parent
                config_path = script_dir / config_file
                if not config_path.exists():
                    print(f"Warning: Material mappings file '{config_file}' not found. Using default mappings.")
                    return self.get_default_mappings()
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            print(f"Loaded material mappings from {config_path}")
            if 'description' in config:
                print(f"  {config['description']}")
            if 'version' in config:
                print(f"  Version: {config['version']}")
            
            return config
            
        except Exception as e:
            print(f"Warning: Error loading material mappings: {str(e)}. Using default mappings.")
            return self.get_default_mappings()

    def get_default_mappings(self):
        """Fallback default material mappings if JSON file is not available."""
        return {
            "material_mappings": {
                "lyso": {"material": "LYSO", "description": "Custom LYSO scintillator material", "requires_custom": True},
                "sipm": {"material": "G4_Si", "description": "Pure silicon for SiPM", "requires_custom": False},
                "pcb": {"material": "G4_POLYETHYLENE", "description": "PCB material", "requires_custom": False},
                "plastic": {"material": "G4_POLYETHYLENE", "description": "Plastic material", "requires_custom": False},
                "aluminum": {"material": "G4_Al", "description": "Aluminum material", "requires_custom": False},
                "al": {"material": "G4_Al", "description": "Aluminum material (short)", "requires_custom": False}
            },
            "fallback_material": {"material": "G4_Si", "description": "Default fallback material", "requires_custom": False}
        }

    def assign_materials_from_names(self, config_file="material_mappings.json"):
        """Assign materials to volumes based on their label/name patterns using JSON configuration."""
        if not self.list_of_objects:
            print("Error: No volumes loaded to assign materials")
            return False

        # Load material mappings from JSON
        config = self.load_material_mappings(config_file)
        mappings = config.get("material_mappings", {})
        fallback = config.get("fallback_material", {"material": "G4_Si"})

        def choose_material_name(label_lower: str) -> tuple:
            """Return (material_name, description, requires_custom) for a given label."""
            for pattern, mapping in mappings.items():
                if pattern in label_lower:
                    return (mapping["material"], mapping["description"], mapping.get("requires_custom", False))
            
            # Fallback
            return (fallback["material"], fallback["description"], fallback.get("requires_custom", False))

        # Build quick lookup for available materials/elements
        name_to_material = {}
        for ele in self.Element_List:
            name_to_material[ele.Name] = ele
        for mat in self.Material_List:
            name_to_material[mat.Name] = mat

        assignments_count = {}
        custom_materials_needed = set()
        fallback_used = set()

        for obj in self.list_of_objects:
            label_lower = str(obj.VolumeCAD.Label).lower()
            mat_name, description, requires_custom = choose_material_name(label_lower)
            
            # Check if this was a fallback assignment
            if mat_name == fallback["material"]:
                # Check if any pattern actually matched
                pattern_matched = False
                for pattern in mappings.keys():
                    if pattern in label_lower:
                        pattern_matched = True
                        break
                if not pattern_matched:
                    fallback_used.add(obj.VolumeCAD.Label)
            
            if requires_custom:
                custom_materials_needed.add(mat_name)
            
            mat_obj = name_to_material.get(mat_name)
            if mat_obj is None:
                print(f"Warning: Material '{mat_name}' not found for volume {obj.VolumeCAD.Label}. Load it via --load-material.")
                continue
            obj.VolumeMaterial = mat_obj
            assignments_count[mat_name] = assignments_count.get(mat_name, 0) + 1

        if assignments_count:
            print("Material assignments summary:")
            for k, v in sorted(assignments_count.items(), key=lambda x: (-x[1], x[0])):
                print(f"  {k}: {v} volumes")
        
        if custom_materials_needed:
            print(f"\nCustom materials needed: {', '.join(custom_materials_needed)}")
            print("  Load them using --load-material flag")
        
        if fallback_used:
            print(f"\n ERROR: {len(fallback_used)} volumes have unmatched names and would use fallback material '{fallback['material']}':")
            # Show first few examples
            examples = list(fallback_used)[:10]
            for example in examples:
                print(f"  - {example}")
            if len(fallback_used) > 10:
                print(f"  ... and {len(fallback_used) - 10} more")
            print(f"\nTo fix this:")
            print(f"  1. Add patterns to src/material_mappings.json for these volume names")
            print(f"  2. Or use --load-props with a CSV file that has explicit material assignments")
            print(f"  3. Or modify the fallback_material in material_mappings.json if this is intentional")
            return False
        
        if not assignments_count:
            print("No materials were assigned.")
            return False
        
        return True

    def auto_set_world_size(self):
        """Calculate optimal world size based on geometry bounding box and ask for confirmation"""
        if not self.list_of_objects:
            return
        
        try:
            # Calculate bounding box for all loaded objects
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
            width = max_x - min_x
            height = max_y - min_y
            depth = max_z - min_z
            
            # Add some margin (20% on each side)
            margin = 0.2
            world_x = width * (1 + 2 * margin)
            world_y = height * (1 + 2 * margin)
            world_z = depth * (1 + 2 * margin)
            
            # Convert from mm to meters
            world_x /= 1000.0
            world_y /= 1000.0
            world_z /= 1000.0
            
            print(f"\n=== Geometry Analysis ===")
            print(f"Bounding box: {width:.1f}mm x {height:.1f}mm x {depth:.1f}mm")
            print(f"Center: ({min_x + width/2:.1f}, {min_y + height/2:.1f}, {min_z + depth/2:.1f}) mm")
            print(f"Calculated world size: {world_x:.2f}m x {world_y:.2f}m x {world_z:.2f}m")
            
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

    def save_properties(self, output_file):
        """Save volume properties to a CSV file"""
        try:
            with open(output_file, 'w') as f:
                for obj in self.list_of_objects:
                    f.write(f"{obj.VolumeCAD.Label};{obj.VolumeMaterial.Name};{obj.VolumeMMD};{obj.VolumeGDMLoption}\n")
            print(f"Properties saved to {output_file}")
            return True
        except Exception as e:
            print(f"Error saving properties: {str(e)}")
            return False

    def load_properties(self, input_file):
        """Load volume properties from a CSV file"""
        if not os.path.exists(input_file):
            print(f"Error: File {input_file} does not exist")
            return False

        try:
            with open(input_file, 'r') as f:
                properties = f.readlines()

            if len(properties) != len(self.list_of_objects):
                print("Error: Number of properties does not match number of objects")
                return False

            for i, line in enumerate(properties):
                props = line.strip().split(';')
                if len(props) != 4:
                    print(f"Error: Invalid format in line {i+1}")
                    continue

                vol_label, mat_name, mmd, gdml_opt = props
                
                if vol_label != self.list_of_objects[i].VolumeCAD.Label:
                    print(f"Warning: Volume name mismatch in line {i+1}")
                    continue

                # Set material
                material_found = False
                for ele in self.Element_List:
                    if mat_name == ele.Name:
                        self.list_of_objects[i].VolumeMaterial = ele
                        material_found = True
                        break
                
                if not material_found:
                    for mat in self.Material_List:
                        if mat_name == mat.Name:
                            self.list_of_objects[i].VolumeMaterial = mat
                            material_found = True
                            break

                if not material_found:
                    print(f"Warning: Material {mat_name} not found for volume {vol_label}")

                # Set MMD
                try:
                    mmd = float(mmd)
                    if mmd > 0:
                        self.list_of_objects[i].VolumeMMD = mmd
                    else:
                        print(f"Warning: Invalid MMD value in line {i+1}")
                except ValueError:
                    print(f"Warning: Invalid MMD value in line {i+1}")

                # Set GDML option
                try:
                    gdml_opt = int(gdml_opt)
                    self.list_of_objects[i].VolumeGDMLoption = 1 if gdml_opt > 0 else 0
                except ValueError:
                    print(f"Warning: Invalid GDML option in line {i+1}")

            print("Properties loaded successfully")
            return True

        except Exception as e:
            print(f"Error loading properties: {str(e)}")
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

            WriteGDML.CreateMother(str(output_path), self.list_of_objects, self.world_dimensions)
            
            for i, obj in enumerate(self.list_of_objects, 1):
                if obj.VolumeGDMLoption == 1:
                    WriteGDML.CreateGDML(obj, i, str(output_path))

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
    parser.add_argument('--save-props', help='Save properties to CSV file')
    parser.add_argument('--load-props', help='Load properties from CSV file')
    parser.add_argument('--output-dir', help='Output directory for GDML files')
    parser.add_argument('--load-material', action='append', help='Load a custom material file. Can be used multiple times.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging and progress messages')
    parser.add_argument('--assign-materials', action='store_true', help='Assign materials based on volume name patterns (single-pass workflow)')
    parser.add_argument('--material-config', default='material_mappings.json', help='JSON file with material assignment rules (default: material_mappings.json)')
    
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    mesh = GUIMeshCLI()
    mesh.verbose = bool(args.verbose)

    if args.step:
        if not mesh.load_step_file(args.step):
            return

    if args.world_size:
        if not mesh.set_world_size(*args.world_size):
            return

    if args.load_material:
        for mat_file in args.load_material:
            if not mesh.load_custom_material(mat_file):
                return

    if args.load_props:
        if not mesh.load_properties(args.load_props):
            return

    # Single-pass material assignment (only if properties were not explicitly loaded)
    if args.assign_materials and not args.load_props:
        if not mesh.assign_materials_from_names(args.material_config):
            return

    if args.save_props:
        if not mesh.save_properties(args.save_props):
            return

    if args.output_dir:
        if not mesh.write_gdml(args.output_dir):
            return

if __name__ == '__main__':
    main() 




