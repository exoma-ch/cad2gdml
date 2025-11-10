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
#Add FreeCAD directory to os path
def Find_FreeCAD_Dir():
        import tkinter.filedialog
        import os.path
        path_to_FreeCAD=tkinter.filedialog.askdirectory()
        #Check if directory is correct
        if((os.path.isfile(path_to_FreeCAD+"/bin/FreeCAD.PYD")==True) or (os.path.isfile(path_to_FreeCAD+"/lib/FreeCAD.so")==True)):
            import sys
            sys.path.append(path_to_FreeCAD+"/bin")
            sys.path.append(path_to_FreeCAD+"/lib")
            import FreeCAD
            try:
                    import FreeCAD
            except:
                    import tkinter.messagebox
                    tkinter.messagebox.showinfo("Warning", "FreeCAD was found. However, there was an error importing FreeCAD.")
                    print("FreeCAD was found. However, there was an error importing FreeCAD.")
            return 1
        else:
            return 0

#Add FreeCAD directory to os path
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
    FreeCAD.newDocument("Unnamed")
    FreeCAD.setActiveDocument("Unnamed")
    
    try: 
        Import.insert(path_to_file, "Unnamed")  # FreeCAD attempts to open file
        print("File read successfully")
        list_of_objects = []
        for obj in FreeCAD.ActiveDocument.Objects:
            try:
                if obj.TypeId == "Part::Feature":
                    obj.Label = obj.Label.replace(" ", "_")
                    obj.Label = obj.Label.replace(".", "_")
                    obj.Label = obj.Label.replace("---", "_")
                    list_of_objects.append(Volumes.Volume(obj, material, 0.1, 1))
            except:
                continue
        return list_of_objects
    except Exception as e:
        print(f"Error reading file. Format might be incorrect: {str(e)}")
        return 0
