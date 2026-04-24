"""
Tests for the --dump-parts feature.

Covers dump_part_list() method and the CLI --dump-parts argument.
"""
import pytest
import os
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import GUIMeshCLI as _guimesh_module
from GUIMeshCLI import GUIMeshCLI, main


def make_mock_volume(label):
    vol = MagicMock()
    vol.VolumeCAD.Label = label
    return vol


# ---------------------------------------------------------------------------
# Unit tests for dump_part_list()
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDumpPartList:

    def test_writes_labels_one_per_line(self, mesh_cli_unit, temp_dir):
        labels = ["lyso_001", "lyso_002", "screw_003"]
        mesh_cli_unit.list_of_objects = [make_mock_volume(l) for l in labels]

        out_file = os.path.join(temp_dir, "parts.txt")
        result = mesh_cli_unit.dump_part_list(out_file)

        assert result is True
        written = Path(out_file).read_text().splitlines()
        assert written == labels

    def test_returns_false_when_no_volumes(self, mesh_cli_unit, temp_dir, capsys):
        mesh_cli_unit.list_of_objects = []

        out_file = os.path.join(temp_dir, "parts.txt")
        result = mesh_cli_unit.dump_part_list(out_file)

        assert result is False
        assert not os.path.exists(out_file)

    def test_label_count_in_output(self, mesh_cli_unit, temp_dir, capsys):
        labels = [f"part_{i:03d}" for i in range(50)]
        mesh_cli_unit.list_of_objects = [make_mock_volume(l) for l in labels]

        out_file = os.path.join(temp_dir, "parts.txt")
        mesh_cli_unit.dump_part_list(out_file)

        written = Path(out_file).read_text().splitlines()
        assert len(written) == 50

    def test_returns_false_on_write_error(self, mesh_cli_unit, capsys):
        mesh_cli_unit.list_of_objects = [make_mock_volume("part_a")]

        # Unwritable path
        result = mesh_cli_unit.dump_part_list("/nonexistent_dir/parts.txt")

        assert result is False
        captured = capsys.readouterr()
        assert "Error" in captured.out

    def test_single_volume(self, mesh_cli_unit, temp_dir):
        mesh_cli_unit.list_of_objects = [make_mock_volume("only_part")]

        out_file = os.path.join(temp_dir, "parts.txt")
        result = mesh_cli_unit.dump_part_list(out_file)

        assert result is True
        assert Path(out_file).read_text().strip() == "only_part"

    def test_labels_with_special_characters(self, mesh_cli_unit, temp_dir):
        labels = ["PH_Countersunk_flat_head_screw_M3x0_5_x_12", "Part_1_alu001"]
        mesh_cli_unit.list_of_objects = [make_mock_volume(l) for l in labels]

        out_file = os.path.join(temp_dir, "parts.txt")
        mesh_cli_unit.dump_part_list(out_file)

        assert Path(out_file).read_text().splitlines() == labels


# ---------------------------------------------------------------------------
# CLI integration tests for --dump-parts argument
# ---------------------------------------------------------------------------

@pytest.mark.cli
class TestDumpPartsCLI:

    def _run_main(self, argv):
        with patch('sys.argv', argv):
            with patch('sys.stdout', new=StringIO()) as out:
                main()
                return out.getvalue()

    def test_dump_parts_without_step_prints_error(self):
        output = self._run_main(['GUIMeshCLI.py', '--dump-parts', '/tmp/parts.txt'])
        assert 'Error' in output

    def test_dump_parts_calls_dump_method(self, temp_dir):
        out_file = os.path.join(temp_dir, "parts.txt")
        mock_mesh_instance = MagicMock()
        mock_mesh_instance.load_step_file.return_value = True
        mock_mesh_instance.check_material_mappings_file.return_value = None
        mock_mesh_instance.dump_part_list.return_value = True
        mock_mesh_instance.verbose = False
        mock_mesh_instance.center_geometry = False
        mock_mesh_instance.output_dir = None

        with patch('sys.argv', ['GUIMeshCLI.py', '--step', 'fake.step', '--dump-parts', out_file]):
            with patch.object(_guimesh_module, 'GUIMeshCLI', return_value=mock_mesh_instance):
                main()

        mock_mesh_instance.load_step_file.assert_called_once_with('fake.step')
        mock_mesh_instance.dump_part_list.assert_called_once_with(out_file)

    def test_dump_parts_exits_before_other_operations(self, temp_dir):
        """After dumping, no material assignment or GDML writing should happen."""
        out_file = os.path.join(temp_dir, "parts.txt")
        mock_mesh_instance = MagicMock()
        mock_mesh_instance.load_step_file.return_value = True
        mock_mesh_instance.dump_part_list.return_value = True

        with patch('sys.argv', ['GUIMeshCLI.py',
                                '--step', 'fake.step',
                                '--dump-parts', out_file,
                                '--output-dir', temp_dir]):
            with patch.object(_guimesh_module, 'GUIMeshCLI', return_value=mock_mesh_instance):
                main()

        mock_mesh_instance.dump_part_list.assert_called_once()
        mock_mesh_instance.write_gdml.assert_not_called()
        mock_mesh_instance.assign_materials_from_names.assert_not_called()
