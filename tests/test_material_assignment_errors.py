"""
Tests for material assignment error handling.

These tests verify that the program handles missing materials and missing patterns correctly.
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
import subprocess
import sys

# Note: This test file uses integration tests that need FreeCAD
# It uses conftest.py for path setup but needs FreeCAD-specific setup
# Check if FreeCAD is available (same logic as conftest.py)
try:
    import FreeCAD
    import Import
    FREECAD_AVAILABLE = True
except (ImportError, ModuleNotFoundError, SystemError, OSError):
    FREECAD_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.skipif(not FREECAD_AVAILABLE, reason="FreeCAD not available")
class TestMaterialAssignmentErrors:
    """Test material assignment error handling scenarios.
    
    These tests verify that material assignment properly handles error conditions
    including missing materials, missing patterns, and invalid configurations.
    """
    
    # Use fixtures from conftest.py - no need to redefine them
    
    def test_material_assignment_success(self, crystal_step_file, lyso_material_file, material_mappings_file, temp_dir):
        """Test successful material assignment when material is loaded."""
        step_file = crystal_step_file
        material_file = lyso_material_file
        cmd = [
        sys.executable,
        "src/GUIMeshCLI.py",
        "--step", crystal_step_file,
        "--load-materials", lyso_material_file,
        "--assign-materials", material_mappings_file,
        "--output-dir", temp_dir
        ]
        
        result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
        )
        
        # Should succeed
        assert result.returncode == 0, f"Command failed with output: {result.stdout}\n{result.stderr}"
        
        # Check that output files were created
        output_dir = Path(temp_dir)
        assert (output_dir / "mother.gdml").exists(), "mother.gdml should be created"
        assert (output_dir / "Volumes").exists(), "Volumes directory should be created"
        
        # Check that material assignment succeeded
        assert "Material assignments summary:" in result.stdout
        assert "LYSO:" in result.stdout
        assert "1 volumes" in result.stdout or "1 volume" in result.stdout
        
        # Check that GDML files were written
        assert "GDML files written to" in result.stdout
            

    
    def test_material_assignment_missing_material(self, crystal_step_file, material_mappings_file, temp_dir):
        """Test error handling when required material is not loaded."""
        cmd = [
        sys.executable,
        "src/GUIMeshCLI.py",
        "--step", crystal_step_file,
        "--assign-materials", material_mappings_file,
        "--output-dir", temp_dir
        ]
        
        result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
        )
        
        # Check for improved error message
        assert "ERROR: Required materials not found" in result.stdout, \
        f"Expected error message not found. Output: {result.stdout}"
        assert "Material 'LYSO'" in result.stdout
        assert "required for" in result.stdout
        assert "_detector_lyso_" in result.stdout
            
            # Check that it suggests how to fix it
        assert "--load-materials" in result.stdout
        assert "tests/files/Materials/LYSO.json" in result.stdout or "LYSO.json" in result.stdout or "Materials/LYSO.json" in result.stdout
            
            # Check that GDML files were NOT created (because assignment failed)
        output_dir = Path(temp_dir)
        assert not (output_dir / "mother.gdml").exists(), \
        "GDML files should not be created when material assignment fails"
        assert "GDML files written to" not in result.stdout, \
        "Should not report GDML files written when assignment fails"
            

    
    def test_material_assignment_no_pattern_match(self, crystal_step_file, lyso_material_file, material_mappings_nolyso_file, temp_dir):
        """Test error handling when volume name doesn't match any pattern."""
        cmd = [
        sys.executable,
        "src/GUIMeshCLI.py",
        "--step", crystal_step_file,
        "--load-materials", lyso_material_file,
        "--assign-materials", material_mappings_nolyso_file,
        "--output-dir", temp_dir
        ]
            
        result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
        )
            
            # Check for error message about unmatched volumes
        assert "ERROR:" in result.stdout, \
        f"Expected error message not found. Output: {result.stdout}"
        assert "volumes have no matching material pattern" in result.stdout
        assert "_detector_lyso_" in result.stdout
            
            # Check that it suggests how to fix it
        assert "Add patterns to the material mappings file" in result.stdout
            
            # Check that GDML files were NOT created (because assignment failed)
        output_dir = Path(temp_dir)
        assert not (output_dir / "mother.gdml").exists(), \
        "GDML files should not be created when material assignment fails"
        assert "GDML files written to" not in result.stdout, \
        "Should not report GDML files written when assignment fails"
            

    
    def test_material_assignment_missing_material_verbose_output(self, crystal_step_file, material_mappings_file, temp_dir):
        """Test that missing material error provides detailed information."""
        cmd = [
        sys.executable,
        "src/GUIMeshCLI.py",
        "--step", crystal_step_file,
        "--assign-materials", material_mappings_file,
        "--output-dir", temp_dir
        ]
            
        result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
        )
            
            # Verify the error message structure
        output = result.stdout
            
            # Should mention the number of missing materials
        assert "1 material(s) need to be loaded" in output, \
        f"Expected error message not found. Output: {output}"
            
            # Should list the material name
        assert "Material 'LYSO'" in output
            
            # Should show which volumes need it
        assert "_detector_lyso_" in output
            
            # Should provide fix instructions
        assert "To fix this:" in output
        assert "Load the missing material(s) using --load-materials" in output
            
            # Should provide an example
        assert "Example:" in output or "Materials" in output
            
            # Verify GDML files were not created
        output_dir = Path(temp_dir)
        assert not (output_dir / "mother.gdml").exists(), \
        "GDML files should not be created when material assignment fails"
            


