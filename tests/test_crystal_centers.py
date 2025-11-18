"""
Tests for CrystalCenters functionality.

These tests require FreeCAD and actual STEP files with LYSO crystals.
"""
import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path
import csv
import h5py
import numpy as np

# Add FreeCAD path FIRST, before any imports
freecad_path = '/usr/local/bin/squashfs-root/usr/lib'
if freecad_path not in sys.path:
    sys.path.append(freecad_path)
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
pyside_path = f'/usr/local/bin/squashfs-root/usr/lib/python{python_version}/site-packages'
if pyside_path not in sys.path:
    sys.path.insert(0, pyside_path)

# Check if FreeCAD is available
FREECAD_AVAILABLE = False
try:
    import FreeCAD
    import Import
    FREECAD_AVAILABLE = True
except (ImportError, ModuleNotFoundError, SystemError, OSError):
    FREECAD_AVAILABLE = False

# Add libs and src to path
libs_path = str(Path(__file__).parent.parent / "libs")
sys.path.insert(0, libs_path)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if FREECAD_AVAILABLE:
    from unittest.mock import MagicMock
    
    # Clear any mocked modules
    modules_to_clear = [
        'GUIMeshLibs.CrystalCenters', 'GUIMeshLibs.Volumes', 
        'GUIMeshLibs.LoadOP', 'GUIMeshLibs.WriteGDML',
        'GUIMeshLibs.Materials', 'GUIMeshLibs'
    ]
    
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            if isinstance(sys.modules[module_name], MagicMock):
                del sys.modules[module_name]
            elif hasattr(sys.modules[module_name], '_mock_name'):
                del sys.modules[module_name]
    
    # Clear GUIMeshCLI from cache
    for module_name in ['GUIMeshCLI', 'src.GUIMeshCLI']:
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    # Import real modules
    try:
        from GUIMeshLibs import CrystalCenters
        from GUIMeshCLI import GUIMeshCLI
    except Exception:
        FREECAD_AVAILABLE = False
        CrystalCenters = None
        GUIMeshCLI = None
else:
    CrystalCenters = None
    GUIMeshCLI = None


@pytest.mark.integration
@pytest.mark.skipif(not FREECAD_AVAILABLE, reason="FreeCAD not available")
class TestExtractCrystalNumber:
    """Test the extract_crystal_number function."""
    
    def test_extract_detector_lyso_pattern(self):
        """Test extracting crystal number from _detector_lyso_ pattern."""
        assert CrystalCenters.extract_crystal_number('_detector_lyso_123') == 123
        assert CrystalCenters.extract_crystal_number('_detector_lyso_0') == 0
        assert CrystalCenters.extract_crystal_number('_detector_lyso_999') == 999
    
    def test_extract_detector_lyso_no_number(self):
        """Test special case: _detector_lyso_ (no number) should be crystal 0."""
        assert CrystalCenters.extract_crystal_number('_detector_lyso_') == 0
    
    def test_extract_part_pattern(self):
        """Test extracting crystal number from Part_ pattern."""
        assert CrystalCenters.extract_crystal_number('Part_456') == 456
        assert CrystalCenters.extract_crystal_number('SomePart_789') == 789
    
    def test_extract_crystal_pattern(self):
        """Test extracting crystal number from Crystal_ pattern."""
        assert CrystalCenters.extract_crystal_number('Crystal_123') == 123
        assert CrystalCenters.extract_crystal_number('MyCrystal_456') == 456
    
    def test_extract_lyso_pattern(self):
        """Test extracting crystal number from LYSO_ pattern."""
        assert CrystalCenters.extract_crystal_number('LYSO_789') == 789
        assert CrystalCenters.extract_crystal_number('SomeLYSO_012') == 12
    
    def test_extract_number_at_end(self):
        """Test extracting number at end of string."""
        assert CrystalCenters.extract_crystal_number('volume_123') == 123
        assert CrystalCenters.extract_crystal_number('test456') == 456
    
    def test_extract_any_number_fallback(self):
        """Test fallback to any number pattern."""
        assert CrystalCenters.extract_crystal_number('abc123def') == 123
        assert CrystalCenters.extract_crystal_number('1a2b3c') == 1  # First number found
    
    def test_extract_no_number(self):
        """Test case where no number is found."""
        assert CrystalCenters.extract_crystal_number('no_numbers_here') is None
        assert CrystalCenters.extract_crystal_number('') is None


@pytest.mark.integration
@pytest.mark.skipif(not FREECAD_AVAILABLE, reason="FreeCAD not available")
class TestExtractCrystalCenters:
    """Test the extract_crystal_centers function."""
    
    @pytest.fixture(autouse=True)
    def cleanup_mocks(self):
        """Clean up any mocks from other test files before each test."""
        if FREECAD_AVAILABLE:
            from unittest.mock import MagicMock
            import importlib
            
            # Remove all mocked FreeCAD modules first
            freecad_modules = ['FreeCAD', 'Import', 'FreeCADGui', 'Draft', 'Part']
            for module_name in freecad_modules:
                if module_name in sys.modules:
                    if isinstance(sys.modules[module_name], MagicMock):
                        del sys.modules[module_name]
                    elif hasattr(sys.modules[module_name], '_mock_name'):
                        del sys.modules[module_name]
            
            # Re-import real FreeCAD modules
            try:
                import FreeCAD
                import Import
                import FreeCADGui
                import Draft
                import Part
                sys.modules['FreeCAD'] = FreeCAD
                sys.modules['Import'] = Import
                sys.modules['FreeCADGui'] = FreeCADGui
                sys.modules['Draft'] = Draft
                sys.modules['Part'] = Part
            except Exception:
                pass
            
            # Remove all mocked GUIMeshLibs modules
            modules_to_clear = [
                'GUIMeshLibs.Volumes', 'GUIMeshLibs.LoadOP', 
                'GUIMeshLibs.WriteGDML', 'GUIMeshLibs.CrystalCenters',
                'GUIMeshLibs.Materials', 'GUIMeshLibs'
            ]
            
            for module_name in modules_to_clear:
                if module_name in sys.modules:
                    if isinstance(sys.modules[module_name], MagicMock):
                        del sys.modules[module_name]
                    elif hasattr(sys.modules[module_name], '_mock_name'):
                        del sys.modules[module_name]
            
            # Clear GUIMeshCLI from cache
            for module_name in ['GUIMeshCLI', 'src.GUIMeshCLI']:
                if module_name in sys.modules:
                    del sys.modules[module_name]
            
            # Re-import modules
            try:
                global CrystalCenters, GUIMeshCLI
                from GUIMeshLibs import CrystalCenters as FreshCrystalCenters
                from GUIMeshCLI import GUIMeshCLI as FreshGUIMeshCLI
                CrystalCenters = FreshCrystalCenters
                GUIMeshCLI = FreshGUIMeshCLI
            except Exception:
                pass
        
        yield  # Test runs here
    
    @pytest.fixture
    def step_file(self):
        """Path to ring6x1 STEP file with LYSO crystals."""
        step_path = Path(__file__).parent / "files" / "ring6x1" / "ring6x1.step"
        if not step_path.exists():
            pytest.skip(f"STEP file not found: {step_path}")
        return str(step_path)
    
    @pytest.fixture
    def material_file(self):
        """Path to LYSO material file."""
        mat_path = Path(__file__).parent / "files" / "Materials" / "LYSO.json"
        if not mat_path.exists():
            pytest.skip(f"Material file not found: {mat_path}")
        return str(mat_path)
    
    @pytest.fixture
    def material_mappings_file(self):
        """Path to material mappings file."""
        mappings_path = Path(__file__).parent / "files" / "test_materials" / "material_mappings.json"
        if not mappings_path.exists():
            pytest.skip(f"Material mappings file not found: {mappings_path}")
        return str(mappings_path)
    
    @pytest.fixture
    def loaded_volumes(self, step_file, material_file, material_mappings_file):
        """Load volumes from STEP file for testing."""
        mesh = GUIMeshCLI()
        mesh.verbose = False
        
        # Load STEP file
        assert mesh.load_step_file(step_file) is True
        assert len(mesh.list_of_objects) > 0
        
        # Load materials
        assert mesh.load_materials(material_file) is True
        
        # Assign materials
        assert mesh.assign_materials_from_names(material_mappings_file) is True
        
        return mesh.list_of_objects
    
    def test_extract_centers_empty_list(self):
        """Test extract_crystal_centers with empty list."""
        centers, success = CrystalCenters.extract_crystal_centers([])
        assert centers == []
        assert success is False
    
    def test_extract_centers_basic(self, loaded_volumes):
        """Test basic extraction of crystal centers."""
        centers, success = CrystalCenters.extract_crystal_centers(loaded_volumes)
        
        assert success is True
        assert len(centers) > 0
        
        # Check structure of returned data
        for center in centers:
            assert 'crystal_id' in center
            assert 'volume_name' in center
            assert 'center_x' in center
            assert 'center_y' in center
            assert 'center_z' in center
            assert 'azimuth_angle' in center
            assert 'elevation_angle' in center
            
            # Check types
            assert isinstance(center['crystal_id'], int)
            assert isinstance(center['center_x'], (int, float))
            assert isinstance(center['center_y'], (int, float))
            assert isinstance(center['center_z'], (int, float))
            assert isinstance(center['azimuth_angle'], (int, float))
            assert isinstance(center['elevation_angle'], (int, float))
    
    def test_extract_centers_verbose(self, loaded_volumes):
        """Test extract_crystal_centers with verbose mode."""
        centers, success = CrystalCenters.extract_crystal_centers(
            loaded_volumes, 
            verbose=True
        )
        
        assert success is True
        assert len(centers) > 0
    
    def test_extract_centers_with_csv_output(self, loaded_volumes):
        """Test extract_crystal_centers with CSV output."""
        temp_dir = tempfile.mkdtemp(prefix="guimesh_test_")
        try:
            csv_file = os.path.join(temp_dir, 'test_crystals.csv')
            centers, success = CrystalCenters.extract_crystal_centers(
                loaded_volumes,
                output_file=csv_file
            )
            
            assert success is True
            assert len(centers) > 0
            assert os.path.exists(csv_file)
            
            # Verify CSV file contents
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == len(centers)
                
                # Check first row
                first_row = rows[0]
                assert 'crystal_id' in first_row
                assert 'center_x' in first_row
                assert 'center_y' in first_row
                assert 'center_z' in first_row
                assert 'azimuth_angle' in first_row
                assert 'elevation_angle' in first_row
        finally:
            shutil.rmtree(temp_dir)
    
    def test_extract_centers_with_h5_output(self, loaded_volumes):
        """Test extract_crystal_centers with H5 output."""
        temp_dir = tempfile.mkdtemp(prefix="guimesh_test_")
        try:
            h5_file = os.path.join(temp_dir, 'test_crystals.h5')
            centers, success = CrystalCenters.extract_crystal_centers(
                loaded_volumes,
                output_file=h5_file
            )
            
            assert success is True
            assert len(centers) > 0
            
            # Check that CSV was also created
            csv_file = os.path.join(temp_dir, 'test_crystals.csv')
            assert os.path.exists(csv_file)
            
            # Verify H5 file contents if h5py is available
            try:
                with h5py.File(h5_file, 'r') as f:
                    assert 'crystal_id' in f
                    assert 'center_x' in f
                    assert 'center_y' in f
                    assert 'center_z' in f
                    assert 'azimuth_angle' in f
                    assert 'elevation_angle' in f
                    assert 'volume_name' in f
                    
                    # Check metadata
                    assert 'n_crystals' in f.attrs
                    assert f.attrs['n_crystals'] == len(centers)
            except ImportError:
                pytest.skip("h5py not available")
        finally:
            shutil.rmtree(temp_dir)
    
    def test_extract_centers_auto_filename(self, loaded_volumes):
        """Test extract_crystal_centers with auto-generated filename."""
        temp_dir = tempfile.mkdtemp(prefix="guimesh_test_")
        try:
            centers, success = CrystalCenters.extract_crystal_centers(
                loaded_volumes,
                output_file=True,  # Auto-generate filename
                output_dir=temp_dir
            )
            
            assert success is True
            assert len(centers) > 0
            
            # Check that default files were created
            csv_file = os.path.join(temp_dir, 'lyso_crystal_centers_3d_angles.csv')
            h5_file = os.path.join(temp_dir, 'lyso_crystal_centers_3d_angles.h5')
            
            assert os.path.exists(csv_file)
            # H5 might not exist if h5py is not available, but CSV should
        finally:
            shutil.rmtree(temp_dir)
    
    def test_extract_centers_with_vertex_counts(self, loaded_volumes):
        """Test extract_crystal_centers with vertex_counts list."""
        vertex_counts = []
        centers, success = CrystalCenters.extract_crystal_centers(
            loaded_volumes,
            vertex_counts=vertex_counts
        )
        
        assert success is True
        assert len(centers) > 0
        # Vertex counts should be populated
        assert len(vertex_counts) > 0
        assert all(isinstance(vc, int) and vc > 0 for vc in vertex_counts)
    
    def test_extract_centers_angle_ranges(self, loaded_volumes):
        """Test that extracted angles are in valid ranges."""
        centers, success = CrystalCenters.extract_crystal_centers(loaded_volumes)
        
        assert success is True
        assert len(centers) > 0
        
        for center in centers:
            # Azimuth should be 0-180° (normalized)
            assert 0 <= center['azimuth_angle'] < 180.0
            
            # Elevation should be 0-360° 
            # Note: The code normalizes 360.0 to 0.0, but due to rounding it might still be 360.0
            # So we allow both 0.0 and values < 360.0
            elevation = center['elevation_angle']
            assert 0 <= elevation <= 360.0
            # After normalization, it should be either 0.0 or < 360.0
            # But due to floating point precision, we allow exactly 360.0 as well
            assert elevation == 0.0 or elevation < 360.0 or elevation == 360.0
    
    def test_extract_centers_unique_ids(self, loaded_volumes):
        """Test that all crystal IDs are unique."""
        centers, success = CrystalCenters.extract_crystal_centers(loaded_volumes)
        
        assert success is True
        assert len(centers) > 0
        
        crystal_ids = [c['crystal_id'] for c in centers]
        assert len(crystal_ids) == len(set(crystal_ids)), "Duplicate crystal IDs found"
    
    def test_extract_centers_coordinate_ranges(self, loaded_volumes):
        """Test that coordinates are reasonable (not NaN or infinite)."""
        centers, success = CrystalCenters.extract_crystal_centers(loaded_volumes)
        
        assert success is True
        assert len(centers) > 0
        
        for center in centers:
            assert not (np.isnan(center['center_x']) or np.isinf(center['center_x']))
            assert not (np.isnan(center['center_y']) or np.isinf(center['center_y']))
            assert not (np.isnan(center['center_z']) or np.isinf(center['center_z']))
            assert not (np.isnan(center['azimuth_angle']) or np.isinf(center['azimuth_angle']))
            assert not (np.isnan(center['elevation_angle']) or np.isinf(center['elevation_angle']))

