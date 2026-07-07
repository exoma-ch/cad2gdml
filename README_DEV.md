# Developer Documentation

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

Volume names are lowercased; the first matching pattern in `material_mappings.json` wins. Each mapping entry may carry an optional `path` field pointing at a custom material JSON file (resolved relative to the mapping JSON); those files are auto-loaded by the script when `--assign-materials` runs. Entries without `path` are assumed to be NIST built-ins.

### Solid export: native box vs tessellated mesh

`WriteGDML.annotate_boxes()` runs once before the mother/volume files are written and classifies every exported part:

- **Cuboids → native GDML `<box>`.** A part whose tessellation is a clean, orthogonal 8-corner box is exported as an origin-centred `G4Box` plus a per-part `<position>`/`<rotation>` in `mother.gdml`. Geant4 navigates the analytic box instead of triangle-by-triangle, a large Stage-2 speedup for scanners built from thousands of crystals (gPET-sim issue #110).
- **Everything else → `<tessellated>`,** byte-for-byte as before.

The box axes/half-extents come from the part's three principal edges (`CrystalCenters.principal_edges`, the same decomposition used to build the crystal map — extent-independent, so cubes and square cross-sections work too). The rotation follows Geant4's placement convention `p_world = Rᵀ·p_local + pos` with `R = Rz(az)·Ry(ay)·Rx(ax)`. Every candidate box is only accepted after reconstructing its 8 corners with that exact math and checking they match the original vertices to < 1e-3 mm; anything above tolerance falls back to tessellated, so a bad fit can never place a solid wrong. The classification is shared by `CreateMother` (placement) and `CreateGDML` (solid) via `obj._box`.

### Hierarchical export (`--hier`) and overlap check (`--check-overlaps`)

`HierGDML.write_hier_gdml()` (runs after `annotate_boxes` and the flat export) emits `mother_hier.gdml`: one vacuum G4Trd wedge envelope per flat panel, tangential faces set back 0.5 mm from the inter-panel bisector planes so the wedges tile the ring disjointly and no envelope face touches matter. Ported from gPET-sim `scripts/issue110/gen_hier_gdml.py` (validated there: 1.6–2.1× Stage-2 throughput, hit-level physics equivalence; measurements and equivalence method in gPET-sim `docs/records/issue110_native_solid_geometry_plan.md` §9); the exporter version derives panels, roles, and the axial axis from geometry instead of that script's hardcoded name-prefix/y-axis assumptions.

**How the structure is discovered** (all in `HierGDML.py`; every step is geometric except crystal identification):

1. **Crystals** are the parts whose label matches the `--add-copynumbers` prefix convention `<prefix><N>` (default `_detector_lyso_`; the bare prefix is crystal 0). This is the only name-based classification. Crystals must be cuboids (native-box fits from `annotate_boxes`); a mesh crystal aborts the export.
2. **Scanner axial axis** (`_axial_axis`): the unit direction all crystal long axes avoid — the smallest-eigenvalue eigenvector of the covariance of the long-axis unit vectors. The long axis of a crystal is its largest box extent (radial in a ring scanner).
3. **Modules/panels** (`_group_modules`): a module is a cluster of crystals sharing (sign-canonicalized long-axis direction rounded to 1e-4, ring side), where side = the sign of (centre − ring centre)·direction and the ring centre is the mean of all crystal centres. I.e. a flat panel = mutually parallel crystals on the same side of the ring. Each module gets a right-handed frame R = [tangential, axial, radial] with radial = the crystal long axis. (Two panels stacked axially at the same azimuth merge into one module — intended, the wedge just grows axially.)
4. **Non-crystal cuboids** (`_assign_to_module` + `_fits_sector`): a part joins the module whose crystal footprint contains its centre (±10 mm tangential/axial margin, 60 mm radial window; radially nearest wins ties) **and** whose ring sector (2π/N wedge minus the 0.5 mm setback) contains every one of its vertices. Anything else — multi-panel rails, out-of-ring hardware — stays in the world with its flat-mother placement.
5. **Non-cuboids**: a 16-vertex tessellation matching the five-sided open-tray shape (`_decompose_cover`: 3 face planes on the open axis, 4 on each transverse axis) is decomposed into 5 exact box slabs, accepted only if the slab volumes sum to the mesh volume (rel. 1e-6) and the tray fits a single panel sector; the slabs are then clipped to the module's crystal AABBs (the CAD interpenetrates cover walls and crystals — see the overlap check below). Everything else stays tessellated in the world, never inside an envelope.

**Assumptions** (violations abort with `HierExportError`, or are checked by the gates):

- crystals follow the copynumber-prefix naming and have unique numbers;
- crystal long axes lie in a common ring plane (max |dir·axial| ≤ 1e-3) and point radially (|dir·r̂| within 1e-6 of 1);
- panels form a **uniform ring**: ≥ 3 panels, equal radii (spread ≤ 0.01 mm), equal azimuthal spacing (≤ 1e-4 rad from 2π/N) — the wedge tiling is only disjoint under this premise, hence asserted;
- every part that lies inside a panel sector is a cuboid or an exactly-decomposable tray (otherwise the world-side clearance gate fails — a tessellated part can't be left in the world where a wedge envelope needs to be).

The wedge (G4Trd) sizing: the tangential half-width tapers with the local radial coordinate exactly along the ring sector, half-width(z) = (Rc + s·z)·tan(π/N) − 0.5 mm, so neighbouring envelopes are disjoint by construction; axial/radial faces sit 0.05 mm outside the content AABB. Panel contents become native `G4Box` physvols sharing one solid + logical volume per (kind, material, dimensions); crystal physvols always carry copy numbers and the shared crystal LV keeps the copynumber-prefix substring downstream readout keys on. Hard gates before anything is written: every in-envelope part's 8 corners reconstructed through the nested placement (envelope rotation ∘ local rotation) match the flat-export vertices to < 1e-3 mm; every content vertex lies inside its wedge; every world-side vertex lies outside every wedge. Tolerances/constants are module-level constants at the top of `HierGDML.py`.

`OverlapCheck.check_overlaps()` (`--check-overlaps`) reports interpenetrating exported parts: AABB sweep for candidate pairs, exact separating-axis penetration depth for box-box pairs (reported above 0.01 mm), FreeCAD boolean common volume for pairs involving tessellated parts (reported above 1e-4 mm³). Touching faces pass. Known real defect this catches: the 34x6 cover walls interpenetrate the crystal ends by ~0.15 mm — masked by flat tessellated navigation but physics-corrupting on native geometries.

### Crystal Orientation Algorithm

The extractor assumes each LYSO volume is a clean parallelepiped that tessellates to exactly 8 vertices, with one unambiguously longest edge. This is true for typical PET crystals (depth ≫ width ≈ height) and is intentionally a strong assumption — there is no fallback for curved, chamfered, or otherwise non-parallelepiped shapes.

From any reference vertex, the 7 outbound vectors are 3 edges, 3 face diagonals, and 1 body diagonal. The body diagonal is the longest. The 3 edges are the unique triple of the remaining 6 vectors that sums to the body diagonal — no other triple does, because face-diagonal-containing triples produce duplicated edge contributions. Sorted by length, the three edges give the radial (long) and the two transverse dimensions. The long-axis unit vector is sign-canonicalized (first significant component non-negative) so opposite-pointing parallel crystals share a direction key.

### File-level metadata

The extractor also emits H5 attrs (no per-row redundancy):

- `scanner_axial_axis` — picked as the world axis with the smallest mean(`dir²`); long axes lie in the ring plane, so this is the axis they avoid.
- `crystal_size_radial_mm` — the long edge length.
- `crystal_size_axial_mm` / `crystal_size_tangential_mm` — the two transverse edge lengths, assigned by which one's edge vector is most parallel to `scanner_axial_axis` (per crystal, aggregated). Identical values for square cross-sections.

If a volume violates the parallelepiped assumption (vertex count != 8 or no edge triple summing to the body diagonal), it is skipped with a prominent warning rather than getting a guessed direction.

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
