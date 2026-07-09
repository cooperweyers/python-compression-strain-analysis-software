"""Point grid generation within a polygon ROI, plus Delaunay triangulation."""

import numpy as np
from scipy.spatial import Delaunay


def generate_grid_points(roi_path, spacing):
    """Generate a regular grid of (row, col) points inside a polygon ROI.

    Parameters
    ----------
    roi_path : matplotlib.path.Path
        Polygon ROI, as returned by roi.select_polygon_roi.
    spacing : int
        Grid spacing in pixels.

    Returns
    -------
    pts : list of (row, col) tuples
        Grid points that fall inside the ROI.
    """
    vertices = np.array(roi_path.vertices)
    xmin, ymin = np.min(vertices, axis=0)
    xmax, ymax = np.max(vertices, axis=0)

    pts = []
    for r in np.arange(int(ymin), int(ymax), spacing):
        for c in np.arange(int(xmin), int(xmax), spacing):
            if roi_path.contains_point((c, r)):
                pts.append((int(r), int(c)))

    return pts


def triangulate_points(pts):
    """Delaunay-triangulate a list of (row, col) points.

    Parameters
    ----------
    pts : list of (row, col) tuples

    Returns
    -------
    tri : scipy.spatial.Delaunay
        Triangulation; tri.simplices gives point-index triples.
    """
    xy = np.array([[p[1], p[0]] for p in pts])
    return Delaunay(xy)


def init_tracks(pts, n_frames, start_frame):
    """Allocate NaN-filled displacement arrays and seed the start frame.

    Parameters
    ----------
    pts : list of (row, col) tuples
    n_frames : int
    start_frame : int

    Returns
    -------
    XA, YA : np.ndarray, shape (len(pts), n_frames)
        Row (XA) and column (YA) position of each point at each frame,
        NaN where not yet tracked.
    """
    n_pts = len(pts)
    XA = np.full((n_pts, n_frames), np.nan)
    YA = np.full((n_pts, n_frames), np.nan)

    for i, (r, c) in enumerate(pts):
        XA[i, start_frame] = r
        YA[i, start_frame] = c

    return XA, YA
