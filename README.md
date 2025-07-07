
This project is based on [GUIMesh3](https://github.com/MPintoSpace/GUIMesh3), originally developed by Marco Gui Alves Pinto. It is now a command line interface that converts STEP geometries to GDML format.

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


## How to run
```bash
python GUIMeshCLI.py \
  --step "STEP files/<stepfile.step>" \
  --load-material "Materials/<material.txt>" \
  --load-props <properties.csv> \
  --output-dir gdml/
  ```
  
## Files description
* `GUIMeshCLI.py` - Main source code for command line interface - for our purposes (GUIMesh.py - original source code for GUI)
* `Documents/` - Folder with "GUIMesh User Manual.pdf", a guide on how to run GUIMesh found in the Documents directory
* `GUIMeshLibs/` - folder containing libraries used in GUIMesh
* `Materials/` - folder which should be used to save materials in a database
* `STEP Files/` - folder with STEP geometries used in all tests
* `gdml/` - folder for the gdml output
* `COPYING` - License disclosure






## Licence  
Licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

See the `COPYING` file for license details.

