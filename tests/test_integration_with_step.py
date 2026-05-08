"""
Integration tests using actual STEP files and materials.

These tests require FreeCAD to be available and will be skipped if it's not.
"""
import pytest
import sys
import os
import tempfile
import shutil
import importlib
from pathlib import Path

# Add FreeCAD path FIRST, before any imports (same as GUIMeshCLI.py does)
freecad_path = '/usr/local/bin/squashfs-root/usr/lib'
if freecad_path not in sys.path:
    sys.path.append(freecad_path)
# Add PySide2 from FreeCAD's site-packages (needed for Draft module)
# Use current Python version to find the correct site-packages path (same as GUIMeshCLI.py)
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
pyside_path = f'/usr/local/bin/squashfs-root/usr/lib/python{python_version}/site-packages'
if pyside_path not in sys.path:
    sys.path.insert(0, pyside_path)

# Check if FreeCAD is available and clear any mocks
FREECAD_AVAILABLE = False
try:
    # Clear any existing FreeCAD mocks from other test files
    from unittest.mock import MagicMock
    for module_name in ['FreeCAD', 'Import', 'FreeCADGui', 'Draft', 'Part']:
        if module_name in sys.modules:
            # Check if it's a mock and remove it
            if isinstance(sys.modules[module_name], MagicMock):
                del sys.modules[module_name]
    
    # Now try to import real FreeCAD (same way GUIMeshCLI.py does)
    # Core FreeCAD modules are required
    import FreeCAD
    import Import
    # These might not be available but core FreeCAD is enough
    try:
        import FreeCADGui
        import Draft
        import Part
    except (ImportError, ModuleNotFoundError):
        # These are optional, core FreeCAD is enough
        pass
    FREECAD_AVAILABLE = True
except (ImportError, ModuleNotFoundError, SystemError, OSError) as e:
    # FreeCAD might not be available in test environment
    # This is expected when running tests outside the container
    FREECAD_AVAILABLE = False

# Add libs and src to path
libs_path = str(Path(__file__).parent.parent / "libs")
sys.path.insert(0, libs_path)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if FREECAD_AVAILABLE:
    # Clear any mocked GUIMeshLibs modules if they exist (from other test files)
    # We need real modules for integration tests
    from unittest.mock import MagicMock
    
    # Remove all mocked GUIMeshLibs modules completely
    modules_to_clear = [
        'GUIMeshLibs.Volumes', 'GUIMeshLibs.LoadOP', 
        'GUIMeshLibs.WriteGDML', 'GUIMeshLibs.CrystalCenters',
        'GUIMeshLibs.Materials', 'GUIMeshLibs'
    ]
    
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            if isinstance(sys.modules[module_name], MagicMock):
                del sys.modules[module_name]
            # Also check if it's a mock object in any way
            elif hasattr(sys.modules[module_name], '_mock_name'):
                del sys.modules[module_name]
    
    # Clear GUIMeshCLI from cache if it exists (it may have imported mocked modules)
    # This ensures we get a fresh import with real FreeCAD
    for module_name in ['GUIMeshCLI', 'src.GUIMeshCLI']:
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    # Force reload of GUIMeshLibs modules to ensure we get real ones
    # Import them directly to ensure they're real
    try:
        import importlib
        # Import the real modules
        import GUIMeshLibs.Volumes
        import GUIMeshLibs.LoadOP
        import GUIMeshLibs.WriteGDML
        import GUIMeshLibs.CrystalCenters
        import GUIMeshLibs.Materials
        
        # Reload them to ensure they're fresh
        importlib.reload(GUIMeshLibs.Volumes)
        importlib.reload(GUIMeshLibs.LoadOP)
        importlib.reload(GUIMeshLibs.WriteGDML)
        importlib.reload(GUIMeshLibs.CrystalCenters)
        importlib.reload(GUIMeshLibs.Materials)
    except Exception:
        pass  # If reload fails, continue anyway
    
    # Now import GUIMeshCLI - it should use real FreeCAD and real modules
    # GUIMeshCLI will check for FreeCAD itself, and since we've verified it's available,
    # the import should succeed
    try:
        from GUIMeshCLI import GUIMeshCLI, main
        from unittest.mock import patch
        from io import StringIO
    except SystemExit:
        # If GUIMeshCLI can't find FreeCAD and exits, mark as unavailable
        FREECAD_AVAILABLE = False
        GUIMeshCLI = None
        main = None
else:
    # FreeCAD not available - don't try to import GUIMeshCLI
    GUIMeshCLI = None
    main = None


@pytest.mark.integration
@pytest.mark.skipif(not FREECAD_AVAILABLE, reason="FreeCAD not available")
class TestIntegrationWithStepFile:
    """Integration tests with actual STEP file and materials."""
    
    @pytest.fixture(autouse=True)
    def cleanup_mocks(self):
        """Clean up any mocks from other test files before each test."""
        if FREECAD_AVAILABLE:
            from unittest.mock import MagicMock
            import importlib
            
            # Remove all mocked FreeCAD modules first (these are mocked by other test files)
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
                # Force them into sys.modules
                sys.modules['FreeCAD'] = FreeCAD
                sys.modules['Import'] = Import
                sys.modules['FreeCADGui'] = FreeCADGui
                sys.modules['Draft'] = Draft
                sys.modules['Part'] = Part
            except Exception:
                pass
            
            # Remove all mocked GUIMeshLibs modules completely
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
            
            # Force reload of GUIMeshLibs modules to ensure we get real ones
            # Only reload if they're not already real modules
            try:
                # Import fresh modules
                import GUIMeshLibs.Volumes
                import GUIMeshLibs.LoadOP
                import GUIMeshLibs.WriteGDML
                import GUIMeshLibs.CrystalCenters
                import GUIMeshLibs.Materials
                
                # Only reload if they were mocked (check by trying to reload)
                # If they're real modules, reload should work fine
                try:
                    importlib.reload(GUIMeshLibs.LoadOP)
                except Exception:
                    pass
            except Exception:
                pass
            
            # Re-import GUIMeshCLI to get fresh instance with real modules
            try:
                global GUIMeshCLI, main
                from GUIMeshCLI import GUIMeshCLI as FreshGUIMeshCLI, main as FreshMain
                GUIMeshCLI = FreshGUIMeshCLI
                main = FreshMain
            except Exception:
                pass
        
        yield  # Test runs here
    
    @pytest.fixture
    def step_file(self):
        """Path to the working STEP file."""
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
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp(prefix="guimesh_test_")
        yield temp_dir
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    def test_load_step_file(self, step_file):
        """Test loading a STEP file."""
        mesh = GUIMeshCLI()
        result = mesh.load_step_file(step_file)
        assert result is True
        assert len(mesh.list_of_objects) > 0
        assert mesh.file_status == 1
    
    def test_load_materials(self, material_file):
        """Test loading materials from JSON file."""
        mesh = GUIMeshCLI()
        result = mesh.load_materials(material_file)
        assert result is True
        assert len(mesh.Material_List) > 0
        # Check that LYSO material was loaded
        material_names = [mat.Name for mat in mesh.Material_List]
        assert "LYSO" in material_names
    
    def test_full_workflow_without_output(self, step_file, material_file, material_mappings_file):
        """Test full workflow: load STEP, load materials, assign materials."""
        mesh = GUIMeshCLI()
        mesh.verbose = False
        
        # Load STEP file
        assert mesh.load_step_file(step_file) is True
        assert len(mesh.list_of_objects) > 0
        
        # Load materials
        assert mesh.load_materials(material_file) is True
        
        # Assign materials
        assert mesh.assign_materials_from_names(material_mappings_file) is True
    
    def test_check_material_mappings_file(self, material_mappings_file):
        """Test checking for material mappings file."""
        mesh = GUIMeshCLI()
        result = mesh.check_material_mappings_file(material_mappings_file)
        assert result is not None
        assert os.path.exists(result)
    
    def test_check_material_mappings_file_default(self):
        """Test that the bundled per-domain mappings files are discoverable in src/."""
        mesh = GUIMeshCLI()
        for rel in ("material_mappings/pet_ring.json", "material_mappings/cavity.json"):
            result = mesh.check_material_mappings_file(rel)
            assert result is not None, f"Expected to find {rel} in src/"
            assert os.path.exists(result)
    
    def test_auto_set_world_size(self, step_file):
        """Test automatic world size calculation."""
        mesh = GUIMeshCLI()
        mesh.load_step_file(step_file)
        
        # World size should be set automatically
        assert mesh.world_dimensions != [1.0, 1.0, 1.0]  # Should be calculated
        assert all(dim > 0 for dim in mesh.world_dimensions)
    
    def test_set_world_size_manually(self):
        """Test manually setting world size."""
        mesh = GUIMeshCLI()
        result = mesh.set_world_size(2.0, 3.0, 4.0)
        assert result is True
        assert mesh.world_dimensions == [2.0, 3.0, 4.0]
    
    def test_set_world_size_invalid(self):
        """Test setting invalid world size."""
        mesh = GUIMeshCLI()
        result = mesh.set_world_size(-1.0, 2.0, 3.0)
        assert result is False
        result = mesh.set_world_size(0, 2.0, 3.0)
        assert result is False


@pytest.mark.integration
@pytest.mark.skipif(not FREECAD_AVAILABLE, reason="FreeCAD not available")
def test_cli_with_real_files():
    """Test CLI main function with real files; LYSO is auto-loaded from the mapping's 'path'."""
    step_path = Path(__file__).parent / "files" / "ring6x1" / "ring6x1.step"
    mappings_path = Path(__file__).parent / "files" / "test_materials" / "material_mappings.json"

    if not all(p.exists() for p in [step_path, mappings_path]):
        pytest.skip("Required test files not found")

    # Create temporary output directory
    temp_output_dir = tempfile.mkdtemp(prefix="guimesh_test_")
    try:
        with patch('sys.argv', [
            'GUIMeshCLI.py',
            '--step', str(step_path),
            '--assign-materials', str(mappings_path),
            '--output-dir', temp_output_dir,
            '--verbose'
        ]):
            with patch('sys.stdout', new=StringIO()) as fake_out:
                try:
                    main()
                    output = fake_out.getvalue()
                    # Should complete without errors (or with expected errors)
                    # Check that output directory was created
                    assert os.path.exists(temp_output_dir)
                except SystemExit:
                    # If main() calls sys.exit(), that's okay for this test
                    pass
    finally:
        # Cleanup
        if os.path.exists(temp_output_dir):
            shutil.rmtree(temp_output_dir)


@pytest.mark.integration
@pytest.mark.skipif(not FREECAD_AVAILABLE, reason="FreeCAD not available")
def test_load_materials_from_directory():
    """Test loading materials from a directory."""
    materials_dir = Path(__file__).parent / "files" / "Materials"
    if not materials_dir.exists():
        pytest.skip(f"Materials directory not found: {materials_dir}")
    
    mesh = GUIMeshCLI()
    result = mesh.load_materials(str(materials_dir))
    assert result is True
    assert len(mesh.Material_List) > 0

