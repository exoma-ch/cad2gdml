#!/usr/bin/env python3
"""Plot scanner geometry from per-crystal centers and long-axis directions.

Reads the H5 file produced by ``--extract-centers`` (per-crystal center +
long-axis unit vector, plus file-level metadata: scanner axial axis and
crystal sizes). Visualisation is axis-agnostic: stick endpoints are
``center ± (L/2) · direction`` projected into XY, XZ, YZ. The axial axis
is read from the H5 attrs (or auto-detected as a fallback) and used only
for labels and block grouping.
"""

import argparse
import glob
import math
import os
import sys

import h5py
import matplotlib.pyplot as plt


AXIS_INDEX = {'x': 0, 'y': 1, 'z': 2}


def read_crystal_data(h5_file):
    """Load per-crystal records and file-level metadata from the H5.

    Returns (crystals, metadata) where ``crystals`` is a list of dicts with
    keys (id, name, x, y, z, dx, dy, dz) and ``metadata`` carries the H5
    attrs (scanner_axial_axis, crystal_size_*_mm) when present.
    """
    required = ('crystal_id', 'volume_name',
                'center_x', 'center_y', 'center_z',
                'dir_x', 'dir_y', 'dir_z')
    crystals = []
    metadata = {}
    with h5py.File(h5_file, 'r') as f:
        missing = [k for k in required if k not in f]
        if missing:
            raise ValueError(
                f"{h5_file} is missing required datasets: {missing}.\n"
                f"Re-run --extract-centers with the current code."
            )
        ids = f['crystal_id'][:]
        names = f['volume_name'][:]
        cx, cy, cz = f['center_x'][:], f['center_y'][:], f['center_z'][:]
        dx, dy, dz = f['dir_x'][:], f['dir_y'][:], f['dir_z'][:]
        for i in range(len(ids)):
            name = names[i]
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            crystals.append({
                'id': int(ids[i]), 'name': name,
                'x': float(cx[i]), 'y': float(cy[i]), 'z': float(cz[i]),
                'dx': float(dx[i]), 'dy': float(dy[i]), 'dz': float(dz[i]),
            })
        for key in ('scanner_axial_axis',
                    'crystal_size_radial_mm',
                    'crystal_size_axial_mm',
                    'crystal_size_tangential_mm'):
            if key in f.attrs:
                value = f.attrs[key]
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                metadata[key] = value
    print(f"Loaded {len(crystals)} crystal records from {h5_file}")
    if metadata:
        bits = []
        if 'scanner_axial_axis' in metadata:
            bits.append(f"axial={str(metadata['scanner_axial_axis']).upper()}")
        for k, label in (('crystal_size_radial_mm', 'radial'),
                         ('crystal_size_axial_mm', 'axial-dim'),
                         ('crystal_size_tangential_mm', 'tangential')):
            if k in metadata:
                bits.append(f"{label}={float(metadata[k]):.3f}mm")
        if bits:
            print(f"H5 metadata: {', '.join(bits)}")
    return crystals, metadata


def detect_axial_axis(crystals):
    """Pick the world axis (x/y/z) that is the scanner axial axis.

    Crystal long-axis directions live in the ring plane (perpendicular to the
    scanner axis), so the axis with the smallest mean-squared direction
    component is the axial axis.
    """
    n = len(crystals)
    components = {
        'x': sum(c['dx'] ** 2 for c in crystals) / n,
        'y': sum(c['dy'] ** 2 for c in crystals) / n,
        'z': sum(c['dz'] ** 2 for c in crystals) / n,
    }
    axial = min(components, key=components.get)
    print(f"Detected axial axis: {axial.upper()}  (mean dir²: "
          f"x={components['x']:.3f}, y={components['y']:.3f}, z={components['z']:.3f})")
    return axial


def stick_endpoints(crystal, length, plane):
    """Return ((u0, v0), (u1, v1)) for the stick projected onto ``plane``.

    ``plane`` is two characters from 'xyz' naming the horizontal and vertical
    axes of the projection (e.g. 'xz' for an XZ plot).
    """
    pos = (crystal['x'], crystal['y'], crystal['z'])
    direction = (crystal['dx'], crystal['dy'], crystal['dz'])
    half = length / 2.0
    u, v = AXIS_INDEX[plane[0]], AXIS_INDEX[plane[1]]
    return (
        (pos[u] - half * direction[u], pos[v] - half * direction[v]),
        (pos[u] + half * direction[u], pos[v] + half * direction[v]),
    )


def around_axis_angle(crystal, axial):
    """Position angle of the crystal around the scanner axis, in [0, 360)°."""
    a = AXIS_INDEX[axial]
    others = [i for i in (0, 1, 2) if i != a]
    pos = (crystal['x'], crystal['y'], crystal['z'])
    return math.degrees(math.atan2(pos[others[1]], pos[others[0]])) % 360.0


def cluster_by_direction(crystals, precision=2):
    """Cluster crystals by rounded direction vector (one cluster per block)."""
    groups = {}
    for c in crystals:
        key = (round(c['dx'], precision), round(c['dy'], precision), round(c['dz'], precision))
        groups.setdefault(key, []).append(c)
    return groups


PLANES = (('xz', 'X (mm)', 'Z (mm)'),
          ('xy', 'X (mm)', 'Y (mm)'),
          ('yz', 'Y (mm)', 'Z (mm)'))


def _ring_plane_label(axial):
    """The two-axis plane perpendicular to the scanner axial axis."""
    return ''.join(a for a in 'xyz' if a != axial)


def _is_ring_plane(plane, axial):
    return set(plane) == set(_ring_plane_label(axial))


def plot_scanner_with_crystals(crystals, depth, axial, save_dir=None):
    """Three orthogonal projections coloured by around-axis angle."""
    if not crystals:
        print("No crystal data to plot")
        return

    angles = [around_axis_angle(c, axial) for c in crystals]
    cmap = plt.cm.hsv
    norm = plt.Normalize(vmin=0.0, vmax=360.0)

    max_crystals = 500
    step = max(1, len(crystals) // max_crystals)
    subset = list(zip(crystals[::step], angles[::step]))

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    print(f"Plotting {len(subset)} oriented crystal sticks in three planes...")

    for ax, (plane, xlabel, ylabel) in zip(axes, PLANES):
        for crystal, angle in subset:
            (u0, v0), (u1, v1) = stick_endpoints(crystal, depth, plane)
            ax.plot([u0, u1], [v0, v1], color=cmap(norm(angle)), linewidth=2, alpha=0.8)
        title = f"{plane.upper()} plane"
        if _is_ring_plane(plane, axial):
            title += "  (ring plane)"
        ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=list(axes), shrink=0.6, aspect=20)
    cbar.set_label(f'Position angle around {axial.upper()} axis (°)')

    fig.suptitle(f'Scanner geometry — three orthogonal views ({len(subset)} crystals shown)',
                 fontsize=14)

    _print_geometry_stats(crystals, depth, axial)

    out = os.path.join(save_dir or '.', 'scanner_with_crystals.png')
    plt.savefig(out, dpi=300, bbox_inches='tight')
    print(f"Saved: {out}")
    plt.show()

    plot_orientation_groups(crystals, depth, axial, save_dir)


def _print_geometry_stats(crystals, depth, axial):
    xs = [c['x'] for c in crystals]
    ys = [c['y'] for c in crystals]
    zs = [c['z'] for c in crystals]

    a = AXIS_INDEX[axial]
    others = [i for i in (0, 1, 2) if i != a]
    radial = [math.sqrt((c['x'], c['y'], c['z'])[others[0]] ** 2
                        + (c['x'], c['y'], c['z'])[others[1]] ** 2)
              for c in crystals]

    print(f"\n=== Scanner geometry ===")
    print(f"Total crystals: {len(crystals)}")
    print(f"X range: {min(xs):.2f} to {max(xs):.2f} mm (span: {max(xs)-min(xs):.2f} mm)")
    print(f"Y range: {min(ys):.2f} to {max(ys):.2f} mm (span: {max(ys)-min(ys):.2f} mm)")
    print(f"Z range: {min(zs):.2f} to {max(zs):.2f} mm (span: {max(zs)-min(zs):.2f} mm)")
    print(f"Crystal long-axis length used for sticks: {depth:.2f} mm")
    print(f"Radial distance from {axial.upper()} axis: "
          f"{min(radial):.1f} to {max(radial):.1f} mm "
          f"(avg: {sum(radial)/len(radial):.1f} mm)")


def plot_orientation_groups(crystals, depth, axial, save_dir=None):
    """One row per block (clustered by direction), three projections per row,
    plus a single superimposed view that overlays all blocks."""
    groups = cluster_by_direction(crystals)
    # Drop tiny clusters (likely fallback/noise) and order by around-axis angle of the block.
    groups = {k: v for k, v in groups.items() if len(v) >= 5}
    if not groups:
        print("No orientation groups large enough to plot.")
        return

    def block_angle(direction):
        a = AXIS_INDEX[axial]
        others = [i for i in (0, 1, 2) if i != a]
        return math.degrees(math.atan2(direction[others[1]], direction[others[0]])) % 360.0

    ordered_keys = sorted(groups.keys(), key=block_angle)
    print(f"\n=== Orientation groups (blocks) ===")
    print(f"Found {len(ordered_keys)} blocks (clusters with ≥5 crystals):")
    for key in ordered_keys:
        n = len(groups[key])
        print(f"  dir=({key[0]:+.2f},{key[1]:+.2f},{key[2]:+.2f})  "
              f"around-{axial.upper()}={block_angle(key):6.1f}°  count={n}")

    palette = plt.cm.tab20
    colors = {k: palette(i % palette.N) for i, k in enumerate(ordered_keys)}

    # Superimposed view
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Orientation groups — superimposed', fontsize=14)
    for ax, (plane, xlabel, ylabel) in zip(axes, PLANES):
        for key in ordered_keys:
            for crystal in groups[key]:
                (u0, v0), (u1, v1) = stick_endpoints(crystal, depth, plane)
                ax.plot([u0, u1], [v0, v1], color=colors[key], linewidth=1.0, alpha=0.6)
        title = f"{plane.upper()} plane"
        if _is_ring_plane(plane, axial):
            title += "  (ring plane)"
        ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

    legend_handles = [plt.Line2D([0], [0], color=colors[k], linewidth=2,
                                 label=f"{block_angle(k):.0f}° ({len(groups[k])})")
                      for k in ordered_keys]
    fig.legend(handles=legend_handles, loc='center', bbox_to_anchor=(0.5, 0.02),
               ncol=min(6, len(legend_handles)), fontsize=9)
    fig.subplots_adjust(bottom=0.18)

    out = os.path.join(save_dir or '.', 'orientation_groups_superimposed.png')
    plt.savefig(out, dpi=300, bbox_inches='tight')
    print(f"Saved: {out}")
    plt.show()

    # One-stick-per-block debug view
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Orientation groups — one crystal per block', fontsize=14)
    for ax, (plane, xlabel, ylabel) in zip(axes, PLANES):
        for key in ordered_keys:
            crystal = groups[key][0]
            (u0, v0), (u1, v1) = stick_endpoints(crystal, depth, plane)
            ax.plot([u0, u1], [v0, v1], color=colors[key], linewidth=3, alpha=0.9,
                    label=f"{block_angle(key):.0f}°")
            u_idx, v_idx = AXIS_INDEX[plane[0]], AXIS_INDEX[plane[1]]
            pos = (crystal['x'], crystal['y'], crystal['z'])
            ax.plot(pos[u_idx], pos[v_idx], 'o', color=colors[key], markersize=6)
        title = f"{plane.upper()} plane"
        if _is_ring_plane(plane, axial):
            title += "  (ring plane)"
        ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)

    out = os.path.join(save_dir or '.', 'orientation_groups_debug.png')
    plt.savefig(out, dpi=300, bbox_inches='tight')
    print(f"Saved: {out}")
    plt.show()


def plot_axial_vs_around(crystals, axial, save_dir=None):
    """Scatter of (around-axis angle, axial position) — one dot per crystal."""
    a = AXIS_INDEX[axial]
    axial_pos = [(c['x'], c['y'], c['z'])[a] for c in crystals]
    angles = [around_axis_angle(c, axial) for c in crystals]

    fig, ax = plt.subplots(figsize=(12, 8))
    sc = ax.scatter(angles, axial_pos, c=angles, cmap='viridis',
                    alpha=0.7, s=20, edgecolors='black', linewidth=0.5)
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label(f'Around-{axial.upper()} angle (°)', rotation=270, labelpad=20)

    ax.set_xlabel(f'Position angle around {axial.upper()} (°)', fontsize=12)
    ax.set_ylabel(f'{axial.upper()} position (mm)', fontsize=12)
    ax.set_title(f'Crystal distribution: {axial.upper()} vs around-{axial.upper()} angle',
                 fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)

    stats = (f'Total crystals: {len(crystals)}\n'
             f'{axial.upper()} range: {min(axial_pos):.1f} to {max(axial_pos):.1f} mm\n'
             f'Angle range: {min(angles):.1f} to {max(angles):.1f}°')
    ax.text(0.02, 0.98, stats, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()
    out = os.path.join(save_dir or '.', 'axial_vs_around_axis.png')
    plt.savefig(out, dpi=300, bbox_inches='tight')
    print(f"Saved: {out}")
    plt.show()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Plot scanner geometry from crystal centers + direction vectors.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('h5_file', nargs='?',
                        help='H5 from --extract-centers (default: auto-detect).')
    parser.add_argument('--depth', type=float, default=None,
                        help='Crystal long-axis length used for stick rendering (mm). '
                             'Defaults to crystal_size_radial_mm from the H5 attrs.')
    parser.add_argument('--save-dir', default='.',
                        help='Directory to save output plots.')
    parser.add_argument('--axial-axis', choices=['x', 'y', 'z'], default=None,
                        help='Override scanner axial axis from H5 attrs / auto-detect.')
    args = parser.parse_args(argv)

    h5_file = args.h5_file
    if not h5_file:
        candidates = sorted(glob.glob('lyso_crystal_centers*.h5'))
        h5_file = candidates[0] if candidates else 'lyso_crystal_centers.h5'

    print(f"Plotting scanner from: {h5_file}")

    crystals, metadata = read_crystal_data(h5_file)
    if not crystals:
        print("No crystal data loaded.")
        return 1

    depth = args.depth
    if depth is None:
        depth = float(metadata.get('crystal_size_radial_mm', 25.0))
    print(f"Stick length (long axis): {depth:.2f} mm")

    axial = args.axial_axis or metadata.get('scanner_axial_axis') or detect_axial_axis(crystals)
    if isinstance(axial, bytes):
        axial = axial.decode('utf-8')
    print(f"Scanner axial axis: {axial.upper()}")

    plot_scanner_with_crystals(crystals, depth, axial, save_dir=args.save_dir)
    plot_axial_vs_around(crystals, axial, save_dir=args.save_dir)
    print(f"\nPlots saved to: {args.save_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
