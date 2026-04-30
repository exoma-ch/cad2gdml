#########################################################################################################
#    GUIMesh v1                                                                                         #
#                                                                                                       #
#    Copyright (c) 2018  Marco Gui Alves Pinto mail:mgpinto11@gmail.com                                 #
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
#                                                                #########################################

import math
import os
import re

def extract_crystal_number(volume_label):
    """Extract crystal number from volume label and check for duplicates"""
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
    
    # Special case: bare label with no numeric suffix is crystal 0
    # (e.g. FreeCAD's first instance is 'Crystal' before duplicates become
    # 'Crystal001', 'Crystal002', ...; same for '_detector_lyso_')
    if volume_label in ('_detector_lyso_', 'Crystal'):
        return 0
    
    for pattern in patterns:
        match = re.search(pattern, volume_label)
        if match:
            return int(match.group(1))
    
    # If no number found, return None (will be handled later)
    return None

def extract_crystal_centers(list_of_objects, verbose=False, output_file=None, output_dir=None, vertex_counts=None, translation=None):
    """Extract center coordinates of LYSO crystals only and optionally save to CSV
    
    Args:
        list_of_objects: List of volume objects
        verbose: Enable verbose output
        output_file: Optional output CSV file path (or True for auto-generated name)
        output_dir: Optional output directory for auto-generated filenames
        vertex_counts: Optional list to append vertex counts to
        translation: Optional translation vector [x, y, z] in mm to apply to crystal centers
    
    Returns:
        tuple: (crystal_centers_list, success)
    """
    if not list_of_objects:
        print("Error: No volumes loaded")
        return [], False
    
    crystal_centers = []
    lyso_count = 0
    used_crystal_ids = set()
    
    if vertex_counts is None:
        vertex_counts = []
    
    print(f"\n=== LYSO Crystal Center Analysis ===")
    if translation is not None:
        print(f"Translation applied: ({translation[0]:.1f}, {translation[1]:.1f}, {translation[2]:.1f}) mm")
        print(f"Coordinates are in transformed (centered) coordinate system")
    else:
        print(f"Using original CAD coordinates (no translation)")
    print(f"Using Direct Edge Vector Analysis for crystal orientation")
    print(f"Scanning {len(list_of_objects)} volumes for LYSO crystals...")
    
    # Debug: Show first few volume names
    if verbose:
        print("First 10 volume names:")
        for i, obj in enumerate(list_of_objects[:10]):
            print(f"  {i}: {obj.VolumeCAD.Label} (material: {obj.VolumeMaterial.Name if obj.VolumeMaterial else 'Unknown'})")
    
    for i, obj in enumerate(list_of_objects):
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
            try:
                # Get the tessellated vertices of the crystal shape
                # This gives us the actual geometric data, not just bounding box
                precision = 0.1  # Use a reasonable precision for orientation calculation
                triangles = obj.VolumeCAD.Shape.tessellate(precision)
                vertices = triangles[0]  # Get the vertices
                
                if len(vertices) > 0:
                    # Print vertex count for debugging and track for statistics
                    vertex_count = len(vertices)
                    vertex_counts.append(vertex_count)
                    if verbose:
                        print(f"  Crystal {obj.VolumeCAD.Label}: {vertex_count} vertices")
                    
                    # DIRECT EDGE VECTOR ANALYSIS (for 8-vertex rectangular crystals)
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
                            
                            # Normalize coordinate system to ensure consistent angles regardless of export orientation
                            # Since elevation should be 0 (crystal axis in XZ plane), the Y component should be small
                            # If Y and Z are swapped in the export, we need to detect and correct this
                            
                            abs_y = abs(main_axis_vector[1])
                            abs_z = abs(main_axis_vector[2])
                            
                            # For crystals in XZ plane (elevation=0), Y component should be minimal
                            # If |Y| > |Z|, it suggests Y and Z might be swapped (since in correct system |Y| should be ~0)
                            # Use a threshold: if Y is significantly larger than Z, swap them
                            # This ensures elevation will be ~0 as expected
                            if abs_y > abs_z:
                                # Likely Y and Z are swapped - swap them back to normalize to standard Y-up system
                                normalized_vector = [main_axis_vector[0], main_axis_vector[2], main_axis_vector[1]]
                            else:
                                normalized_vector = main_axis_vector
                            
                            # Calculate azimuth angle (rotation in XZ plane)
                            azimuth_angle = math.degrees(math.atan2(normalized_vector[2], normalized_vector[0]))
                            
                            # Calculate elevation angle (tilt relative to XZ plane - should be ~0 for this geometry)
                            elevation_angle = math.degrees(math.atan2(normalized_vector[1], 
                                                                    math.sqrt(normalized_vector[0]**2 + normalized_vector[2]**2)))
                        else:
                            # Fallback to radial direction
                            azimuth_angle = math.degrees(math.atan2(bbox_center_z, bbox_center_x))
                            elevation_angle = math.degrees(math.atan2(bbox_center_y, bbox_center_x))
                    else:
                        # Fallback to radial direction
                        azimuth_angle = math.degrees(math.atan2(bbox_center_z, bbox_center_x))
                        elevation_angle = math.degrees(math.atan2(bbox_center_y, bbox_center_x))
                    
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
                if verbose:
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
            
            # Extract crystal number from volume label
            crystal_number = extract_crystal_number(volume_label)
            
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
                return [], False
            elif crystal_number in used_crystal_ids:
                # Duplicate found - this is an error
                print(f"\n ERROR: Duplicate crystal ID {crystal_number} found in volume name '{volume_label}'")
                print(f"Previous volume with same ID was already processed.")
                print(f"Found {lyso_count} LYSO crystals before error.")
                print(f"\nTo fix this:")
                print(f"  1. Check for duplicate volume names in your STEP file")
                print(f"  2. Ensure each crystal has a unique number")
                print(f"  3. Verify the geometry export from your CAD software")
                return [], False
            else:
                # Valid unique crystal number
                final_crystal_id = crystal_number
            
            used_crystal_ids.add(final_crystal_id)
            
            # Apply translation if provided (for geometry centering)
            if translation is not None:
                center_x = center_x + translation[0]
                center_y = center_y + translation[1]
                center_z = center_z + translation[2]
            
            # Store center coordinates (transformed if translation was applied)
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
            
            if verbose and lyso_count <= 10:  # Show first 10 LYSO crystals for preview
                print(f"  {lyso_count:4d}: {obj.VolumeCAD.Label:30s} | "
                      f"Center: ({center_x:7.2f}, {center_y:7.2f}, {center_z:7.2f}) mm | "
                      f"Azimuth: {azimuth_angle:6.1f}° | Elevation: {elevation_angle:6.1f}°")
            
        except Exception as e:
            print(f"Warning: Could not process volume {i+1} ({obj.VolumeCAD.Label}): {str(e)}")
            continue
    
    print(f"Found {lyso_count} LYSO crystals")
    
    if verbose and lyso_count > 10:
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
        if vertex_counts:
            print(f"Vertex counts: {min(vertex_counts)} to {max(vertex_counts)} vertices per crystal (avg: {sum(vertex_counts)/len(vertex_counts):.1f})")
    
    # Save to CSV and H5 if requested
    if output_file:
        # If output_file is True (from --extract-centers flag without filename), create default filename
        if output_file is True:
            # Use the output directory if available, otherwise current directory
            if output_dir:
                csv_file = os.path.join(output_dir, 'lyso_crystal_centers_3d_angles.csv')
                h5_file = os.path.join(output_dir, 'lyso_crystal_centers_3d_angles.h5')
            else:
                csv_file = 'lyso_crystal_centers_3d_angles.csv'
                h5_file = 'lyso_crystal_centers_3d_angles.h5'
        else:
            # output_file is a string (filename provided by user)
            # If output directory is set and filename is not already a full path, prepend it
            if output_dir and not os.path.isabs(output_file) and not os.path.dirname(output_file):
                output_file = os.path.join(output_dir, output_file)
            
            # Generate CSV and H5 filenames from the provided filename
            if output_file.endswith('.csv'):
                csv_file = output_file
                h5_file = output_file[:-4] + '.h5'
            elif output_file.endswith('.h5'):
                h5_file = output_file
                csv_file = output_file[:-3] + '.csv'
            else:
                csv_file = output_file + '.csv'
                h5_file = output_file + '.h5'
        
        # Create output directory if it doesn't exist
        csv_dir = os.path.dirname(csv_file)
        if csv_dir and not os.path.exists(csv_dir):
            try:
                os.makedirs(csv_dir, exist_ok=True)
                if verbose:
                    print(f"Created output directory: {csv_dir}")
            except Exception as e:
                print(f"Error creating output directory '{csv_dir}': {str(e)}")
                return crystal_centers, False
        
        # Save CSV file
        try:
            import csv
            with open(csv_file, 'w', newline='') as csvfile:
                fieldnames = ['crystal_id', 'volume_name', 'center_x', 'center_y', 'center_z', 'azimuth_angle', 'elevation_angle']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for crystal in crystal_centers:
                    writer.writerow(crystal)
            
            print(f"\nCrystal centers saved to CSV: {csv_file}")
            
        except Exception as e:
            print(f"Error saving crystal centers to CSV: {str(e)}")
            return crystal_centers, False
        
        # Save H5 file
        try:
            import h5py
            import numpy as np
            
            with h5py.File(h5_file, 'w') as f:
                # Create datasets for each field
                n_crystals = len(crystal_centers)
                
                # Create datasets
                crystal_ids = np.array([c['crystal_id'] for c in crystal_centers], dtype=np.int32)
                center_x = np.array([c['center_x'] for c in crystal_centers], dtype=np.float64)
                center_y = np.array([c['center_y'] for c in crystal_centers], dtype=np.float64)
                center_z = np.array([c['center_z'] for c in crystal_centers], dtype=np.float64)
                azimuth_angle = np.array([c['azimuth_angle'] for c in crystal_centers], dtype=np.float64)
                elevation_angle = np.array([c['elevation_angle'] for c in crystal_centers], dtype=np.float64)
                
                # Store as datasets
                f.create_dataset('crystal_id', data=crystal_ids, compression='gzip')
                f.create_dataset('center_x', data=center_x, compression='gzip')
                f.create_dataset('center_y', data=center_y, compression='gzip')
                f.create_dataset('center_z', data=center_z, compression='gzip')
                f.create_dataset('azimuth_angle', data=azimuth_angle, compression='gzip')
                f.create_dataset('elevation_angle', data=elevation_angle, compression='gzip')
                
                # Store volume names as variable-length strings
                volume_names = [c['volume_name'].encode('utf-8') for c in crystal_centers]
                f.create_dataset('volume_name', data=volume_names, compression='gzip')
                
                # Add metadata
                f.attrs['description'] = 'LYSO crystal center coordinates and orientations'
                f.attrs['n_crystals'] = n_crystals
                f.attrs['units'] = 'mm for coordinates, degrees for angles'
                f.attrs['created_by'] = 'GUIMeshCLI'
            
            print(f"Crystal centers saved to H5: {h5_file}")
            
        except ImportError:
            print(f"Warning: h5py not available. Skipping H5 file creation.")
            print(f"Install h5py with: pip install h5py")
        except Exception as e:
            print(f"Error saving crystal centers to H5: {str(e)}")
            # Don't fail completely if H5 save fails, CSV is more important
    
    return crystal_centers, True

