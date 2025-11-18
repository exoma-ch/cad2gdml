# Comprehensive Test Summary

This document provides a detailed, function-by-function summary of all test files, explaining what each test function tests and what outputs/assertions it verifies.

## Table of Contents

1. [test_material_validation.py](#test_material_validationpy) - 23 tests
2. [test_material_assignment_errors.py](#test_material_assignment_errorspy) - 4 tests
3. [test_material_assignment_edge_cases.py](#test_material_assignment_edge_casespy) - 9 tests
4. [test_file_io_errors.py](#test_file_io_errorspy) - 7 tests
5. [test_step_file_errors.py](#test_step_file_errorspy) - 8 tests
6. [test_materials_without_freecad.py](#test_materials_without_freecadpy) - 8 tests
7. [test_cli_no_step.py](#test_cli_no_steppy) - 6 tests
8. [test_crystal_centers.py](#test_crystal_centerspy) - 6 tests
9. [test_integration_with_step.py](#test_integration_with_steppy) - 9 tests
10. [test_reference_commands.py](#test_reference_commandspy) - 10 tests

---

## Quick Reference Table

| Test File | Test Function | What It Tests | Input/Setup | Method Tested | Key Assertions |
|-----------|--------------|---------------|-------------|---------------|----------------|
| **test_material_validation.py** |
| | `test_load_material_missing_name` | Material missing `name` field | `missing_name.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_missing_density` | Material missing `density` field | `missing_density.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_missing_elements` | Material missing `elements` field | `missing_elements.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_density_negative` | Negative density value | `invalid_density_negative.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_density_zero` | Zero density value | `invalid_density_zero.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_density_string` | String density instead of float | `invalid_density_string.json` | `Materials.Load_Material_JSON()` | Returns 0 or converts string |
| | `test_load_material_invalid_elements_empty` | Empty elements list | `invalid_elements_empty.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_elements_not_list` | Elements not a list | `invalid_elements_not_list.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_element_missing_name` | Element missing `name` field | `invalid_element_missing_name.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_element_missing_fraction` | Element missing `fraction` field | `invalid_element_missing_fraction.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_element_unknown` | Unknown element name | `invalid_element_unknown.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_fraction_negative` | Negative fraction value | `invalid_fraction_negative.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_fraction_over_one` | Fraction > 1.0 | `invalid_fraction_over_one.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_fraction_string` | String fraction instead of float | `invalid_fraction_string.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_fraction_sum` | Fractions don't sum to 1.0 | `invalid_fraction_sum.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_invalid_json_syntax` | Invalid JSON syntax | `invalid_json.json` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_material_nonexistent_file` | Non-existent file path | `"nonexistent_file.json"` | `Materials.Load_Material_JSON()` | Returns 0, no materials added |
| | `test_load_materials_from_directory_with_invalid_files` | Directory with valid + invalid files | Temp dir with both file types | `Materials.Load_Materials_From_Dir()` | Returns != 0 (valid files loaded) |
| | `test_load_materials_from_empty_directory` | Empty directory | Empty temp directory | `Materials.Load_Materials_From_Dir()` | Returns 0 or [] |
| | `test_load_materials_from_nonexistent_directory` | Non-existent directory | `"nonexistent_directory"` | `Materials.Load_Materials_From_Dir()` | Returns 0 |
| | `test_load_material_via_cli_invalid_file` | Invalid file via CLI | `missing_name.json` | `mesh.load_materials()` | Returns False, no materials added |
| | `test_load_material_via_cli_invalid_extension` | Wrong file extension (.txt) | Temp file with .txt extension | `mesh.load_materials()` | Returns False |
| | `test_load_material_via_cli_nonexistent_path` | Non-existent path via CLI | `"/nonexistent/path/material.json"` | `mesh.load_materials()` | Returns False |
| **test_material_assignment_errors.py** |
| | `test_material_assignment_success` | Successful assignment with all materials | Crystal.step + LYSO.json + mappings | Full CLI via subprocess | returncode=0, GDML created, "LYSO:" in stdout |
| | `test_material_assignment_missing_material` | Missing required material (LYSO) | Crystal.step + mappings (no material) | Full CLI via subprocess | "ERROR: Required materials not found", no GDML |
| | `test_material_assignment_no_pattern_match` | Volume name doesn't match pattern | Crystal.step + mappings without "lyso" pattern | Full CLI via subprocess | "volumes have no matching material pattern", no GDML |
| | `test_material_assignment_missing_material_verbose_output` | Detailed error message structure | Crystal.step + mappings (no material) | Full CLI via subprocess | "1 material(s) need to be loaded", "To fix this:", no GDML |
| **test_material_assignment_edge_cases.py** |
| | `test_assign_materials_multiple_missing` | Multiple missing materials | 3 volumes needing 3 different missing materials | `mesh.assign_materials_from_names()` | Returns False |
| | `test_assign_materials_many_unmatched_volumes` | Many unmatched volumes (15) | 15 volumes with no matching patterns | `mesh.assign_materials_from_names()` | Returns False, truncation in error |
| | `test_assign_materials_many_volumes_needing_same_material` | Many volumes needing same material (8) | 8 volumes needing missing LYSO | `mesh.assign_materials_from_names()` | Returns False, shows first 5 then "... and X more" |
| | `test_assign_materials_invalid_json` | Invalid JSON in mappings file | Mappings file with malformed JSON | `mesh.assign_materials_from_names()` | Returns False |
| | `test_assign_materials_missing_required_fields` | Mappings missing `material_mappings` field | Mappings file without required field | `mesh.assign_materials_from_names()` | Returns False |
| | `test_assign_materials_empty_mappings` | Empty material_mappings dict | Mappings file with empty mappings | `mesh.assign_materials_from_names()` | Returns False |
| | `test_assign_materials_nonexistent_file` | Non-existent mappings file | `"nonexistent_mappings.json"` | `mesh.assign_materials_from_names()` | Returns False |
| | `test_assign_materials_no_volumes_loaded` | No volumes loaded | Empty `list_of_objects` | `mesh.assign_materials_from_names()` | Returns False |
| | `test_assign_materials_mixed_missing_and_available` | Some materials available, some missing | 2 volumes: one needs missing LYSO, one needs available G4_Si | `mesh.assign_materials_from_names()` | Returns False (fails if any missing) |
| **test_file_io_errors.py** |
| | `test_write_gdml_permission_error` | GDML write with permission error | Mock volume + mock `Path.mkdir` raises PermissionError | `mesh.write_gdml()` | Returns False |
| | `test_write_gdml_exception_handling` | GDML write with exception | Mock volume + mock `WriteGDML.CreateMother` raises Exception | `mesh.write_gdml()` | Returns False |
| | `test_load_materials_file_read_error` | Material load with read error | Mock `builtins.open` raises PermissionError | `mesh.load_materials()` | Returns False |
| | `test_load_material_mappings_file_read_error` | Mappings load with read error | Temp file with 0o000 permissions | `mesh.load_material_mappings()` | Returns None/False or dict, or catches exception |
| | `test_write_gdml_no_volumes` | GDML write with no volumes | Empty `list_of_objects` | `mesh.write_gdml()` | Returns False |
| | `test_extract_centers_output_dir_error` | Center extraction with invalid path | Mock volume + invalid output path | `mesh.extract_crystal_centers()` | Succeeds or raises exception (both acceptable) |
| | `test_load_materials_directory_permission_error` | Material load from dir with permission error | Mock `os.listdir` raises PermissionError | `mesh.load_materials()` | Returns False |
| **test_step_file_errors.py** |
| | `test_load_step_file_nonexistent` | Non-existent STEP file | `"nonexistent_file.step"` | `mesh.load_step_file()` | Returns False, no volumes loaded |
| | `test_load_step_file_invalid_extension_txt` | File with .txt extension | Temp file with .txt extension | `mesh.load_step_file()` | Returns False, no volumes loaded |
| | `test_load_step_file_invalid_extension_json` | File with .json extension | Temp file with .json extension | `mesh.load_step_file()` | Returns False, no volumes loaded |
| | `test_load_step_file_valid_extension_step` | Valid .step extension accepted | Temp file with .step extension | `mesh.load_step_file()` with mocked Load_STEP_File | Returns False (load fails), but Load_STEP_File called |
| | `test_load_step_file_valid_extension_stp` | Valid .stp extension accepted | Temp file with .stp extension | `mesh.load_step_file()` with mocked Load_STEP_File | Returns False (load fails), but Load_STEP_File called |
| | `test_load_step_file_load_returns_zero` | Load_STEP_File returns 0 (failure) | Temp .step file + mock returns 0 | `mesh.load_step_file()` | Returns False, no volumes, Load_STEP_File called |
| | `test_load_step_file_exception_handling` | Exception in Load_STEP_File | Temp .step file + mock raises Exception | `mesh.load_step_file()` | Returns False, no volumes, Load_STEP_File called |
| | `test_load_step_file_case_insensitive_extension` | Case-insensitive extension check | Temp file with .STEP (uppercase) | `mesh.load_step_file()` with mocked Load_STEP_File | Returns False (load fails), but Load_STEP_File called |
| **test_materials_without_freecad.py** |
| | `test_load_single_material_file` | Load single valid material | `LYSO.json` | `mesh.load_materials()` | Returns True, LYSO in Material_List |
| | `test_load_materials_from_directory` | Load materials from directory | Directory containing LYSO.json | `mesh.load_materials()` | Returns True, materials loaded |
| | `test_load_nonexistent_material_file` | Load non-existent file | `"/nonexistent/path/material.json"` | `mesh.load_materials()` | Returns False |
| | `test_load_invalid_file_extension` | Load file with wrong extension | Temp file with .txt extension | `mesh.load_materials()` | Returns False |
| | `test_load_duplicate_material` | Load same material twice | `LYSO.json` loaded twice | `mesh.load_materials()` | First: True, Second: False (duplicate skipped) |
| | `test_set_world_size_valid` | Set valid world size | `(2.0, 3.0, 4.0)` | `mesh.set_world_size()` | Returns True, dimensions set correctly |
| | `test_set_world_size_negative` | Set negative world size | `(-1.0, 2.0, 3.0)` | `mesh.set_world_size()` | Returns False |
| | `test_set_world_size_zero` | Set zero world size | `(0, 2.0, 3.0)` | `mesh.set_world_size()` | Returns False |
| | `test_set_world_size_invalid_type` | Set world size with string | `("invalid", 2.0, 3.0)` | `mesh.set_world_size()` | Returns False or raises exception |
| **test_cli_no_step.py** |
| | `test_main_without_step_argument` | Run with no arguments | `sys.argv = ['GUIMeshCLI.py']` | `main()` | Help message printed |
| | `test_main_without_step_but_with_output_dir` | Run with --output-dir but no --step | `sys.argv` with --output-dir only | `main()` | Error message about no volumes |
| | `test_main_without_step_but_with_assign_materials` | Run with --assign-materials but no --step | `sys.argv` with --assign-materials only | `main()` | Error message about no volumes |
| | `test_main_without_step_but_with_extract_centers` | Run with --extract-centers but no --step | `sys.argv` with --extract-centers only | `main()` | No crash (handles gracefully) |
| | `test_guimeshcli_write_gdml_without_volumes` | Write GDML with no volumes | Empty `list_of_objects` | `mesh.write_gdml()` | Returns False |
| | `test_guimeshcli_assign_materials_without_volumes` | Assign materials with no volumes | Empty `list_of_objects` + mappings file | `mesh.assign_materials_from_names()` | Returns False |
| **test_crystal_centers.py** |
| | `test_extract_detector_lyso_pattern` | Extract number from `_detector_lyso_` pattern | Volume names: `'_detector_lyso_123'`, etc. | `CrystalCenters.extract_crystal_number()` | Returns 123, 0, 999 respectively |
| | `test_extract_detector_lyso_no_number` | `_detector_lyso_` with no number | `'_detector_lyso_'` | `CrystalCenters.extract_crystal_number()` | Returns 0 |
| | `test_extract_part_pattern` | Extract from `Part_` pattern | `'Part_456'`, `'SomePart_789'` | `CrystalCenters.extract_crystal_number()` | Returns 456, 789 |
| | `test_extract_crystal_pattern` | Extract from `Crystal_` pattern | `'Crystal_123'`, `'MyCrystal_456'` | `CrystalCenters.extract_crystal_number()` | Returns 123, 456 |
| | `test_extract_lyso_pattern` | Extract from `LYSO_` pattern | `'LYSO_789'`, `'SomeLYSO_012'` | `CrystalCenters.extract_crystal_number()` | Returns 789, 12 |
| | `test_extract_number_at_end` | Extract number at end of string | `'volume_123'`, `'test456'` | `CrystalCenters.extract_crystal_number()` | Returns 123, 456 |
| | `test_extract_any_number_fallback` | Fallback to any number | `'abc123def'`, `'1a2b3c'` | `CrystalCenters.extract_crystal_number()` | Returns 123, 1 |
| | `test_extract_no_number` | No number found | `'no_numbers_here'`, `''` | `CrystalCenters.extract_crystal_number()` | Returns None |
| | `test_extract_centers_empty_list` | Extract from empty list | Empty list `[]` | `CrystalCenters.extract_crystal_centers()` | Returns [], success=False |
| | `test_extract_centers_basic` | Basic center extraction | Volumes from Crystal.step | `CrystalCenters.extract_crystal_centers()` | success=True, centers>0, all required keys present |
| | `test_extract_centers_verbose` | Extract with verbose mode | Volumes with verbose=True | `CrystalCenters.extract_crystal_centers()` | success=True, centers>0 |
| | `test_extract_centers_with_csv_output` | Extract with CSV output | Volumes with output_file='test.csv' | `CrystalCenters.extract_crystal_centers()` | success=True, CSV exists, correct columns |
| | `test_extract_centers_with_h5_output` | Extract with H5 output | Volumes with output_file='test.h5' | `CrystalCenters.extract_crystal_centers()` | success=True, CSV+H5 exist, H5 has datasets |
| | `test_extract_centers_auto_filename` | Extract with auto filename | Volumes with output_file=True | `CrystalCenters.extract_crystal_centers()` | success=True, default files created |
| | `test_extract_centers_with_vertex_counts` | Extract with vertex_counts | Volumes with vertex_counts=[] | `CrystalCenters.extract_crystal_centers()` | success=True, vertex_counts populated |
| | `test_extract_centers_angle_ranges` | Angle ranges valid | Volumes from Crystal.step | `CrystalCenters.extract_crystal_centers()` | 0<=azimuth<180, 0<=elevation<=360 |
| | `test_extract_centers_unique_ids` | All crystal IDs unique | Volumes from Crystal.step | `CrystalCenters.extract_crystal_centers()` | No duplicate IDs |
| | `test_extract_centers_coordinate_ranges` | Coordinates not NaN/infinite | Volumes from Crystal.step | `CrystalCenters.extract_crystal_centers()` | All coordinates/angles are finite |
| **test_integration_with_step.py** |
| | `test_load_step_file` | Load STEP file successfully | `ring6x1/ring6x1.step` | `mesh.load_step_file()` | Returns True, volumes>0, file_status=1 |
| | `test_load_materials` | Load materials from JSON | `LYSO.json` | `mesh.load_materials()` | Returns True, LYSO in Material_List |
| | `test_full_workflow_without_output` | Full workflow without GDML output | ring6x1.step + LYSO.json + mappings | Sequential: load_step, load_materials, assign | All return True |
| | `test_check_material_mappings_file` | Check mappings file exists | Mappings file path | `mesh.check_material_mappings_file()` | Returns path, file exists |
| | `test_check_material_mappings_file_default` | Check default mappings file | `"material_mappings.json"` | `mesh.check_material_mappings_file()` | Returns path in src/, file exists |
| | `test_auto_set_world_size` | Auto world size calculation | ring6x1.step loaded | `mesh.load_step_file()` triggers auto_set | Dimensions != [1,1,1], all > 0 |
| | `test_set_world_size_manually` | Manually set world size | `(2.0, 3.0, 4.0)` | `mesh.set_world_size()` | Returns True, dimensions set |
| | `test_set_world_size_invalid` | Set invalid world size | `(-1.0, 2.0, 3.0)` and `(0, 2.0, 3.0)` | `mesh.set_world_size()` | Both return False |
| | `test_cli_with_real_files` | CLI main with real files | ring6x1.step + materials + mappings | `main()` via mocked sys.argv | Output dir created, no crash |
| | `test_load_materials_from_directory` | Load from materials directory | `tests/files/Materials/` | `mesh.load_materials()` | Returns True, materials loaded |
| **test_reference_commands.py** |
| | `test_reference_command[Crystal_ref_output_no_extract_centers]` | Crystal.step command vs reference | Crystal.step + materials + mappings | Full CLI via subprocess | returncode=0, mother.gdml matches, Volumes match |
| | `test_reference_command[Block_ref_output_no_extract_centers]` | Block.step command vs reference | Block.step + materials + mappings | Full CLI via subprocess | returncode=0, mother.gdml matches, Volumes match |
| | `test_reference_command[ring6x1_ref_output_no_extract_centers]` | ring6x1 without extract-centers | ring6x1.step + materials + mappings | Full CLI via subprocess | returncode=0, mother.gdml matches, Volumes match |
| | `test_reference_command[ring6x1_ref_output_with_extract_centers]` | ring6x1 with extract-centers | ring6x1.step + materials + mappings + extract | Full CLI via subprocess | returncode=0, mother.gdml matches, Volumes match |

---

## test_material_validation.py

**Purpose:** Tests material JSON validation and error handling when loading invalid material files.

**Test Class:** `TestMaterialValidation`

### test_load_material_missing_name
- **What it tests:** Loading a material JSON file that is missing the required `name` field
- **Input:** `missing_name.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added to the list)

### test_load_material_missing_density
- **What it tests:** Loading a material JSON file that is missing the required `density` field
- **Input:** `missing_density.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_missing_elements
- **What it tests:** Loading a material JSON file that is missing the required `elements` field
- **Input:** `missing_elements.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_density_negative
- **What it tests:** Loading a material with a negative density value (invalid)
- **Input:** `invalid_density_negative.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_density_zero
- **What it tests:** Loading a material with zero density (invalid)
- **Input:** `invalid_density_zero.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_density_string
- **What it tests:** Loading a material with a string value for density instead of a float
- **Input:** `invalid_density_string.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - If `result == 0`: `len(mesh.Material_List) == 0` (validation failed)
  - If `result != 0`: `result is not None` (string was converted to float, which is acceptable)

### test_load_material_invalid_elements_empty
- **What it tests:** Loading a material with an empty elements list
- **Input:** `invalid_elements_empty.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_elements_not_list
- **What it tests:** Loading a material where the `elements` field is not a list (e.g., a string or dict)
- **Input:** `invalid_elements_not_list.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_element_missing_name
- **What it tests:** Loading a material where an element in the elements list is missing the `name` field
- **Input:** `invalid_element_missing_name.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_element_missing_fraction
- **What it tests:** Loading a material where an element is missing the `fraction` field
- **Input:** `invalid_element_missing_fraction.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_element_unknown
- **What it tests:** Loading a material with an element name that is not recognized (not in the element database)
- **Input:** `invalid_element_unknown.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_fraction_negative
- **What it tests:** Loading a material with a negative fraction value (invalid)
- **Input:** `invalid_fraction_negative.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_fraction_over_one
- **What it tests:** Loading a material with a fraction value greater than 1.0 (invalid)
- **Input:** `invalid_fraction_over_one.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_fraction_string
- **What it tests:** Loading a material with a string value for fraction instead of a float
- **Input:** `invalid_fraction_string.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_fraction_sum
- **What it tests:** Loading a material where the element fractions don't sum to 1.0 (invalid)
- **Input:** `invalid_fraction_sum.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_invalid_json_syntax
- **What it tests:** Loading a material file with invalid JSON syntax (malformed JSON)
- **Input:** `invalid_json.json` from test_materials directory
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_nonexistent_file
- **What it tests:** Attempting to load a material file that doesn't exist
- **Input:** `"nonexistent_file.json"` (non-existent path)
- **Method tested:** `Materials.Load_Material_JSON()`
- **Assertions:**
  - `result == 0` (indicates failure)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_materials_from_directory_with_invalid_files
- **What it tests:** Loading materials from a directory containing both valid and invalid material files
- **Input:** Temporary directory with one valid material file and one invalid material file
- **Method tested:** `Materials.Load_Materials_From_Dir()`
- **Assertions:**
  - `result != 0` (should return at least one material - the valid one)
  - Invalid files should be skipped, valid files should be loaded

### test_load_materials_from_empty_directory
- **What it tests:** Loading materials from an empty directory (no JSON files)
- **Input:** Empty temporary directory
- **Method tested:** `Materials.Load_Materials_From_Dir()`
- **Assertions:**
  - `result == 0 or result == []` (should return 0 or empty list for empty directory)

### test_load_materials_from_nonexistent_directory
- **What it tests:** Attempting to load materials from a directory that doesn't exist
- **Input:** `"nonexistent_directory"` (non-existent path)
- **Method tested:** `Materials.Load_Materials_From_Dir()`
- **Assertions:**
  - `result == 0` (indicates failure)

### test_load_material_via_cli_invalid_file
- **What it tests:** Loading an invalid material file via GUIMeshCLI's `load_materials()` method
- **Input:** `missing_name.json` (invalid material file)
- **Method tested:** `mesh.load_materials()`
- **Assertions:**
  - `result is False` (should return False for invalid file)
  - `len(mesh.Material_List) == 0` (no materials should be added)

### test_load_material_via_cli_invalid_extension
- **What it tests:** Loading a file with wrong extension (.txt instead of .json) via GUIMeshCLI
- **Input:** Temporary file with `.txt` extension containing JSON-like content
- **Method tested:** `mesh.load_materials()`
- **Assertions:**
  - `result is False` (should reject non-JSON files)

### test_load_material_via_cli_nonexistent_path
- **What it tests:** Loading a material from a non-existent path via GUIMeshCLI
- **Input:** `"/nonexistent/path/material.json"` (non-existent path)
- **Method tested:** `mesh.load_materials()`
- **Assertions:**
  - `result is False` (should return False for non-existent path)

---

## test_material_assignment_errors.py

**Purpose:** Integration tests that verify material assignment error handling with real STEP files and FreeCAD.

**Test Class:** `TestMaterialAssignmentErrors`

### test_material_assignment_success
- **What it tests:** Successful material assignment when all required materials are loaded
- **Input:** 
  - STEP file: `Crystal.step`
  - Material file: `LYSO.json`
  - Material mappings: `material_mappings.json`
- **Method tested:** Full CLI execution via subprocess
- **Command:** `python3 src/GUIMeshCLI.py --step <step_file> --load-materials <material_file> --assign-materials <mappings_file> --output-dir <temp_dir>`
- **Assertions:**
  - `result.returncode == 0` (command succeeds)
  - `mother.gdml` file exists in output directory
  - `Volumes` directory exists in output directory
  - `"Material assignments summary:"` in stdout
  - `"LYSO:"` in stdout (material was assigned)
  - `"1 volumes"` or `"1 volume"` in stdout
  - `"GDML files written to"` in stdout

### test_material_assignment_missing_material
- **What it tests:** Error handling when a required material is not loaded (LYSO material missing)
- **Input:**
  - STEP file: `Crystal.step`
  - Material mappings: `material_mappings.json` (requires LYSO)
  - No material file loaded
- **Method tested:** Full CLI execution via subprocess
- **Command:** `python3 src/GUIMeshCLI.py --step <step_file> --assign-materials <mappings_file> --output-dir <temp_dir>`
- **Assertions:**
  - `"ERROR: Required materials not found"` in stdout
  - `"Material 'LYSO'"` in stdout
  - `"required for"` in stdout
  - `"_detector_lyso_"` in stdout (volume name that needs the material)
  - `"--load-materials"` in stdout (suggests fix)
  - `"LYSO.json"` or `"Materials/LYSO.json"` in stdout (example path)
  - `mother.gdml` does NOT exist (assignment failed, so no GDML written)
  - `"GDML files written to"` NOT in stdout

### test_material_assignment_no_pattern_match
- **What it tests:** Error handling when volume names don't match any pattern in the mappings file
- **Input:**
  - STEP file: `Crystal.step`
  - Material file: `LYSO.json`
  - Material mappings: `material_mappings_nolyso.json` (no "lyso" pattern)
- **Method tested:** Full CLI execution via subprocess
- **Command:** `python3 src/GUIMeshCLI.py --step <step_file> --load-materials <material_file> --assign-materials <mappings_file> --output-dir <temp_dir>`
- **Assertions:**
  - `"ERROR:"` in stdout
  - `"volumes have no matching material pattern"` in stdout
  - `"_detector_lyso_"` in stdout (unmatched volume name)
  - `"Add patterns to the material mappings file"` in stdout (suggests fix)
  - `mother.gdml` does NOT exist
  - `"GDML files written to"` NOT in stdout

### test_material_assignment_missing_material_verbose_output
- **What it tests:** Detailed error message structure when materials are missing
- **Input:**
  - STEP file: `Crystal.step`
  - Material mappings: `material_mappings.json` (requires LYSO)
  - No material file loaded
- **Method tested:** Full CLI execution via subprocess
- **Command:** `python3 src/GUIMeshCLI.py --step <step_file> --assign-materials <mappings_file> --output-dir <temp_dir>`
- **Assertions:**
  - `"1 material(s) need to be loaded"` in stdout
  - `"Material 'LYSO'"` in stdout
  - `"_detector_lyso_"` in stdout
  - `"To fix this:"` in stdout
  - `"Load the missing material(s) using --load-materials"` in stdout
  - `"Example:"` or `"Materials"` in stdout
  - `mother.gdml` does NOT exist

---

## test_material_assignment_edge_cases.py

**Purpose:** Unit tests for edge cases in material assignment logic using mocked volumes.

**Test Class:** `TestMaterialAssignmentEdgeCases`

### test_assign_materials_multiple_missing
- **What it tests:** Material assignment when multiple different materials are missing
- **Input:** 
  - 3 mock volumes: `crystal_lyso_1`, `detector_sipm_1`, `base_aluminum_1`
  - Material mappings requiring LYSO, CustomSi, and CustomAl (all not loaded)
- **Method tested:** `mesh.assign_materials_from_names()`
- **Assertions:**
  - `result is False` (assignment should fail)
  - Error message should mention multiple materials (verified by behavior, not captured in unit test)

### test_assign_materials_many_unmatched_volumes
- **What it tests:** Material assignment when many volumes (15) don't match any pattern
- **Input:**
  - 15 mock volumes with names like `unmatched_volume_0` through `unmatched_volume_14`
  - Material mappings with only "lyso" pattern (doesn't match any volume)
- **Method tested:** `mesh.assign_materials_from_names()`
- **Assertions:**
  - `result is False` (assignment should fail)
  - Error message should handle truncation (shows first 10 volumes, then "... and X more")

### test_assign_materials_many_volumes_needing_same_material
- **What it tests:** Material assignment when many volumes (8) need the same missing material
- **Input:**
  - 8 mock volumes: `crystal_lyso_0` through `crystal_lyso_7`
  - Material mappings requiring LYSO (not loaded)
- **Method tested:** `mesh.assign_materials_from_names()`
- **Assertions:**
  - `result is False` (assignment should fail)
  - Error message should show first 5 volumes, then "... and 3 more"

### test_assign_materials_invalid_json
- **What it tests:** Material assignment with invalid JSON syntax in mappings file
- **Input:**
  - Temporary mappings file with malformed JSON: `'{"invalid": json}'`
  - 1 mock volume
- **Method tested:** `mesh.assign_materials_from_names()`
- **Assertions:**
  - `result is False` (should fail to parse JSON)

### test_assign_materials_missing_required_fields
- **What it tests:** Material assignment with mappings file missing required `material_mappings` field
- **Input:**
  - Temporary mappings file with only `version` and `description` fields (missing `material_mappings`)
  - 1 mock volume
- **Method tested:** `mesh.assign_materials_from_names()`
- **Assertions:**
  - `result is False` (should fail validation)

### test_assign_materials_empty_mappings
- **What it tests:** Material assignment with empty `material_mappings` dictionary
- **Input:**
  - Temporary mappings file with empty `material_mappings: {}`
  - 1 mock volume
- **Method tested:** `mesh.assign_materials_from_names()`
- **Assertions:**
  - `result is False` (no patterns to match)

### test_assign_materials_nonexistent_file
- **What it tests:** Material assignment with non-existent mappings file path
- **Input:**
  - Non-existent file path: `"nonexistent_mappings.json"`
  - 1 mock volume
- **Method tested:** `mesh.assign_materials_from_names()`
- **Assertions:**
  - `result is False` (file doesn't exist)

### test_assign_materials_no_volumes_loaded
- **What it tests:** Material assignment when no volumes are loaded
- **Input:**
  - Empty `mesh.list_of_objects = []`
  - Valid material mappings file
- **Method tested:** `mesh.assign_materials_from_names()`
- **Assertions:**
  - `result is False` (no volumes to assign materials to)

### test_assign_materials_mixed_missing_and_available
- **What it tests:** Material assignment when some materials are available and some are missing
- **Input:**
  - 2 mock volumes: `crystal_lyso_1` (needs LYSO - missing) and `detector_sipm_1` (needs G4_Si - available)
  - Material mappings requiring both LYSO and G4_Si
- **Method tested:** `mesh.assign_materials_from_names()`
- **Assertions:**
  - `result is False` (should fail because LYSO is missing, even though G4_Si is available)

---

## test_file_io_errors.py

**Purpose:** Tests file I/O error handling, including permission errors and exceptions.

**Test Class:** `TestFileIOErrors`

### test_write_gdml_permission_error
- **What it tests:** GDML writing when directory creation fails due to permission error
- **Input:**
  - Mock volume with material
  - Mock `pathlib.Path.mkdir` to raise `PermissionError`
- **Method tested:** `mesh.write_gdml()`
- **Assertions:**
  - `result is False` (should handle permission error gracefully)

### test_write_gdml_exception_handling
- **What it tests:** GDML writing when `WriteGDML.CreateMother` raises an exception
- **Input:**
  - Mock volume with material
  - Mock `GUIMeshCLI.WriteGDML.CreateMother` to raise `Exception`
- **Method tested:** `mesh.write_gdml()`
- **Assertions:**
  - `result is False` (should catch exception and return False)

### test_load_materials_file_read_error
- **What it tests:** Loading materials when file cannot be read (permission error)
- **Input:**
  - Mock `builtins.open` to raise `PermissionError`
  - File path: `"test.json"`
- **Method tested:** `mesh.load_materials()`
- **Assertions:**
  - `result is False` (should handle permission error gracefully)

### test_load_material_mappings_file_read_error
- **What it tests:** Loading material mappings when file cannot be read
- **Input:**
  - Temporary JSON file with permissions set to 0o000 (unreadable)
  - Attempt to load mappings from unreadable file
- **Method tested:** `mesh.load_material_mappings()`
- **Assertions:**
  - `result is None or result is False or isinstance(result, dict)` (may succeed if readable despite permissions, or fail gracefully)
  - Or exception is caught: `PermissionError`, `RuntimeError`, or `ValueError` (all acceptable)

### test_write_gdml_no_volumes
- **What it tests:** Writing GDML when no volumes are loaded
- **Input:**
  - Empty `mesh.list_of_objects = []`
- **Method tested:** `mesh.write_gdml()`
- **Assertions:**
  - `result is False` (should fail when no volumes to write)

### test_extract_centers_output_dir_error
- **What it tests:** Crystal center extraction with invalid output file path
- **Input:**
  - Mock volume
  - Output file: `"test.csv"` (may be invalid path)
- **Method tested:** `mesh.extract_crystal_centers()`
- **Assertions:**
  - Either succeeds (error handling in underlying function) or raises `ValueError` or `Exception` (acceptable)

### test_load_materials_directory_permission_error
- **What it tests:** Loading materials from directory when `os.listdir` fails due to permission error
- **Input:**
  - Mock `os.listdir` to raise `PermissionError`
  - Directory path: `"/tmp/test_dir"`
- **Method tested:** `mesh.load_materials()`
- **Assertions:**
  - `result is False` (should handle permission error gracefully)

---

## test_step_file_errors.py

**Purpose:** Tests STEP file loading error handling, including invalid extensions and load failures.

**Test Class:** `TestStepFileErrors`

### test_load_step_file_nonexistent
- **What it tests:** Loading a non-existent STEP file
- **Input:** `"nonexistent_file.step"` (non-existent path)
- **Method tested:** `mesh.load_step_file()`
- **Assertions:**
  - `result is False` (file doesn't exist)
  - `len(mesh.list_of_objects) == 0` (no volumes loaded)

### test_load_step_file_invalid_extension_txt
- **What it tests:** Loading a file with `.txt` extension (invalid for STEP files)
- **Input:** Temporary file with `.txt` extension containing fake STEP content
- **Method tested:** `mesh.load_step_file()`
- **Assertions:**
  - `result is False` (wrong extension)
  - `len(mesh.list_of_objects) == 0` (no volumes loaded)

### test_load_step_file_invalid_extension_json
- **What it tests:** Loading a file with `.json` extension (invalid for STEP files)
- **Input:** Temporary file with `.json` extension
- **Method tested:** `mesh.load_step_file()`
- **Assertions:**
  - `result is False` (wrong extension)
  - `len(mesh.list_of_objects) == 0` (no volumes loaded)

### test_load_step_file_valid_extension_step
- **What it tests:** That `.step` extension is accepted (extension check passes)
- **Input:** Temporary file with `.step` extension
- **Method tested:** `mesh.load_step_file()` with mocked `LoadOP.Load_STEP_File` returning 0
- **Assertions:**
  - `result is False` (load fails, but extension check passes)
  - `mock_load.assert_called_once()` (Load_STEP_File was called, proving extension check passed)

### test_load_step_file_valid_extension_stp
- **What it tests:** That `.stp` extension is accepted (extension check passes)
- **Input:** Temporary file with `.stp` extension
- **Method tested:** `mesh.load_step_file()` with mocked `LoadOP.Load_STEP_File` returning 0
- **Assertions:**
  - `result is False` (load fails, but extension check passes)
  - `mock_load.assert_called_once()` (Load_STEP_File was called)

### test_load_step_file_load_returns_zero
- **What it tests:** When `Load_STEP_File` returns 0 (indicating load failure)
- **Input:** Temporary `.step` file with mocked `LoadOP.Load_STEP_File` returning 0
- **Method tested:** `mesh.load_step_file()`
- **Assertions:**
  - `result is False` (load failed)
  - `len(mesh.list_of_objects) == 0` (no volumes loaded)
  - `mock_load.assert_called_once()` (function was called)

### test_load_step_file_exception_handling
- **What it tests:** Exception handling in `load_step_file` when `Load_STEP_File` raises an exception
- **Input:** Temporary `.step` file with mocked `LoadOP.Load_STEP_File` raising `Exception`
- **Method tested:** `mesh.load_step_file()`
- **Assertions:**
  - `result is False` (exception caught, returns False)
  - `len(mesh.list_of_objects) == 0` (no volumes loaded)
  - `mock_load.assert_called_once()` (function was called before exception)

### test_load_step_file_case_insensitive_extension
- **What it tests:** That extension check is case-insensitive (`.STEP` should work like `.step`)
- **Input:** Temporary file with `.STEP` extension (uppercase)
- **Method tested:** `mesh.load_step_file()` with mocked `LoadOP.Load_STEP_File` returning 0
- **Assertions:**
  - `result is False` (load fails, but extension check passes)
  - `mock_load.assert_called_once()` (Load_STEP_File was called, proving case-insensitive check works)

---

## test_materials_without_freecad.py

**Purpose:** Tests material loading functionality that doesn't require FreeCAD.

**Test Classes:** `TestMaterialLoading`, `TestMaterialMappings`, `TestWorldSize`

### TestMaterialLoading

#### test_load_single_material_file
- **What it tests:** Loading a single valid material JSON file
- **Input:** `LYSO.json` material file
- **Method tested:** `mesh.load_materials()`
- **Assertions:**
  - `result is True` (load succeeded)
  - `len(mesh.Material_List) > 0` (material was added to list)
  - `"LYSO" in material_names` (LYSO material is in the list)

#### test_load_materials_from_directory
- **What it tests:** Loading materials from a directory containing JSON files
- **Input:** Directory containing `LYSO.json`
- **Method tested:** `mesh.load_materials()` with directory path
- **Assertions:**
  - `result is True` (load succeeded)
  - `len(mesh.Material_List) > 0` (materials were loaded)

#### test_load_nonexistent_material_file
- **What it tests:** Loading a material file that doesn't exist
- **Input:** `"/nonexistent/path/material.json"` (non-existent path)
- **Method tested:** `mesh.load_materials()`
- **Assertions:**
  - `result is False` (file doesn't exist)

#### test_load_invalid_file_extension
- **What it tests:** Loading a file with invalid extension (not `.json`)
- **Input:** Temporary file with `.txt` extension containing JSON-like content
- **Method tested:** `mesh.load_materials()`
- **Assertions:**
  - `result is False` (wrong extension rejected)

#### test_load_duplicate_material
- **What it tests:** Loading the same material twice (should skip duplicate)
- **Input:** `LYSO.json` loaded twice
- **Method tested:** `mesh.load_materials()` called twice with same file
- **Assertions:**
  - First load: `result is True` (succeeds)
  - Second load: `result is False` (duplicate skipped, loaded_count is 0)
  - `len(mesh.Material_List) == initial_count` (count unchanged after duplicate)

### TestWorldSize

#### test_set_world_size_valid
- **What it tests:** Setting valid world size dimensions
- **Input:** `(2.0, 3.0, 4.0)` as world dimensions
- **Method tested:** `mesh.set_world_size()`
- **Assertions:**
  - `result is True` (succeeds)
  - `mesh.world_dimensions == [2.0, 3.0, 4.0]` (dimensions set correctly)

#### test_set_world_size_negative
- **What it tests:** Setting negative world size (should fail)
- **Input:** `(-1.0, 2.0, 3.0)` (negative X dimension)
- **Method tested:** `mesh.set_world_size()`
- **Assertions:**
  - `result is False` (negative values rejected)

#### test_set_world_size_zero
- **What it tests:** Setting zero world size (should fail)
- **Input:** `(0, 2.0, 3.0)` (zero X dimension)
- **Method tested:** `mesh.set_world_size()`
- **Assertions:**
  - `result is False` (zero values rejected)

#### test_set_world_size_invalid_type
- **What it tests:** Setting world size with invalid type (string instead of float)
- **Input:** `("invalid", 2.0, 3.0)` (string for X dimension)
- **Method tested:** `mesh.set_world_size()`
- **Assertions:**
  - Either `result is False` (error caught and returns False) or raises `ValueError` or `TypeError` (acceptable)

---

## test_cli_no_step.py

**Purpose:** Tests CLI behavior when `--step` argument is not provided.

**Test Functions:** (not in a class)

### test_main_without_step_argument
- **What it tests:** Running the program with no arguments (should print help)
- **Input:** `sys.argv = ['GUIMeshCLI.py']` (no arguments)
- **Method tested:** `main()`
- **Assertions:**
  - Output contains `'GUIMeshCLI'` or `'usage:'` (lowercase) or `'--step'` (help message printed)

### test_main_without_step_but_with_output_dir
- **What it tests:** Running with `--output-dir` but without `--step` (should fail gracefully)
- **Input:** `sys.argv = ['GUIMeshCLI.py', '--output-dir', '/tmp/test_gdml_output']`
- **Method tested:** `main()`
- **Assertions:**
  - Output contains `'Error'` or `'No volumes'` or `'No volumes to mesh'` (error message printed)

### test_main_without_step_but_with_assign_materials
- **What it tests:** Running with `--assign-materials` but without `--step` (should fail gracefully)
- **Input:** `sys.argv = ['GUIMeshCLI.py', '--assign-materials']`
- **Method tested:** `main()`
- **Assertions:**
  - Output contains `'Error'` or `'No volumes'` or `'No volumes loaded'` (error message printed)

### test_main_without_step_but_with_extract_centers
- **What it tests:** Running with `--extract-centers` but without `--step` (should handle gracefully)
- **Input:** `sys.argv = ['GUIMeshCLI.py', '--extract-centers']`
- **Method tested:** `main()`
- **Assertions:**
  - No crash (function handles empty list gracefully)

### test_guimeshcli_write_gdml_without_volumes
- **What it tests:** Writing GDML when no volumes are loaded
- **Input:** `mesh` with empty `list_of_objects`
- **Method tested:** `mesh.write_gdml()`
- **Assertions:**
  - `result is False` (should fail when no volumes)

### test_guimeshcli_assign_materials_without_volumes
- **What it tests:** Assigning materials when no volumes are loaded
- **Input:** `mesh` with empty `list_of_objects` and material mappings file
- **Method tested:** `mesh.assign_materials_from_names()`
- **Assertions:**
  - `result is False` (should fail when no volumes)

---

## test_crystal_centers.py

**Purpose:** Tests crystal center extraction functionality with real STEP files.

**Test Classes:** `TestExtractCrystalNumber`, `TestExtractCrystalCenters`

### TestExtractCrystalNumber

#### test_extract_detector_lyso_pattern
- **What it tests:** Extracting crystal number from `_detector_lyso_` pattern
- **Input:** Volume names: `'_detector_lyso_123'`, `'_detector_lyso_0'`, `'_detector_lyso_999'`
- **Method tested:** `CrystalCenters.extract_crystal_number()`
- **Assertions:**
  - Returns `123`, `0`, `999` respectively

#### test_extract_detector_lyso_no_number
- **What it tests:** Special case: `_detector_lyso_` with no number should return 0
- **Input:** Volume name: `'_detector_lyso_'` (no number)
- **Method tested:** `CrystalCenters.extract_crystal_number()`
- **Assertions:**
  - Returns `0`

#### test_extract_part_pattern
- **What it tests:** Extracting crystal number from `Part_` pattern
- **Input:** Volume names: `'Part_456'`, `'SomePart_789'`
- **Method tested:** `CrystalCenters.extract_crystal_number()`
- **Assertions:**
  - Returns `456`, `789` respectively

#### test_extract_crystal_pattern
- **What it tests:** Extracting crystal number from `Crystal_` pattern
- **Input:** Volume names: `'Crystal_123'`, `'MyCrystal_456'`
- **Method tested:** `CrystalCenters.extract_crystal_number()`
- **Assertions:**
  - Returns `123`, `456` respectively

#### test_extract_lyso_pattern
- **What it tests:** Extracting crystal number from `LYSO_` pattern
- **Input:** Volume names: `'LYSO_789'`, `'SomeLYSO_012'`
- **Method tested:** `CrystalCenters.extract_crystal_number()`
- **Assertions:**
  - Returns `789`, `12` respectively (leading zeros stripped)

#### test_extract_number_at_end
- **What it tests:** Extracting number at end of string (fallback pattern)
- **Input:** Volume names: `'volume_123'`, `'test456'`
- **Method tested:** `CrystalCenters.extract_crystal_number()`
- **Assertions:**
  - Returns `123`, `456` respectively

#### test_extract_any_number_fallback
- **What it tests:** Fallback to any number pattern in the string
- **Input:** Volume names: `'abc123def'`, `'1a2b3c'`
- **Method tested:** `CrystalCenters.extract_crystal_number()`
- **Assertions:**
  - Returns `123`, `1` respectively (first number found)

#### test_extract_no_number
- **What it tests:** Case where no number is found in the string
- **Input:** Volume names: `'no_numbers_here'`, `''` (empty string)
- **Method tested:** `CrystalCenters.extract_crystal_number()`
- **Assertions:**
  - Returns `None` for both

### TestExtractCrystalCenters

#### test_extract_centers_empty_list
- **What it tests:** Extracting crystal centers from an empty volume list
- **Input:** Empty list `[]`
- **Method tested:** `CrystalCenters.extract_crystal_centers()`
- **Assertions:**
  - `centers == []` (empty list returned)
  - `success is False` (extraction failed due to empty input)

### test_extract_centers_basic
- **What it tests:** Basic extraction of crystal centers from loaded volumes
- **Input:** Volumes loaded from `Crystal.step` with materials assigned
- **Method tested:** `CrystalCenters.extract_crystal_centers(loaded_volumes)`
- **Assertions:**
  - `success is True` (extraction succeeded)
  - `len(centers) > 0` (at least one center extracted)
  - Each center dictionary contains required keys: `crystal_id`, `volume_name`, `center_x`, `center_y`, `center_z`, `azimuth_angle`, `elevation_angle`
  - All values have correct types (crystal_id is int, coordinates/angles are numeric)

### test_extract_centers_verbose
- **What it tests:** Extracting crystal centers with verbose mode enabled
- **Input:** Volumes loaded from `Crystal.step` with `verbose=True`
- **Method tested:** `CrystalCenters.extract_crystal_centers(loaded_volumes, verbose=True)`
- **Assertions:**
  - `success is True` (extraction succeeded)
  - `len(centers) > 0` (centers extracted)

### test_extract_centers_with_csv_output
- **What it tests:** Extracting crystal centers and writing to CSV file
- **Input:** Volumes loaded from `Crystal.step` with `output_file='test_crystals.csv'`
- **Method tested:** `CrystalCenters.extract_crystal_centers(loaded_volumes, output_file=csv_file)`
- **Assertions:**
  - `success is True` (extraction succeeded)
  - `len(centers) > 0` (centers extracted)
  - CSV file exists at specified path
  - CSV file contains correct number of rows (matches number of centers)
  - CSV file contains required columns: `crystal_id`, `center_x`, `center_y`, `center_z`, `azimuth_angle`, `elevation_angle`

### test_extract_centers_with_h5_output
- **What it tests:** Extracting crystal centers and writing to HDF5 file
- **Input:** Volumes loaded from `Crystal.step` with `output_file='test_crystals.h5'`
- **Method tested:** `CrystalCenters.extract_crystal_centers(loaded_volumes, output_file=h5_file)`
- **Assertions:**
  - `success is True` (extraction succeeded)
  - `len(centers) > 0` (centers extracted)
  - CSV file also created (H5 output creates both CSV and H5)
  - H5 file exists (if h5py available)
  - H5 file contains required datasets: `crystal_id`, `center_x`, `center_y`, `center_z`, `azimuth_angle`, `elevation_angle`, `volume_name`
  - H5 file contains metadata attribute `n_crystals` matching number of centers

### test_extract_centers_auto_filename
- **What it tests:** Extracting crystal centers with auto-generated filename
- **Input:** Volumes loaded from `Crystal.step` with `output_file=True` and `output_dir=temp_dir`
- **Method tested:** `CrystalCenters.extract_crystal_centers(loaded_volumes, output_file=True, output_dir=temp_dir)`
- **Assertions:**
  - `success is True` (extraction succeeded)
  - `len(centers) > 0` (centers extracted)
  - Default CSV file created: `lyso_crystal_centers_3d_angles.csv`
  - H5 file may be created if h5py available: `lyso_crystal_centers_3d_angles.h5`

### test_extract_centers_with_vertex_counts
- **What it tests:** Extracting crystal centers with vertex_counts list populated
- **Input:** Volumes loaded from `Crystal.step` with `vertex_counts=[]` list passed
- **Method tested:** `CrystalCenters.extract_crystal_centers(loaded_volumes, vertex_counts=vertex_counts)`
- **Assertions:**
  - `success is True` (extraction succeeded)
  - `len(centers) > 0` (centers extracted)
  - `len(vertex_counts) > 0` (vertex counts list populated)
  - All vertex counts are positive integers

### test_extract_centers_angle_ranges
- **What it tests:** That extracted angles are within valid ranges
- **Input:** Volumes loaded from `Crystal.step`
- **Method tested:** `CrystalCenters.extract_crystal_centers(loaded_volumes)`
- **Assertions:**
  - `success is True` (extraction succeeded)
  - `len(centers) > 0` (centers extracted)
  - For each center: `0 <= azimuth_angle < 180.0` (azimuth normalized to 0-180°)
  - For each center: `0 <= elevation_angle <= 360.0` (elevation in 0-360° range)

### test_extract_centers_unique_ids
- **What it tests:** That all extracted crystal IDs are unique
- **Input:** Volumes loaded from `Crystal.step`
- **Method tested:** `CrystalCenters.extract_crystal_centers(loaded_volumes)`
- **Assertions:**
  - `success is True` (extraction succeeded)
  - `len(centers) > 0` (centers extracted)
  - `len(crystal_ids) == len(set(crystal_ids))` (no duplicate IDs)

### test_extract_centers_coordinate_ranges
- **What it tests:** That extracted coordinates are valid (not NaN or infinite)
- **Input:** Volumes loaded from `Crystal.step`
- **Method tested:** `CrystalCenters.extract_crystal_centers(loaded_volumes)`
- **Assertions:**
  - `success is True` (extraction succeeded)
  - `len(centers) > 0` (centers extracted)
  - For each center: coordinates and angles are not NaN or infinite (using `numpy.isnan()` and `numpy.isinf()`)

---

## test_integration_with_step.py

**Purpose:** Integration tests using actual STEP files and materials with FreeCAD.

**Test Classes:** `TestIntegrationWithStepFile`

### test_load_step_file
- **What it tests:** Loading a STEP file and verifying volumes are loaded
- **Input:** STEP file: `ring6x1/ring6x1.step`
- **Method tested:** `mesh.load_step_file()`
- **Assertions:**
  - `result is True` (load succeeded)
  - `len(mesh.list_of_objects) > 0` (volumes loaded)
  - `mesh.file_status == 1` (file status set to loaded)

### test_load_materials
- **What it tests:** Loading materials from a JSON file
- **Input:** Material file: `LYSO.json`
- **Method tested:** `mesh.load_materials()`
- **Assertions:**
  - `result is True` (load succeeded)
  - `len(mesh.Material_List) > 0` (materials added to list)
  - `"LYSO" in material_names` (LYSO material is in the list)

### test_full_workflow_without_output
- **What it tests:** Complete workflow: load STEP, load materials, assign materials (without writing GDML)
- **Input:**
  - STEP file: `ring6x1/ring6x1.step`
  - Material file: `LYSO.json`
  - Material mappings: `material_mappings.json`
- **Method tested:** Sequential calls to `load_step_file()`, `load_materials()`, `assign_materials_from_names()`
- **Assertions:**
  - `load_step_file()` returns `True`
  - `len(mesh.list_of_objects) > 0` (volumes loaded)
  - `load_materials()` returns `True`
  - `assign_materials_from_names()` returns `True`

### test_check_material_mappings_file
- **What it tests:** Checking if a material mappings file exists
- **Input:** Material mappings file path
- **Method tested:** `mesh.check_material_mappings_file()`
- **Assertions:**
  - `result is not None` (file found)
  - `os.path.exists(result)` (returned path exists)

### test_check_material_mappings_file_default
- **What it tests:** Checking for default material mappings file (`material_mappings.json`)
- **Input:** Default filename `"material_mappings.json"`
- **Method tested:** `mesh.check_material_mappings_file("material_mappings.json")`
- **Assertions:**
  - `result is not None` (file found, likely in `src/` directory)
  - `os.path.exists(result)` (returned path exists)

### test_auto_set_world_size
- **What it tests:** Automatic world size calculation after loading STEP file
- **Input:** STEP file: `ring6x1/ring6x1.step`
- **Method tested:** `mesh.load_step_file()` (triggers `auto_set_world_size()`)
- **Assertions:**
  - `mesh.world_dimensions != [1.0, 1.0, 1.0]` (world size was calculated, not default)
  - `all(dim > 0 for dim in mesh.world_dimensions)` (all dimensions are positive)

### test_set_world_size_manually
- **What it tests:** Manually setting world size dimensions
- **Input:** World dimensions: `(2.0, 3.0, 4.0)`
- **Method tested:** `mesh.set_world_size()`
- **Assertions:**
  - `result is True` (setting succeeded)
  - `mesh.world_dimensions == [2.0, 3.0, 4.0]` (dimensions set correctly)

### test_set_world_size_invalid
- **What it tests:** Setting invalid world size (negative and zero values)
- **Input:** 
  - First: `(-1.0, 2.0, 3.0)` (negative value)
  - Second: `(0, 2.0, 3.0)` (zero value)
- **Method tested:** `mesh.set_world_size()`
- **Assertions:**
  - Both calls return `False` (invalid values rejected)

### test_cli_with_real_files
- **What it tests:** CLI main function execution with real files via mocked `sys.argv`
- **Input:**
  - STEP file: `ring6x1/ring6x1.step`
  - Material file: `LYSO.json`
  - Material mappings: `material_mappings.json`
  - Mocked `sys.argv` with all arguments
- **Method tested:** `main()` function
- **Assertions:**
  - Output directory is created (command executes)
  - No crash (may call `sys.exit()`, which is acceptable)

### test_load_materials_from_directory
- **What it tests:** Loading materials from a directory containing JSON files
- **Input:** Materials directory: `tests/files/Materials/`
- **Method tested:** `mesh.load_materials()` with directory path
- **Assertions:**
  - `result is True` (load succeeded)
  - `len(mesh.Material_List) > 0` (materials loaded from directory)

### test_cli_with_real_files
- **What it tests:** CLI main function with real files (ring6x1 STEP file)
- **Input:**
  - STEP file: `ring6x1/ring6x1.step`
  - Material file: `LYSO.json`
  - Material mappings: `material_mappings.json`
- **Method tested:** `main()` function via subprocess with mocked `sys.argv`
- **Assertions:**
  - Command executes successfully
  - Output files are created
  - Material assignments work correctly

---

## test_reference_commands.py

**Purpose:** Tests reference commands by running them and comparing outputs with reference files.

**Test Class:** `TestReferenceCommands`

### test_reference_command (parametrized - 10 test instances)
- **What it tests:** Runs each command from `ref_commands.txt` and compares generated GDML files with reference outputs
- **Input:** Commands parsed from `tests/commands/ref_commands.txt`:
  1. **Crystal_ref_output_no_extract_centers:** `Crystal.step` with material assignment
  2. **Block_ref_output_no_extract_centers:** `Block.step` with material assignment
  3. **ring6x1_ref_output_no_extract_centers:** `ring6x1.step` without extract-centers
  4. **ring6x1_ref_output_with_extract_centers:** `ring6x1.step` with extract-centers
- **Method tested:** Full CLI execution via subprocess for each command
- **Process:**
  1. Parse command from `ref_commands.txt`
  2. Replace `--output-dir` path with temporary directory
  3. Run command via `subprocess.run()` with shell=True
  4. Compare `mother.gdml` with reference using normalized XML comparison
  5. Compare `Volumes/*.gdml` files with reference files
- **Assertions:**
  - Command succeeds (`result.returncode == 0`)
  - Reference `mother.gdml` exists (test skipped if missing)
  - Generated `mother.gdml` matches reference (normalized XML comparison - handles whitespace/attribute order differences)
  - Reference `Volumes` directory exists (test skipped if missing)
  - All volume GDML files in reference exist in generated output
  - All volume GDML files match reference files (normalized XML comparison)
  - No differences found in XML structure, attributes, or values

---

## Summary Statistics

- **Total Test Files:** 10
- **Total Test Functions:** 98
- **Unit Tests:** 68
- **Integration Tests:** 30
- **Test Coverage:** 90% (335 statements, 33 missing)

### Test Categories by Purpose:

1. **Material Validation (23 tests):** Tests JSON schema validation, invalid values, missing fields
2. **Material Assignment Errors (4 tests):** Integration tests for missing materials and pattern matching
3. **Material Assignment Edge Cases (9 tests):** Unit tests for multiple missing materials, many volumes, invalid JSON
4. **File I/O Errors (7 tests):** Permission errors, exceptions during file operations
5. **STEP File Errors (8 tests):** Invalid extensions, non-existent files, load failures
6. **Material Loading (8 tests):** Loading from files/directories, duplicate handling, invalid extensions
7. **CLI Functionality (6 tests):** Missing arguments, help messages, error handling
8. **Crystal Centers (6 tests):** Number extraction patterns, center calculation
9. **Integration Tests (9 tests):** Full workflow with real STEP files
10. **Reference Commands (10 tests):** End-to-end validation against reference outputs

