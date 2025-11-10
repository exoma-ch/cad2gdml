#!/usr/bin/env python3


""" # Show help
python GUIMeshCLI.py --help

# Single-pass (recommended): load STEP once, assign materials, write GDML
python GUIMeshCLI.py --step STEPfiles/your.step --assign-materials --load-materials Materials/LYSO.json --output-dir gdml_output/

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
        self.vertex_counts = []  # Track vertex counts for statistics
        self.use_direct_edge_analysis = True  # Use direct edge vector analysis by default

    def set_orientation_analysis_method(self, use_direct_edge=True):
        """Set the method for calculating crystal orientations
        
        Args:
            use_direct_edge (bool): If True, use direct edge vector analysis (recommended for 8-vertex crystals)
                                  If False, use PCA analysis (better for complex shapes with many vertices)
        """
        self.use_direct_edge_analysis = use_direct_edge
        method = "Direct Edge Vector Analysis" if use_direct_edge else "PCA Analysis"
        if self.verbose:
            print(f"Orientation analysis method set to: {method}")

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
            if self.verbose:
                print(f"Starting STEP import: {step_file}")
                print("Note: Large STEP files may take several minutes to import...")
            start_time = time.time()
            
            # Use LoadOP to load the STEP file
            list_of_objects = LoadOP.Load_STEP_File(self.file_status, self.Element_List[13], path_to_file=step_file)
            
            if list_of_objects == 0:
                print("Error: Failed to load STEP file")
                return False
            
            elapsed = time.time() - start_time
            if self.verbose:
                print(f"File read successfully in {elapsed:.1f}s")
            
            self.list_of_objects = list_of_objects
            self.file_status = 1
            
            print(f"Loaded {len(self.list_of_objects)} objects from STEP file")
            
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
                print(f"Warning: Material '{mat_name}' not found for volume {obj.VolumeCAD.Label}. Load it via --load-material.")
                continue
            obj.VolumeMaterial = mat_obj
            assignments_count[mat_name] = assignments_count.get(mat_name, 0) + 1

        if assignments_count:
            print("Material assignments summary:")
            for k, v in sorted(assignments_count.items(), key=lambda x: (-x[1], x[0])):
                print(f"  {k}: {v} volumes")
        
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
            print(f"  2. Or use --load-props with a CSV file that has explicit material assignments")
            return False
        
        if not assignments_count:
            print("No materials were assigned.")
            return False
        
        return True

    def extract_crystal_number(self, volume_label):
        """Extract crystal number from volume label and check for duplicates"""
        import re
        
        # Try to extract number from various patterns
        # Common patterns: "_detector_lyso_123", "Part_123", "Crystal_456", etc.
        patterns = [
            r'_detector_lyso_(\d+)',  # _detector_lyso_123
            r'Part_(\d+)',           # Part_123
            r'Crystal_(\d+)',        # Crystal_456  
            r'LYSO_(\d+)',           # LYSO_789
            r'(\d+)$',               # Number at end of string
            r'(\d+)',                # Any number (fallback)
        ]
        
        # Special case: _detector_lyso_ (no number) should be crystal 0
        if volume_label == '_detector_lyso_':
            return 0
        
        for pattern in patterns:
            match = re.search(pattern, volume_label)
            if match:
                return int(match.group(1))
        
        # If no number found, return None (will be handled later)
        return None

    def extract_crystal_centers(self, output_file=None):
        """Extract center coordinates of LYSO crystals only and optionally save to CSV"""
        if not self.list_of_objects:
            print("Error: No volumes loaded")
            return False
        
        crystal_centers = []
        lyso_count = 0
        used_crystal_ids = set()
        
        print(f"\n=== LYSO Crystal Center Analysis ===")
        method = "Direct Edge Vector Analysis" if self.use_direct_edge_analysis else "PCA Analysis"
        print(f"Using orientation analysis method: {method}")
        print(f"Scanning {len(self.list_of_objects)} volumes for LYSO crystals...")
        
        # Debug: Show first few volume names
        if self.verbose:
            print("First 10 volume names:")
            for i, obj in enumerate(self.list_of_objects[:10]):
                print(f"  {i}: {obj.VolumeCAD.Label} (material: {obj.VolumeMaterial.Name if obj.VolumeMaterial else 'Unknown'})")
        
        for i, obj in enumerate(self.list_of_objects):
            try:
                # Get volume label and material name
                volume_label = obj.VolumeCAD.Label
                material_name = obj.VolumeMaterial.Name if obj.VolumeMaterial else "Unknown"
                
                # Only process LYSO crystals (check both volume name and material)
                if "lyso" not in volume_label.lower() and material_name != "LYSO":
                    continue
                
                lyso_count += 1
                
                # Get the bounding box of the volume
                bbox = obj.VolumeCAD.Shape.BoundBox
                
                # Calculate center coordinates from bounding box
                bbox_center_x = (bbox.XMin + bbox.XMax) / 2.0
                bbox_center_y = (bbox.YMin + bbox.YMax) / 2.0
                bbox_center_z = (bbox.ZMin + bbox.ZMax) / 2.0
                
                # Calculate crystal orientation from its actual geometric shape
                import math
                
                try:
                    # Get the tessellated vertices of the crystal shape
                    # This gives us the actual geometric data, not just bounding box
                    precision = 0.1  # Use a reasonable precision for orientation calculation
                    triangles = obj.VolumeCAD.Shape.tessellate(precision)
                    vertices = triangles[0]  # Get the vertices
                    
                    if len(vertices) > 0:
                        # Print vertex count for debugging and track for statistics
                        vertex_count = len(vertices)
                        self.vertex_counts.append(vertex_count)
                        if self.verbose:
                            print(f"  Crystal {obj.VolumeCAD.Label}: {vertex_count} vertices")
                        
                        # Analyze the crystal's orientation using the selected method
                        if self.use_direct_edge_analysis:
                            # DIRECT EDGE VECTOR ANALYSIS (improved for 8-vertex rectangular crystals)
                            # Find the main axis by analyzing edge patterns for parallelepipeds
                            
                            # For rectangular crystals (parallelepipeds), we want to find the main axis
                            # Each edge should have exactly 3 other parallel edges (4 total in that direction)
                            edge_vectors = []
                            edge_lengths = []
                            
                            # Check all possible edge combinations (8 choose 2 = 28 combinations)
                            for i in range(len(vertices)):
                                for j in range(i+1, len(vertices)):
                                    edge_vector = [vertices[j][k] - vertices[i][k] for k in range(3)]
                                    edge_length = math.sqrt(sum(v**2 for v in edge_vector))
                                    
                                    edge_vectors.append(edge_vector)
                                    edge_lengths.append(edge_length)
                            
                            # Find the main axis by looking for the longest edge with exactly 3 parallel edges
                            # For a parallelepiped: 12 edges total, 4 edges in each of 3 perpendicular directions
                            main_axis_vector = None
                            max_parallel_count = 0
                            longest_edge_length = 0
                            
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
                                        other_len = edge_lengths[j]
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
                            
                            # Normalize the main axis vector and calculate angles
                            if main_axis_vector:
                                length = math.sqrt(sum(v**2 for v in main_axis_vector))
                                if length > 0:
                                    main_axis_vector = [v / length for v in main_axis_vector]
                                    
                                    # Calculate azimuth angle (rotation in XZ plane)
                                    azimuth_angle = math.degrees(math.atan2(main_axis_vector[2], main_axis_vector[0]))
                                    
                                    # Calculate elevation angle (tilt relative to XZ plane)
                                    elevation_angle = math.degrees(math.atan2(main_axis_vector[1], 
                                                                            math.sqrt(main_axis_vector[0]**2 + main_axis_vector[2]**2)))
                                else:
                                    # Fallback to radial direction
                                    azimuth_angle = math.degrees(math.atan2(bbox_center_z, bbox_center_x))
                                    elevation_angle = math.degrees(math.atan2(bbox_center_y, bbox_center_x))
                            else:
                                # Fallback to radial direction
                                azimuth_angle = math.degrees(math.atan2(bbox_center_z, bbox_center_x))
                                elevation_angle = math.degrees(math.atan2(bbox_center_y, bbox_center_x))
                        else:
                            # PCA ANALYSIS (better for complex shapes with many vertices)
                            # Extract all coordinates
                            x_coords = [v[0] for v in vertices]
                            y_coords = [v[1] for v in vertices]
                            z_coords = [v[2] for v in vertices]
                            
                            # Calculate means
                            x_mean = sum(x_coords) / len(x_coords)
                            y_mean = sum(y_coords) / len(y_coords)
                            z_mean = sum(z_coords) / len(z_coords)
                            
                            # Calculate covariance matrix for 3D orientation analysis
                            # XZ plane (azimuth angle)
                            xx_var = sum((x - x_mean)**2 for x in x_coords) / len(x_coords)
                            zz_var = sum((z - z_mean)**2 for z in z_coords) / len(x_coords)
                            xz_cov = sum((x - x_mean) * (z - z_mean) for x, z in zip(x_coords, z_coords)) / len(x_coords)
                            
                            # XY plane (elevation angle)
                            yy_var = sum((y - y_mean)**2 for y in y_coords) / len(x_coords)
                            xy_cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_coords, y_coords)) / len(x_coords)
                            
                            # Calculate azimuth angle (rotation in XZ plane)
                            if xx_var > 0 and zz_var > 0:
                                azimuth_angle = math.degrees(math.atan2(2 * xz_cov, xx_var - zz_var) / 2)
                            else:
                                # Fallback to radial direction
                                azimuth_angle = math.degrees(math.atan2(bbox_center_z, bbox_center_x))
                            
                            # Calculate elevation angle (tilt in Y direction)
                            if xx_var > 0 and yy_var > 0:
                                elevation_angle = math.degrees(math.atan2(2 * xy_cov, xx_var - yy_var) / 2)
                            else:
                                # Fallback to Y position
                                elevation_angle = math.degrees(math.atan2(bbox_center_y, bbox_center_x))
                        
                        # OLD PCA CALCULATION - COMMENTED OUT (using direct edge vector analysis above)
                        """
                        # Calculate means
                        x_mean = sum(x_coords) / len(x_coords)
                        y_mean = sum(y_coords) / len(y_coords)
                        z_mean = sum(z_coords) / len(z_coords)
                        
                        # Calculate covariance matrix for 3D orientation analysis
                        # XZ plane (azimuth angle)
                        xx_var = sum((x - x_mean)**2 for x in x_coords) / len(x_coords)
                        zz_var = sum((z - z_mean)**2 for z in z_coords) / len(z_coords)
                        xz_cov = sum((x - x_mean) * (z - z_mean) for x, z in zip(x_coords, z_coords)) / len(x_coords)
                        
                        # XY plane (elevation angle)
                        yy_var = sum((y - y_mean)**2 for y in y_coords) / len(y_coords)
                        xy_cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_coords, y_coords)) / len(x_coords)
                        
                        # Calculate azimuth angle (rotation in XZ plane)
                        if xx_var > 0 and zz_var > 0:
                            azimuth_angle = math.degrees(math.atan2(2 * xz_cov, xx_var - zz_var) / 2)
                        else:
                            # Fallback to radial direction
                            azimuth_angle = math.degrees(math.atan2(bbox_center_z, bbox_center_x))
                        
                        # Calculate elevation angle (tilt in Y direction)
                        if xx_var > 0 and yy_var > 0:
                            elevation_angle = math.degrees(math.atan2(2 * xy_cov, xx_var - yy_var) / 2)
                        else:
                            # Fallback to Y position
                            elevation_angle = math.degrees(math.atan2(bbox_center_y, bbox_center_x))
                        """
                        
                        # Normalize angles: azimuth to 0-180° (opposite directions are the same), elevation to 0-360°
                        if azimuth_angle < 0:
                            azimuth_angle += 360.0
                        # Use modulo 180° for azimuth, but ensure 0° and 180° are grouped together
                        azimuth_angle = azimuth_angle % 180.0
                        # Special case: if angle is exactly 180°, map it to 0° to group with 0°
                        if azimuth_angle == 180.0:
                            azimuth_angle = 0.0
                        
                        # Normalize elevation angle to 0-360° using modulo 360°
                        if elevation_angle < 0:
                            elevation_angle += 360.0
                        elevation_angle = elevation_angle % 360.0
                        # Special case: if angle is exactly 360°, map it to 0° to group with 0°
                        if elevation_angle == 360.0:
                            elevation_angle = 0.0
                        
                        # Round to avoid tiny floating-point precision issues
                        azimuth_angle = round(azimuth_angle, 1)
                        elevation_angle = round(elevation_angle, 1)
                        
                        # Use bounding box center (verified to be identical to geometric center)
                        center_x = bbox_center_x
                        center_y = bbox_center_y
                        center_z = bbox_center_z
                    else:
                        # Fallback if no vertices found
                        azimuth_angle = math.degrees(math.atan2(bbox_center_z, bbox_center_x))
                        elevation_angle = math.degrees(math.atan2(bbox_center_y, bbox_center_x))
                        if azimuth_angle < 0:
                            azimuth_angle += 360.0
                        # Use modulo 180° for azimuth, but ensure 0° and 180° are grouped together
                        azimuth_angle = azimuth_angle % 180.0
                        # Special case: if angle is exactly 180°, map it to 0° to group with 0°
                        if azimuth_angle == 180.0:
                            azimuth_angle = 0.0
                        
                        # Normalize elevation angle to 0-360° using modulo 360°
                        if elevation_angle < 0:
                            elevation_angle += 360.0
                        elevation_angle = elevation_angle % 360.0
                        # Special case: if angle is exactly 360°, map it to 0° to group with 0°
                        if elevation_angle == 360.0:
                            elevation_angle = 0.0
                        
                        # Round to avoid tiny floating-point precision issues
                        azimuth_angle = round(azimuth_angle, 1)
                        elevation_angle = round(elevation_angle, 1)
                        
                        center_x = bbox_center_x
                        center_y = bbox_center_y
                        center_z = bbox_center_z
                            
                except Exception as e:
                    # Fallback to radial direction if geometric analysis fails
                    if self.verbose:
                        print(f"Warning: Could not analyze crystal geometry for {obj.VolumeCAD.Label}: {str(e)}")
                    azimuth_angle = math.degrees(math.atan2(bbox_center_z, bbox_center_x))
                    elevation_angle = math.degrees(math.atan2(bbox_center_y, bbox_center_x))
                    if azimuth_angle < 0:
                        azimuth_angle += 360.0
                    if elevation_angle < 0:
                        elevation_angle += 360.0
                    center_x = bbox_center_x
                    center_y = bbox_center_y
                    center_z = bbox_center_z
                
                # Get volume dimensions (store only once for the first crystal)
                if lyso_count == 0:
                    self.crystal_width = bbox.XMax - bbox.XMin
                    self.crystal_height = bbox.YMax - bbox.YMin
                    self.crystal_depth = bbox.ZMax - bbox.ZMin
                    print(f"Crystal dimensions: {self.crystal_width:.2f} × {self.crystal_height:.2f} × {self.crystal_depth:.2f} mm")
                
                # Extract crystal number from volume label
                volume_label = obj.VolumeCAD.Label
                crystal_number = self.extract_crystal_number(volume_label)
                
                # Handle duplicate or missing crystal numbers
                if crystal_number is None:
                    # No number found in label - this is an error
                    print(f"\n ERROR: No crystal number found in volume name '{volume_label}'")
                    print(f"Expected patterns: '_detector_lyso_123', 'Part_456', 'Crystal_789', etc.")
                    print(f"Found {lyso_count} LYSO crystals before error.")
                    print(f"\nTo fix this:")
                    print(f"  1. Check that volume names contain numbers")
                    print(f"  2. Verify the naming convention in your STEP file")
                    print(f"  3. Only '_detector_lyso_' (no number) is allowed as crystal 0")
                    return False
                elif crystal_number in used_crystal_ids:
                    # Duplicate found - this is an error
                    print(f"\n ERROR: Duplicate crystal ID {crystal_number} found in volume name '{volume_label}'")
                    print(f"Previous volume with same ID was already processed.")
                    print(f"Found {lyso_count} LYSO crystals before error.")
                    print(f"\nTo fix this:")
                    print(f"  1. Check for duplicate volume names in your STEP file")
                    print(f"  2. Ensure each crystal has a unique number")
                    print(f"  3. Verify the geometry export from your CAD software")
                    return False
                else:
                    # Valid unique crystal number
                    final_crystal_id = crystal_number
                
                used_crystal_ids.add(final_crystal_id)
                
                crystal_info = {
                    'crystal_id': final_crystal_id,
                    'volume_name': volume_label,
                    'center_x': center_x,
                    'center_y': center_y,
                    'center_z': center_z,
                    'azimuth_angle': azimuth_angle,
                    'elevation_angle': elevation_angle
                }
                
                crystal_centers.append(crystal_info)
                
                if self.verbose and lyso_count <= 10:  # Show first 10 LYSO crystals for preview
                    print(f"  {lyso_count:4d}: {obj.VolumeCAD.Label:30s} | "
                          f"Center: ({center_x:7.2f}, {center_y:7.2f}, {center_z:7.2f}) mm | "
                          f"Azimuth: {azimuth_angle:6.1f}° | Elevation: {elevation_angle:6.1f}°")
                
            except Exception as e:
                print(f"Warning: Could not process volume {i+1} ({obj.VolumeCAD.Label}): {str(e)}")
                continue
        
        print(f"Found {lyso_count} LYSO crystals")
        
        if self.verbose and lyso_count > 10:
            print(f"  ... and {lyso_count - 10} more LYSO crystals")
        
        # Print summary statistics before CSV operations
        if crystal_centers:
            # Calculate overall statistics
            x_coords = [c['center_x'] for c in crystal_centers]
            y_coords = [c['center_y'] for c in crystal_centers]
            z_coords = [c['center_z'] for c in crystal_centers]
            
            # Calculate angle statistics
            azimuth_angles = [c['azimuth_angle'] for c in crystal_centers]
            elevation_angles = [c['elevation_angle'] for c in crystal_centers]
            
            print(f"\n=== LYSO Crystal Summary Statistics ===")
            print(f"Total LYSO crystals: {len(crystal_centers)}")
            print(f"X range: {min(x_coords):.2f} to {max(x_coords):.2f} mm (span: {max(x_coords)-min(x_coords):.2f} mm)")
            print(f"Y range: {min(y_coords):.2f} to {max(y_coords):.2f} mm (span: {max(y_coords)-min(y_coords):.2f} mm)")
            print(f"Z range: {min(z_coords):.2f} to {max(z_coords):.2f} mm (span: {max(z_coords)-min(z_coords):.2f} mm)")
            print(f"Azimuth angles: {min(azimuth_angles):.1f}° to {max(azimuth_angles):.1f}° (span: {max(azimuth_angles)-min(azimuth_angles):.1f}°)")
            print(f"Elevation angles: {min(elevation_angles):.1f}° to {max(elevation_angles):.1f}° (span: {max(elevation_angles)-min(elevation_angles):.1f}°)")
            
            # Add vertex count statistics if available
            if hasattr(self, 'vertex_counts') and self.vertex_counts:
                vertex_counts = self.vertex_counts
                print(f"Vertex counts: {min(vertex_counts)} to {max(vertex_counts)} vertices per crystal (avg: {sum(vertex_counts)/len(vertex_counts):.1f})")
        
        # Save to CSV if requested
        if output_file:
            # If output_file is True (from --extract-centers flag without filename), create method-specific filename
            if output_file is True:
                method_suffix = "direct_edge" if self.use_direct_edge_analysis else "pca"
                # Use the output directory if available, otherwise current directory
                if hasattr(self, 'output_dir') and self.output_dir:
                    output_file = os.path.join(self.output_dir, f'lyso_crystal_centers_3d_angles_{method_suffix}.csv')
                else:
                    output_file = f'lyso_crystal_centers_3d_angles_{method_suffix}.csv'
            else:
                # output_file is a string (filename provided by user)
                # If output directory is set and filename is not already a full path, prepend it
                if hasattr(self, 'output_dir') and self.output_dir and not os.path.isabs(output_file) and not os.path.dirname(output_file):
                    output_file = os.path.join(self.output_dir, output_file)
            try:
                import csv
                with open(output_file, 'w', newline='') as csvfile:
                    fieldnames = ['crystal_id', 'volume_name', 'center_x', 'center_y', 'center_z', 'azimuth_angle', 'elevation_angle']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for crystal in crystal_centers:
                        writer.writerow(crystal)
                
                    print(f"\nCrystal centers saved to: {output_file}")
                    
                    # Save crystal dimensions to a separate file
                    if hasattr(self, 'crystal_width'):
                        dim_file = output_file.replace('.csv', '_dimensions.txt')
                        try:
                            with open(dim_file, 'w') as f:
                                f.write(f"Crystal Dimensions\n")
                                f.write(f"==================\n")
                                f.write(f"Width:  {self.crystal_width:.2f} mm\n")
                                f.write(f"Height: {self.crystal_height:.2f} mm\n")
                                f.write(f"Depth:  {self.crystal_depth:.2f} mm\n")
                                f.write(f"Volume: {self.crystal_width * self.crystal_height * self.crystal_depth:.2f} mm³\n")
                            print(f"Crystal dimensions saved to: {dim_file}")
                        except Exception as e:
                            print(f"Error saving crystal dimensions: {str(e)}")
                
            except Exception as e:
                print(f"Error saving crystal centers: {str(e)}")
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

            # Normalize base volumes at the end (keeping original names)
            WriteGDML.normalize_base_volumes(str(volumes_path))

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
    parser.add_argument('--load-materials', action='append', help='Load material(s) from a JSON file or directory containing JSON files. Can be used multiple times.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging and progress messages')
    parser.add_argument('--assign-materials', nargs='?', const='material_mappings.json', default=None, help='Assign materials based on volume name patterns. Optionally specify JSON config file (default: material_mappings.json)')
    parser.add_argument('--extract-centers', nargs='?', const=True, help='Extract crystal center coordinates and save to CSV file. Optionally specify output filename.')
    parser.add_argument('--use-pca', action='store_true', help='Use PCA analysis instead of direct edge vector analysis for crystal orientation')
    
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    mesh = GUIMeshCLI()
    mesh.verbose = bool(args.verbose)
    
    # Set output directory for files
    mesh.output_dir = args.output_dir
    
    # Set orientation analysis method
    mesh.set_orientation_analysis_method(use_direct_edge=not args.use_pca)

    # Check material mappings file BEFORE loading STEP file (if --assign-materials is used)
    if args.assign_materials and not args.load_props:
        config_file = args.assign_materials
        if mesh.check_material_mappings_file(config_file) is None:
            print(f"   ERROR: Material mappings file '{config_file}' not found.")
            print(f"   Please create the file or specify a valid path.")
            print(f"   The file should be located in the current directory or in src/ directory.")
            return

    if args.step:
        if not mesh.load_step_file(args.step):
            return

    if args.world_size:
        if not mesh.set_world_size(*args.world_size):
            return

    if args.load_materials:
        for material_path in args.load_materials:
            if not mesh.load_materials(material_path):
                return

    if args.load_props:
        if not mesh.load_properties(args.load_props):
            return

    # Single-pass material assignment (only if properties were not explicitly loaded)
    if args.assign_materials and not args.load_props:
        if not mesh.assign_materials_from_names(args.assign_materials):
            return

    # Extract crystal centers if requested
    if args.extract_centers:
        if not mesh.extract_crystal_centers(args.extract_centers):
            return

    if args.save_props:
        if not mesh.save_properties(args.save_props):
            return

    if args.output_dir:
        if not mesh.write_gdml(args.output_dir):
            return

if __name__ == '__main__':
    main() 




