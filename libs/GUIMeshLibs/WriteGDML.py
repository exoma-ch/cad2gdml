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
import os
import re
from GUIMeshLibs import Materials
from GUIMeshLibs import Volumes

# Default filename prefix that identifies crystal volumes when emitting copy
# numbers. Matches g4ring's add_copynumbers.py so the two produce identical GDML.
DEFAULT_COPYNUMBER_PREFIX = "_detector_lyso_"


def _crystal_physvol_open(gdml_filename, prefix):
    """Return the ``<physvol ...>`` opening tag for a child include.

    With ``prefix`` set, crystal volumes (whose file is ``<prefix><N>.gdml``,
    or the bare ``<prefix>.gdml`` for the un-numbered first instance) get a
    ``name`` and ``copynumber`` attribute; everything else, and the ``prefix is
    None`` case, stay a bare ``<physvol>``. The number extraction and ``_PV``
    naming reproduce g4ring's add_copynumbers.py exactly, so exporting with
    ``--add-copynumbers`` is equivalent to running that script afterwards.

    gPET-sim's readout keys on this copy number (``GetCopyNo()``); without it
    every hit lands with volume id 0.
    """
    if prefix is None:
        return '<physvol>'
    m = re.search(re.escape(prefix) + r'(\d+)\.gdml', gdml_filename)
    if m:
        crystal_num = int(m.group(1))
    elif (prefix + '.gdml') in gdml_filename:
        crystal_num = 0
    else:
        return '<physvol>'
    base_name = gdml_filename.replace('.gdml', '_PV')
    return '<physvol name="{}" copynumber="{}">'.format(base_name, crystal_num)

# --- native-box export ------------------------------------------------------
# A part whose tessellation is a plain cuboid is exported as a native GDML
# <box> (plus a per-part placement transform) instead of a <tessellated> mesh.
# Geant4 navigates a G4Box analytically instead of triangle-by-triangle, which
# is a large Stage-2 speedup for scanners built from thousands of crystals.
# Non-cuboid parts stay tessellated, byte-for-byte as before.
#
# Orientation/dimensions come from the part's three principal edges (shared with
# the crystal-map extractor, CrystalCenters.principal_edges). The GDML rotation
# convention and the corner-reconstruction check are ported verbatim from the
# vetted downstream prototype (gPET-sim scripts/issue110/gen_box_gdml.py).
# See BOX_EXPORT_HANDOFF.md.

# Max allowed disagreement (mm) between a reconstructed box corner and the
# original tessellated vertex. The prototype measured < 3e-13 mm over a full
# scanner; anything above this tolerance means the shape is not a clean cuboid
# (or a convention bug), so we fall back to tessellated.
_BOX_CORNER_TOL_MM = 1e-3


def _angles_from_R(R):
    """Extract (ax, ay, az) from R = Rz(az)·Ry(ay)·Rx(ax). Ported verbatim."""
    import numpy as np
    if abs(R[2, 0]) < 1 - 1e-9:
        ay = np.arcsin(-R[2, 0])
        ax = np.arctan2(R[2, 1], R[2, 2])
        az = np.arctan2(R[1, 0], R[0, 0])
    else:  # gimbal lock
        ay = np.pi / 2 * (-np.sign(R[2, 0]))
        ax = np.arctan2(-R[1, 2], R[1, 1])
        az = 0.0
    return ax, ay, az


def _R_from_angles(ax, ay, az):
    """Rebuild R = Rz(az)·Ry(ay)·Rx(ax) — the matrix Geant4 builds internally."""
    import numpy as np
    cx, sx = np.cos(ax), np.sin(ax)
    cy, sy = np.cos(ay), np.sin(ay)
    cz, sz = np.cos(az), np.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _box_from_vertices(vertices, label=""):
    """Return the native-box description of ``vertices`` if they form a cuboid.

    On success returns a dict with:
      - ``center``  : box centre in the CAD frame (mm), numpy (3,)
      - ``full``    : full box dimensions (mm) along local x,y,z (long→short)
      - ``angles``  : (ax, ay, az) in radians for the physvol <rotation>

    Returns ``None`` if the shape is not a clean cuboid, so the caller keeps the
    tessellated path. Orientation and dimensions come from the part's three
    principal edges (:func:`CrystalCenters.principal_edges`, the same
    decomposition used to build the crystal map) — extent-independent, so cubes
    and square cross-sections work. The part is a box only if those edges are
    mutually orthogonal. Every candidate is then verified by reconstructing all
    8 corners with the exact placement math Geant4 will use
    (``p_world = Rᵀ·p_local + centre``) and requiring agreement <
    ``_BOX_CORNER_TOL_MM``, else it falls back to tessellated.
    """
    import numpy as np
    from GUIMeshLibs.CrystalCenters import principal_edges

    pts = np.asarray(vertices, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 3 or pts.shape[0] != 8:
        return None

    edges = principal_edges(pts)                       # 3 (unit, length), long→short
    if edges is None:
        return None
    units = np.array([u for u, _ in edges])            # rows = edge unit vectors
    lengths = np.array([L for _, L in edges])
    if (lengths <= 0).any():
        return None

    # A cuboid's edges are mutually orthogonal; a sheared parallelepiped is not
    # a box (a G4Box would misplace material), so keep it tessellated.
    if np.abs(units @ units.T - np.eye(3)).max() > 1e-6:
        return None

    V = units.T                                        # columns = local axes in world
    if np.linalg.det(V) < 0:
        V[:, 0] = -V[:, 0]                             # proper rotation (det +1)
    center = pts.mean(0)                               # cuboid centroid == centre
    half = lengths / 2.0
    # We want Rᵀ = V (columns = local axes in world), so R = Vᵀ.
    ax, ay, az = _angles_from_R(V.T)

    # Safety net: reconstruct the 8 corners the way Geant4 will and compare to
    # the original vertices. This is the guard against orientation bugs.
    Rchk = _R_from_angles(ax, ay, az)
    corners = np.array([[sx, sy, sz]
                        for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)],
                       dtype=float)
    recon = (Rchk.T @ (corners * half).T).T + center
    d = np.linalg.norm(recon[:, None, :] - pts[None, :, :], axis=2)
    err = max(d.min(1).max(), d.min(0).max())
    if err > _BOX_CORNER_TOL_MM:
        # Looked like a cuboid but the reconstruction disagrees — flag loudly
        # and fall back to tessellated (always correct) rather than emit a box
        # that would place the solid wrong.
        print("Warning: {} looks cuboid but box reconstruction error is "
              "{:.2e} mm (> {:.0e} mm); keeping tessellated.".format(
                  label, err, _BOX_CORNER_TOL_MM))
        return None

    return {'center': center, 'full': lengths, 'angles': (ax, ay, az), 'err': err}


def annotate_boxes(object_list, verbose=False):
    """Tessellate each exported part once and tag it as box vs mesh.

    Sets on every object with ``VolumeGDMLoption == 1``:
      - ``obj._triangles`` : the ``Shape.tessellate`` result (reused by CreateGDML)
      - ``obj._box``       : dict from :func:`_box_from_vertices`, or ``None`` (mesh)

    Cuboids are exported as native ``<box>``; everything else stays tessellated.
    Computed here once so CreateMother and CreateGDML share the same decision
    (and the same vertices) without tessellating twice.
    """
    n_incl = 0
    n_box = 0
    max_err = 0.0
    for obj in object_list:
        obj._box = None
        obj._triangles = None
        if getattr(obj, 'VolumeGDMLoption', None) != 1:
            continue
        n_incl += 1
        try:
            triangles = obj.VolumeCAD.Shape.tessellate(obj.VolumeMMD)
        except Exception as e:
            print("Warning: tessellate failed for {} ({}); keeping mesh path.".format(
                obj.VolumeCAD.Label, e))
            continue
        obj._triangles = triangles
        box = _box_from_vertices(triangles[0], label=str(obj.VolumeCAD.Label))
        obj._box = box
        if box is not None:
            n_box += 1
            max_err = max(max_err, box['err'])
            if verbose:
                bx, by, bz = box['full']
                print("  box: {:30s} dims=({:.3f}, {:.3f}, {:.3f}) mm  "
                      "corner-err={:.1e} mm".format(str(obj.VolumeCAD.Label),
                                                    bx, by, bz, box['err']))

    print("Native-box export: {}/{} exported parts are cuboids -> <box> "
          "(max corner reconstruction error {:.1e} mm); rest stay tessellated.".format(
              n_box, n_incl, max_err))
    return n_box


def _write_inline_default_vacuum(F):
    """Legacy hardcoded vacuum block kept for backward compatibility when no
    world material is supplied via the mapping JSON."""
    F.write('<element name="Vacuum_el"  formula="Hv" Z="1">\n')
    F.write('<atom value="1.008"/>\n')
    F.write('</element> \n')
    F.write('<material name="Vacuum">\n')
    F.write('<D value="0.0000000000000000000001" unit="mg/cm3"/>\n')
    F.write('<fraction n="1.0" ref="Vacuum_el"/>\n')
    F.write('</material>\n')


def _write_world_material_from_object(F, mat):
    """Render a Material object using the same style as per-volume GDMLs."""
    F.write('<material name="'+str(mat.Name)+'" state="solid">\n')
    F.write('<D unit="g/cm3" value="'+str(mat.Density)+'"/>\n')
    for i in range(mat.Nelements):
        F.write('<fraction n="'+str(mat.ElementFractions[i])+'" ref="'+str(mat.Elements[i])+'"/>\n')
    F.write('</material>\n')


#Write Mother.gdml file
def CreateMother(dir_path,object_list,world,world_pos=[0.0,0.0,0.0],world_material=None,
                 copynumber_prefix=None):
    """Write mother.gdml.

    world_material:
      - None (default): emit the legacy inline ``Vacuum`` block (Vacuum_el / mg/cm3 form).
        Preserves byte-stable output for existing test references and any GDML consumer
        that depends on the historical format.
      - A loaded ``Materials.Material`` object: render that material using the same
        per-volume style (state, g/cm3 density, NIST-element fraction refs).
        The world's ``<materialref>`` is the material's name.

    copynumber_prefix:
      - None (default): child ``<physvol>`` tags are bare (byte-stable output).
      - A string (e.g. ``"_detector_lyso_"``): crystal physvols get ``name`` and
        ``copynumber`` attributes, matching g4ring's add_copynumbers.py so no
        separate post-processing step is needed. See :func:`_crystal_physvol_open`.
    """
    world_material_name = world_material.Name if world_material is not None else "Vacuum"
    #write headers and globals
    F=open(str(dir_path)+"/mother.gdml","w")
    F.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
    F.write('<gdml xmlns:gdml="../schema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="../schema/gdml.xsd" >\n')
    F.write('<!--\n')
    F.write('  Geometry Transformation Information:\n')
    if world_pos != [0.0, 0.0, 0.0]:
        F.write('  Geometry has been translated to center the bounding box at (0, 0, 0).\n')
        # The actual translation applied to geometry is -world_pos (see geometry_offset below)
        translation_applied = [-world_pos[0], -world_pos[1], -world_pos[2]]
        F.write('  Translation applied to geometry: ({:.6f}, {:.6f}, {:.6f}) m\n'.format(translation_applied[0], translation_applied[1], translation_applied[2]))
        F.write('  Translation in mm: ({:.3f}, {:.3f}, {:.3f}) mm\n'.format(translation_applied[0]*1000.0, translation_applied[1]*1000.0, translation_applied[2]*1000.0))
        F.write('  Crystal center coordinates in output files are in the transformed (centered) coordinate system.\n')
        F.write('  To convert back to original CAD coordinates, subtract the translation values.\n')
    else:
        F.write('  Geometry uses original CAD coordinates (no translation applied).\n')
    F.write('  For detailed transformation information, see geometry_transform.json in the output directory.\n')
    F.write('-->\n')
    F.write('<define>\n')
    # Translate geometry volumes to center them in world box (world is at origin)
    # Negative of world position to center geometry in world
    F.write('<position name="geometry_offset" x="'+str(-world_pos[0])+'" y="'+str(-world_pos[1])+'" z="'+str(-world_pos[2])+'" unit="m"/>\n')
    F.write('<rotation name="identity" x="0" y="0" z="0"/>\n')
    F.write('</define>\n')
    #write material information
    F.write('<materials>\n')
    if world_material is None:
        _write_inline_default_vacuum(F)
    else:
        _write_world_material_from_object(F, world_material)
    # Aggregate unique volume materials so each is declared exactly once at
    # mother scope. Children reference them via <materialref>; without this,
    # every child re-declared its material and Geant4's GDML parser emitted a
    # "duplicate name of material" warning per include.
    seen = {world_material_name}
    for obj in object_list:
        if obj.VolumeGDMLoption != 1:
            continue
        mat = obj.VolumeMaterial
        if mat.Nelements == 0 or mat.Name in seen:
            continue
        seen.add(mat.Name)
        _write_world_material_from_object(F, mat)
    F.write('</materials>\n')
    #write solid information (world volume)
    F.write('<solids>\n')
    F.write('<box name="WorldBox" x="'+str(world[0])+'" y="'+str(world[1])+'" z="'+str(world[2])+'" lunit="m"/>\n')
    F.write('</solids>\n')
    #write structure
    F.write('<structure>\n')
    F.write('<volume name="World">\n')
    F.write('<materialref ref="'+world_material_name+'"/>\n')
    F.write('<solidref ref="WorldBox"/>\n')
    # geometry_offset in mm (define block is in metres): applied to every part
    # to centre the bounding box at the origin. Mesh parts reference it; box
    # parts carry a per-part position, so we bake the offset into that position.
    offset_mm = [-world_pos[0]*1000.0, -world_pos[1]*1000.0, -world_pos[2]*1000.0]
    for i in range(0,len(object_list)):
        if (object_list[i].VolumeGDMLoption==1):
            # Use volume label directly - normalization happens at the end
            gdml_filename = str(object_list[i].VolumeCAD.Label) + ".gdml"
            F.write(_crystal_physvol_open(gdml_filename, copynumber_prefix)+'\n')
            F.write('<file name="Volumes/'+gdml_filename+'"/>\n')
            box = getattr(object_list[i], '_box', None)
            if box is not None:
                # Native box: place the origin-centred G4Box with its own pose.
                # position = box centre (CAD, mm) + geometry_offset (mm);
                # rotation = (ax, ay, az) such that p_world = Rᵀ·p_local + pos.
                cx = box['center'][0] + offset_mm[0]
                cy = box['center'][1] + offset_mm[1]
                cz = box['center'][2] + offset_mm[2]
                ax, ay, az = box['angles']
                F.write('<position x="{:.10f}" y="{:.10f}" z="{:.10f}" unit="mm"/>\n'.format(cx, cy, cz))
                F.write('<rotation x="{:.12f}" y="{:.12f}" z="{:.12f}" unit="rad"/>\n'.format(ax, ay, az))
            else:
                # Translate geometry to center it in world box
                F.write('<positionref ref="geometry_offset"/>\n')
                F.write('<rotationref ref="identity"/>\n')
            F.write('</physvol>\n')
    F.write('</volume>\n')
    F.write('</structure>\n')
    F.write('<setup name="Default" version="1.0">\n')
    F.write('<world ref="World"/>\n')
    F.write('</setup>\n')
    F.write('</gdml>') 
    F.close()

     
####################Function to write individual volume GDML file#####################     
def CreateGDML(obj,vol_numb,path_to_mesh):
    # Box vs mesh is decided once in annotate_boxes (which also caches the
    # tessellation on obj._triangles). Fall back to tessellating here if this
    # part was never annotated (e.g. CreateGDML called directly).
    box = getattr(obj, '_box', None)
    triangles = getattr(obj, '_triangles', None)
    if triangles is None:
        triangles = obj.VolumeCAD.Shape.tessellate(obj.VolumeMMD)
    count=0

    # Use volume label directly - normalization happens at the end
    gdml_name = str(obj.VolumeCAD.Label)
    #write file
    F=open(str(path_to_mesh)+"/Volumes/"+gdml_name+".gdml","w")
    #write header
    F.write('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n')
    F.write('<gdml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://service-spi.web.cern.ch/service-spi/app/releases/GDML/schema/gdml.xsd">\n')
    if box is not None:
        # Native cuboid: a G4Box at the origin, axis-aligned. The pose lives in
        # the mother's per-part <position>/<rotation> (see CreateMother).
        bx, by, bz = box['full']
        F.write(' <define>\n')
        F.write(" </define>\n\n")
        # Material is declared once in mother.gdml; children reference it via
        # <materialref> only. See CreateMother for the aggregated <materials> block.
        F.write(" <solids>\n")
        F.write(' <box lunit="mm" name="'+gdml_name+'_solid" x="{:.10f}" y="{:.10f}" z="{:.10f}"/>\n'.format(bx, by, bz))
        F.write(' <box lunit="mm" name="worldsolid" x="1000" y="1000" z="1000"/>\n')
        F.write(' </solids>'+"\n")
    else:
        #write position
        F.write(' <define>\n')
        for tri in triangles[0]:
            F.write(' <position name="'+gdml_name+'_v'+str(count)+'" unit="mm" x="'+str(tri[0])+'" y="'+str(tri[1])+'" z="'+str(tri[2])+'"/>\n')
            count=count+1
        F.write(" </define>\n\n")
        # Material is declared once in mother.gdml; children reference it via
        # <materialref> only. See CreateMother for the aggregated <materials> block.
        #write solids
        F.write(" <solids>\n")
        F.write(' <tessellated aunit="deg" lunit="mm" name="'+gdml_name+'_solid">\n')
        count=0
        for tri in triangles[1]:
            F.write(' <triangular vertex1="'+gdml_name+'_v'+str(tri[0])+'" vertex2="'+gdml_name+'_v'+str(tri[1])+'" vertex3="'+gdml_name+'_v'+str(tri[2])+'"/>'+"\n")
            count+=3
        F.write(' </tessellated>\n')
        F.write(' <box lunit="mm" name="worldsolid" x="1000" y="1000" z="1000"/>\n')
        F.write(' </solids>'+"\n")
    #write structure
    F.write(' <structure>\n')
    F.write(' <volume name="'+gdml_name+'">\n')
    F.write(' <materialref ref="'+str(obj.VolumeMaterial.Name)+'"/>'+"\n")
    F.write(' <solidref ref="'+gdml_name+'_solid"/>'+"\n")
    F.write(' </volume>\n')
    F.write(' </structure>\n')
    F.write(' <setup name="Default" version="1.0">'+"\n")
    F.write(' <world ref="'+gdml_name+'"/>'+"\n")
    F.write(' </setup>'+"\n")
    F.write('</gdml>')
    F.close()

# Function to normalize base volume names (no longer needed - keeping original names)
def normalize_base_volumes(volumes_dir):
    # No longer performing any normalization - keeping original names as they are
    pass

#Note: A number is added to each volumes label to avoid that two different volumes have the same name. This can be seen in the mother and in the volumes GDMLs
