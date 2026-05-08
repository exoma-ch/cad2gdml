"""
Pytest configuration and shared fixtures for all tests.

This module provides common setup, fixtures, and utilities used across
all test files to reduce code duplication and ensure consistency.
"""
import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add libs and src to path FIRST, before any imports
PROJECT_ROOT = Path(__file__).parent.parent
LIBS_PATH = str(PROJECT_ROOT / "libs")
SRC_PATH = str(PROJECT_ROOT / "src")

if LIBS_PATH not in sys.path:
    sys.path.insert(0, LIBS_PATH)
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# FreeCAD path setup (for integration tests)
FREECAD_PATH = '/usr/local/bin/squashfs-root/usr/lib'
if FREECAD_PATH not in sys.path:
    sys.path.append(FREECAD_PATH)

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


def setup_freecad_mocks():
    """Set up FreeCAD mocks for unit tests that don't need real FreeCAD."""
    sys.modules['FreeCAD'] = MagicMock()
    sys.modules['Import'] = MagicMock()
    sys.modules['FreeCADGui'] = MagicMock()
    sys.modules['Draft'] = MagicMock()
    sys.modules['Part'] = MagicMock()


def clear_module_mocks(modules_to_clear=None):
    """Clear mocked modules from sys.modules.
    
    Args:
        modules_to_clear: List of module names to clear. If None, clears
                         common GUIMeshLibs modules.
    """
    if modules_to_clear is None:
        modules_to_clear = [
            'GUIMeshLibs.Volumes', 'GUIMeshLibs.LoadOP',
            'GUIMeshLibs.WriteGDML', 'GUIMeshLibs.CrystalCenters',
            'GUIMeshLibs.Materials', 'GUIMeshLibs', 'GUIMeshCLI', 'src.GUIMeshCLI'
        ]
    
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            if isinstance(sys.modules[module_name], MagicMock):
                del sys.modules[module_name]
            elif hasattr(sys.modules[module_name], '_mock_name'):
                del sys.modules[module_name]


def setup_guimesh_mocks(keep_materials_real=True):
    """Set up GUIMeshLibs mocks for unit tests.
    
    Args:
        keep_materials_real: If True, keeps Materials module real (not mocked).
    """
    clear_module_mocks()
    
    # Mock modules that require FreeCAD
    sys.modules['GUIMeshLibs.Volumes'] = MagicMock()
    sys.modules['GUIMeshLibs.LoadOP'] = MagicMock()
    sys.modules['GUIMeshLibs.WriteGDML'] = MagicMock()
    sys.modules['GUIMeshLibs.CrystalCenters'] = MagicMock()
    
    if keep_materials_real:
        # Import real Materials module
        from GUIMeshLibs import Materials
        sys.modules['GUIMeshLibs.Materials'] = Materials


# Path fixtures
@pytest.fixture
def tests_dir():
    """Path to tests directory."""
    return Path(__file__).parent


@pytest.fixture
def test_files_dir(tests_dir):
    """Path to tests/files directory."""
    return tests_dir / "files"


@pytest.fixture
def test_materials_dir(test_files_dir):
    """Path to test materials directory."""
    return test_files_dir / "test_materials"


@pytest.fixture
def valid_materials_dir(test_files_dir):
    """Path to valid materials directory."""
    return test_files_dir / "Materials"


@pytest.fixture
def step_files_dir(test_files_dir):
    """Path to STEP files directory."""
    return test_files_dir


# Material file fixtures
@pytest.fixture
def lyso_material_file(valid_materials_dir):
    """Path to LYSO material file."""
    mat_path = valid_materials_dir / "LYSO.json"
    if not mat_path.exists():
        pytest.skip(f"Material file not found: {mat_path}")
    return str(mat_path)


@pytest.fixture
def material_mappings_file(test_materials_dir):
    """Path to material mappings file with lyso pattern."""
    mappings_path = test_materials_dir / "material_mappings.json"
    if not mappings_path.exists():
        pytest.skip(f"Material mappings file not found: {mappings_path}")
    return str(mappings_path)


@pytest.fixture
def material_mappings_nolyso_file(test_materials_dir):
    """Path to material mappings file without lyso pattern (test-only)."""
    mappings_path = test_materials_dir / "material_mappings_nolyso.json"
    if not mappings_path.exists():
        pytest.skip(f"Material mappings file not found: {mappings_path}")
    return str(mappings_path)


@pytest.fixture
def material_mappings_lyso_nopath_file(test_materials_dir):
    """Path to mappings file that references LYSO but provides no 'path' (test-only)."""
    mappings_path = test_materials_dir / "material_mappings_lyso_nopath.json"
    if not mappings_path.exists():
        pytest.skip(f"Material mappings file not found: {mappings_path}")
    return str(mappings_path)


# STEP file fixtures
@pytest.fixture
def crystal_step_file(step_files_dir):
    """Path to Crystal.step file."""
    step_path = step_files_dir / "crystal" / "Crystal.step"
    if not step_path.exists():
        pytest.skip(f"STEP file not found: {step_path}")
    return str(step_path)


@pytest.fixture
def ring6x1_step_file(step_files_dir):
    """Path to ring6x1.step file."""
    step_path = step_files_dir / "ring6x1" / "ring6x1.step"
    if not step_path.exists():
        pytest.skip(f"STEP file not found: {step_path}")
    return str(step_path)


@pytest.fixture
def block_step_file(step_files_dir):
    """Path to Block.step file."""
    step_path = step_files_dir / "block" / "Block.step"
    if not step_path.exists():
        pytest.skip(f"STEP file not found: {step_path}")
    return str(step_path)


# Temporary directory fixture
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test output.
    
    Yields:
        str: Path to temporary directory
        
    The directory is automatically cleaned up after the test.
    """
    temp_path = tempfile.mkdtemp(prefix="guimesh_test_")
    yield temp_path
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path, ignore_errors=True)


# GUIMeshCLI fixture (for unit tests with mocks)
@pytest.fixture(scope="function")
def mesh_cli_unit():
    """Create a GUIMeshCLI instance for unit tests (with mocks).
    
    This fixture sets up all necessary mocks before creating the instance.
    Each test gets a fresh instance to ensure test isolation.
    """
    # Set up mocks
    setup_freecad_mocks()
    setup_guimesh_mocks(keep_materials_real=True)
    
    # Clear GUIMeshCLI from cache to ensure fresh import
    clear_module_mocks(['GUIMeshCLI', 'src.GUIMeshCLI'])
    
    # Import after mocks are set up
    from GUIMeshCLI import GUIMeshCLI
    instance = GUIMeshCLI()
    
    yield instance
    
    # Cleanup after test
    clear_module_mocks(['GUIMeshCLI', 'src.GUIMeshCLI'])


# GUIMeshCLI fixture (for integration tests with real FreeCAD)
@pytest.fixture
def mesh_cli_integration():
    """Create a GUIMeshCLI instance for integration tests (with real FreeCAD).
    
    This fixture requires FreeCAD to be available and will skip the test
    if it's not available.
    """
    if not FREECAD_AVAILABLE:
        pytest.skip("FreeCAD not available")
    
    # Clear any mocks
    clear_module_mocks()
    
    from GUIMeshCLI import GUIMeshCLI
    return GUIMeshCLI()


# Invalid material file fixtures
@pytest.fixture
def invalid_material_files(test_materials_dir):
    """Dictionary of invalid material file paths for testing.
    
    Returns:
        dict: Mapping of test name to file path
    """
    return {
        'missing_name': test_materials_dir / "missing_name.json",
        'missing_density': test_materials_dir / "missing_density.json",
        'missing_elements': test_materials_dir / "missing_elements.json",
        'invalid_density_negative': test_materials_dir / "invalid_density_negative.json",
        'invalid_density_zero': test_materials_dir / "invalid_density_zero.json",
        'invalid_density_string': test_materials_dir / "invalid_density_string.json",
        'invalid_elements_empty': test_materials_dir / "invalid_elements_empty.json",
        'invalid_elements_not_list': test_materials_dir / "invalid_elements_not_list.json",
        'invalid_element_missing_name': test_materials_dir / "invalid_element_missing_name.json",
        'invalid_element_missing_fraction': test_materials_dir / "invalid_element_missing_fraction.json",
        'invalid_element_unknown': test_materials_dir / "invalid_element_unknown.json",
        'invalid_fraction_negative': test_materials_dir / "invalid_fraction_negative.json",
        'invalid_fraction_over_one': test_materials_dir / "invalid_fraction_over_one.json",
        'invalid_fraction_string': test_materials_dir / "invalid_fraction_string.json",
        'invalid_fraction_sum': test_materials_dir / "invalid_fraction_sum.json",
        'invalid_json': test_materials_dir / "invalid_json.json",
    }


# Pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that don't require FreeCAD"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that require FreeCAD and STEP files"
    )

