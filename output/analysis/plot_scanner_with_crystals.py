#!/usr/bin/env python3
"""
Plot scanner geometry with crystal dimensions and orientations.
Shows three orthogonal plane views: XY, XZ, and YZ.
"""

import matplotlib.pyplot as plt
import csv
import math
import sys
import os
import argparse

def read_crystal_data(csv_file):
    """Read crystal data from CSV file"""
    crystals = []
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                crystal = {
                    'id': int(row['crystal_id']),
                    'name': row['volume_name'],
                    'x': float(row['center_x']),
                    'y': float(row['center_y']),
                    'z': float(row['center_z']),
                    'azimuth': float(row['azimuth_angle']),
                    'elevation': float(row['elevation_angle'])
                }
                crystals.append(crystal)
        
        print(f"Loaded {len(crystals)} crystal centers from {csv_file}")
        return crystals
        
    except FileNotFoundError:
        print(f"Error reading CSV file: {csv_file}")
        return []
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []


def plot_scanner_with_crystals(crystals, width, height, depth, save_dir=None):
    """Plot scanner geometry with crystal dimensions in three orthogonal planes"""
    
    if not crystals:
        print("No crystal data to plot")
        return
    
    # Extract coordinates
    x = [c['x'] for c in crystals]
    y = [c['y'] for c in crystals]
    z = [c['z'] for c in crystals]
    azimuth_angles = [c['azimuth'] for c in crystals]
    elevation_angles = [c['elevation'] for c in crystals]
    
    # Create figure with three orthogonal plane views
    fig = plt.figure(figsize=(18, 6))
    
    # Create a colormap for azimuth angles
    cmap = plt.cm.hsv
    norm = plt.Normalize(vmin=min(azimuth_angles), vmax=max(azimuth_angles))
    
    # Plot a subset of crystals to avoid overcrowding
    max_crystals = 500
    step = max(1, len(crystals) // max_crystals)
    subset_crystals = crystals[::step]
    
    print(f"Plotting {len(subset_crystals)} oriented crystal sticks in three planes...")
    
    # 1. Top view (XZ plane) - looking down from above
    ax1 = fig.add_subplot(131)
    
    for i, crystal in enumerate(subset_crystals):
        azimuth_rad = math.radians(crystal['azimuth'])
        stick_length = depth  # 20mm in the depth direction
        
        # Calculate stick endpoints in XZ plane
        dx = (stick_length/2) * math.cos(azimuth_rad)
        dz = (stick_length/2) * math.sin(azimuth_rad)
        
        x_start = crystal['x'] - dx
        x_end = crystal['x'] + dx
        z_start = crystal['z'] - dz
        z_end = crystal['z'] + dz
        
        color = cmap(norm(crystal['azimuth']))
        ax1.plot([x_start, x_end], [z_start, z_end], 
                color=color, linewidth=2, alpha=0.8)
    
    ax1.set_xlabel('X (mm)')
    ax1.set_ylabel('Z (mm)')
    ax1.set_title('Top View (XZ plane)')
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal')
    
    # 2. Side view (XY plane) - looking from the side
    ax2 = fig.add_subplot(132)
    
    for i, crystal in enumerate(subset_crystals):
        azimuth_rad = math.radians(crystal['azimuth'])
        elevation_rad = math.radians(crystal['elevation'])  # Read elevation from CSV
        stick_length = depth  # 20mm in the depth direction
        
        # Calculate stick endpoints in XY plane using both angles
        dx = (stick_length/2) * math.cos(azimuth_rad) * math.cos(elevation_rad)
        dy = (stick_length/2) * math.sin(elevation_rad)
        
        x_start = crystal['x'] - dx
        x_end = crystal['x'] + dx
        y_start = crystal['y'] - dy
        y_end = crystal['y'] + dy
        
        color = cmap(norm(crystal['azimuth']))
        ax2.plot([x_start, x_end], [y_start, y_end], 
                color=color, linewidth=2, alpha=0.8)
    
    ax2.set_xlabel('X (mm)')
    ax2.set_ylabel('Y (mm)')
    ax2.set_title('Side View (XY plane)')
    ax2.grid(True, alpha=0.3)
    ax2.set_aspect('equal')
    
    # 3. Front view (YZ plane) - looking from the front
    ax3 = fig.add_subplot(133)
    
    for i, crystal in enumerate(subset_crystals):
        azimuth_rad = math.radians(crystal['azimuth'])
        elevation_rad = math.radians(crystal['elevation'])  # Read elevation from CSV
        stick_length = depth  # 20mm in the depth direction
        
        # Calculate stick endpoints in YZ plane using both angles
        dz = (stick_length/2) * math.sin(azimuth_rad) * math.cos(elevation_rad)
        dy = (stick_length/2) * math.sin(elevation_rad)
        
        z_start = crystal['z'] - dz
        z_end = crystal['z'] + dz
        y_start = crystal['y'] - dy
        y_end = crystal['y'] + dy
        
        color = cmap(norm(crystal['azimuth']))
        ax3.plot([z_start, z_end], [y_start, y_end], 
                color=color, linewidth=2, alpha=0.8)
    
    ax3.set_xlabel('Z (mm)')
    ax3.set_ylabel('Y (mm)')
    ax3.set_title('Front View (YZ plane)')
    ax3.grid(True, alpha=0.3)
    ax3.set_aspect('equal')
    
    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=[ax1, ax2, ax3], shrink=0.6, aspect=20)
    cbar.set_label('Azimuth Angle (degrees)')
    
    # Add overall title
    fig.suptitle(f'Scanner Geometry - Three Orthogonal Views\n{len(subset_crystals)} crystals shown', fontsize=14)
    
    # Statistics
    print(f"\n=== Scanner Geometry with Crystal Sizes ===")
    print(f"Total crystals: {len(crystals)}")
    print(f"X range: {min(x):.2f} to {max(x):.2f} mm (span: {max(x)-min(x):.2f} mm)")
    print(f"Y range: {min(y):.2f} to {max(y):.2f} mm (span: {max(y)-min(y):.2f} mm)")
    print(f"Z range: {min(z):.2f} to {max(z):.2f} mm (span: {max(z)-min(z):.2f} mm)")
    print(f"Azimuth angles: {min(azimuth_angles):.1f}° to {max(azimuth_angles):.1f}° (span: {max(azimuth_angles)-min(azimuth_angles):.1f}°)")
    print(f"Elevation angles: {min(elevation_angles):.1f}° to {max(elevation_angles):.1f}° (span: {max(elevation_angles)-min(elevation_angles):.1f}°)")
    
    print(f"\n=== Crystal Dimension Statistics ===")
    print(f"Width:  {width:.2f} mm")
    print(f"Height: {height:.2f} mm")
    print(f"Depth:  {depth:.2f} mm")
    print(f"Volume: {width * height * depth:.1f} mm³")
    
    # Calculate radial distances
    radial_distances = [math.sqrt(c['x']**2 + c['z']**2) for c in crystals]
    print(f"Radial distances: {min(radial_distances):.1f} to {max(radial_distances):.1f} mm (avg: {sum(radial_distances)/len(radial_distances):.1f} mm)")
    
    # Save the plot
    if save_dir:
        output_file = os.path.join(save_dir, 'scanner_with_crystals.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_file}")
    else:
        plt.savefig('scanner_with_crystals.png', dpi=300, bbox_inches='tight')
        print("Saved: ./scanner_with_crystals.png")
    
    plt.show()
    
    # Now create orientation group plots
    plot_orientation_groups(crystals, width, height, depth, save_dir)

def plot_orientation_groups(crystals, width, height, depth, save_dir=None):
    """Plot all orientation groups in a single combined figure"""
    
    if not crystals:
        return
    
    # Group crystals by orientation angle using modulo 180° (opposite directions are the same)
    orientation_groups = {}
    for crystal in crystals:
        # Use modulo 180° to group opposite directions (0° = 180°, 30° = 210°, etc.)
        group_angle = crystal['azimuth'] % 180
        
        # Round to nearest 10 degrees for cleaner grouping
        group_angle = round(group_angle / 10) * 10
        
        # Special case: if angle is exactly 180°, map it to 0° to group with 0°
        if group_angle == 180:
            group_angle = 0
        
        if group_angle not in orientation_groups:
            orientation_groups[group_angle] = []
        orientation_groups[group_angle].append(crystal)
    
    print(f"\n=== Orientation Group Analysis ===")
    print(f"Found {len(orientation_groups)} orientation groups:")
    for angle in sorted(orientation_groups.keys()):
        count = len(orientation_groups[angle])
        print(f"  {angle:3.0f}°: {count:4d} crystals")
    
    # Create a single combined figure with all orientation groups
    n_groups = len(orientation_groups)
    if n_groups == 0:
        return
    
    # Create a grid layout: 3 columns (top, side, front views) and multiple rows
    n_cols = 3  # Top, Side, Front views
    n_rows = n_groups
    
    fig = plt.figure(figsize=(18, 6 * n_rows))
    fig.suptitle(f'All Orientation Groups - Combined View', fontsize=16)
    
    # Define colors for each orientation group
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    
    row = 0
    for group_angle in sorted(orientation_groups.keys()):
        group_crystals = orientation_groups[group_angle]
        
        if len(group_crystals) < 5:  # Skip groups with too few crystals
            continue
        
        color = colors[row % len(colors)]
        
        # 1. Top view (XZ plane)
        ax1 = fig.add_subplot(n_rows, n_cols, row * n_cols + 1)
        for crystal in group_crystals:
            azimuth_rad = math.radians(crystal['azimuth'])
            stick_length = depth
            
            dx = (stick_length/2) * math.cos(azimuth_rad)
            dz = (stick_length/2) * math.sin(azimuth_rad)
            
            x_start = crystal['x'] - dx
            x_end = crystal['x'] + dx
            z_start = crystal['z'] - dz
            z_end = crystal['z'] + dz
            
            ax1.plot([x_start, x_end], [z_start, z_end], 
                    color=color, linewidth=1.5, alpha=0.7)
        
        ax1.set_xlabel('X (mm)')
        ax1.set_ylabel('Z (mm)')
        ax1.set_title(f'Top View - {group_angle:.0f}° ({len(group_crystals)} crystals)')
        ax1.grid(True, alpha=0.3)
        ax1.set_aspect('equal')
        
        # 2. Side view (XY plane)
        ax2 = fig.add_subplot(n_rows, n_cols, row * n_cols + 2)
        for crystal in group_crystals:
            azimuth_rad = math.radians(crystal['azimuth'])
            elevation_rad = math.radians(crystal['elevation'])  # Read elevation from CSV
            stick_length = depth
            
            dx = (stick_length/2) * math.cos(azimuth_rad) * math.cos(elevation_rad)
            dy = (stick_length/2) * math.sin(elevation_rad)
            
            x_start = crystal['x'] - dx
            x_end = crystal['x'] + dx
            y_start = crystal['y'] - dy
            y_end = crystal['y'] + dy
            
            ax2.plot([x_start, x_end], [y_start, y_end], 
                    color=color, linewidth=1.5, alpha=0.7)
        
        ax2.set_xlabel('X (mm)')
        ax2.set_ylabel('Y (mm)')
        ax2.set_title(f'Side View - {group_angle:.0f}°')
        ax2.grid(True, alpha=0.3)
        ax2.set_aspect('equal')
        
        # 3. Front view (YZ plane)
        ax3 = fig.add_subplot(n_rows, n_cols, row * n_cols + 3)
        for crystal in group_crystals:
            azimuth_rad = math.radians(crystal['azimuth'])
            elevation_rad = math.radians(crystal['elevation'])  # Read elevation from CSV
            stick_length = depth
            
            dz = (stick_length/2) * math.sin(azimuth_rad) * math.cos(elevation_rad)
            dy = (stick_length/2) * math.sin(elevation_rad)
            
            z_start = crystal['z'] - dz
            z_end = crystal['z'] + dz
            y_start = crystal['y'] - dy
            y_end = crystal['y'] + dy
            
            ax3.plot([z_start, z_end], [y_start, y_end], 
                    color=color, linewidth=1.5, alpha=0.7)
        
        ax3.set_xlabel('Z (mm)')
        ax3.set_ylabel('Y (mm)')
        ax3.set_title(f'Front View - {group_angle:.0f}°')
        ax3.grid(True, alpha=0.3)
        ax3.set_aspect('equal')
        
        row += 1
    
    # Save the combined plot
    if save_dir:
        output_file = os.path.join(save_dir, 'all_orientation_groups_combined.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_file}")
    else:
        plt.savefig('all_orientation_groups_combined.png', dpi=300, bbox_inches='tight')
        print(f"Saved: ./all_orientation_groups_combined.png")
    
    plt.show()
    
    # Create superimposed plot with all orientation groups overlaid
    plot_superimposed_orientation_groups(crystals, width, height, depth, save_dir)

def plot_superimposed_orientation_groups(crystals, width, height, depth, save_dir=None):
    """Plot all orientation groups superimposed on the same three planes"""
    
    if not crystals:
        return
    
    # Group crystals by orientation angle using modulo 180° (opposite directions are the same)
    orientation_groups = {}
    for crystal in crystals:
        # Use modulo 180° to group opposite directions (0° = 180°, 30° = 210°, etc.)
        group_angle = crystal['azimuth'] % 180
        
        # Round to nearest 10 degrees for cleaner grouping
        group_angle = round(group_angle / 10) * 10
        
        # Special case: if angle is exactly 180°, map it to 0° to group with 0°
        if group_angle == 180:
            group_angle = 0
        
        if group_angle not in orientation_groups:
            orientation_groups[group_angle] = []
        orientation_groups[group_angle].append(crystal)
    
    print(f"\n=== Creating Superimposed Orientation Groups Plot ===")
    print(f"Overlaying {len(orientation_groups)} orientation groups on three planes...")
    
    # Create figure with three orthogonal plane views
    fig = plt.figure(figsize=(18, 6))
    fig.suptitle('All Orientation Groups - Superimposed View', fontsize=16)
    
    # Define colors for each orientation group
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    
    # 1. Top view (XZ plane) - all groups superimposed
    ax1 = fig.add_subplot(131)
    for i, (group_angle, group_crystals) in enumerate(sorted(orientation_groups.items())):
        if len(group_crystals) < 5:  # Skip groups with too few crystals
            continue
        
        color = colors[i % len(colors)]
        alpha = 0.6  # Slightly transparent for overlay effect
        
        for crystal in group_crystals:
            azimuth_rad = math.radians(crystal['azimuth'])
            stick_length = depth
            
            dx = (stick_length/2) * math.cos(azimuth_rad)
            dz = (stick_length/2) * math.sin(azimuth_rad)
            
            x_start = crystal['x'] - dx
            x_end = crystal['x'] + dx
            z_start = crystal['z'] - dz
            z_end = crystal['z'] + dz
            
            ax1.plot([x_start, x_end], [z_start, z_end], 
                    color=color, linewidth=1.0, alpha=alpha)
    
    ax1.set_xlabel('X (mm)')
    ax1.set_ylabel('Z (mm)')
    ax1.set_title('Top View - All Groups Superimposed')
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal')
    
    # 2. Side view (XY plane) - all groups superimposed
    ax2 = fig.add_subplot(132)
    for i, (group_angle, group_crystals) in enumerate(sorted(orientation_groups.items())):
        if len(group_crystals) < 5:  # Skip groups with too few crystals
            continue
        
        color = colors[i % len(colors)]
        alpha = 0.6  # Slightly transparent for overlay effect
        
        for crystal in group_crystals:
            azimuth_rad = math.radians(crystal['azimuth'])
            elevation_rad = math.radians(crystal['elevation'])  # Read elevation from CSV
            stick_length = depth
            
            dx = (stick_length/2) * math.cos(azimuth_rad) * math.cos(elevation_rad)
            dy = (stick_length/2) * math.sin(elevation_rad)
            
            x_start = crystal['x'] - dx
            x_end = crystal['x'] + dx
            y_start = crystal['y'] - dy
            y_end = crystal['y'] + dy
            
            ax2.plot([x_start, x_end], [y_start, y_end], 
                    color=color, linewidth=1.0, alpha=alpha)
    
    ax2.set_xlabel('X (mm)')
    ax2.set_ylabel('Y (mm)')
    ax2.set_title('Side View - All Groups Superimposed')
    ax2.grid(True, alpha=0.3)
    ax2.set_aspect('equal')
    
    # 3. Front view (YZ plane) - all groups superimposed
    ax3 = fig.add_subplot(133)
    for i, (group_angle, group_crystals) in enumerate(sorted(orientation_groups.items())):
        if len(group_crystals) < 5:  # Skip groups with too few crystals
            continue
        
        color = colors[i % len(colors)]
        alpha = 0.6  # Slightly transparent for overlay effect
        
        for crystal in group_crystals:
            azimuth_rad = math.radians(crystal['azimuth'])
            elevation_rad = math.radians(crystal['elevation'])  # Read elevation from CSV
            stick_length = depth
            
            dz = (stick_length/2) * math.sin(azimuth_rad) * math.cos(elevation_rad)
            dy = (stick_length/2) * math.sin(elevation_rad)
            
            z_start = crystal['z'] - dz
            z_end = crystal['z'] + dz
            y_start = crystal['y'] - dy
            y_end = crystal['y'] + dy
            
            ax3.plot([z_start, z_end], [y_start, y_end], 
                    color=color, linewidth=1.0, alpha=alpha)
    
    ax3.set_xlabel('Z (mm)')
    ax3.set_ylabel('Y (mm)')
    ax3.set_title('Front View - All Groups Superimposed')
    ax3.grid(True, alpha=0.3)
    ax3.set_aspect('equal')
    
    # Add legend showing orientation groups
    legend_elements = []
    for i, (group_angle, group_crystals) in enumerate(sorted(orientation_groups.items())):
        if len(group_crystals) >= 5:  # Only include groups with enough crystals
            color = colors[i % len(colors)]
            legend_elements.append(plt.Line2D([0], [0], color=color, linewidth=2, 
                                           label=f'{group_angle:.0f}° ({len(group_crystals)} crystals)'))
    
    fig.legend(handles=legend_elements, loc='center', bbox_to_anchor=(0.5, 0.02), 
               ncol=3, fontsize=10)
    
    # Save the superimposed plot
    if save_dir:
        output_file = os.path.join(save_dir, 'all_orientation_groups_superimposed.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_file}")
    else:
        plt.savefig('all_orientation_groups_superimposed.png', dpi=300, bbox_inches='tight')
        print(f"Saved: ./all_orientation_groups_superimposed.png")
    
    plt.show()
    
    # Create debug plot with one crystal per orientation group
    plot_debug_single_crystals(crystals, width, height, depth, save_dir)

def plot_debug_single_crystals(crystals, width, height, depth, save_dir=None):
    """Plot one crystal per orientation group for debugging"""
    
    if not crystals:
        return
    
    # Group crystals by orientation angle using modulo 180° (opposite directions are the same)
    orientation_groups = {}
    for crystal in crystals:
        # Use modulo 180° to group opposite directions (0° = 180°, 30° = 210°, etc.)
        group_angle = crystal['azimuth'] % 180
        
        # Round to nearest 10 degrees for cleaner grouping
        group_angle = round(group_angle / 10) * 10
        
        # Special case: if angle is exactly 180°, map it to 0° to group with 0°
        if group_angle == 180:
            group_angle = 0
        
        if group_angle not in orientation_groups:
            orientation_groups[group_angle] = []
        orientation_groups[group_angle].append(crystal)
    
    print(f"\n=== Debug: Single Crystal per Orientation Group ===")
    print(f"Showing one crystal from each of {len(orientation_groups)} orientation groups...")
    
    # Create figure with three orthogonal plane views
    fig = plt.figure(figsize=(18, 6))
    fig.suptitle('Debug: One Crystal per Orientation Group', fontsize=16)
    
    # Define colors for each orientation group
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    
    # 1. Top view (XZ plane) - one crystal per group
    ax1 = fig.add_subplot(131)
    for i, (group_angle, group_crystals) in enumerate(sorted(orientation_groups.items())):
        if len(group_crystals) < 5:  # Skip groups with too few crystals
            continue
        
        # Take the first crystal from each group
        crystal = group_crystals[0]
        color = colors[i % len(colors)]
        
        azimuth_rad = math.radians(crystal['azimuth'])
        stick_length = depth
        
        dx = (stick_length/2) * math.cos(azimuth_rad)
        dz = (stick_length/2) * math.sin(azimuth_rad)
        
        x_start = crystal['x'] - dx
        x_end = crystal['x'] + dx
        z_start = crystal['z'] - dz
        z_end = crystal['z'] + dz
        
        ax1.plot([x_start, x_end], [z_start, z_end], 
                color=color, linewidth=3, alpha=0.8, label=f'{group_angle:.0f}°')
        
        # Add crystal center point
        ax1.plot(crystal['x'], crystal['z'], 'o', color=color, markersize=6, alpha=0.8)
    
    ax1.set_xlabel('X (mm)')
    ax1.set_ylabel('Z (mm)')
    ax1.set_title('Top View - One Crystal per Group')
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # 2. Side view (XY plane) - one crystal per group
    ax2 = fig.add_subplot(132)
    for i, (group_angle, group_crystals) in enumerate(sorted(orientation_groups.items())):
        if len(group_crystals) < 5:  # Skip groups with too few crystals
            continue
        
        # Take the first crystal from each group
        crystal = group_crystals[0]
        color = colors[i % len(colors)]
        
        azimuth_rad = math.radians(crystal['azimuth'])
        elevation_rad = math.radians(crystal['elevation'])  # Read elevation from CSV
        stick_length = depth
        
        dx = (stick_length/2) * math.cos(azimuth_rad) * math.cos(elevation_rad)
        dy = (stick_length/2) * math.sin(elevation_rad)
        
        x_start = crystal['x'] - dx
        x_end = crystal['x'] + dx
        y_start = crystal['y'] - dy
        y_end = crystal['y'] + dy
        
        ax2.plot([x_start, x_end], [y_start, y_end], 
                color=color, linewidth=3, alpha=0.8, label=f'{group_angle:.0f}°')
        
        # Add crystal center point
        ax2.plot(crystal['x'], crystal['y'], 'o', color=color, markersize=6, alpha=0.8)
    
    ax2.set_xlabel('X (mm)')
    ax2.set_ylabel('Y (mm)')
    ax2.set_title('Side View - One Crystal per Group')
    ax2.grid(True, alpha=0.3)
    ax2.set_aspect('equal')
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # 3. Front view (YZ plane) - one crystal per group
    ax3 = fig.add_subplot(133)
    for i, (group_angle, group_crystals) in enumerate(sorted(orientation_groups.items())):
        if len(group_crystals) < 5:  # Skip groups with too few crystals
            continue
        
        # Take the first crystal from each group
        crystal = group_crystals[0]
        color = colors[i % len(colors)]
        
        azimuth_rad = math.radians(crystal['azimuth'])
        elevation_rad = math.radians(crystal['elevation'])  # Read elevation from CSV
        stick_length = depth
        
        dz = (stick_length/2) * math.sin(azimuth_rad) * math.cos(elevation_rad)
        dy = (stick_length/2) * math.sin(elevation_rad)
        
        z_start = crystal['z'] - dz
        z_end = crystal['z'] + dz
        y_start = crystal['y'] - dy
        y_end = crystal['y'] + dy
        
        ax3.plot([z_start, z_end], [y_start, y_end], 
                color=color, linewidth=3, alpha=0.8, label=f'{group_angle:.0f}°')
        
        # Add crystal center point
        ax3.plot(crystal['z'], crystal['y'], 'o', color=color, markersize=6, alpha=0.8)
    
    ax3.set_xlabel('Z (mm)')
    ax3.set_ylabel('Y (mm)')
    ax3.set_title('Front View - One Crystal per Group')
    ax3.grid(True, alpha=0.3)
    ax3.set_aspect('equal')
    ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Save the debug plot
    if save_dir:
        output_file = os.path.join(save_dir, 'debug_single_crystals_per_group.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_file}")
    else:
        plt.savefig('debug_single_crystals_per_group.png', dpi=300, bbox_inches='tight')
        print(f"Saved: ./debug_single_crystals_per_group.png")
    
    plt.show()

def plot_y_vs_radial_angle(crystals, save_dir=None):
    """Plot Y position vs radial angle (azimuth) to show all crystals"""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    # Extract data
    y_positions = [crystal['y'] for crystal in crystals]
    azimuth_angles = [crystal['azimuth'] for crystal in crystals]
    
    # Create scatter plot
    scatter = ax.scatter(azimuth_angles, y_positions, c=azimuth_angles, cmap='viridis', 
                       alpha=0.7, s=20, edgecolors='black', linewidth=0.5)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Azimuth Angle (degrees)', rotation=270, labelpad=20)
    
    # Customize plot
    ax.set_xlabel('Radial Angle (Azimuth) [degrees]', fontsize=12)
    ax.set_ylabel('Y Position [mm]', fontsize=12)
    ax.set_title('Crystal Distribution: Y Position vs Radial Angle', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Set axis limits with some padding
    ax.set_xlim(min(azimuth_angles) - 5, max(azimuth_angles) + 5)
    ax.set_ylim(min(y_positions) - 5, max(y_positions) + 5)
    
    # Add statistics text
    stats_text = f'Total Crystals: {len(crystals)}\n'
    stats_text += f'Y Range: {min(y_positions):.1f} to {max(y_positions):.1f} mm\n'
    stats_text += f'Azimuth Range: {min(azimuth_angles):.1f} to {max(azimuth_angles):.1f}°'
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    # Save plot
    if save_dir:
        filename = os.path.join(save_dir, "y_vs_radial_angle.png")
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Y vs Radial Angle plot saved to: {filename}")
    
    plt.show()

if __name__ == "__main__":
    import glob
    
    parser = argparse.ArgumentParser(
        description="Plot scanner geometry with crystal dimensions and orientations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s crystal_centers.csv
  %(prog)s --width 15.92 --height 5.30 --depth 23.63
  %(prog)s crystal_centers.csv --width 15.92 --height 5.30 --depth 23.63
        """
    )
    
    parser.add_argument(
        'csv_file',
        nargs='?',
        help='CSV file with crystal center data (default: auto-detect)'
    )
    
    parser.add_argument(
        '--width',
        type=float,
        default=3.95,
        help='Crystal width in mm (default: 3.95)'
    )
    
    parser.add_argument(
        '--height',
        type=float,
        default=5.3,
        help='Crystal height in mm (default: 25.0)'
    )
    
    parser.add_argument(
        '--depth',
        type=float,
        default=25.0,
        help='Crystal depth in mm (default: 5.3)'
    )
    
    parser.add_argument(
        '--save-dir',
        type=str,
        default='.',
        help='Directory to save output plots (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Auto-detect CSV file if not provided
    csv_file = args.csv_file
    if not csv_file:
        csv_files = glob.glob("lyso_crystal_centers_3d_angles*.csv")
        if csv_files:
            csv_file = csv_files[0]  # Use the first one found
        else:
            csv_file = "lyso_crystal_centers_3d_angles.csv"  # Fallback
    
    print(f"Plotting scanner with crystal sizes from: {csv_file}")
    print(f"Crystal dimensions: {args.width:.2f} × {args.height:.2f} × {args.depth:.2f} mm")
    
    # Read crystal data
    crystals = read_crystal_data(csv_file)
    
    if crystals:
        # Main geometry plot with crystal sizes
        plot_scanner_with_crystals(crystals, args.width, args.height, args.depth, save_dir=args.save_dir)
        
        # Y vs Radial Angle plot
        plot_y_vs_radial_angle(crystals, save_dir=args.save_dir)
        
        print(f"\nScanner with crystal sizes visualizations saved to: {args.save_dir}")
    else:
        print("No crystal data loaded.")