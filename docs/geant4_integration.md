# Reading crystal poses in Geant4

`--extract-centers` writes a single `<output_dir>/lyso_crystal_centers.h5`. One row per LYSO crystal in the CAD frame (post-translation if `--center-geometry` was used; the applied translation is in `geometry_transform.json`).

## Per-crystal datasets

| Field | Type | Units | Meaning |
|---|---|---|---|
| `crystal_id` | int32 | — | Unique crystal index |
| `volume_name` | bytes | — | Source CAD label |
| `center_x`, `center_y`, `center_z` | float64 | mm | Bounding-box center |
| `dir_x`, `dir_y`, `dir_z` | float64 | unit vector | Long (radial) axis, sign-canonicalized |

`dir` is undirected — opposite-pointing parallel crystals share a direction.

## File-level attrs

Constants of the geometry, written once:

| Attr | Type | Meaning |
|---|---|---|
| `scanner_axial_axis` | `'x' \| 'y' \| 'z'` | World axis pointing along the scanner long direction |
| `crystal_size_radial_mm` | float64 | Crystal depth (along `dir`) |
| `crystal_size_axial_mm` | float64 | Transverse dimension along `scanner_axial_axis` |
| `crystal_size_tangential_mm` | float64 | Remaining transverse dimension |

For square cross-sections `axial == tangential`.

## Building a `G4PVPlacement`

Box dimensions: `(tangential, axial, radial)` if your local frame is `(x, y, z)` = (tangential, axial, radial). Then build the rotation by mapping local `z` → `dir` and local `y` → `scanner_axial_axis` world unit vector:

```cpp
G4ThreeVector position(center_x * mm, center_y * mm, center_z * mm);
G4ThreeVector dir(dir_x, dir_y, dir_z);                 // long axis
G4ThreeVector axialWorld = /* (1,0,0), (0,1,0), or (0,0,1) per attr */;

// Local z → dir, local y → axialWorld; local x = local y × local z.
G4ThreeVector localY = axialWorld;
G4ThreeVector localZ = dir;
G4ThreeVector localX = localY.cross(localZ).unit();
localY = localZ.cross(localX).unit();   // re-orthogonalise

G4RotationMatrix rot(localX, localY, localZ);   // columns = local axes in world frame
new G4PVPlacement(G4Transform3D(rot, position),
                  crystal_logical, "crystal", world_logical, false, crystal_id);
```

`crystal_logical` is a `G4Box` of half-extents `(tangential/2, axial/2, radial/2)` in mm.

## Reading the H5 (HDF5 C++ API)

```cpp
H5::H5File f("lyso_crystal_centers.h5", H5F_ACC_RDONLY);

// Per-crystal arrays
auto read_double = [&](const char* name) {
    H5::DataSet d = f.openDataSet(name);
    hsize_t n; d.getSpace().getSimpleExtentDims(&n);
    std::vector<double> v(n);
    d.read(v.data(), H5::PredType::NATIVE_DOUBLE);
    return v;
};
auto cx = read_double("center_x"), cy = read_double("center_y"), cz = read_double("center_z");
auto dx = read_double("dir_x"),    dy = read_double("dir_y"),    dz = read_double("dir_z");

// File-level attrs
auto get_double_attr = [&](const char* name) {
    double v; f.openAttribute(name).read(H5::PredType::NATIVE_DOUBLE, &v); return v;
};
double radial      = get_double_attr("crystal_size_radial_mm");
double axial_dim   = get_double_attr("crystal_size_axial_mm");
double tangential  = get_double_attr("crystal_size_tangential_mm");

H5::Attribute axisAttr = f.openAttribute("scanner_axial_axis");
H5::StrType vlen(0, H5T_VARIABLE);
std::string axisName;
axisAttr.read(vlen, axisName);   // "x" | "y" | "z"
```

## Migrating from `azimuth_angle` / `elevation_angle`

If you previously read those columns: derive on the fly. Pick the projection by `scanner_axial_axis`:

```cpp
// axial = "y": azimuth lives in XZ
double azimuth   = std::atan2(dir_z, dir_x);
double elevation = std::atan2(dir_y, std::hypot(dir_x, dir_z));

// axial = "z": azimuth lives in XY
double azimuth   = std::atan2(dir_y, dir_x);
double elevation = std::atan2(dir_z, std::hypot(dir_x, dir_y));
```
