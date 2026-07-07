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

"""Hierarchical (``--hier``) GDML export: ``mother_hier.gdml``.

Emits a two-level ALL-NATIVE geometry alongside the flat ``mother.gdml``: one
vacuum G4Trd wedge envelope per flat panel (module), containing the panel's
cuboid parts as native G4Box physvols (one shared solid + logical volume per
part type; crystal physvols keep their copy numbers) and each five-sided cover
tray decomposed into 5 native box slabs. Parts that fit no single panel sector
(e.g. multi-panel base rails) stay in the world, placed exactly as in the flat
mother. Wedge tangential faces are set back from the inter-panel bisector
planes so the envelopes tile the ring disjointly and no envelope face touches
matter (a flush face measurably perturbs electron MSC stepping).

Ported from the vetted downstream post-processor
``gPET-sim/scripts/issue110/gen_hier_gdml.py`` (measured 1.6-2.1x Stage-2
throughput on the 34x6; hit-level physics equivalence documented in gPET-sim
``docs/records/issue110_native_solid_geometry_plan.md`` section 9). Where that
script reverse-engineered structure from the flattened GDML, this module works
from the exporter's ground truth, generalizing what was hardcoded downstream:

- scanner axial axis derived from the crystal long-axis directions (the
  direction they all avoid) instead of assuming y;
- part grouping by (material, dimensions) instead of a name-prefix role table
  (crystals are still identified by the ``--add-copynumbers`` label prefix,
  the established downstream convention);
- the uniform-ring assumption is asserted explicitly (equal panel radii and
  equal azimuthal spacing) instead of silently assumed;
- non-cuboid parts that don't decompose exactly into boxes stay tessellated in
  the world, never inside an envelope.

Cover clipping: the CAD interpenetrates the cover walls and the crystal ends
(~0.15 mm on the 34x6). Flat tessellated navigation resolves the contested slab
inconsistently and masked the defect; on the hier geometry it silently voided
~0.02 % of in-crystal-source events until root-caused. The cover slabs are
clipped to the crystal faces, making the resolution deterministic (slab =
crystal, the reference majority behaviour). ``--check-overlaps`` reports the
underlying CAD defect on the flat export.

Correctness gates (export aborts with :class:`HierExportError` if violated):

1. every in-envelope part's 8 corners reconstructed through the full nested
   Geant4 placement math (envelope rotation o local rotation) agree with the
   flat-export vertices to < 1e-3 mm (cover slabs: after a mesh-volume ==
   box-sum gate on the 5-slab decomposition);
2. panels form a uniform ring (equal radii, equal azimuthal spacing) so the
   wedges tile the ring disjointly by construction (0.5 mm setback from the
   inter-panel bisector planes);
3. every in-envelope part lies strictly inside its wedge;
4. world-side parts stay strictly outside every wedge;
5. crystal copy numbers are unique and the crystal-prefix substring survives
   in the shared crystal LV name (downstream readout keys on both).
"""

import re

import numpy as np

from GUIMeshLibs.WriteGDML import (
    DEFAULT_COPYNUMBER_PREFIX,
    _angles_from_R,
    _R_from_angles,
    _write_materials_block,
)


class HierExportError(RuntimeError):
    """A --hier correctness gate failed; mother_hier.gdml was not written."""


# mm clearance between the envelope faces and the content AABB (axial/radial).
ENVELOPE_MARGIN_MM = 0.05
# mm setback of each wedge tangential face from the inter-panel bisector plane.
SECTOR_GAP_MM = 0.5
# Panel-assignment pre-filter: a part is a candidate for a panel if its centre
# lies within the panel's crystal footprint plus this tangential/axial margin
# and within this radial window of the crystal-stack centre. Pure heuristic —
# the sector-fit test and the hard containment gates decide correctness.
ASSIGN_TA_MARGIN_MM = 10.0
ASSIGN_RADIAL_WINDOW_MM = 60.0
# Max nested corner-reconstruction disagreement (mm), as in the box export.
CORNER_TOL_MM = 1e-3
# Crystal long axes must lie in the ring plane: max |dir . axial| allowed.
AXIAL_TOL = 1e-3
# Uniform-ring gates: spread of panel radii (mm) / azimuthal spacing (rad).
RING_RADIUS_TOL_MM = 0.01
RING_SPACING_TOL_RAD = 1e-4
# Cover decomposition gate: |sum(slab volumes) - mesh volume| / mesh volume.
COVER_VOLUME_RTOL = 1e-6

_CORNERS = np.array([[sx, sy, sz]
                     for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)],
                    dtype=float)


def _crystal_number(label, prefix):
    """Copy number from a crystal label ('<prefix><N>', bare '<prefix>' -> 0),
    or None if the label doesn't follow the crystal naming convention."""
    if label == prefix:
        return 0
    m = re.fullmatch(re.escape(prefix) + r'(\d+)', label)
    return int(m.group(1)) if m else None


def _sanitize(name):
    return re.sub(r'[^A-Za-z0-9_]', '_', name)


def _type_base_name(label):
    """Part-type name from a part label: strip the trailing instance number
    ('sipm_si014' -> 'sipm_si') and sanitize for GDML name tokens."""
    base = re.sub(r'[_\-]*\d+$', '', label) or label
    return _sanitize(base)


def _mesh_volume(triangles):
    """Volume (mm^3) enclosed by a tessellation (verts, tri-indices) via the
    divergence theorem. Same quantity gen_hier_gdml.py computed from the GDML."""
    verts = np.asarray(triangles[0], dtype=float)
    tris = np.asarray(triangles[1], dtype=int)
    v1, v2, v3 = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    return abs(np.einsum('ij,ij->i', v1, np.cross(v2, v3)).sum() / 6.0)


def _box_verts(center, M, h):
    """8 world corners of a box: columns of M are the local axes in world."""
    return (M @ (_CORNERS * h).T).T + center


def _collect_parts(object_list, prefix):
    """Split annotated exported objects into crystal boxes, other boxes, and
    tessellated (non-cuboid) parts, as plain numpy records."""
    crystals, boxes, meshes = [], [], []
    for obj in object_list:
        if getattr(obj, 'VolumeGDMLoption', None) != 1:
            continue
        label = str(obj.VolumeCAD.Label)
        material = str(obj.VolumeMaterial.Name)
        copyno = _crystal_number(label, prefix)
        box = getattr(obj, '_box', None)
        if box is not None:
            M = _R_from_angles(*box['angles']).T   # columns = local axes in world
            h = np.asarray(box['full'], dtype=float) / 2.0
            center = np.asarray(box['center'], dtype=float)
            rec = dict(name=label, material=material, copyno=copyno,
                       center=center, M=M, h=h, verts=_box_verts(center, M, h))
            (crystals if copyno is not None else boxes).append(rec)
            continue
        if copyno is not None:
            raise HierExportError(
                "--hier: crystal '{}' is not a clean cuboid (no native-box fit); "
                "cannot build the hierarchical geometry.".format(label))
        triangles = getattr(obj, '_triangles', None)
        if triangles is None:
            raise HierExportError(
                "--hier: part '{}' has no cached tessellation; run "
                "annotate_boxes first.".format(label))
        verts = np.asarray(triangles[0], dtype=float)
        meshes.append(dict(name=label, material=material, copyno=None,
                           verts=verts, triangles=triangles,
                           center=verts.mean(0)))
    return crystals, boxes, meshes


def _long_axis(p):
    return p['M'][:, int(np.argmax(p['h']))]


def _canonical(vec):
    d = np.asarray(vec, dtype=float)
    return -d if d[int(np.argmax(np.abs(d)))] < 0 else d


def _axial_axis(crystals):
    """Scanner axial axis: the unit direction all crystal long axes avoid
    (smallest-eigenvalue eigenvector of the direction covariance). Generalizes
    the downstream hardcoded y axis; aborts if the long axes don't lie in a
    common ring plane."""
    dirs = np.array([_long_axis(p) for p in crystals])
    _, V = np.linalg.eigh(dirs.T @ dirs / len(dirs))
    axial = _canonical(V[:, 0])
    worst = float(np.abs(dirs @ axial).max())
    if worst > AXIAL_TOL:
        raise HierExportError(
            "--hier: crystal long axes do not lie in a common ring plane "
            "(max |dir.axial| = {:.2e} > {:.0e}); not a ring scanner?".format(
                worst, AXIAL_TOL))
    return axial


def _group_modules(crystals, axial, ring_center):
    """Group crystals into flat panels by (canonical long-axis direction, ring
    side) and build each panel's local frame R = [tangential, axial, radial]
    (columns = module axes in world)."""
    groups = {}
    for i, p in enumerate(crystals):
        dd = _canonical(_long_axis(p))
        side = 1 if np.dot(p['center'] - ring_center, dd) >= 0 else -1
        key = tuple(np.round(dd * 1e4).astype(int)) + (side,)
        groups.setdefault(key, []).append(i)

    modules = []
    for key, idxs in groups.items():
        dd = _canonical(_long_axis(crystals[idxs[0]]))
        eT = np.cross(axial, dd)
        eT /= np.linalg.norm(eT)
        eA = np.cross(dd, eT)
        R = np.stack([eT, eA, dd], axis=1)
        mc = np.mean([crystals[i]['center'] for i in idxs], axis=0)
        locs = np.array([R.T @ (crystals[i]['center'] - mc) for i in idxs])
        modules.append(dict(R=R, mc=mc, s=float(key[-1]), cryst=idxs,
                            parts=[], covers=[],
                            ext=(locs[:, 0].min(), locs[:, 0].max(),
                                 locs[:, 1].min(), locs[:, 1].max())))
    return modules


def _assert_uniform_ring(modules, axial, ring_center):
    """The wedge tiling needs equally spaced panels at equal radius; assert it
    instead of silently assuming it (the downstream script's implicit premise)."""
    n = len(modules)
    if n < 3:
        raise HierExportError(
            "--hier needs at least 3 panels to tile a ring with wedges "
            "(found {}).".format(n))
    # Orthonormal in-plane basis for azimuth angles.
    u = np.cross(axial, [1.0, 0.0, 0.0])
    if np.linalg.norm(u) < 1e-6:
        u = np.cross(axial, [0.0, 1.0, 0.0])
    u /= np.linalg.norm(u)
    v = np.cross(axial, u)
    radii, angles, rhats = [], [], []
    for M in modules:
        r = M['mc'] - ring_center
        r_perp = r - np.dot(r, axial) * axial
        radii.append(np.linalg.norm(r_perp))
        angles.append(np.arctan2(np.dot(r_perp, v), np.dot(r_perp, u)))
        rhats.append(r_perp / np.linalg.norm(r_perp))
    spread = max(radii) - min(radii)
    if spread > RING_RADIUS_TOL_MM:
        raise HierExportError(
            "--hier: panels are not at a common radius (spread {:.4f} mm > "
            "{} mm); wedge tiling needs a uniform ring.".format(
                spread, RING_RADIUS_TOL_MM))
    order = np.argsort(angles)
    gaps = np.diff(np.array(angles)[order])
    gaps = np.append(gaps, 2 * np.pi + angles[order[0]] - angles[order[-1]])
    worst = float(np.abs(gaps - 2 * np.pi / n).max())
    if worst > RING_SPACING_TOL_RAD:
        raise HierExportError(
            "--hier: panels are not equally spaced in azimuth (max deviation "
            "{:.2e} rad from 2*pi/{}); wedge tiling needs a uniform ring.".format(
                worst, n))
    for M, rhat in zip(modules, rhats):
        # The wedge taper assumes the panel's radial axis points away from the
        # ring axis; check it (module R[:,2] is the crystal long axis).
        if abs(np.dot(M['R'][:, 2], rhat)) < 1.0 - 1e-6:
            raise HierExportError(
                "--hier: panel radial axis is not aligned with the ring "
                "radius (|dd.rhat| = {:.6f}); wedge tiling is not valid.".format(
                    abs(np.dot(M['R'][:, 2], rhat))))


def _decompose_cover(verts):
    """16-vert five-sided open tray -> 5 exact box slabs (top plate + 4 walls).

    Returns ([(center, half_extents, V_cols)] x 5, sum of slab volumes), or
    None if the vertex cloud doesn't match the tray shape. Ported verbatim
    from gen_hier_gdml.py.
    """
    verts = np.asarray(verts, dtype=float)
    c0 = verts.mean(0)
    q = verts - c0
    _, V = np.linalg.eigh(q.T @ q)
    if np.linalg.det(V) < 0:
        V[:, 0] = -V[:, 0]
    loc = q @ V

    def cluster(vals):
        vals = np.sort(vals)
        groups, cur = [], [vals[0]]
        for x in vals[1:]:
            if x - cur[-1] < 1e-4:
                cur.append(x)
            else:
                groups.append(np.mean(cur))
                cur = [x]
        groups.append(np.mean(cur))
        return np.array(groups)

    planes = [cluster(loc[:, k]) for k in range(3)]
    open_ax = next((k for k in range(3) if len(planes[k]) == 3), None)
    if open_ax is None or any(len(planes[k]) != 4 for k in range(3) if k != open_ax):
        return None
    a1, a2 = [k for k in range(3) if k != open_ax]
    q1, q2, q3 = planes[open_ax]
    if q2 - q1 < q3 - q2:              # plate at the LOW end: flip the axis so
        V[:, open_ax] *= -1            # the plate is always at the top
        loc = q @ V
        planes[open_ax] = cluster(loc[:, open_ax])
    bot, itop, otop = planes[open_ax]
    o1lo, i1lo, i1hi, o1hi = planes[a1]
    o2lo, i2lo, i2hi, o2hi = planes[a2]

    def box(lo, hi):
        lo3 = np.array([lo[k] for k in range(3)])
        hi3 = np.array([hi[k] for k in range(3)])
        return (V @ ((lo3 + hi3) / 2) + c0, (hi3 - lo3) / 2, V)

    boxes = [
        box({open_ax: itop, a1: o1lo, a2: o2lo}, {open_ax: otop, a1: o1hi, a2: o2hi}),   # top plate
        box({open_ax: bot, a1: o1lo, a2: o2lo}, {open_ax: itop, a1: i1lo, a2: o2hi}),    # wall a1-
        box({open_ax: bot, a1: i1hi, a2: o2lo}, {open_ax: itop, a1: o1hi, a2: o2hi}),    # wall a1+
        box({open_ax: bot, a1: i1lo, a2: o2lo}, {open_ax: itop, a1: i1hi, a2: i2lo}),    # wall a2-
        box({open_ax: bot, a1: i1lo, a2: i2hi}, {open_ax: itop, a1: i1hi, a2: o2hi}),    # wall a2+
    ]
    vol_boxes = sum(8 * h[0] * h[1] * h[2] for _, h, _ in boxes)
    return boxes, vol_boxes


def _fits_sector(verts, module, axial, ring_center, n_modules):
    """True if every vertex lies inside the module's ring sector (with the
    SECTOR_GAP_MM setback) on the module's side of the ring. Exact geometric
    eligibility test for putting a part inside this module's wedge."""
    R = module['R']
    tan_th = np.tan(np.pi / n_modules)
    rel = verts - ring_center
    t = rel @ R[:, 0]                              # offset from the panel
    r = (rel @ R[:, 2]) * module['s']              # azimuth plane; outward radial
    if np.any(r <= 0):
        return False
    return bool(np.all(np.abs(t) < r * tan_th - SECTOR_GAP_MM))


def _assign_to_module(part, modules, axial, ring_center):
    """Panel whose crystal footprint contains the part's centre (radially
    nearest on ties), or None. Mirrors gen_hier_gdml.py's assignment."""
    best, bestd = None, None
    for mi, M in enumerate(modules):
        loc = M['R'].T @ (part['center'] - M['mc'])
        t0, t1, a0, a1 = M['ext']
        if (t0 - ASSIGN_TA_MARGIN_MM < loc[0] < t1 + ASSIGN_TA_MARGIN_MM
                and a0 - ASSIGN_TA_MARGIN_MM < loc[1] < a1 + ASSIGN_TA_MARGIN_MM
                and abs(loc[2]) < ASSIGN_RADIAL_WINDOW_MM):
            if best is None or abs(loc[2]) < bestd:
                best, bestd = mi, abs(loc[2])
    return best


def _build_envelopes(modules, crystals, boxes, covers, axial, ring_center):
    """Per module: local placements, cover-slab clipping, envelope AABB, and
    the end-to-end nested corner-reconstruction gate. Returns env_defs entries
    (envc_w, R, half, contents, ctr_l, Re) mirroring gen_hier_gdml.py, where
    contents = (kind, part, pos_local, angles_local)."""
    maxerr = 0.0
    nclip_total = 0
    env_defs = []
    for M in modules:
        R, mc = M['R'], M['mc']
        contents = []
        lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
        for kind, pool, idxs in (('cryst', crystals, M['cryst']),
                                 ('box', boxes, M['parts'])):
            for i in idxs:
                p = pool[i]
                Rc = p['M'].T @ R                  # part rotation in module frame
                angles = _angles_from_R(Rc)
                pos_l = R.T @ (p['center'] - mc)
                corners_l = (_R_from_angles(*angles).T @ (_CORNERS * p['h']).T).T + pos_l
                lo = np.minimum(lo, corners_l.min(0))
                hi = np.maximum(hi, corners_l.max(0))
                contents.append((kind, p, pos_l, angles))

        # Crystal AABBs in the module frame (crystals are axis-aligned there),
        # used to clip the cover slabs: the CAD interpenetrates cover walls and
        # crystal ends, and the legacy tessellated navigation resolves the
        # contested slab to the CRYSTAL. Clipping the cover boxes to the
        # crystal faces makes the native geometry reproduce that resolution
        # deterministically.
        cry_lo = np.array([R.T @ (crystals[i]['center'] - mc) for i in M['cryst']])
        c0 = crystals[M['cryst'][0]]
        chalf_l = np.abs((c0['M'].T @ R).T) @ c0['h']
        cry_hi = cry_lo + chalf_l
        cry_lo = cry_lo - chalf_l
        for ci in M['covers']:
            p = covers[ci]
            for k, (bc, bh, BV) in enumerate(p['boxes']):
                Rc = BV.T @ R
                pos_l = R.T @ (bc - mc)
                ext_l = np.abs(Rc).T @ bh
                blo, bhi = pos_l - ext_l, pos_l + ext_l
                # Clip against every intersecting crystal along the
                # least-overlap axis.
                for it in range(9):
                    ov_lo = np.maximum(blo, cry_lo)
                    ov_hi = np.minimum(bhi, cry_hi)
                    depth = ov_hi - ov_lo
                    inter = np.all(depth > 1e-9, axis=1)
                    if not inter.any():
                        break
                    if it == 8:
                        raise HierExportError(
                            "--hier: cover slab {}_w{} still intersects "
                            "crystals after 8 clips.".format(p['name'], k))
                    j = int(np.argmax(np.where(inter, depth.min(1), -1)))
                    ax = int(np.argmin(depth[j]))
                    if cry_lo[j, ax] <= blo[ax]:
                        blo[ax] = cry_hi[j, ax]
                    else:
                        bhi[ax] = cry_lo[j, ax]
                    nclip_total += 1
                    if bhi[ax] - blo[ax] <= 1e-6:
                        raise HierExportError(
                            "--hier: cover slab {}_w{} clipped away entirely "
                            "by the crystals.".format(p['name'], k))
                pos_l = (blo + bhi) / 2
                ext_l = (bhi - blo) / 2
                bh2 = np.abs(Rc) @ ext_l           # back to slab-local half extents
                bc2 = R @ pos_l + mc
                part = dict(name='{}_w{}'.format(p['name'], k),
                            material=p['material'], copyno=None,
                            center=bc2, M=BV, h=bh2,
                            verts=_box_verts(bc2, BV, bh2))
                angles = _angles_from_R(Rc)
                corners_l = (_R_from_angles(*angles).T @ (_CORNERS * bh2).T).T + pos_l
                lo = np.minimum(lo, corners_l.min(0))
                hi = np.maximum(hi, corners_l.max(0))
                contents.append(('coverbox', part, pos_l, angles))

        ctr_l = (lo + hi) / 2
        ctr_l[0] = 0.0                             # wedge centred on the panel azimuth
        half = (hi - lo) / 2 + ENVELOPE_MARGIN_MM
        half[0] = max(abs(lo[0]), abs(hi[0])) + ENVELOPE_MARGIN_MM
        envc_w = R @ ctr_l + mc
        Re = _angles_from_R(R.T)                   # envelope physvol angles
        Re_R = _R_from_angles(*Re)
        # End-to-end reconstruction check through the nested placement.
        for kind, p, pos_l, angles in contents:
            pos_env = pos_l - ctr_l
            recon = (Re_R.T @ ((_R_from_angles(*angles).T @ (_CORNERS * p['h']).T).T
                               + pos_env).T).T + envc_w
            d = np.linalg.norm(recon[:, None, :] - p['verts'][None, :, :], axis=2)
            maxerr = max(maxerr, float(d.min(1).max()))
        env_defs.append((envc_w, R, half, contents, ctr_l, Re))
    if maxerr >= CORNER_TOL_MM:
        raise HierExportError(
            "--hier: nested corner-reconstruction gate failed "
            "(max error {:.2e} mm >= {:.0e} mm).".format(maxerr, CORNER_TOL_MM))
    return env_defs, maxerr, nclip_total


def _size_wedges(env_defs, axial, ring_center):
    """Wedge (G4Trd) tangential half-widths at the local -z/+z faces: the faces
    taper with the ring sector, half-width(z) = (Rc + s*z)*tan(pi/N) - GAP, so
    neighbouring envelopes are disjoint by construction. Gates every content
    vertex inside its wedge."""
    th = np.pi / len(env_defs)
    wedges = []
    for mi, (envc_w, R, half, contents, ctr_l, Re) in enumerate(env_defs):
        rel = envc_w - ring_center
        r_perp = rel - np.dot(rel, axial) * axial
        Rc = float(np.linalg.norm(r_perp))
        s = 1.0 if np.dot(R[:, 2], r_perp / Rc) > 0 else -1.0
        x1h = (Rc + s * (-half[2])) * np.tan(th) - SECTOR_GAP_MM
        x2h = (Rc + s * (+half[2])) * np.tan(th) - SECTOR_GAP_MM
        if min(x1h, x2h) <= 0:
            raise HierExportError(
                "--hier: wedge {} has non-positive tangential half-width "
                "({:.3f}/{:.3f} mm); ring too small for the {} mm sector "
                "setback.".format(mi, x1h, x2h, SECTOR_GAP_MM))
        for kind, p, pos_l, angles in contents:
            vloc = (p['verts'] - envc_w) @ R
            if not np.all(np.abs(vloc[:, 1]) < half[1] + 1e-9):
                raise HierExportError(
                    "--hier: envelope {}: {} overflows axially.".format(mi, p['name']))
            if not np.all(np.abs(vloc[:, 2]) < half[2] + 1e-9):
                raise HierExportError(
                    "--hier: envelope {}: {} overflows radially.".format(mi, p['name']))
            wz = x1h + (x2h - x1h) * (vloc[:, 2] + half[2]) / (2 * half[2])
            excess = float((np.abs(vloc[:, 0]) - wz).max())
            if excess >= 0:
                raise HierExportError(
                    "--hier: envelope {}: {} outside the wedge by {:.3f} mm.".format(
                        mi, p['name'], excess))
        wedges.append((x1h, x2h))
    return wedges


def _gate_world_side(world_side, env_defs, wedges):
    """World-side parts must stay strictly outside every wedge envelope."""
    for p in world_side:
        for mi, (envc_w, R, half, contents, ctr_l, Re) in enumerate(env_defs):
            vloc = (p['verts'] - envc_w) @ R
            x1h, x2h = wedges[mi]
            wz = x1h + (x2h - x1h) * np.clip((vloc[:, 2] + half[2]) / (2 * half[2]), 0, 1)
            inside = ((np.abs(vloc[:, 1]) < half[1])
                      & (np.abs(vloc[:, 2]) < half[2])
                      & (np.abs(vloc[:, 0]) < wz))
            if inside.any():
                raise HierExportError(
                    "--hier: world-side part '{}' penetrates wedge envelope {}. "
                    "Parts inside a panel sector must be cuboids (or exactly "
                    "decomposable covers) to join the envelope.".format(
                        p['name'], mi))


def _shared_lv_groups(env_defs, prefix):
    """One shared <box> solid + logical volume per distinct in-envelope part
    type, keyed by (kind, material, full dims). Names come from the part labels
    (crystals: the copynumber prefix, preserving the substring downstream
    readout keys on; cover slabs: cover_slab_<i>)."""
    groups = {}
    for envc_w, R, half, contents, ctr_l, Re in env_defs:
        for kind, p, pos_l, angles in contents:
            key = (kind, p['material'], tuple(np.round(2 * p['h'], 9)))
            if key in groups:
                p['lv'] = groups[key]['name']
                continue
            if kind == 'cryst':
                base = _sanitize(prefix) + 'box'
            elif kind == 'coverbox':
                base = 'cover_slab_{}'.format(
                    sum(1 for g in groups if g[0] == 'coverbox'))
            else:
                base = _type_base_name(p['name']) + '_box'
            name, k = base, 1
            existing = {g['name'] for g in groups.values()}
            while name in existing:
                name = '{}_{}'.format(base, k)
                k += 1
            groups[key] = dict(name=name, material=p['material'],
                               full=tuple(2 * p['h']))
            p['lv'] = name
    return groups


def write_hier_gdml(dir_path, object_list, world, world_pos=(0.0, 0.0, 0.0),
                    world_material=None, copynumber_prefix=None, verbose=False):
    """Write ``mother_hier.gdml`` next to the flat mother. See module docstring.

    Must run after :func:`WriteGDML.annotate_boxes` (uses the cached box fits
    and tessellations) and after the flat export (world-side tessellated parts
    file-include the already-written ``Volumes/*.gdml``). Raises
    :class:`HierExportError` if any correctness gate fails.
    """
    prefix = copynumber_prefix if copynumber_prefix else DEFAULT_COPYNUMBER_PREFIX
    crystals, boxparts, meshparts = _collect_parts(object_list, prefix)
    if not crystals:
        raise HierExportError(
            "--hier: no crystal volumes matching prefix '{}' found; cannot "
            "identify panels.".format(prefix))
    seen_copynos = {}
    for p in crystals:
        if p['copyno'] in seen_copynos:
            raise HierExportError(
                "--hier: duplicate crystal copy number {} ('{}' and '{}').".format(
                    p['copyno'], seen_copynos[p['copyno']], p['name']))
        seen_copynos[p['copyno']] = p['name']

    axial = _axial_axis(crystals)
    ring_center = np.mean([p['center'] for p in crystals], axis=0)
    modules = _group_modules(crystals, axial, ring_center)
    _assert_uniform_ring(modules, axial, ring_center)
    n_mod = len(modules)
    print("Hier export: {} crystals in {} panels; scanner axial axis "
          "({:+.4f}, {:+.4f}, {:+.4f})".format(len(crystals), n_mod,
                                               axial[0], axial[1], axial[2]))

    # Non-crystal cuboids: into the owning panel's envelope if they fit its
    # ring sector, else stay in the world (exactly as in the flat mother).
    world_side = []
    n_env_boxes = 0
    for bi, p in enumerate(boxparts):
        mi = _assign_to_module(p, modules, axial, ring_center)
        if mi is not None and _fits_sector(p['verts'], modules[mi], axial,
                                           ring_center, n_mod):
            modules[mi]['parts'].append(bi)
            n_env_boxes += 1
        else:
            world_side.append(p)

    # Non-cuboid parts: decompose five-sided cover trays into 5 exact box
    # slabs (mesh-volume == box-sum gate); everything else keeps its
    # tessellated placement in the world, never inside an envelope.
    covers = []
    n_dropped_decomp = 0
    for p in meshparts:
        dec = _decompose_cover(p['verts']) if len(p['verts']) == 16 else None
        if dec is not None:
            boxes_slabs, vol_boxes = dec
            vol_mesh = _mesh_volume(p['triangles'])
            if abs(vol_boxes - vol_mesh) < COVER_VOLUME_RTOL * max(vol_mesh, 1.0):
                mi = _assign_to_module(p, modules, axial, ring_center)
                if mi is not None and _fits_sector(p['verts'], modules[mi],
                                                   axial, ring_center, n_mod):
                    p['boxes'] = boxes_slabs
                    covers.append(p)
                    modules[mi]['covers'].append(len(covers) - 1)
                    continue
                n_dropped_decomp += 1
        world_side.append(p)
    print("Hier export: per envelope {} crystals; {} box parts and {} covers "
          "(5 slabs each) joined envelopes; {} parts stay in the world.".format(
              len(modules[0]['cryst']), n_env_boxes, len(covers),
              len(world_side)))
    if n_dropped_decomp:
        print("Hier export: {} decomposable covers did not fit a single panel "
              "sector; kept tessellated in the world.".format(n_dropped_decomp))

    env_defs, maxerr, nclip = _build_envelopes(modules, crystals, boxparts,
                                               covers, axial, ring_center)
    wedges = _size_wedges(env_defs, axial, ring_center)
    _gate_world_side(world_side, env_defs, wedges)
    th = np.pi / n_mod
    print("Hier export gates: max nested corner error {:.2e} mm; {} cover-slab "
          "clips; neighbour wedge faces separated by {:.2f} mm; {} world-side "
          "parts clear of all wedges.".format(
              maxerr, nclip, 2 * SECTOR_GAP_MM * np.cos(th), len(world_side)))

    groups = _shared_lv_groups(env_defs, prefix)

    # ---- emit ---------------------------------------------------------------
    offset_mm = [-world_pos[0] * 1000.0, -world_pos[1] * 1000.0,
                 -world_pos[2] * 1000.0]
    out_path = str(dir_path) + "/mother_hier.gdml"
    F = open(out_path, "w")
    F.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
    F.write('<gdml xmlns:gdml="../schema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="../schema/gdml.xsd" >\n')
    F.write('<!--\n')
    F.write('  Hierarchical export (- -hier): one vacuum G4Trd wedge envelope per panel,\n')
    F.write('  panel contents as native G4Box physvols (shared solid+LV per part type,\n')
    F.write('  crystal copy numbers preserved), cover trays decomposed into 5 box slabs\n')
    F.write('  clipped to the crystal faces. Multi-panel parts stay in the world.\n')
    F.write('  The flat mother.gdml in this directory is the visual/debug reference.\n')
    F.write('-->\n')
    F.write('<define>\n')
    F.write('<position name="geometry_offset" x="'+str(-world_pos[0])+'" y="'+str(-world_pos[1])+'" z="'+str(-world_pos[2])+'" unit="m"/>\n')
    F.write('<rotation name="identity" x="0" y="0" z="0"/>\n')
    F.write('</define>\n')
    world_material_name = _write_materials_block(F, object_list, world_material)

    F.write('<solids>\n')
    F.write('<box name="WorldBox" x="'+str(world[0])+'" y="'+str(world[1])+'" z="'+str(world[2])+'" lunit="m"/>\n')
    for g in groups.values():
        F.write('<box name="{}_solid" x="{:.10f}" y="{:.10f}" z="{:.10f}" lunit="mm"/>\n'.format(
            g['name'], g['full'][0], g['full'][1], g['full'][2]))
    for mi, (envc_w, R, half, contents, ctr_l, Re) in enumerate(env_defs):
        x1h, x2h = wedges[mi]
        F.write('<trd name="module_env_{}_solid" x1="{:.10f}" x2="{:.10f}" '
                'y1="{:.10f}" y2="{:.10f}" z="{:.10f}" lunit="mm"/>\n'.format(
                    mi, 2 * x1h, 2 * x2h, 2 * half[1], 2 * half[1], 2 * half[2]))
    F.write('</solids>\n')

    F.write('<structure>\n')
    for g in groups.values():
        F.write('<volume name="{}_LV">\n'.format(g['name']))
        F.write('<materialref ref="{}"/>\n'.format(g['material']))
        F.write('<solidref ref="{}_solid"/>\n'.format(g['name']))
        F.write('</volume>\n')
    for mi, (envc_w, R, half, contents, ctr_l, Re) in enumerate(env_defs):
        F.write('<volume name="module_env_{}_LV">\n'.format(mi))
        F.write('<materialref ref="{}"/>\n'.format(world_material_name))
        F.write('<solidref ref="module_env_{}_solid"/>\n'.format(mi))
        for kind, p, pos_l, angles in contents:
            pe = pos_l - ctr_l
            cn = ' copynumber="{}"'.format(p['copyno']) if kind == 'cryst' else ''
            F.write('<physvol name="{}_PV"{}>\n'.format(p['name'], cn))
            F.write('<volumeref ref="{}_LV"/>\n'.format(p['lv']))
            F.write('<position name="{}_pos" x="{:.10f}" y="{:.10f}" z="{:.10f}" unit="mm"/>\n'.format(
                p['name'], pe[0], pe[1], pe[2]))
            if max(abs(a) for a in angles) >= 1e-15:
                F.write('<rotation name="{}_rot" x="{:.12f}" y="{:.12f}" z="{:.12f}" unit="rad"/>\n'.format(
                    p['name'], angles[0], angles[1], angles[2]))
            F.write('</physvol>\n')
        F.write('</volume>\n')

    F.write('<volume name="World">\n')
    F.write('<materialref ref="{}"/>\n'.format(world_material_name))
    F.write('<solidref ref="WorldBox"/>\n')
    # World-side parts: identical placement to the flat mother.
    for p in world_side:
        F.write('<physvol>\n')
        F.write('<file name="Volumes/{}.gdml"/>\n'.format(p['name']))
        if 'M' in p:                               # native box: pose baked in
            F.write('<position x="{:.10f}" y="{:.10f}" z="{:.10f}" unit="mm"/>\n'.format(
                p['center'][0] + offset_mm[0], p['center'][1] + offset_mm[1],
                p['center'][2] + offset_mm[2]))
            ax, ay, az = _angles_from_R(p['M'].T)
            F.write('<rotation x="{:.12f}" y="{:.12f}" z="{:.12f}" unit="rad"/>\n'.format(ax, ay, az))
        else:                                      # tessellated mesh
            F.write('<positionref ref="geometry_offset"/>\n')
            F.write('<rotationref ref="identity"/>\n')
        F.write('</physvol>\n')
    for mi, (envc_w, R, half, contents, ctr_l, Re) in enumerate(env_defs):
        pw = envc_w + np.asarray(offset_mm)
        F.write('<physvol name="module_env_{}_PV" copynumber="{}">\n'.format(mi, mi))
        F.write('<volumeref ref="module_env_{}_LV"/>\n'.format(mi))
        F.write('<position name="module_env_{}_pos" x="{:.10f}" y="{:.10f}" z="{:.10f}" unit="mm"/>\n'.format(
            mi, pw[0], pw[1], pw[2]))
        F.write('<rotation name="module_env_{}_rot" x="{:.12f}" y="{:.12f}" z="{:.12f}" unit="rad"/>\n'.format(
            mi, Re[0], Re[1], Re[2]))
        F.write('</physvol>\n')
    F.write('</volume>\n')
    F.write('</structure>\n')
    F.write('<setup name="Default" version="1.0">\n')
    F.write('<world ref="World"/>\n')
    F.write('</setup>\n')
    F.write('</gdml>')
    F.close()
    print("Hierarchical GDML written to {}".format(out_path))
    return out_path
