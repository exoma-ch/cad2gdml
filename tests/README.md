# Test Suite Documentation

## Overview

This directory contains the test suite for GUIMesh. Tests are organized by functionality and test type.

## Test Organization

### Test Files

- **`test_material_validation.py`**: Tests for material JSON validation and error handling
- **`test_step_file_errors.py`**: Tests for STEP file loading error handling
- **`test_material_assignment_errors.py`**: Tests for material assignment error scenarios
- **`test_material_assignment_edge_cases.py`**: Tests for edge cases in material assignment
- **`test_file_io_errors.py`**: Tests for file I/O error handling
- **`test_materials_without_freecad.py`**: Unit tests for material loading (no FreeCAD required)
- **`test_cli_no_step.py`**: Unit tests for CLI functionality (no STEP files required)
- **`test_crystal_centers.py`**: Integration tests for crystal center extraction
- **`test_integration_with_step.py`**: Integration tests with real STEP files
- **`test_reference_commands.py`**: Tests that verify reference command outputs

### Test Markers

Tests are marked with pytest markers:

- `@pytest.mark.unit`: Unit tests that don't require FreeCAD
- `@pytest.mark.integration`: Integration tests that require FreeCAD and STEP files

### Shared Fixtures

Common fixtures are defined in `conftest.py`:

- **Path fixtures**: `tests_dir`, `test_files_dir`, `test_materials_dir`, `valid_materials_dir`
- **File fixtures**: `lyso_material_file`, `material_mappings_file`, `crystal_step_file`, etc.
- **Instance fixtures**: `mesh_cli_unit`, `mesh_cli_integration`
- **Utility fixtures**: `temp_dir`

## Running Tests

```bash
# Run all tests
pytest tests/

# Run only unit tests
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration

# Run with coverage
pytest tests/ --cov=src --cov=libs --cov-report=html

# Run specific test file
pytest tests/test_material_validation.py
```

## Test Data

Test data files are located in `tests/files/`:

- **`Materials/`**: Valid material JSON files
- **`test_materials/`**: Invalid material JSON files for validation testing
- **`crystal/`**, **`block/`**, **`ring6x1/`**: STEP files for integration tests
- **`test_materials/`**: All test material files including:
  - **`material_mappings.json`**: Standard material mappings
  - **`material_mappings_nolyso.json`**: Test-only mappings without lyso pattern
  - Invalid material JSON files for validation testing

## Best Practices

1. **Use shared fixtures**: Import fixtures from `conftest.py` instead of duplicating setup
2. **Mark tests appropriately**: Use `@pytest.mark.unit` or `@pytest.mark.integration`
3. **Clean up resources**: Use `temp_dir` fixture for temporary files
4. **Skip when needed**: Use `pytest.skip()` when required files are missing
5. **Clear docstrings**: Each test should have a clear docstring explaining what it tests

## Coverage

Current test coverage: **84%**

See `COVERAGE_ANALYSIS.md` for detailed coverage breakdown and improvement recommendations.

