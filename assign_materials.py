#!/usr/bin/env python3
"""
Script to automatically assign materials based on volume names
"""

import sys
import re

def assign_material_from_name(volume_name):
    """
    Assign material based on volume name patterns
    """
    volume_lower = volume_name.lower()
    
    # Material mapping based on volume name patterns
    if 'lyso' in volume_lower:
        return 'LYSO'  # Custom LYSO material from Materials/LYSO.txt
    elif 'si' in volume_lower and 'sipm' in volume_lower:
        return 'G4_Si'  # Pure silicon for SiPM
    elif 'al' in volume_lower or 'aluminum' in volume_lower:
        return 'G4_Al'  # Built-in Geant4 aluminum
    elif 'pcb' in volume_lower:
        return 'G4_POLYETHYLENE'  # PCB typically fiberglass/epoxy composite
    elif 'plastic' in volume_lower:
        return 'G4_POLYETHYLENE'  # Built-in Geant4 plastic
    elif 'glass' in volume_lower:
        return 'SiO2'  # Custom SiO2 material from Materials/SiO2.txt
    elif 'steel' in volume_lower or 'iron' in volume_lower:
        return 'G4_Fe'  # Built-in Geant4 iron
    elif 'copper' in volume_lower or 'cu' in volume_lower:
        return 'G4_Cu'  # Built-in Geant4 copper
    elif 'lead' in volume_lower or 'pb' in volume_lower:
        return 'G4_Pb'  # Built-in Geant4 lead
    elif 'tungsten' in volume_lower or 'w' in volume_lower:
        return 'G4_W'  # Built-in Geant4 tungsten
    else:
        return 'G4_Si'  # Default to built-in Geant4 silicon

def process_properties_file(input_file, output_file):
    """
    Process the properties CSV file and assign materials based on volume names
    """
    try:
        with open(input_file, 'r') as f:
            lines = f.readlines()
        
        modified_lines = []
        material_assignments = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split(';')
            if len(parts) != 4:
                print(f"Warning: Skipping malformed line: {line}")
                continue
            
            volume_label, current_material, mmd, gdml_option = parts
            
            # Assign material based on volume name
            new_material = assign_material_from_name(volume_label)
            
            # Track material assignments for summary
            if new_material not in material_assignments:
                material_assignments[new_material] = 0
            material_assignments[new_material] += 1
            
            # Create new line with assigned material
            new_line = f"{volume_label};{new_material};{mmd};{gdml_option}"
            modified_lines.append(new_line)
        
        # Write the modified file
        with open(output_file, 'w') as f:
            for line in modified_lines:
                f.write(line + '\n')
        
        # Print summary
        print(f"Processed {len(modified_lines)} volumes")
        print("\nMaterial assignments:")
        for material, count in sorted(material_assignments.items()):
            print(f"  {material}: {count} volumes")
        
        print(f"\nModified properties saved to: {output_file}")
        return True
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python assign_materials.py <input_properties.csv> <output_properties.csv>")
        print("Example: python assign_materials.py properties-test-ring.csv properties-ring-with-materials.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not process_properties_file(input_file, output_file):
        sys.exit(1)

if __name__ == '__main__':
    main()