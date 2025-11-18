"""
Tests for material loading that don't require FreeCAD.

These tests can run in any environment and test material loading functionality.
"""
import pytest
from pathlib import Path
from unittest.mock import patch

from GUIMeshLibs import Materials
from GUIMeshCLI import GUIMeshCLI


@pytest.mark.unit
class TestMaterialLoading:
    """Test material loading functionality.
    
    These tests verify that materials can be loaded from JSON files
    and directories, with proper error handling for invalid files.
    """
    
    # Use fixtures from conftest.py
    def test_load_single_material_file(self, lyso_material_file, mesh_cli_unit):
        """Test loading a single material JSON file."""
        mesh = mesh_cli_unit
        result = mesh.load_materials(lyso_material_file)
        assert result is True
        assert len(mesh.Material_List) > 0
        # Check that LYSO material was loaded
        material_names = [mat.Name for mat in mesh.Material_List]
        assert "LYSO" in material_names
    
    def test_load_materials_from_directory(self, lyso_material_file, mesh_cli_unit):
        """Test loading materials from a directory."""
        mesh = mesh_cli_unit
        # Use the directory containing the material file
        from pathlib import Path
        materials_dir = str(Path(lyso_material_file).parent)
        result = mesh.load_materials(materials_dir)
        assert result is True
        assert len(mesh.Material_List) > 0
    
    def test_load_nonexistent_material_file(self, mesh_cli_unit):
        """Test loading a non-existent material file."""
        mesh = mesh_cli_unit
        result = mesh.load_materials("/nonexistent/path/material.json")
        assert result is False
    
    def test_load_invalid_file_extension(self, tmp_path, mesh_cli_unit):
        """Test loading a file with invalid extension."""
        invalid_file = tmp_path / "material.txt"
        invalid_file.write_text('{"name": "Test"}')
        
        mesh = mesh_cli_unit
        result = mesh.load_materials(str(invalid_file))
        assert result is False
    
    def test_load_duplicate_material(self, lyso_material_file, mesh_cli_unit):
        """Test loading the same material twice (should skip duplicate)."""
        mesh = mesh_cli_unit
        # Load first time
        result1 = mesh.load_materials(lyso_material_file)
        assert result1 is True
        initial_count = len(mesh.Material_List)
        
        # Load second time (should skip duplicate)
        result2 = mesh.load_materials(lyso_material_file)
        # When duplicate is skipped, loaded_count is 0, so returns False
        assert result2 is False
        assert len(mesh.Material_List) == initial_count  # Count should be same


@pytest.mark.unit
class TestMaterialMappings:
    """Test material mappings file checking."""
    

@pytest.mark.unit
class TestWorldSize:
    """Test world size setting functionality."""
    
    def test_set_world_size_valid(self, mesh_cli_unit):
        """Test setting valid world size."""
        mesh = mesh_cli_unit
        result = mesh.set_world_size(2.0, 3.0, 4.0)
        assert result is True
        assert mesh.world_dimensions == [2.0, 3.0, 4.0]
    
    def test_set_world_size_negative(self, mesh_cli_unit):
        """Test setting negative world size (should fail)."""
        mesh = mesh_cli_unit
        result = mesh.set_world_size(-1.0, 2.0, 3.0)
        assert result is False
    
    def test_set_world_size_zero(self, mesh_cli_unit):
        """Test setting zero world size (should fail)."""
        mesh = mesh_cli_unit
        result = mesh.set_world_size(0, 2.0, 3.0)
        assert result is False
    
    def test_set_world_size_invalid_type(self, mesh_cli_unit):
        """Test setting world size with invalid type."""
        mesh = mesh_cli_unit
        # This should handle the error gracefully
        # The actual implementation uses float() which will raise ValueError
        # but the method catches it and returns False
        try:
            result = mesh.set_world_size("invalid", 2.0, 3.0)
            assert result is False
        except (ValueError, TypeError):
            # If it raises an exception, that's also acceptable
            pass

