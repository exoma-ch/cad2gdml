# Reading crystal poses in Geant4

`--extract-centers` produces `<output_dir>/lyso_crystal_centers.{csv,h5}` (same data, two formats). One row per LYSO crystal.

## Schema

| Column | Type | Units | Meaning |
|---|---|---|---|
| `crystal_id` | int32 | — | Unique crystal index |
| `volume_name` | string | — | Source CAD label |
| `center_x`, `center_y`, `center_z` | float64 | mm | Bounding-box center |
| `dir_x`, `dir_y`, `dir_z` | float64 | unit vector | Crystal long axis |

Frame: the original CAD frame, post-translation if `--center-geometry` was used (the applied translation is in `geometry_transform.json`).

`(dir_x, dir_y, dir_z)` is sign-canonicalized: the first significant component is non-negative. The long axis is undirected, so opposite-pointing crystals share a direction vector.

## Building a placement

If your `G4Box` has its long axis along **local Z** (typical PET convention):

```cpp
G4ThreeVector position(center_x * mm, center_y * mm, center_z * mm);
G4ThreeVector direction(dir_x, dir_y, dir_z);

G4RotationMatrix rot;
G4ThreeVector localZ(0, 0, 1);
G4double angle = localZ.angle(direction);
if (angle > 1e-9 && angle < CLHEP::pi - 1e-9) {
    rot.rotate(angle, localZ.cross(direction).unit());
} else if (angle >= CLHEP::pi - 1e-9) {
    rot.rotate(CLHEP::pi, G4ThreeVector(1, 0, 0));  // 180° flip
}

new G4PVPlacement(G4Transform3D(rot, position),
                  crystal_logical, "crystal", world_logical, false, crystal_id);
```

Rotation around the long axis is undefined by the schema. Fine for square cross-sections; if your crystals are rectangular, you need a separate convention (e.g. align local X with the scanner axial axis).

## Migrating from `azimuth_angle` / `elevation_angle`

The old columns are gone. Pick the projection that matches your scanner's axial axis and derive on the fly:

```cpp
// Y-axial scanner (azimuth in XZ plane):
double azimuth   = std::atan2(dir_z, dir_x);
double elevation = std::atan2(dir_y, std::hypot(dir_x, dir_z));

// Z-axial scanner (azimuth in XY plane):
double azimuth   = std::atan2(dir_y, dir_x);
double elevation = std::atan2(dir_z, std::hypot(dir_x, dir_y));
```

To detect the axial axis from the data: it's the world axis `i` for which `mean(dir_i²)` is smallest (long axes lie in the ring plane, perpendicular to the scanner axis).
