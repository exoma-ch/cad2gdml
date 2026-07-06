"""Unit tests for native-box export math in WriteGDML.

These exercise the cuboid detection and the vertex->box+rotation fit that
turns a tessellated cuboid into a native GDML <box> plus placement transform.
They are pure-numpy (no FreeCAD/STEP needed) but import WriteGDML, whose
top-level imports assume the package layout is on sys.path, so the whole module
is skipped if WriteGDML cannot be imported (e.g. outside the container).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

# Same sys.path bootstrap the other tests use.
freecad_path = '/usr/local/bin/squashfs-root/usr/lib'
if freecad_path not in sys.path:
    sys.path.append(freecad_path)
sys.path.insert(0, str(Path(__file__).parent.parent / "libs"))
# GUIMeshLibs.Volumes does a bare `import Materials`, so its own dir must be on
# the path too. With this, the module imports without FreeCAD (the box math is
# pure numpy), letting these tests run on the host as well as in the container.
sys.path.insert(0, str(Path(__file__).parent.parent / "libs" / "GUIMeshLibs"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from GUIMeshLibs import WriteGDML
    WRITEGDML_AVAILABLE = True
except Exception:  # pragma: no cover - environment without the package layout
    WRITEGDML_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not WRITEGDML_AVAILABLE, reason="WriteGDML not importable in this environment")

# 8 unit-cube corners (matches the ±half ordering the exporter reconstructs with).
UNIT_CORNERS = np.array(
    [[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], float)


def _R(ax, ay, az):
    """R = Rz(az)·Ry(ay)·Rx(ax) — the matrix Geant4 builds from the angles."""
    cx, sx = np.cos(ax), np.sin(ax)
    cy, sy = np.cos(ay), np.sin(ay)
    cz, sz = np.cos(az), np.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _make_cuboid(dims, R, center):
    """8 world vertices of a cuboid with the given full dims, orientation, centre."""
    half = np.asarray(dims, float) / 2.0
    return (R @ (UNIT_CORNERS * half).T).T + np.asarray(center, float)


def _reconstruct(box):
    """World corners implied by the emitted <box> + physvol transform.

    Uses the exact Geant4 placement convention p_world = Rᵀ·p_local + pos, so a
    match against the input vertices proves the emitted GDML is correct.
    """
    half = box['full'] / 2.0
    R = _R(*box['angles'])
    return (R.T @ (UNIT_CORNERS * half).T).T + box['center']


def _match_max_err(a, b):
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    return max(d.min(1).max(), d.min(0).max())


@pytest.mark.parametrize("dims", [
    (3.95, 5.3, 25.0),      # a scanner LYSO crystal (all extents distinct)
    (3.2, 3.2, 20.0),       # square cross-section (two equal extents)
    (10.0, 10.0, 10.0),     # a cube (all extents equal / degenerate covariance)
    (1.0, 2.0, 3.0),
])
@pytest.mark.parametrize("angles", [
    (0.0, 0.0, 0.0),
    (0.0, 0.0, 0.7),        # pure ring rotation about z
    (0.3, -0.9, 2.1),       # general orientation
])
def test_cuboid_detected_and_reconstructs(dims, angles):
    R = _R(*angles)
    center = np.array([120.0, -30.0, 55.0])
    verts = _make_cuboid(dims, R, center)

    box = WriteGDML._box_from_vertices(verts, label="test")
    assert box is not None, "clean cuboid should be detected"

    # Full dimensions recovered (order-independent: fit sorts by extent).
    assert sorted(box['full']) == pytest.approx(sorted(dims), abs=1e-6)
    # Centre recovered.
    assert box['center'] == pytest.approx(center, abs=1e-6)
    # The emitted box+transform reproduces the original vertices.
    assert _match_max_err(_reconstruct(box), verts) < 1e-6


def test_non_cuboid_rejected():
    # A tetrahedron-ish cloud (not a box) padded to 8 points must not fit a box.
    pts = np.array([
        [0, 0, 0], [10, 0, 0], [0, 10, 0], [0, 0, 10],
        [3, 3, 3], [7, 1, 2], [1, 8, 4], [2, 2, 9],
    ], float)
    assert WriteGDML._box_from_vertices(pts, label="tetra") is None


def test_too_few_vertices_rejected():
    assert WriteGDML._box_from_vertices(np.zeros((4, 3)), label="few") is None


def test_degenerate_flat_box_rejected():
    # Zero-thickness slab: a half-extent is 0, so it is not a valid solid box.
    flat = _make_cuboid((5.0, 5.0, 0.0), np.eye(3), (0, 0, 0))
    assert WriteGDML._box_from_vertices(flat, label="flat") is None


def test_sheared_parallelepiped_rejected():
    # 8-corner parallelepiped whose edges are not mutually orthogonal is not a
    # box (a G4Box would misplace material), so it must stay tessellated.
    e1 = np.array([10.0, 0.0, 0.0])
    e2 = np.array([2.0, 10.0, 0.0])   # skewed, not orthogonal to e1
    e3 = np.array([0.0, 0.0, 10.0])
    ref = np.array([0.0, 0.0, 0.0])
    verts = np.array([ref + a * e1 + b * e2 + c * e3
                      for a in (0, 1) for b in (0, 1) for c in (0, 1)])
    assert WriteGDML._box_from_vertices(verts, label="shear") is None
