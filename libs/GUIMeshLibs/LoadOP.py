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
#                                                                                                       #
#########################################################################################################
#Libraries
#import os
#import Materials
#import Volumes
def Load_STEP_File(doc_status, material, path_to_file):
    """Load a STEP file and return list of Volume objects.
    
    Args:
        doc_status: Whether a document is already open (1) or not (0)
        material: Material object to assign to volumes
        path_to_file: Path to the STEP file to load
    
    Returns:
        list: List of Volume objects, or 0 on error
    """
    from GUIMeshLibs import Volumes
    import FreeCAD
    import Import
    import FreeCADGui
    import Draft
    import Part
    import os.path
    
    # Validate file extension
    if not (path_to_file[-5:].lower() == ".step" or 
            path_to_file[-4:].lower() == ".stp"):
        print("Error with file extension")
        return 0
    
    # Check if file exists
    if not os.path.exists(path_to_file):
        print(f"Error: File {path_to_file} does not exist")
        return 0
    
    # Close previous document if needed
    if doc_status:
        FreeCAD.closeDocument("Unnamed")
        print("Previous document closed")
    
    # Create new document
    print("Creating FreeCAD document...")
    FreeCAD.newDocument("Unnamed")
    FreeCAD.setActiveDocument("Unnamed")
    
    try: 
        # Import STEP file - this can take a long time for large files
        file_basename = os.path.basename(path_to_file)
        file_size_mb = os.path.getsize(path_to_file) / (1024 * 1024) if os.path.exists(path_to_file) else 0
        
        print(f"\n{'='*60}")
        print(f"Importing STEP file: {file_basename}")
        if file_size_mb > 0:
            print(f"File size: {file_size_mb:.1f} MB")
        print(f"{'='*60}")
        print("Parsing STEP file geometry (this may take several minutes for large files)...")
        print("Please wait", end="", flush=True)
        
        # Import the file (blocking operation - can't show progress during this)
        Import.insert(path_to_file, "Unnamed")  # FreeCAD attempts to open file
        
        print(" ✓")
        print("Processing objects...", end="", flush=True)
        
        list_of_objects = []
        all_objects = list(FreeCAD.ActiveDocument.Objects)
        total_objects = len(all_objects)
        
        # Process objects with progress indication
        processed_count = 0
        for i, obj in enumerate(all_objects):
            try:
                if obj.TypeId == "Part::Feature":
                    obj.Label = obj.Label.replace(" ", "_")
                    obj.Label = obj.Label.replace(".", "_")
                    obj.Label = obj.Label.replace("---", "_")
                    list_of_objects.append(Volumes.Volume(obj, material, 0.1, 1))
                    processed_count += 1
                    
                    # Show progress every 10 objects or at milestones
                    if total_objects > 10:
                        if (i + 1) % max(1, total_objects // 10) == 0 or (i + 1) == total_objects:
                            progress = int((i + 1) / total_objects * 100)
                            print(f"\rProcessing objects... {progress}% ({i + 1}/{total_objects})", end="", flush=True)
                    elif (i + 1) == total_objects:
                        print(f"\rProcessing objects... {i + 1} objects", end="", flush=True)
            except:
                continue
        
        print(" Done!")
        print(f"Successfully loaded {processed_count} volume(s) from {total_objects} object(s)")
        return list_of_objects
    except Exception as e:
        print(f"Error reading file. Format might be incorrect: {str(e)}")
        return 0
