"""Strain computation: local least-squares displacement gradient, NaN-aware.

The original script computed strain per-triangle directly from a Delaunay simplex's 3
vertices (a "constant strain triangle" / CST calculation). That's exact for a perfectly
rigid triangle, but any single vertex's tracking noise goes straight into that triangle's
strain value with no averaging -- a noisy point corrupts every triangle touching it.

Here, strain is instead estimated at each *point* from a local least-squares fit over all
of its mesh neighbors (typically 4-8 points, not just 2). This is the same small-strain
displacement-gradient math, just over-determined instead of exactly-determined, so a
single noisy neighbor is damped rather than directly propagated. Per-triangle strain
(still needed for the mesh-overlay visualization) is then just the average of its 3
vertices' point strains.

Convention (kept identical to the original script for compatibility): "x" refers to the
column direction (YA), "y" refers to the row direction (XA). ex = du/dx, ey = dv/dy,
gxy = du/dy + dv/dx.
"""

import numpy as np


def build_neighbor_lists(n_pts, tri):
    """One-ring neighbor point-indices for every point, from a Delaunay triangulation's
    edges.
    """
    neighbors = [set() for _ in range(n_pts)]
    for simplex in tri.simplices:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            i, j = simplex[a], simplex[b]
            neighbors[i].add(j)
            neighbors[j].add(i)
    return [np.array(sorted(s), dtype=int) for s in neighbors]


def _fit_point_strain(dx, dy, du, dv):
    """Least-squares fit of [ex, exy_from_u] from du = ex*dx + exy_from_u*dy, and
    [exy_from_v, ey] from dv = exy_from_v*dx + ey*dy. Returns (ex, ey, gxy) or None if
    the system is degenerate (e.g. all neighbors collinear).
    """
    A = np.column_stack([dx, dy])
    try:
        coef_u, *_ = np.linalg.lstsq(A, du, rcond=None)
        coef_v, *_ = np.linalg.lstsq(A, dv, rcond=None)
    except np.linalg.LinAlgError:
        return None

    ex = coef_u[0]
    ey = coef_v[1]
    gxy = coef_u[1] + coef_v[0]
    return ex, ey, gxy


def compute_point_strain(pts, tri, XA, YA, start_frame, min_neighbors=3):
    """Local least-squares strain at every point, for every frame.

    Parameters
    ----------
    pts : list of (row, col) tuples
    tri : scipy.spatial.Delaunay
    XA, YA : np.ndarray, shape (n_pts, n_frames)
        Row/col position of each point per frame (NaN where untracked), as produced by
        tracking.track_sequence.
    start_frame : int
        Reference frame; strain is relative to positions at this frame.
    min_neighbors : int
        Minimum number of valid (non-NaN) neighbors required to fit strain at a point.
        Below this, the point's strain is NaN for that frame.

    Returns
    -------
    point_strain : np.ndarray, shape (n_pts, n_frames, 3)
        (ex, ey, gxy) per point per frame; NaN where not computable.
    """
    n_pts, n_frames = XA.shape
    neighbor_lists = build_neighbor_lists(n_pts, tri)

    x_ref = YA[:, start_frame]  # column = "x"
    y_ref = XA[:, start_frame]  # row = "y"

    point_strain = np.full((n_pts, n_frames, 3), np.nan)

    for k in range(start_frame, n_frames):
        x_cur = YA[:, k]
        y_cur = XA[:, k]

        for i in range(n_pts):
            if np.isnan(x_ref[i]) or np.isnan(x_cur[i]):
                continue

            nbrs = neighbor_lists[i]
            if nbrs.size == 0:
                continue

            valid = ~np.isnan(x_ref[nbrs]) & ~np.isnan(x_cur[nbrs])
            nbrs = nbrs[valid]
            if nbrs.size < min_neighbors:
                continue

            dx = x_ref[nbrs] - x_ref[i]
            dy = y_ref[nbrs] - y_ref[i]
            du = (x_cur[nbrs] - x_cur[i]) - dx
            dv = (y_cur[nbrs] - y_cur[i]) - dy

            fit = _fit_point_strain(dx, dy, du, dv)
            if fit is None:
                continue

            point_strain[i, k, :] = fit

    return point_strain


def compute_triangle_strain(tri, point_strain, min_valid_vertices=2):
    """Per-triangle strain (for mesh-overlay visualization), averaged from vertex
    point-strains. A triangle needs at least `min_valid_vertices` non-NaN vertices to
    produce a value; otherwise it's NaN for that frame.

    Returns
    -------
    tri_strain : np.ndarray, shape (n_frames, n_triangles, 3)
    """
    n_pts, n_frames, _ = point_strain.shape
    simplices = tri.simplices
    n_tri = len(simplices)

    tri_strain = np.full((n_frames, n_tri, 3), np.nan)

    for k in range(n_frames):
        for t, simplex in enumerate(simplices):
            vals = point_strain[simplex, k, :]  # (3, 3)
            valid_mask = ~np.isnan(vals[:, 0])
            if valid_mask.sum() < min_valid_vertices:
                continue
            tri_strain[k, t, :] = np.nanmean(vals, axis=0)

    return tri_strain
