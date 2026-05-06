#########################################################################################################
#    GUIMesh v1                                                                                         #
#                                                                                                       #
#    Copyright (c) 2018  Marco Gui Alves Pinto mail:mgpinto11@gmail.com                                 #
#                                                                                                       #
#    This program is free software: you can redistribute it and/or modify                               #
#    it under the terms of the GNU General Public License as published by                               #
#    the Free Software Foundation, either version 3 of the License, or                                  #
#    (at your option) any later version.                                                                #
#                                                                                                       #
#    This program is distributed in the hope that it will be useful,                                    #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of                                     #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                                      #
#    GNU General Public License for more details.                                                       #
#                                                                                                       #
#    You should have received a copy of the GNU General Public License                                  #
#    along with this program.  If not, see <https://www.gnu.org/licenses/>                              #
#                                                                #########################################

import math
import os
import re

# Output schema for crystal centers (CSV columns and H5 datasets).
# Direction is a unit vector along the crystal's long axis, in the same
# coordinate frame as the centers. No spherical-coordinate convention is baked
# in: anything that needs azimuth/elevation can derive them from the direction.
CRYSTAL_FIELDS = (
    'crystal_id', 'volume_name',
    'center_x', 'center_y', 'center_z',
    'dir_x', 'dir_y', 'dir_z',
)


def _canonical_sign(vec, eps=1e-9):
    """Flip sign so the first significant component is positive.

    The crystal long axis is undirected (a line, not an arrow), so two crystals
    with opposite long-axis vectors describe the same orientation. Canonicalizing
    the sign makes equality and clustering by direction stable.
    """
    for v in vec:
        if v > eps:
            return tuple(vec)
        if v < -eps:
            return tuple(-v for v in vec)
    return tuple(vec)


def _long_axis_from_vertices(vertices):
    """Long-axis unit vector of a parallelepiped from its 8 tessellated vertices.

    From any reference vertex V0, the other 7 vertices are reached by:
      - 3 edge vectors           e1, e2, e3
      - 3 face-diagonal vectors  e1+e2, e1+e3, e2+e3
      - 1 body-diagonal vector   e1+e2+e3
    The body diagonal is the longest outbound vector. The 3 edges are the
    unique triple in the remaining 6 whose sum equals the body diagonal —
    no other triple sums to it (face-diagonal-containing triples produce
    duplicated edge contributions). Once edges are identified, the longest
    is the crystal's long axis.

    This characterisation works for elongated crystals (where length-based
    selection like "3 shortest outbound vectors" picks face diagonals
    instead of edges) and for rectangular as well as oblique parallelepipeds.

    Returns None if the vertex count is not 8 or no triple sums to the body
    diagonal within tolerance (degenerate / non-parallelepiped shape).
    """
    from itertools import combinations

    if len(vertices) != 8:
        return None

    ref = vertices[0]
    outbound = [(v[0] - ref[0], v[1] - ref[1], v[2] - ref[2]) for v in vertices[1:]]

    def sq(v):
        return v[0] * v[0] + v[1] * v[1] + v[2] * v[2]

    diag_idx = max(range(7), key=lambda i: sq(outbound[i]))
    diag = outbound[diag_idx]
    diag_sq = sq(diag)
    if diag_sq == 0:
        return None
    others = [v for i, v in enumerate(outbound) if i != diag_idx]

    # Triple sum tolerance scales with the body-diagonal magnitude squared so
    # tessellation noise on big crystals doesn't cause false rejections.
    tol_sq = max(diag_sq * 1e-12, 1e-12)
    edges = None
    for i, j, k in combinations(range(6), 3):
        a, b, c = others[i], others[j], others[k]
        diff = (a[0] + b[0] + c[0] - diag[0],
                a[1] + b[1] + c[1] - diag[1],
                a[2] + b[2] + c[2] - diag[2])
        if sq(diff) < tol_sq:
            edges = (a, b, c)
            break
    if edges is None:
        return None

    longest = max(edges, key=sq)
    length = math.sqrt(sq(longest))
    return (longest[0] / length, longest[1] / length, longest[2] / length)


def extract_crystal_number(volume_label):
    """Extract crystal number from a volume label.

    Returns the int found in the label, or 0 for the special bare label
    (FreeCAD's first instance has no numeric suffix), or None if no number
    can be extracted.
    """
    if volume_label in ('_detector_lyso_', 'Crystal'):
        return 0

    patterns = [
        r'_detector_lyso_(\d+)',
        r'Part_(\d+)',
        r'Crystal_(\d+)',
        r'LYSO_(\d+)',
        r'(\d+)$',
        r'(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, volume_label)
        if match:
            return int(match.group(1))
    return None


def extract_crystal_centers(list_of_objects, verbose=False, output_file=None,
                            output_dir=None, vertex_counts=None, translation=None):
    """Extract LYSO crystal centers and long-axis direction vectors.

    For each LYSO crystal the function emits:
      - center_{x,y,z}: bounding-box center in mm (in original CAD frame, or
        translated if ``translation`` is given).
      - dir_{x,y,z}: unit vector along the crystal's long axis, in the same
        frame, sign-canonicalized so opposite-pointing crystals share a direction.

    No axial-axis convention is applied here — downstream code (plotting,
    Geant4 export) is expected to consume the raw vector and apply whatever
    convention it needs. This makes the extractor agnostic to whether the CAD
    has its scanner axial axis along X, Y, or Z.

    Assumptions on the input geometry (no fallback if violated):
      - Each LYSO volume is a clean parallelepiped that tessellates to exactly
        8 vertices. Curved or chamfered shapes will fail.
      - The three edge lengths are distinct enough that one is unambiguously the
        long axis (typical PET crystal: depth ≫ width ≈ height).
      - That long axis is the physically meaningful crystal axis (the depth
        direction, ~radial in a ring scanner). The extractor does not check
        that — it just trusts the geometry.

    Crystals that violate the parallelepiped assumption (vertex count != 8 or
    no edge triple summing to the body diagonal) are skipped with a warning.

    Args:
        list_of_objects: List of volume objects (FreeCAD-style with .VolumeCAD/.VolumeMaterial).
        verbose: Enable verbose output.
        output_file: Optional output path (or True to use the default name).
                     CSV and H5 are written side-by-side.
        output_dir: Optional output directory for auto-generated filenames.
        vertex_counts: Optional list, populated with per-crystal tessellated vertex counts.
        translation: Optional (tx, ty, tz) in mm applied to crystal centers.

    Returns:
        (crystal_records, success): list of dicts with the columns above,
        and a bool indicating clean completion.
    """
    if not list_of_objects:
        print("Error: No volumes loaded")
        return [], False

    crystal_centers = []
    lyso_count = 0
    used_crystal_ids = set()

    if vertex_counts is None:
        vertex_counts = []

    print(f"\n=== LYSO Crystal Center Analysis ===")
    if translation is not None:
        print(f"Translation applied: ({translation[0]:.1f}, {translation[1]:.1f}, {translation[2]:.1f}) mm")
    else:
        print(f"Using original CAD coordinates (no translation)")
    print(f"Direction vectors are unit vectors along the crystal long axis (sign-canonicalized).")
    print(f"Scanning {len(list_of_objects)} volumes for LYSO crystals...")

    if verbose:
        print("First 10 volume names:")
        for i, obj in enumerate(list_of_objects[:10]):
            print(f"  {i}: {obj.VolumeCAD.Label} (material: {obj.VolumeMaterial.Name if obj.VolumeMaterial else 'Unknown'})")

    for i, obj in enumerate(list_of_objects):
        try:
            volume_label = obj.VolumeCAD.Label
            material_name = obj.VolumeMaterial.Name if obj.VolumeMaterial else "Unknown"
            if "lyso" not in volume_label.lower() and material_name != "LYSO":
                continue

            lyso_count += 1
            bbox = obj.VolumeCAD.Shape.BoundBox
            cx = (bbox.XMin + bbox.XMax) / 2.0
            cy = (bbox.YMin + bbox.YMax) / 2.0
            cz = (bbox.ZMin + bbox.ZMax) / 2.0

            triangles = obj.VolumeCAD.Shape.tessellate(0.1)
            vertices = triangles[0]
            vertex_counts.append(len(vertices))
            if verbose:
                print(f"  Crystal {volume_label}: {len(vertices)} vertices")
            direction = _long_axis_from_vertices(vertices)
            if direction is None:
                # Hard assumption: LYSO volumes are clean parallelepipeds with a
                # clearly identifiable long axis. If we get here, the input
                # violates that — skip with a prominent warning rather than
                # invent a wrong direction.
                print(f"  WARNING: {volume_label} is not a valid parallelepiped "
                      f"(vertex count={len(vertices)}, no edge triple summed to "
                      f"the body diagonal). Skipping this crystal.")
                lyso_count -= 1
                continue

            dx, dy, dz = _canonical_sign(direction)

            crystal_number = extract_crystal_number(volume_label)
            if crystal_number is None:
                print(f"\n ERROR: No crystal number found in volume name '{volume_label}'")
                print(f"Expected patterns: '_detector_lyso_123', 'Part_456', 'Crystal_789', etc.")
                print(f"Found {lyso_count} LYSO crystals before error.")
                return [], False
            if crystal_number in used_crystal_ids:
                print(f"\n ERROR: Duplicate crystal ID {crystal_number} in volume name '{volume_label}'")
                print(f"Found {lyso_count} LYSO crystals before error.")
                return [], False
            used_crystal_ids.add(crystal_number)

            if translation is not None:
                cx += translation[0]
                cy += translation[1]
                cz += translation[2]

            crystal_centers.append({
                'crystal_id': crystal_number,
                'volume_name': volume_label,
                'center_x': cx, 'center_y': cy, 'center_z': cz,
                'dir_x': dx, 'dir_y': dy, 'dir_z': dz,
            })

            if verbose and lyso_count <= 10:
                print(f"  {lyso_count:4d}: {volume_label:30s} | "
                      f"Center: ({cx:7.2f}, {cy:7.2f}, {cz:7.2f}) mm | "
                      f"Dir: ({dx:+.3f}, {dy:+.3f}, {dz:+.3f})")

        except Exception as e:
            print(f"Warning: Could not process volume {i+1} ({obj.VolumeCAD.Label}): {e}")
            continue

    print(f"Found {lyso_count} LYSO crystals")
    if verbose and lyso_count > 10:
        print(f"  ... and {lyso_count - 10} more LYSO crystals")

    if crystal_centers:
        xs = [c['center_x'] for c in crystal_centers]
        ys = [c['center_y'] for c in crystal_centers]
        zs = [c['center_z'] for c in crystal_centers]
        n = len(crystal_centers)
        # Mean of squared direction component per axis: small means "long axis
        # rarely points this way" → likely the scanner axial axis.
        mx = sum(c['dir_x'] ** 2 for c in crystal_centers) / n
        my = sum(c['dir_y'] ** 2 for c in crystal_centers) / n
        mz = sum(c['dir_z'] ** 2 for c in crystal_centers) / n
        likely_axial = min((('x', mx), ('y', my), ('z', mz)), key=lambda kv: kv[1])[0]

        print(f"\n=== LYSO Crystal Summary Statistics ===")
        print(f"Total LYSO crystals: {n}")
        print(f"X range: {min(xs):.2f} to {max(xs):.2f} mm (span: {max(xs)-min(xs):.2f} mm)")
        print(f"Y range: {min(ys):.2f} to {max(ys):.2f} mm (span: {max(ys)-min(ys):.2f} mm)")
        print(f"Z range: {min(zs):.2f} to {max(zs):.2f} mm (span: {max(zs)-min(zs):.2f} mm)")
        print(f"Mean(dir²) per axis: x={mx:.3f}, y={my:.3f}, z={mz:.3f}  → likely axial: {likely_axial.upper()}")

        if vertex_counts:
            print(f"Vertex counts: {min(vertex_counts)} to {max(vertex_counts)} per crystal "
                  f"(avg: {sum(vertex_counts)/len(vertex_counts):.1f})")

    if output_file:
        csv_file, h5_file = _resolve_output_paths(output_file, output_dir)
        csv_dir = os.path.dirname(csv_file)
        if csv_dir and not os.path.exists(csv_dir):
            try:
                os.makedirs(csv_dir, exist_ok=True)
                if verbose:
                    print(f"Created output directory: {csv_dir}")
            except Exception as e:
                print(f"Error creating output directory '{csv_dir}': {e}")
                return crystal_centers, False

        if not _write_csv(csv_file, crystal_centers):
            return crystal_centers, False
        print(f"\nCrystal centers saved to CSV: {csv_file}")

        if _write_h5(h5_file, crystal_centers):
            print(f"Crystal centers saved to H5: {h5_file}")

    return crystal_centers, True


def _resolve_output_paths(output_file, output_dir):
    """Compute the (csv_path, h5_path) pair for the requested output_file."""
    if output_file is True:
        base = os.path.join(output_dir, 'lyso_crystal_centers') if output_dir else 'lyso_crystal_centers'
        return base + '.csv', base + '.h5'

    if output_dir and not os.path.isabs(output_file) and not os.path.dirname(output_file):
        output_file = os.path.join(output_dir, output_file)

    if output_file.endswith('.csv'):
        return output_file, output_file[:-4] + '.h5'
    if output_file.endswith('.h5'):
        return output_file[:-3] + '.csv', output_file
    return output_file + '.csv', output_file + '.h5'


def _write_csv(csv_file, crystal_centers):
    try:
        import csv
        with open(csv_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=list(CRYSTAL_FIELDS))
            writer.writeheader()
            for crystal in crystal_centers:
                writer.writerow(crystal)
        return True
    except Exception as e:
        print(f"Error saving crystal centers to CSV: {e}")
        return False


def _write_h5(h5_file, crystal_centers):
    try:
        import h5py
        import numpy as np
    except ImportError:
        print("Warning: h5py not available. Skipping H5 file creation.")
        print("Install h5py with: pip install h5py")
        return False

    try:
        with h5py.File(h5_file, 'w') as f:
            f.create_dataset('crystal_id',
                             data=np.array([c['crystal_id'] for c in crystal_centers], dtype=np.int32),
                             compression='gzip')
            for col in ('center_x', 'center_y', 'center_z', 'dir_x', 'dir_y', 'dir_z'):
                f.create_dataset(col,
                                 data=np.array([c[col] for c in crystal_centers], dtype=np.float64),
                                 compression='gzip')
            f.create_dataset('volume_name',
                             data=[c['volume_name'].encode('utf-8') for c in crystal_centers],
                             compression='gzip')
            f.attrs['description'] = 'LYSO crystal centers and long-axis direction vectors'
            f.attrs['n_crystals'] = len(crystal_centers)
            f.attrs['units'] = 'mm for centers; dimensionless for direction (unit vector)'
            f.attrs['frame'] = 'CAD coordinate frame (post-translation if --center-geometry was used)'
            f.attrs['created_by'] = 'GUIMeshCLI'
        return True
    except Exception as e:
        print(f"Error saving crystal centers to H5: {e}")
        return False
