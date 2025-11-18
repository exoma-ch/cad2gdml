"""
Tests for STEP file loading error handling.

These tests verify that invalid STEP files and error conditions are
properly handled.
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from GUIMeshCLI import GUIMeshCLI


@pytest.mark.unit
class TestStepFileErrors:
    """Test STEP file loading error handling.
    
    These tests verify that the STEP file loading system properly handles
    various error conditions including non-existent files, invalid extensions,
    and load failures.
    """
    
    def test_load_step_file_nonexistent(self, mesh_cli_unit):
        """Test loading non-existent STEP file."""
        mesh = mesh_cli_unit
        result = mesh.load_step_file("nonexistent_file.step")
        assert result is False
        assert len(mesh.list_of_objects) == 0
    
    def test_load_step_file_invalid_extension_txt(self, mesh_cli_unit):
        """Test loading file with .txt extension."""
        mesh = mesh_cli_unit
        # Create a temporary file with wrong extension
        temp_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        temp_file.write(b'fake step content')
        temp_file.close()
        try:
            result = mesh.load_step_file(temp_file.name)
            assert result is False
            assert len(mesh.list_of_objects) == 0
        finally:
            os.unlink(temp_file.name)
    
    def test_load_step_file_invalid_extension_json(self, mesh_cli_unit):
        """Test loading file with .json extension."""
        mesh = mesh_cli_unit
        # Create a temporary JSON file
        temp_file = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        temp_file.write(b'{"test": "data"}')
        temp_file.close()
        try:
            result = mesh.load_step_file(temp_file.name)
            assert result is False
            assert len(mesh.list_of_objects) == 0
        finally:
            os.unlink(temp_file.name)
    
    def test_load_step_file_valid_extension_step(self, mesh_cli_unit):
        """Test that .step extension is accepted."""
        mesh = mesh_cli_unit
        # Create a temporary .step file (even if empty, extension check should pass)
        temp_file = tempfile.NamedTemporaryFile(suffix='.step', delete=False)
        temp_file.write(b'fake step content')
        temp_file.close()
        try:
            # Mock Load_STEP_File to return 0 (failure) so we test the extension check
            # but the actual load will fail
            with patch('src.GUIMeshCLI.LoadOP.Load_STEP_File', return_value=0) as mock_load:
                result = mesh.load_step_file(temp_file.name)
                # Extension check passes, but load fails
                assert result is False
                # Verify Load_STEP_File was called (extension check passed)
                mock_load.assert_called_once()
        finally:
            os.unlink(temp_file.name)
    
    def test_load_step_file_valid_extension_stp(self, mesh_cli_unit):
        """Test that .stp extension is accepted."""
        mesh = mesh_cli_unit
        temp_file = tempfile.NamedTemporaryFile(suffix='.stp', delete=False)
        temp_file.write(b'fake step content')
        temp_file.close()
        try:
            with patch('GUIMeshCLI.LoadOP.Load_STEP_File', return_value=0) as mock_load:
                result = mesh.load_step_file(temp_file.name)
                assert result is False
                # Verify Load_STEP_File was called (extension check passed)
                mock_load.assert_called_once()
        finally:
            os.unlink(temp_file.name)
    
    def test_load_step_file_load_returns_zero(self, mesh_cli_unit):
        """Test when Load_STEP_File returns 0 (failure)."""
        mesh = mesh_cli_unit
        temp_file = tempfile.NamedTemporaryFile(suffix='.step', delete=False)
        temp_file.write(b'fake step content')
        temp_file.close()
        try:
            with patch('GUIMeshCLI.LoadOP.Load_STEP_File', return_value=0) as mock_load:
                result = mesh.load_step_file(temp_file.name)
                assert result is False
                assert len(mesh.list_of_objects) == 0
                # Verify Load_STEP_File was called
                mock_load.assert_called_once()
        finally:
            os.unlink(temp_file.name)
    
    def test_load_step_file_exception_handling(self, mesh_cli_unit):
        """Test exception handling in load_step_file."""
        mesh = mesh_cli_unit
        temp_file = tempfile.NamedTemporaryFile(suffix='.step', delete=False)
        temp_file.write(b'fake step content')
        temp_file.close()
        try:
            # Mock Load_STEP_File to raise an exception
            with patch('GUIMeshCLI.LoadOP.Load_STEP_File', side_effect=Exception("Test exception")) as mock_load:
                result = mesh.load_step_file(temp_file.name)
                assert result is False
                assert len(mesh.list_of_objects) == 0
                # Verify Load_STEP_File was called before exception
                mock_load.assert_called_once()
        finally:
            os.unlink(temp_file.name)
    
    def test_load_step_file_case_insensitive_extension(self, mesh_cli_unit):
        """Test that extension check is case-insensitive."""
        mesh = mesh_cli_unit
        temp_file = tempfile.NamedTemporaryFile(suffix='.STEP', delete=False)
        temp_file.write(b'fake step content')
        temp_file.close()
        try:
            with patch('GUIMeshCLI.LoadOP.Load_STEP_File', return_value=0) as mock_load:
                result = mesh.load_step_file(temp_file.name)
                # Extension check should pass (case-insensitive)
                # But load will fail because we mocked it to return 0
                assert result is False
                # Verify Load_STEP_File was called (extension check passed)
                mock_load.assert_called_once()
        finally:
            os.unlink(temp_file.name)
