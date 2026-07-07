#########################################################################################################
#    GUIMesh v1                                                                                         #
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
#                                                                                                       #
#########################################################################################################

"""Part-overlap check (``--check-overlaps``): exported parts must not
interpenetrate.

Motivation (issue #20): the 34x6 CAD's cover walls interpenetrate the crystal
ends by ~0.15 mm. In a flat tessellated world Geant4 resolves the contested
slab by navigation happenstance, silently mis-assigning energy deposits; on
native geometries the same defect voided ~0.02 % of in-crystal-source events
until root-caused downstream. Overlaps should be fixed in the CAD (or clipped,
as ``--hier`` does for covers) — this check makes them fail loudly at export
time instead of surfacing as physics anomalies months later.

Method: after :func:`WriteGDML.annotate_boxes`, every exported part has either
a native-box fit or a cached tessellation. Candidate pairs come from an
axis-aligned bounding-box sweep. For box-box pairs the exact separating-axis
test on the fitted cuboids gives a penetration depth (minimum translation
distance upper bound); touching faces report ~0 and are ignored below
``PENETRATION_TOL_MM``. Pairs involving a non-cuboid part are decided on the
ground-truth CAD solids with a FreeCAD boolean intersection; a common volume
above ``COMMON_VOLUME_TOL_MM3`` is an overlap.
"""

import numpy as np

from GUIMeshLibs.WriteGDML import _R_from_angles

# Minimum box-box penetration depth (mm) reported as an overlap. Must sit above
# the native-box corner-fit tolerance (1e-3 mm) so faces that merely touch
# never trigger; the known CAD defects are >= 0.1 mm.
PENETRATION_TOL_MM = 0.01
# Minimum boolean-intersection volume (mm^3) reported as an overlap for pairs
# involving a tessellated part. Touching solids produce ~0 (sliver noise well
# below this); the known cover/crystal defect measures a few mm^3 per pair.
COMMON_VOLUME_TOL_MM3 = 1e-4

_CORNERS = np.array([[sx, sy, sz]
                     for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)],
                    dtype=float)


def _entries(object_list):
    """Per exported part: name, box pose (or None), vertex cloud, AABB, and
    the FreeCAD object (for boolean fallbacks)."""
    entries = []
    for obj in object_list:
        if getattr(obj, 'VolumeGDMLoption', None) != 1:
            continue
        name = str(obj.VolumeCAD.Label)
        box = getattr(obj, '_box', None)
        if box is not None:
            center = np.asarray(box['center'], dtype=float)
            M = _R_from_angles(*box['angles']).T   # columns = local axes in world
            h = np.asarray(box['full'], dtype=float) / 2.0
            verts = (M @ (_CORNERS * h).T).T + center
        else:
            triangles = getattr(obj, '_triangles', None)
            if triangles is None:
                triangles = obj.VolumeCAD.Shape.tessellate(obj.VolumeMMD)
            center = M = h = None
            verts = np.asarray(triangles[0], dtype=float)
        entries.append(dict(name=name, obj=obj, center=center, M=M, h=h,
                            lo=verts.min(0), hi=verts.max(0)))
    return entries


def _sat_depth(a, b):
    """Penetration depth (mm) of two oriented boxes via the separating-axis
    test over the 15 candidate axes: > 0 means the boxes interpenetrate by at
    least that translation distance; <= 0 means separated (or just touching)."""
    axes = [a['M'][:, k] for k in range(3)] + [b['M'][:, k] for k in range(3)]
    for i in range(3):
        for j in range(3):
            c = np.cross(a['M'][:, i], b['M'][:, j])
            n = np.linalg.norm(c)
            if n > 1e-9:
                axes.append(c / n)
    d = b['center'] - a['center']
    depth = np.inf
    for ax in axes:
        ra = np.abs(ax @ a['M']) @ a['h']
        rb = np.abs(ax @ b['M']) @ b['h']
        depth = min(depth, ra + rb - abs(float(np.dot(d, ax))))
        if depth <= 0:
            return depth
    return depth


def check_overlaps(object_list, verbose=False):
    """Check all exported parts for mutual overlaps. Returns the list of
    offending pairs (dicts with part names and a measured penetration depth or
    intersection volume); empty list means the export is overlap-free."""
    entries = _entries(object_list)
    n = len(entries)
    lo = np.array([e['lo'] for e in entries])
    hi = np.array([e['hi'] for e in entries])

    # Broad phase: sweep along x, then AABB test. Requiring AABB overlap
    # > PENETRATION_TOL_MM on every axis is sound for the SAT stage (the
    # minimum translation distance never exceeds any single-axis AABB overlap)
    # and safe for the boolean stage (a common volume needs interior overlap).
    order = np.argsort(lo[:, 0], kind='stable')
    candidates = []
    for oi, i in enumerate(order):
        for j in order[oi + 1:]:
            if lo[j, 0] >= hi[i, 0] - PENETRATION_TOL_MM:
                break
            ov = np.minimum(hi[i], hi[j]) - np.maximum(lo[i], lo[j])
            if np.all(ov > PENETRATION_TOL_MM):
                candidates.append((int(min(i, j)), int(max(i, j))))
    print("Overlap check: {} exported parts, {} AABB candidate pairs".format(
        n, len(candidates)))

    overlaps = []
    n_bool = sum(1 for i, j in candidates
                 if entries[i]['M'] is None or entries[j]['M'] is None)
    done_bool = 0
    for i, j in candidates:
        a, b = entries[i], entries[j]
        if a['M'] is not None and b['M'] is not None:
            depth = _sat_depth(a, b)
            if depth > PENETRATION_TOL_MM:
                overlaps.append(dict(a=a['name'], b=b['name'],
                                     metric='penetration {:.3f} mm'.format(depth),
                                     depth_mm=float(depth)))
        else:
            # Ground-truth CAD boolean for pairs involving a non-cuboid part.
            done_bool += 1
            if verbose or done_bool % 50 == 0:
                print("  boolean intersection {}/{} ({} vs {})".format(
                    done_bool, n_bool, a['name'], b['name']))
            try:
                common = a['obj'].VolumeCAD.Shape.common(b['obj'].VolumeCAD.Shape)
                vol = float(common.Volume)
            except Exception as e:
                print("Warning: boolean intersection failed for {} vs {} ({}); "
                      "pair not checked.".format(a['name'], b['name'], e))
                continue
            if vol > COMMON_VOLUME_TOL_MM3:
                overlaps.append(dict(a=a['name'], b=b['name'],
                                     metric='common volume {:.4f} mm^3'.format(vol),
                                     volume_mm3=vol))

    if overlaps:
        overlaps.sort(key=lambda o: -(o.get('depth_mm', 0.0) * 1e6
                                      + o.get('volume_mm3', 0.0)))
        print("\nOVERLAP CHECK FAILED: {} interpenetrating part pair(s):".format(
            len(overlaps)))
        for o in overlaps[:30]:
            print("  {} <-> {}  ({})".format(o['a'], o['b'], o['metric']))
        if len(overlaps) > 30:
            print("  ... and {} more".format(len(overlaps) - 30))
        print("These parts interpenetrate in the CAD. Geant4 resolves the "
              "contested region by navigation happenstance, silently "
              "corrupting energy assignment. Fix the CAD (preferred) or "
              "handle the overlap explicitly downstream.")
    else:
        print("Overlap check passed: no interpenetrating parts.")
    return overlaps
