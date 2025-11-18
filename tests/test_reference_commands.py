"""
Test suite for reference commands.

This test suite runs the commands from tests/commands/ref_commands.txt and
verifies that the generated outputs (mother.gdml and Volumes/*.gdml) match
the reference outputs.
"""
import pytest
import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import List, Tuple, Optional

# Add FreeCAD path FIRST, before any imports (same as GUIMeshCLI.py does)
freecad_path = '/usr/local/bin/squashfs-root/usr/lib'
if freecad_path not in sys.path:
    sys.path.append(freecad_path)
# Add PySide2 from FreeCAD's site-packages
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
pyside_path = f'/usr/local/bin/squashfs-root/usr/lib/python{python_version}/site-packages'
if pyside_path not in sys.path:
    sys.path.insert(0, pyside_path)

# Check if FreeCAD is available
# Clear any mocks first
FREECAD_AVAILABLE = False
try:
    from unittest.mock import MagicMock
    for module_name in ['FreeCAD', 'Import', 'FreeCADGui', 'Draft', 'Part']:
        if module_name in sys.modules:
            if isinstance(sys.modules[module_name], MagicMock):
                del sys.modules[module_name]
    
    import FreeCAD
    import Import
    FREECAD_AVAILABLE = True
except (ImportError, ModuleNotFoundError, SystemError, OSError):
    FREECAD_AVAILABLE = False


def parse_ref_commands() -> List[Tuple[str, str, Optional[str]]]:
    """
    Parse ref_commands.txt and extract commands.
    
    Returns:
        List of tuples: (command, ref_output_dir, description)
        - command: The command to run (without cd and output redirection)
        - ref_output_dir: The reference output directory
        - description: Optional description/test name
    """
    ref_commands_file = Path(__file__).parent.parent / "tests" / "commands" / "ref_commands.txt"
    if not ref_commands_file.exists():
        pytest.skip(f"Reference commands file not found: {ref_commands_file}")
    
    commands = []
    with open(ref_commands_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse command line
            # Format: cd /mnt/guimesh & python3 ... --output-dir PATH > output.txt
            if 'cd /mnt/guimesh &' in line:
                # Extract the python command part
                parts = line.split('&', 1)
                if len(parts) > 1:
                    cmd_part = parts[1].strip()
                    # Remove output redirection
                    if '>' in cmd_part:
                        cmd_part = cmd_part.rsplit('>', 1)[0].strip()
                    
                    # Extract output directory from --output-dir argument
                    ref_output_dir = None
                    if '--output-dir' in cmd_part:
                        cmd_parts = cmd_part.split()
                        for i, part in enumerate(cmd_parts):
                            if part == '--output-dir' and i + 1 < len(cmd_parts):
                                ref_output_dir = cmd_parts[i + 1]
                                break
                    
                    # Skip plot commands for now (they don't generate GDML)
                    if 'plot_scanner_with_crystals.py' in cmd_part:
                        continue
                    
                    if ref_output_dir:
                        # Generate a test name from the output dir and step file
                        test_name = Path(ref_output_dir).name
                        # Try to extract a better name from the step file path
                        if '--step' in cmd_part:
                            step_idx = cmd_parts.index('--step')
                            if step_idx + 1 < len(cmd_parts):
                                step_file = Path(cmd_parts[step_idx + 1])
                                test_name = f"{step_file.stem}_{test_name}"
                        
                        # Add suffix for extract-centers commands
                        if '--extract-centers' in cmd_part:
                            test_name = f"{test_name}_with_extract_centers"
                        else:
                            test_name = f"{test_name}_no_extract_centers"
                        
                        commands.append((cmd_part, ref_output_dir, test_name))
    
    return commands


def normalize_xml(xml_string: str) -> str:
    """
    Normalize XML string for comparison.
    
    This handles:
    - Whitespace differences
    - Attribute ordering
    - Empty elements
    """
    try:
        # Parse and re-serialize to normalize
        root = ET.fromstring(xml_string)
        # Sort attributes for consistent comparison
        def sort_attributes(elem):
            if elem.attrib:
                # Sort attributes by name
                sorted_attrs = sorted(elem.attrib.items())
                elem.attrib.clear()
                elem.attrib.update(sorted_attrs)
            for child in elem:
                sort_attributes(child)
        
        sort_attributes(root)
        
        # Use a consistent formatting
        ET.indent(root, space=' ')
        normalized = ET.tostring(root, encoding='unicode', method='xml')
        return normalized
    except ET.ParseError as e:
        # If XML parsing fails, return original (will fail comparison)
        return xml_string


def compare_gdml_files(file1: Path, file2: Path) -> Tuple[bool, str]:
    """
    Compare two GDML files.
    
    Returns:
        (are_equal, diff_message)
    """
    if not file1.exists():
        return False, f"File 1 does not exist: {file1}"
    if not file2.exists():
        return False, f"File 2 does not exist: {file2}"
    
    try:
        with open(file1, 'r', encoding='utf-8') as f:
            content1 = f.read()
        with open(file2, 'r', encoding='utf-8') as f:
            content2 = f.read()
        
        # Normalize both files
        norm1 = normalize_xml(content1)
        norm2 = normalize_xml(content2)
        
        if norm1 == norm2:
            return True, ""
        else:
            # Find first difference
            lines1 = norm1.splitlines()
            lines2 = norm2.splitlines()
            diff_line = None
            for i, (l1, l2) in enumerate(zip(lines1, lines2)):
                if l1 != l2:
                    diff_line = i + 1
                    break
            
            if diff_line:
                return False, f"Files differ at line {diff_line}"
            elif len(lines1) != len(lines2):
                return False, f"Files have different number of lines: {len(lines1)} vs {len(lines2)}"
            else:
                return False, "Files differ (normalized comparison)"
    
    except Exception as e:
        return False, f"Error comparing files: {str(e)}"


def compare_volumes_directories(dir1: Path, dir2: Path) -> Tuple[bool, List[str]]:
    """
    Compare two Volumes directories.
    
    Returns:
        (are_equal, list_of_errors)
    """
    errors = []
    
    if not dir1.exists():
        errors.append(f"Volumes directory 1 does not exist: {dir1}")
        return False, errors
    if not dir2.exists():
        errors.append(f"Volumes directory 2 does not exist: {dir2}")
        return False, errors
    
    # Get all .gdml files from both directories
    files1 = set(f.name for f in dir1.glob("*.gdml"))
    files2 = set(f.name for f in dir2.glob("*.gdml"))
    
    # Check for missing files
    missing_in_2 = files1 - files2
    missing_in_1 = files2 - files1
    
    if missing_in_2:
        errors.append(f"Files missing in dir2: {missing_in_2}")
    if missing_in_1:
        errors.append(f"Files missing in dir1: {missing_in_1}")
    
    # Compare common files
    common_files = files1 & files2
    for filename in sorted(common_files):
        file1 = dir1 / filename
        file2 = dir2 / filename
        are_equal, diff_msg = compare_gdml_files(file1, file2)
        if not are_equal:
            errors.append(f"{filename}: {diff_msg}")
    
    return len(errors) == 0, errors


@pytest.mark.integration
@pytest.mark.skipif(not FREECAD_AVAILABLE, reason="FreeCAD not available")
class TestReferenceCommands:
    """Test suite for reference commands."""
    
    @pytest.fixture(scope="class")
    def workspace_root(self):
        """Get the workspace root directory."""
        return Path(__file__).parent.parent
    
    @pytest.fixture(scope="class")
    def ref_commands(self):
        """Parse reference commands."""
        return parse_ref_commands()
    
    @pytest.mark.parametrize("command,ref_output_dir,test_name", 
                             [(cmd, ref_dir, name) for cmd, ref_dir, name in parse_ref_commands()],
                             ids=[name for _, _, name in parse_ref_commands()])
    def test_reference_command(self, workspace_root, command, ref_output_dir, test_name):
        """
        Test reference commands by running them and comparing outputs.
        
        This test:
        1. Runs each command with a temporary output directory
        2. Compares mother.gdml with reference
        3. Compares Volumes/*.gdml files with reference
        """
        self._run_and_compare(workspace_root, command, ref_output_dir, test_name)
    
    def _run_and_compare(self, workspace_root, command, ref_output_dir, test_name):
        """Run a single command and compare outputs."""
        # Create temporary output directory
        temp_output_dir = tempfile.mkdtemp(prefix=f"guimesh_test_{test_name}_")
        
        try:
            # Modify command to use temporary output directory
            # Replace the --output-dir and --extract-centers arguments
            cmd_parts = command.split()
            final_cmd = []
            skip_next = False
            for i, part in enumerate(cmd_parts):
                if skip_next:
                    skip_next = False
                    # Check if we just saw --output-dir
                    if len(final_cmd) > 0 and final_cmd[-1] == '--output-dir':
                        # Always replace output-dir path with temp dir
                        final_cmd.append(temp_output_dir)
                    elif 'ref_output' in part:
                        # For --extract-centers or other paths in ref_output, replace with temp dir
                        filename = Path(part).name
                        final_cmd.append(str(Path(temp_output_dir) / filename))
                    else:
                        final_cmd.append(part)
                    continue
                
                if part == '--output-dir':
                    final_cmd.append(part)
                    # Next part will be the output dir path, which we'll replace
                    skip_next = True
                elif part == '--extract-centers':
                    final_cmd.append(part)
                    # Next part will be the extract-centers path, which we'll replace if needed
                    skip_next = True
                else:
                    final_cmd.append(part)
            
            # Run the command
            cmd_str = ' '.join(final_cmd)
            result = subprocess.run(
                cmd_str,
                shell=True,
                cwd=str(workspace_root),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Check if command succeeded
            if result.returncode != 0:
                pytest.fail(
                    f"Command failed with return code {result.returncode}\n"
                    f"Command: {cmd_str}\n"
                    f"STDOUT: {result.stdout}\n"
                    f"STDERR: {result.stderr}"
                )
            
            # Compare outputs
            ref_output_path = workspace_root / ref_output_dir
            temp_output_path = Path(temp_output_dir)
            
            # Compare mother.gdml
            ref_mother = ref_output_path / "mother.gdml"
            temp_mother = temp_output_path / "mother.gdml"
            
            if not ref_mother.exists():
                pytest.skip(f"Reference mother.gdml not found: {ref_mother}")
            
            are_equal, diff_msg = compare_gdml_files(temp_mother, ref_mother)
            assert are_equal, f"mother.gdml differs: {diff_msg}"
            
            # Compare Volumes directory
            ref_volumes = ref_output_path / "Volumes"
            temp_volumes = temp_output_path / "Volumes"
            
            if not ref_volumes.exists():
                pytest.skip(f"Reference Volumes directory not found: {ref_volumes}")
            
            are_equal, errors = compare_volumes_directories(temp_volumes, ref_volumes)
            if not are_equal:
                error_msg = "Volumes directory comparison failed:\n" + "\n".join(f"  - {e}" for e in errors)
                pytest.fail(error_msg)
        
        finally:
            # Cleanup
            if os.path.exists(temp_output_dir):
                shutil.rmtree(temp_output_dir)

