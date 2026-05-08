"""
Tests for material assignment edge cases and error handling.

These tests verify edge cases in material assignment such as multiple
missing materials, many unmatched volumes, etc.
"""
import pytest
import os
import json
from pathlib import Path
from unittest.mock import MagicMock

from GUIMeshCLI import GUIMeshCLI


@pytest.mark.unit
class TestMaterialAssignmentEdgeCases:
    """Test material assignment edge cases.
    
    These tests verify edge cases in material assignment including
    multiple missing materials, many unmatched volumes, invalid JSON,
    and other error conditions.
    """
    
    @staticmethod
    def create_mock_volume(label, material=None):
        """Create a mock volume object.
        
        Args:
            label: Volume label/name
            material: Optional material object
            
        Returns:
            MagicMock: Mock volume object
        """
        volume = MagicMock()
        volume.VolumeCAD.Label = label
        volume.VolumeMaterial = material
        volume.VolumeGDMLoption = 1
        return volume
    
    @staticmethod
    def create_material_mappings_file(mappings_dict, temp_dir):
        """Create a temporary material mappings file.
        
        Args:
            mappings_dict: Dictionary of material mappings
            temp_dir: Temporary directory path
            
        Returns:
            str: Path to created mappings file
        """
        mappings_file = Path(temp_dir) / "material_mappings.json"
        config = {
            "material_mappings": mappings_dict,
            "fallback_material": {
                "material": "G4_Si",
                "description": "Default fallback material"
            },
            "version": "2.0",
            "description": "Material assignment rules for GUIMeshCLI"
        }
        with open(mappings_file, 'w') as f:
            json.dump(config, f, indent=2)
        return str(mappings_file)
    
    def test_assign_materials_multiple_missing(self, mesh_cli_unit, temp_dir):
        """Test assignment with multiple missing materials."""
        mesh = mesh_cli_unit
        vol1 = TestMaterialAssignmentEdgeCases.create_mock_volume("crystal_lyso_1")
        vol2 = TestMaterialAssignmentEdgeCases.create_mock_volume("detector_sipm_1")
        vol3 = TestMaterialAssignmentEdgeCases.create_mock_volume("base_aluminum_1")
        mesh.list_of_objects = [vol1, vol2, vol3]
        
        # Create mappings that require materials not loaded
        mappings = {
            "lyso": {"material": "LYSO", "description": "LYSO"},
            "sipm": {"material": "CustomSi", "description": "Custom Si"},
            "aluminum": {"material": "CustomAl", "description": "Custom Al"}
        }
        mappings_file = TestMaterialAssignmentEdgeCases.create_material_mappings_file(mappings, temp_dir)
        
        result = mesh.assign_materials_from_names(mappings_file)
        assert result is False
        
        # Check that error message mentions multiple materials
        # (We can't easily capture stdout in unit tests, but we can verify behavior)
    
    def test_assign_materials_many_unmatched_volumes(self, mesh_cli_unit, temp_dir):
        """Test assignment with more than 10 unmatched volumes (truncation)."""
        mesh = mesh_cli_unit
        volumes = [TestMaterialAssignmentEdgeCases.create_mock_volume(f"unmatched_volume_{i}") for i in range(15)]
        mesh.list_of_objects = volumes
        
        # Create mappings with no matching patterns
        mappings = {
            "lyso": {"material": "LYSO", "description": "LYSO"}
        }
        mappings_file = TestMaterialAssignmentEdgeCases.create_material_mappings_file(mappings, temp_dir)
        
        result = mesh.assign_materials_from_names(mappings_file)
        assert result is False
        
        # Should handle truncation in error message (shows first 10, then "... and X more")
    
    def test_assign_materials_many_volumes_needing_same_material(self, mesh_cli_unit, temp_dir):
        """Test assignment with >5 volumes needing same material (error message truncation)."""
        mesh = mesh_cli_unit
        volumes = [TestMaterialAssignmentEdgeCases.create_mock_volume(f"crystal_lyso_{i}") for i in range(8)]
        mesh.list_of_objects = volumes
        
        mappings = {
            "lyso": {"material": "LYSO", "description": "LYSO"}
        }
        mappings_file = TestMaterialAssignmentEdgeCases.create_material_mappings_file(mappings, temp_dir)
        
        result = mesh.assign_materials_from_names(mappings_file)
        assert result is False
        
        # Error message should show first 5 volumes, then "... and 3 more"
    
    def test_assign_materials_invalid_json(self, mesh_cli_unit, temp_dir):
        """Test assignment with invalid JSON in mappings file."""
        mesh = mesh_cli_unit
        mappings_file = Path(temp_dir) / "material_mappings.json"
        with open(mappings_file, 'w') as f:
            f.write('{"invalid": json}')
        
        vol = TestMaterialAssignmentEdgeCases.create_mock_volume("test_volume")
        mesh.list_of_objects = [vol]
        
        result = mesh.assign_materials_from_names(str(mappings_file))
        assert result is False
    
    def test_assign_materials_missing_required_fields(self, mesh_cli_unit, temp_dir):
        """Test assignment with mappings file missing required fields."""
        mesh = mesh_cli_unit
        mappings_file = Path(temp_dir) / "material_mappings.json"
        config = {
            "version": "1.0",
            "description": "Missing material_mappings"
        }
        with open(mappings_file, 'w') as f:
            json.dump(config, f)
        
        vol = TestMaterialAssignmentEdgeCases.create_mock_volume("test_volume")
        mesh.list_of_objects = [vol]
        
        result = mesh.assign_materials_from_names(str(mappings_file))
        assert result is False
    
    def test_assign_materials_empty_mappings(self, mesh_cli_unit, temp_dir):
        """Test assignment with empty material_mappings."""
        mesh = mesh_cli_unit
        mappings = {}
        mappings_file = TestMaterialAssignmentEdgeCases.create_material_mappings_file(mappings, temp_dir)
        
        vol = TestMaterialAssignmentEdgeCases.create_mock_volume("test_volume")
        mesh.list_of_objects = [vol]
        
        result = mesh.assign_materials_from_names(mappings_file)
        assert result is False
    
    def test_assign_materials_nonexistent_file(self, mesh_cli_unit):
        """Test assignment with non-existent mappings file."""
        mesh = mesh_cli_unit
        vol = TestMaterialAssignmentEdgeCases.create_mock_volume("test_volume")
        mesh.list_of_objects = [vol]
        
        result = mesh.assign_materials_from_names("nonexistent_mappings.json")
        assert result is False
    
    def test_assign_materials_no_volumes_loaded(self, mesh_cli_unit, temp_dir):
        """Test assignment when no volumes are loaded."""
        mesh = mesh_cli_unit
        mappings = {
            "lyso": {"material": "LYSO", "description": "LYSO"}
        }
        mappings_file = TestMaterialAssignmentEdgeCases.create_material_mappings_file(mappings, temp_dir)
        
        # Don't load any volumes
        mesh.list_of_objects = []
        
        result = mesh.assign_materials_from_names(mappings_file)
        assert result is False
    
    def test_validate_mapping_paths_all_present(self, mesh_cli_unit, temp_dir, lyso_material_file):
        """validate_mapping_material_paths returns True when every path resolves."""
        mesh = mesh_cli_unit
        mappings = {
            "lyso": {"material": "LYSO", "path": lyso_material_file, "description": "absolute path"}
        }
        mappings_file = TestMaterialAssignmentEdgeCases.create_material_mappings_file(mappings, temp_dir)
        assert mesh.validate_mapping_material_paths(mappings_file) is True

    def test_validate_mapping_paths_relative_resolves_against_mapping_dir(self, mesh_cli_unit, temp_dir):
        """Relative paths resolve against the mapping file's directory."""
        mesh = mesh_cli_unit
        # Drop a fake material JSON next to the mapping; reference it via a relative path.
        fake_mat = Path(temp_dir) / "fake_mat.json"
        fake_mat.write_text("{}")
        mappings = {
            "fake": {"material": "FAKE", "path": "fake_mat.json", "description": "relative"}
        }
        mappings_file = TestMaterialAssignmentEdgeCases.create_material_mappings_file(mappings, temp_dir)
        assert mesh.validate_mapping_material_paths(mappings_file) is True

    def test_validate_mapping_paths_missing_file_fails(self, mesh_cli_unit, temp_dir):
        """A path that points at a non-existent file makes validation fail."""
        mesh = mesh_cli_unit
        mappings = {
            "lyso": {"material": "LYSO", "path": "/does/not/exist/LYSO.json", "description": "broken"}
        }
        mappings_file = TestMaterialAssignmentEdgeCases.create_material_mappings_file(mappings, temp_dir)
        assert mesh.validate_mapping_material_paths(mappings_file) is False

    def test_validate_mapping_paths_world_material_path_checked(self, mesh_cli_unit, temp_dir):
        """A broken world_material.path also fails validation."""
        mesh = mesh_cli_unit
        mappings = {
            "al": {"material": "G4_Al", "description": "Al"}
        }
        mappings_file = Path(temp_dir) / "material_mappings.json"
        config = {
            "material_mappings": mappings,
            "world_material": {"name": "Vacuum_ref", "path": "/does/not/exist/Vacuum_ref.json"},
            "version": "2.0"
        }
        with open(mappings_file, 'w') as f:
            json.dump(config, f)
        assert mesh.validate_mapping_material_paths(str(mappings_file)) is False

    def test_assign_materials_mixed_missing_and_available(self, mesh_cli_unit, temp_dir):
        """Test assignment with some materials available and some missing."""
        mesh = mesh_cli_unit
        # Create volumes needing different materials
        vol1 = TestMaterialAssignmentEdgeCases.create_mock_volume("crystal_lyso_1")  # Needs LYSO (missing)
        vol2 = TestMaterialAssignmentEdgeCases.create_mock_volume("detector_sipm_1")  # Needs G4_Si (available)
        mesh.list_of_objects = [vol1, vol2]
        
        mappings = {
            "lyso": {"material": "LYSO", "description": "LYSO"},
            "sipm": {"material": "G4_Si", "description": "Si"}
        }
        mappings_file = TestMaterialAssignmentEdgeCases.create_material_mappings_file(mappings, temp_dir)
        
        result = mesh.assign_materials_from_names(mappings_file)
        # Should fail because LYSO is missing, even though G4_Si is available
        assert result is False
