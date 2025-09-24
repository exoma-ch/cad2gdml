#!/usr/bin/env python3


""" # Show help
python GUIMeshCLI.py --help

# Load a STEP file and write GDML
python GUIMeshCLI.py --step input.step --output-dir output/

# Set world dimensions
python GUIMeshCLI.py --world-size 2.0 2.0 2.0

# Save properties to CSV
python GUIMeshCLI.py --save-props properties.csv

# Load properties from CSV
python GUIMeshCLI.py --load-props properties.csv

# Full workflow example
python GUIMeshCLI.py --step input.step --world-size 2.0 2.0 2.0 --save-props props.csv --output-dir output/ """

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
    from GUIMeshLibs import Materials
    from GUIMeshLibs import Volumes
    from GUIMeshLibs import LoadOP
    from GUIMeshLibs import MaterialManager
    from GUIMeshLibs import WriteGDML
except ImportError:
    print("Error: Could not load GUIMesh libraries. Please check if the folder GUIMeshLibs exists and if the files are there.")
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

    if args.save_props:
        if not mesh.save_properties(args.save_props):
            return

    if args.output_dir:
        if not mesh.write_gdml(args.output_dir):
            return

if __name__ == '__main__':
    main() 




