# Handoff: native `<box>` export for cuboid parts (CADtoGeant4)

**For a fresh chat working in `/home/icortino/irene_playground/cad2gdml`.**
Goal: make the CAD→GDML exporter emit a native GDML `<box>` (plus a placement
transform) for parts that are cuboids, instead of always emitting a
`<tessellated>` triangle mesh. Non-cuboid parts stay tessellated. This is a
clean, upstream fix for gPET-sim issue #110.

---

## 1. Why

In gPET-sim, Stage-2 (scanner replay) spends ~50 % of its time navigating the
29,376 scanner crystals, which are **tessellated solids**. But every crystal is
a plain cuboid (3.95 × 5.3 × 25 mm), just rotated into the ring — navigated the
slow triangle-by-triangle way. Swapping them to native `G4Box` measured
**+21.9 % Stage-2 throughput, −30 % geometry init, and physics bit-identical**
(23 hits differ out of 6.53 M; per-crystal-map χ²/ndf = 0.000).

That win was prototyped in gPET-sim with a **downstream patch** that reads the
tessellated triangles back and re-fits a box (`gPET-sim/scripts/issue110/gen_box_gdml.py`
on branch `feature/issue110-native-solids`). That's backwards: the tessellation
is *born here*, in CADtoGeant4. The right fix is to **not tessellate cuboids in
the first place** — do it at export. Then gPET-sim receives clean native GDML,
no patch, bit-exact, for every scanner ever exported.

(The separate hierarchical/module speedup — another ~+50 % on top — is a
Geant4-runtime construction choice and stays in gPET-sim. This task is only the
per-part `box`-vs-`mesh` decision.)

---

## 2. Where the code is

`libs/GUIMeshLibs/WriteGDML.py`:

- **`CreateGDML(obj, vol_numb, path_to_mesh)`** (~line 133) — writes one part's
  `Volumes/<label>.gdml`. Today it calls
  `triangles = obj.VolumeCAD.Shape.tessellate(precision)` and **always** writes
  `<tessellated>` (line ~156) from `triangles[1]` (triangle index list) over
  vertices `triangles[0]` (Nx3 vertex list). The part's *pose is baked into the
  absolute vertex coordinates*; the solid sits at origin conceptually.
- **`CreateMother(dir_path, object_list, world, world_pos, world_material)`**
  (~line 48) — writes `mother.gdml`. For each part it emits a `<physvol>` that
  `<file>`-includes the part and places it at
  `<positionref ref="geometry_offset"/>` + `<rotationref ref="identity"/>`.
  `geometry_offset` = `-world_pos` (m), the translation that centres the bounding
  box at the origin — applied to **every** part.

Both are called from `src/GUIMeshCLI.py` (~lines 640–644): `CreateMother(...)`
first, then a loop of `CreateGDML(obj, i, ...)`.

`libs/GUIMeshLibs/CrystalCenters.py` already computes crystal centres/orientations
— read it, it may have reusable box-fitting / orientation code, and its output
(the crystal map) must stay consistent with whatever transform you emit.

---

## 3. What to build

For each part, decide **box vs mesh**, and if box, emit a native `<box>` with a
per-part placement transform.

### 3a. Detect a cuboid
Robust, FreeCAD-independent test (matches the vetted downstream prototype): fit
an oriented bounding box (OBB) to the tessellated vertices and check every vertex
lies on an OBB corner within a tolerance (residual ≈ 0). A true cuboid mesh has 8
distinct corner positions and 12 triangles; but fit-and-check is safer than
counting. (Optional cross-check via FreeCAD: `obj.VolumeCAD.Shape` with 6 planar
faces and `ShapeType == "Solid"`.)

### 3b. Box + orientation from vertices (the vetted math)
This is the tricky part — **it's already solved** in
`gPET-sim/scripts/issue110/gen_box_gdml.py` (branch `feature/issue110-native-solids`).
**Read that file; port `box_from_vertices` and `angles_from_R` verbatim.** Summary:

```python
# vertices: (N,3) array of the part's tessellated vertices (CAD frame, mm)
c = vertices.mean(0)                    # box centre
q = vertices - c
evals, V = np.linalg.eigh(q.T @ q)      # V columns = box local axes in world (ascending extent)
if np.linalg.det(V) < 0: V[:,0] = -V[:,0]   # make a proper rotation (det +1)
half = np.abs(q @ V).max(0)             # half-extents along local x,y,z
# full box dims = 2*half; local x=smallest extent ... z=largest (stable if extents differ)
```

### 3c. GDML rotation convention (VERIFIED against Geant4 11.3.1 source — do not guess)
`G4GDMLReadStructure::PhysvolRead` builds the placement as
`transform = GetRotationMatrix(rot).inverse() * position`, and
`GetRotationMatrix(ax,ay,az) = rotateX(ax).rotateY(ay).rotateZ(az)`. CLHEP
rotate* left-multiply, so the built matrix is `R = Rz(az)·Ry(ay)·Rx(ax)` and the
placement uses `R⁻¹ = Rᵀ`. Net: a local point maps to world as
`p_world = Rᵀ · p_local + position`.

We want `Rᵀ = M` (the local-axes-in-world matrix, i.e. `V` above), so `R = Mᵀ`,
then extract `(ax,ay,az)` from `R = Rz·Ry·Rx`:

```python
# R = M.T
ay = arcsin(-R[2,0]);  ax = atan2(R[2,1], R[2,2]);  az = atan2(R[1,0], R[0,0])
# gimbal-lock fallback when |R[2,0]|≈1 — see gen_box_gdml.py angles_from_R()
```

Write these as the physvol `<rotation ... unit="rad">`. **Always verify** by
reconstructing the 8 box corners `Rᵀ·(±half) + c` (rebuild R from the emitted
angles) and checking they match the original vertices to < 1e-3 mm — the
prototype does this over every crystal and aborts on failure (max error there was
2.7e-13 mm). This is the safety net against orientation bugs (the classic
"careful with orientation and translation" trap).

### 3d. Placement + the geometry_offset
Tessellated parts get `geometry_offset` (= `-world_pos`) applied at placement.
A box part carries a *per-part* position, so it can't use `<positionref
ref="geometry_offset"/>`. Bake the offset in:

```
physvol position (mm) = box_centre_CAD (mm) + geometry_offset (mm)
physvol rotation      = (ax, ay, az) from 3c
```

(`geometry_offset` is in metres in `<define>`; convert to mm.)

---

## 4. Design / wiring

`CreateMother` runs before the `CreateGDML` loop and both iterate the same
`object_list`, so compute the box decision **once** and share it. Cleanest:

1. A small pass (or inside `CreateGDML`) annotates each `obj` with, e.g.,
   `obj._box = None` (mesh) or `obj._box = {center, half_dims, angles}` (cuboid).
2. **`CreateGDML`**: if `obj._box`, write a `<box name="<label>_solid" x= y= z=
   lunit="mm"/>` (full dims, axis-aligned at origin) instead of `<tessellated>`;
   the `<structure>`/`<volume>`/`<solidref>`/`<setup>` boilerplate is unchanged.
3. **`CreateMother`**: for a box part, emit the physvol with an inline
   `<position .../>` + `<rotation ... unit="rad"/>` (offset baked in) instead of
   the `geometry_offset` + `identity` refs. Mesh parts unchanged.

Keep it minimal and matching the surrounding style (this repo writes GDML with
raw `F.write(...)` string building — follow that, don't introduce an XML lib).

---

## 5. Validate

1. **Geometry round-trip (offline, no Geant4):** for each box part, reconstruct
   corners from the emitted `<box>`+transform and compare to the original
   tessellated vertices — must match < 1e-3 mm (see §3c). This alone proves
   correctness.
2. **End-to-end in gPET-sim (authoritative):** export a scanner (the 34x6 /
   4D-PET geometry is the reference), point g4ring's `detectorGeometry` at the
   new `mother.gdml`, run a Stage-2 replay, and compare per-crystal hit map +
   energy spectrum against the tessellated export with the χ² harness at
   `gPET-sim/scripts/issue110/compare.py`. Expect bit-identical (per-crystal
   χ²/ndf ≈ 0, only a handful of fp-boundary hits differing). Ask the user before
   running long sims — and note the sim host runs a production sweep that must be
   paused first (`gPET-sim/scripts/sweep_ops/pause.sh sc44_nema_prod`) and
   resumed after.
3. **Existing tests:** `tests/test_reference_commands.py` checks **byte-stable**
   GDML output against references — emitting boxes will change those outputs.
   Regenerate/adjust the reference fixtures deliberately (confirm with the user),
   and keep a tessellated-only regression path so mesh parts stay byte-stable.

---

## 6. Environment / running

- Python tool; geometry ops need **FreeCAD** (`obj.VolumeCAD.Shape.tessellate`).
  See `README_DEV.md` / `README_morePET.md` for setup; a `.venv/` exists.
- Entry point: `src/GUIMeshCLI.py`. Read `README.md` for the CLI invocation and
  `tests/test_reference_commands.py` for exact working command lines + fixtures.
- Tests: `pytest` (`pytest.ini` present). Some tests are guarded to run without
  FreeCAD; the STEP/mesh path needs it.

---

## 7. Reference material (read these first)

- `gPET-sim/scripts/issue110/gen_box_gdml.py` (branch `feature/issue110-native-solids`)
  — the vetted vertex→box+rotation implementation with the verified GDML
  convention and the corner-check. **Port its math.**
- `gPET-sim/docs/records/issue110_native_solid_geometry_plan.md` (same branch) —
  full findings: why boxes, the +21.9 %/+74 % measurements, the orientation
  convention, and why parameterised/OBB-passive approaches failed (context, not
  needed to implement this task).
- This repo: `libs/GUIMeshLibs/WriteGDML.py` (`CreateGDML`, `CreateMother`),
  `libs/GUIMeshLibs/CrystalCenters.py`, `src/GUIMeshCLI.py`.

## 8. Scope guardrails

- **Only** the per-part box-vs-mesh export + placement transform. No hierarchy /
  module grouping (that lives in gPET-sim's `NativeScanner`).
- Cuboids → `<box>`; everything else (covers, baseplates, anything non-box) →
  keep `<tessellated>` exactly as today.
- Preserve part labels, copy-number workflow, materials, and `geometry_offset`
  semantics — gPET-sim's readout keys on the physvol copy number and the
  `_detector_lyso` name substring; don't change those.
- Byte-stable output for mesh parts (don't perturb the tessellated path).
