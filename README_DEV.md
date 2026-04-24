# GUIMeshCLI - Developer Documentation

## Development Environment

All dependencies (FreeCAD, Python packages) are in the container. Build and enter it as described in `README.md`. All development, testing, and manual runs happen inside the container.

### Releasing a new container image version

Push a git tag to trigger the automated build:

```bash
git tag -a v1.1.0 -m "Release version 1.1.0"
git push origin v1.1.0
```

GitHub Actions builds the image and pushes it to `ghcr.io/morepet/cadtogeant4/cadtogeant4` with the version tag. Monitor progress in the Actions tab.

## Project Architecture

### Data Flow

```
STEP file
  └─► LoadOP.Load_STEP_File()          → list of Volume objects
        ├─► Materials.Load_Material_JSON()
        ├─► assign_materials_from_names()   (pattern match on volume names)
        ├─► CrystalCenters.extract_crystal_centers()
        └─► WriteGDML.CreateMother() / CreateGDML()
```

### Source Files

| File | Role |
|------|------|
| `src/GUIMeshCLI.py` | CLI entry point, orchestration |
| `libs/GUIMeshLibs/LoadOP.py` | STEP loading via FreeCAD |
| `libs/GUIMeshLibs/Materials.py` | Material loading and validation |
| `libs/GUIMeshLibs/Volumes.py` | `Volume` data structure |
| `libs/GUIMeshLibs/WriteGDML.py` | GDML file generation |
| `libs/GUIMeshLibs/CrystalCenters.py` | Crystal center/orientation extraction |
| `src/material_mappings.json` | Pattern → material assignment rules |

### Material Assignment

Volume names are lowercased; the first matching pattern in `material_mappings.json` wins. Materials marked `requires_custom: true` must also be loaded via `--load-materials`.

### Crystal Orientation Algorithm (Direct Edge Vector Analysis)

1. Extract all vertices from the tessellated shape
2. Compute all pairwise edge vectors
3. For each edge, count parallel edges
4. Select the longest edge that has exactly 3 parallel edges (parallelepiped property)
5. Derive azimuth (`atan2(z, x)`) and elevation (`atan2(y, sqrt(x²+z²))`) from that axis

This works well for rectangular parallelepiped crystals and is more reliable than PCA for regular geometries.

## Testing

Tests must be run **inside the container** (FreeCAD and all dependencies are only available there).

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Single test file
pytest tests/test_cli_no_step.py
```

Coverage is reported automatically. HTML report is written to `htmlcov/`.

## Troubleshooting

**FreeCAD import errors** — check `PYTHONPATH` and `LD_LIBRARY_PATH`; the container sets these automatically. If running outside the container, FreeCAD libs are expected at `/usr/local/bin/squashfs-root/usr/lib` (configurable in `GUIMeshCLI.py` line 42).

**Material loading issues** — validate JSON syntax; confirm the `material` name in `material_mappings.json` matches the `name` field in the loaded material JSON.

**GDML generation errors** — ensure every volume has an assigned material; check for invalid geometry (self-intersections).

**Crystal extraction issues** — algorithm assumes rectangular parallelepipeds; use `--verbose` to trace which volumes are processed.

## Additional Resources

- [FreeCAD Documentation](https://www.freecad.org/)
- [GDML Specification](https://gdml.web.cern.ch/GDML/)
- [Geant4 Documentation](https://geant4.web.cern.ch/)
- [Original GUIMesh3](https://github.com/MPintoSpace/GUIMesh3)

## License

GNU General Public License v3.0 — see `COPYING.txt`.
