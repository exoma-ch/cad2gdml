"""Unit tests for the --add-copynumbers physvol tagging in WriteGDML.

Pure-string logic (no FreeCAD); the module is skipped if WriteGDML cannot be
imported. The expected outputs mirror g4ring's add_copynumbers.py so that
exporting with --add-copynumbers is equivalent to running that script.
"""
import sys
from pathlib import Path

import pytest

freecad_path = '/usr/local/bin/squashfs-root/usr/lib'
if freecad_path not in sys.path:
    sys.path.append(freecad_path)
sys.path.insert(0, str(Path(__file__).parent.parent / "libs"))
sys.path.insert(0, str(Path(__file__).parent.parent / "libs" / "GUIMeshLibs"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from GUIMeshLibs import WriteGDML
    WRITEGDML_AVAILABLE = True
except Exception:  # pragma: no cover
    WRITEGDML_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not WRITEGDML_AVAILABLE, reason="WriteGDML not importable in this environment")

PREFIX = "_detector_lyso_"


def test_prefix_none_is_bare_physvol():
    # Default (no flag) keeps output byte-stable.
    assert WriteGDML._crystal_physvol_open("_detector_lyso_976.gdml", None) == "<physvol>"


def test_numbered_crystal_gets_name_and_copynumber():
    assert WriteGDML._crystal_physvol_open("_detector_lyso_976.gdml", PREFIX) == \
        '<physvol name="_detector_lyso_976_PV" copynumber="976">'


def test_zero_padded_number_preserved_in_name_int_in_copynumber():
    assert WriteGDML._crystal_physvol_open("_detector_lyso_001.gdml", PREFIX) == \
        '<physvol name="_detector_lyso_001_PV" copynumber="1">'


def test_bare_prefix_maps_to_zero():
    # FreeCAD's first instance has no numeric suffix -> copynumber 0.
    assert WriteGDML._crystal_physvol_open("_detector_lyso_.gdml", PREFIX) == \
        '<physvol name="_detector_lyso__PV" copynumber="0">'


def test_non_crystal_stays_bare():
    for fn in ("sipm_si138.gdml", "pcb-sipm_pcb023.gdml", "unit-cover_plastic.gdml"):
        assert WriteGDML._crystal_physvol_open(fn, PREFIX) == "<physvol>"


def test_custom_prefix():
    assert WriteGDML._crystal_physvol_open("crystalX_042.gdml", "crystalX_") == \
        '<physvol name="crystalX_042_PV" copynumber="42">'
    assert WriteGDML._crystal_physvol_open("_detector_lyso_5.gdml", "crystalX_") == "<physvol>"
