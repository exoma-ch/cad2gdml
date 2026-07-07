"""Unit tests for the hierarchical export (--hier) and the overlap check.

Pure numpy — a synthetic uniform ring of fake annotated Volume objects stands
in for a FreeCAD STEP import, so these run on the host as well as in the
container. The scanner axial axis is deliberately z (the downstream prototype
hardcoded y) to exercise the generalized axial-axis detection.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pytest

freecad_path = '/usr/local/bin/squashfs-root/usr/lib'
if freecad_path not in sys.path:
    sys.path.append(freecad_path)
sys.path.insert(0, str(Path(__file__).parent.parent / "libs"))
sys.path.insert(0, str(Path(__file__).parent.parent / "libs" / "GUIMeshLibs"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from GUIMeshLibs import HierGDML, OverlapCheck, WriteGDML
    LIBS_AVAILABLE = True
except Exception:  # pragma: no cover - environment without the package layout
    LIBS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not LIBS_AVAILABLE, reason="GUIMeshLibs not importable in this environment")


# ---------------------------------------------------------------- fakes -----

class FakeCAD:
    def __init__(self, label):
        self.Label = label


class FakeMat:
    def __init__(self, name):
        self.Name = name
        self.Nelements = 0


class FakeObj:
    def __init__(self, label, material, box=None, triangles=None):
        self.VolumeCAD = FakeCAD(label)
        self.VolumeMaterial = FakeMat(material)
        self.VolumeGDMLoption = 1
        self.VolumeMMD = 0.1
        self._box = box
        self._triangles = triangles


def box_obj(label, material, center, M, full):
    """Fake annotated native-box part; M columns = local axes in world."""
    angles = WriteGDML._angles_from_R(np.asarray(M, float).T)
    return FakeObj(label, material, box={
        'center': np.asarray(center, float),
        'full': np.asarray(full, float),
        'angles': angles, 'err': 0.0})


def tray_triangulation(M, center, outer_full, wall, plate):
    """Closed triangulated five-sided tray (open at local -z): 16 unique
    vertices, consistently outward-wound triangles. Local frame = columns of M,
    plate at local +z."""
    ox, oy, oz = np.asarray(outer_full, float) / 2.0
    ix, iy = ox - wall, oy - wall
    iz = oz - plate                                  # cavity ceiling (local z)
    verts, index = [], {}

    def vid(p):
        key = tuple(np.round(p, 9))
        if key not in index:
            index[key] = len(verts)
            verts.append(p)
        return index[key]

    tris = []

    def tri(p0, p1, p2, outward):
        p0, p1, p2 = (np.asarray(p, float) for p in (p0, p1, p2))
        if np.dot(np.cross(p1 - p0, p2 - p0), outward) < 0:
            p1, p2 = p2, p1
        tris.append((vid(p0), vid(p1), vid(p2)))

    def rect(p0, p1, p2, p3, outward):
        tri(p0, p1, p2, outward)
        tri(p0, p2, p3, outward)

    # outer top plate face (+z) and 4 outer sides
    rect((-ox, -oy, oz), (ox, -oy, oz), (ox, oy, oz), (-ox, oy, oz), (0, 0, 1))
    rect((-ox, -oy, -oz), (-ox, oy, -oz), (-ox, oy, oz), (-ox, -oy, oz), (-1, 0, 0))
    rect((ox, -oy, -oz), (ox, oy, -oz), (ox, oy, oz), (ox, -oy, oz), (1, 0, 0))
    rect((-ox, -oy, -oz), (ox, -oy, -oz), (ox, -oy, oz), (-ox, -oy, oz), (0, -1, 0))
    rect((-ox, oy, -oz), (ox, oy, -oz), (ox, oy, oz), (-ox, oy, oz), (0, 1, 0))
    # bottom rim: annulus between the outer and inner bottom rectangles,
    # triangulated with only the 8 existing corners (normal -z)
    O = [(-ox, -oy, -oz), (ox, -oy, -oz), (ox, oy, -oz), (-ox, oy, -oz)]
    I = [(-ix, -iy, -oz), (ix, -iy, -oz), (ix, iy, -oz), (-ix, iy, -oz)]
    for k in range(4):
        tri(O[k], O[(k + 1) % 4], I[(k + 1) % 4], (0, 0, -1))
        tri(O[k], I[(k + 1) % 4], I[k], (0, 0, -1))
    # inner cavity: 4 sides (normals point INTO the cavity) and ceiling
    rect((-ix, -iy, -oz), (-ix, iy, -oz), (-ix, iy, iz), (-ix, -iy, iz), (1, 0, 0))
    rect((ix, -iy, -oz), (ix, iy, -oz), (ix, iy, iz), (ix, -iy, iz), (-1, 0, 0))
    rect((-ix, -iy, -oz), (ix, -iy, -oz), (ix, -iy, iz), (-ix, -iy, iz), (0, 1, 0))
    rect((-ix, iy, -oz), (ix, iy, -oz), (ix, iy, iz), (-ix, iy, iz), (0, -1, 0))
    rect((-ix, -iy, iz), (ix, -iy, iz), (ix, iy, iz), (-ix, iy, iz), (0, 0, -1))

    M = np.asarray(M, float)
    world = [(M @ v + np.asarray(center, float)).tolist() for v in verts]
    return world, tris


# ------------------------------------------------------- synthetic ring -----

N_PANELS = 8
RING_R = 70.0            # crystal-stack centre radius (mm)
CRYSTAL_FULL = (4.0, 5.0, 20.0)          # tangential, axial, radial
CRYSTAL_PITCH_T, CRYSTAL_PITCH_A = 4.5, 5.5
SIPM_FULL = (8.0, 10.0, 1.5)   # fits the 8.4 x 10.4 tray cavity
TRAY_OUTER = (12.0, 14.0, 26.0)          # cavity 8.4 x 12 — walls overlap the
TRAY_WALL, TRAY_PLATE = 1.8, 1.0         # crystal grid (span 8.5) by 0.05 mm
TRAY_R = 71.0                            # tray centre radius; plate at 84


def panel_frame(phi):
    d = np.array([np.cos(phi), np.sin(phi), 0.0])       # radial (long axis)
    eT = np.cross([0.0, 0.0, 1.0], d)
    eA = np.cross(d, eT)
    return np.stack([eT, eA, d], axis=1)


def make_ring(perturb_radius_of=None, with_trays=True, with_rail=True):
    objs = []
    cid = 0
    for m in range(N_PANELS):
        phi = 2 * np.pi * m / N_PANELS
        M = panel_frame(phi)
        r0 = RING_R + (1.0 if perturb_radius_of == m else 0.0)
        for st in (-0.5, 0.5):
            for sa in (-0.5, 0.5):
                cid += 1
                c = M @ np.array([st * CRYSTAL_PITCH_T, sa * CRYSTAL_PITCH_A, r0])
                objs.append(box_obj('_detector_lyso_{:03d}'.format(cid),
                                    'LYSO', c, M, CRYSTAL_FULL))
        objs.append(box_obj('sipm_si{:03d}'.format(m + 1), 'G4_Si',
                            M @ np.array([0.0, 0.0, r0 + 10.0 + 0.8]),
                            M, SIPM_FULL))
        if with_trays:
            # Tray local +z = radial (plate at the outer radius, open inward).
            verts, tris = tray_triangulation(
                M, M @ np.array([0.0, 0.0, TRAY_R]), TRAY_OUTER,
                TRAY_WALL, TRAY_PLATE)
            objs.append(FakeObj('unit-cover_plastic{:03d}'.format(m + 1),
                                'G4_POLYETHYLENE', triangles=(verts, tris)))
    if with_rail:
        # Long box between two panel azimuths, radially outside every wedge.
        phi = np.pi / N_PANELS
        M = panel_frame(phi)
        objs.append(box_obj('rail_al001', 'G4_Al',
                            M @ np.array([0.0, 0.0, 96.0]), M,
                            (40.0, 5.0, 3.0)))
    return objs


def crystal_centers(objs):
    out = {}
    for o in objs:
        m = re.fullmatch(r'_detector_lyso_(\d+)', o.VolumeCAD.Label)
        if m:
            out[int(m.group(1))] = np.asarray(o._box['center'])
    return out


def parse_hier_crystals(path):
    """Reconstruct crystal world centres (by copynumber) from mother_hier.gdml
    through the exact nested Geant4 placement math."""
    txt = Path(path).read_text()
    lv_bodies = dict(re.findall(
        r'<volume name="(module_env_\d+)_LV">(.*?)</volume>', txt, re.S))
    world = txt[txt.index('<volume name="World">'):]
    centers = {}
    for pv in re.finditer(
            r'<physvol name="(module_env_\d+)_PV"[^>]*>(.*?)</physvol>',
            world, re.S):
        env, body = pv.group(1), pv.group(2)
        pm = re.search(r'<position[^>]*x="([^"]+)" y="([^"]+)" z="([^"]+)"', body)
        rm = re.search(r'<rotation[^>]*x="([^"]+)" y="([^"]+)" z="([^"]+)"', body)
        pos_e = np.array([float(pm.group(k)) for k in (1, 2, 3)])
        Re = WriteGDML._R_from_angles(*[float(rm.group(k)) for k in (1, 2, 3)])
        for cv in re.finditer(
                r'<physvol name="[^"]*" copynumber="(\d+)">(.*?)</physvol>',
                lv_bodies[env], re.S):
            cn = int(cv.group(1))
            cm = re.search(r'<position[^>]*x="([^"]+)" y="([^"]+)" z="([^"]+)"',
                           cv.group(2))
            pos_c = np.array([float(cm.group(k)) for k in (1, 2, 3)])
            centers[cn] = Re.T @ pos_c + pos_e
    return centers, txt


# ---------------------------------------------------------------- tests -----

def test_tray_triangulation_volume():
    verts, tris = tray_triangulation(np.eye(3), (0, 0, 0), (20, 24, 10), 1.0, 2.0)
    assert len(verts) == 16
    expected = 20 * 24 * 10 - 18 * 22 * 8
    assert abs(HierGDML._mesh_volume((verts, tris)) - expected) < 1e-9


def test_decompose_cover_exact():
    M = WriteGDML._R_from_angles(0.3, -0.5, 0.9).T
    center = np.array([12.0, -7.0, 30.0])
    verts, tris = tray_triangulation(M, center, (20, 24, 10), 1.0, 2.0)
    dec = HierGDML._decompose_cover(np.asarray(verts))
    assert dec is not None
    boxes, vol = dec
    assert len(boxes) == 5
    assert abs(vol - (20 * 24 * 10 - 18 * 22 * 8)) < 1e-6


def test_hier_export_synthetic_ring(tmp_path, capsys):
    objs = make_ring()
    out = HierGDML.write_hier_gdml(str(tmp_path), objs, [1.0, 1.0, 1.0])
    log = capsys.readouterr().out
    assert '8 panels' in log
    centers, txt = parse_hier_crystals(out)

    # every crystal present with its copynumber, placed exactly (nested math)
    truth = crystal_centers(objs)
    assert set(centers) == set(truth)
    for cn, c in centers.items():
        assert np.linalg.norm(c - truth[cn]) < 1e-6

    # structure: 8 wedges, shared crystal LV (prefix substring preserved),
    # cover slabs decomposed, rail kept in the world as a file include
    assert txt.count('<trd name="module_env_') == N_PANELS
    assert '_detector_lyso_box_LV' in txt
    assert 'cover_slab_0_LV' in txt
    assert '<file name="Volumes/rail_al001.gdml"/>' in txt
    world = txt[txt.index('<volume name="World">'):]
    assert world.count('<physvol name="module_env_') == N_PANELS
    # trays joined the envelopes: no cover file includes in the world
    assert 'unit-cover' not in world

    # interpenetrating tray walls were clipped to the crystal faces
    assert re.search(r'gates: .*; (\d+) cover-slab clips', log)
    assert int(re.search(r'; (\d+) cover-slab clips', log).group(1)) > 0


def test_hier_rejects_nonuniform_ring(tmp_path):
    objs = make_ring(perturb_radius_of=2, with_trays=False, with_rail=False)
    with pytest.raises(HierGDML.HierExportError, match='common radius'):
        HierGDML.write_hier_gdml(str(tmp_path), objs, [1.0, 1.0, 1.0])


def test_hier_requires_crystals(tmp_path):
    objs = [box_obj('sipm_si001', 'G4_Si', (0, 0, 50), np.eye(3), (8, 11, 1.5))]
    with pytest.raises(HierGDML.HierExportError, match='no crystal volumes'):
        HierGDML.write_hier_gdml(str(tmp_path), objs, [1.0, 1.0, 1.0])


def test_crystal_number_extraction():
    f = HierGDML._crystal_number
    assert f('_detector_lyso_042', '_detector_lyso_') == 42
    assert f('_detector_lyso_', '_detector_lyso_') == 0
    assert f('sipm_si042', '_detector_lyso_') is None
    assert f('_detector_lyso_042_extra', '_detector_lyso_') is None


def test_overlap_check_flags_interpenetration(capsys):
    M = np.eye(3)
    a = box_obj('a', 'LYSO', (0, 0, 0), M, (10, 10, 10))
    b = box_obj('b', 'LYSO', (9.85, 0, 0), M, (10, 10, 10))   # 0.15 mm overlap
    overlaps = OverlapCheck.check_overlaps([a, b])
    assert len(overlaps) == 1
    assert abs(overlaps[0]['depth_mm'] - 0.15) < 1e-9


def test_overlap_check_accepts_touching_and_rotated(capsys):
    M = np.eye(3)
    a = box_obj('a', 'LYSO', (0, 0, 0), M, (10, 10, 10))
    b = box_obj('b', 'LYSO', (10.0, 0, 0), M, (10, 10, 10))    # exactly touching
    # rotated 45 deg about z, corner pointing at a's face but 0.1 mm clear
    Mr = WriteGDML._R_from_angles(0.0, 0.0, np.pi / 4).T
    c = box_obj('c', 'LYSO', (0, 5 + np.sqrt(50) + 0.1, 0), Mr, (10, 10, 10))
    assert OverlapCheck.check_overlaps([a, b, c]) == []
