"""
Test CLI behavior when --step argument is not provided.

These tests verify that the CLI handles missing arguments gracefully
and provides appropriate error messages.
"""
import pytest
import sys
import os
from pathlib import Path
from io import StringIO
from unittest.mock import patch, MagicMock

from GUIMeshCLI import main, GUIMeshCLI


@pytest.mark.cli
def test_main_without_step_argument():
    """Test that running the program without --step argument handles gracefully."""
    # Test case 1: No arguments at all - should print help
    with patch('sys.argv', ['GUIMeshCLI.py']):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            main()
            output = fake_out.getvalue()
            assert 'GUIMeshCLI' in output or 'usage:' in output.lower() or '--step' in output


@pytest.mark.cli
def test_main_without_step_but_with_output_dir():
    """Test that running with --output-dir but without --step fails gracefully."""
    test_output_dir = "/tmp/test_gdml_output"
    
    # Clean up if exists
    if os.path.exists(test_output_dir):
        import shutil
        shutil.rmtree(test_output_dir)
    
    with patch('sys.argv', ['GUIMeshCLI.py', '--output-dir', test_output_dir]):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            with patch('sys.stderr', new=StringIO()) as fake_err:
                main()
                output = fake_out.getvalue()
                error_output = fake_err.getvalue()
                
                # Should fail because no volumes are loaded
                # The write_gdml method should return False and print an error
                assert 'Error' in output or 'No volumes' in output or 'No volumes to mesh' in output


@pytest.mark.cli
def test_main_without_step_but_with_assign_materials():
    """Test that running with --assign-materials but without --step fails gracefully."""
    with patch('sys.argv', ['GUIMeshCLI.py', '--assign-materials']):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            with patch('sys.stderr', new=StringIO()) as fake_err:
                main()
                output = fake_out.getvalue()
                error_output = fake_err.getvalue()
                
                # Should fail because no volumes are loaded
                # The assign_materials_from_names method should return False
                assert 'Error' in output or 'No volumes' in output or 'No volumes loaded' in output


@pytest.mark.cli
def test_main_without_step_but_with_extract_centers():
    """Test that running with --extract-centers but without --step fails gracefully."""
    # The mock is already configured at module level to return ([], False)
    with patch('sys.argv', ['GUIMeshCLI.py', '--extract-centers']):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            with patch('sys.stderr', new=StringIO()) as fake_err:
                main()
                output = fake_out.getvalue()
                error_output = fake_err.getvalue()
                
                # The extract_crystal_centers should handle empty list gracefully
                # Check that it doesn't crash


@pytest.mark.unit
def test_guimeshcli_write_gdml_without_volumes():
    """Test that write_gdml fails gracefully when no volumes are loaded."""
    mesh = GUIMeshCLI()
    # Don't load any STEP file, so list_of_objects is empty
    
    result = mesh.write_gdml("/tmp/test_output")
    assert result is False


@pytest.mark.unit
def test_guimeshcli_assign_materials_without_volumes():
    """Test that assign_materials_from_names fails gracefully when no volumes are loaded."""
    mesh = GUIMeshCLI()
    # Don't load any STEP file, so list_of_objects is empty
    
    # Use test material mappings file
    # Note: Can't use fixture directly in non-test function, so use path
    test_mappings = str(Path(__file__).parent / "files" / "test_materials" / "material_mappings.json")
    result = mesh.assign_materials_from_names(test_mappings)
    assert result is False

