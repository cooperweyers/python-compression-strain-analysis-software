"""CSV / plot / video-overlay export of tracking and strain results."""

import csv
import os
from datetime import datetime

import cv2
import numpy as np


def select_strain_component(data, strain_mode):
    """Pick out ex, ey, gxy, or von Mises from a (..., 3) strain array.

    Works for both point_strain (n_pts, n_frames, 3) and tri_strain
    (n_frames, n_triangles, 3) since only the last axis is interpreted.
    """
    ex, ey, gxy = data[..., 0], data[..., 1], data[..., 2]

    if strain_mode == "ex":
        return ex, "εx (Horizontal Strain)"
    elif strain_mode == "ey":
        return ey, "εy (Vertical Strain)"
    elif strain_mode == "gxy":
        return gxy, "γxy (Shear Strain)"
    else:
        vonmises = np.sqrt(ex**2 - ex * ey + ey**2 + 0.75 * gxy**2)
        return vonmises, "Von Mises Strain"


def make_export_dir(script_dir, filename):
    """Create a timestamped results/<basename>_<timestamp>/ directory."""
    base_name = os.path.splitext(os.path.basename(filename))[0]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_name = f"{base_name}_{timestamp}"
    export_dir = os.path.join(script_dir, "results", run_name)
    os.makedirs(export_dir, exist_ok=True)
    return export_dir, base_name


def export_strain_csv(export_dir, base_name, point_strain, confidence, XA, YA, start_frame):
    """Write per-point, per-frame strain + tracking confidence to CSV.

    Columns: frame, point, row, col, ex, ey, gxy, confidence

    confidence is the real match correlation (>= corr_threshold) for a genuinely
    tracked point, or tracking.ESTIMATED_CONFIDENCE (-1) if the position was instead
    estimated from neighbors because no real match was found that frame (see
    tracking.track_sequence's fill_gaps option) -- filter on confidence < 0 to exclude
    estimated points from downstream analysis if you only want real measurements.
    """
    n_pts, n_frames, _ = point_strain.shape
    csv_path = os.path.join(export_dir, f"{base_name}_strain.csv")

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "point", "row", "col", "ex", "ey", "gxy", "confidence"])
        for k in range(start_frame, n_frames):
            for i in range(n_pts):
                ex_val, ey_val, gxy_val = point_strain[i, k, :]
                if np.isnan(ex_val):
                    continue
                writer.writerow(
                    [
                        k,
                        i,
                        f"{XA[i, k]:.3f}",
                        f"{YA[i, k]:.3f}",
                        f"{ex_val:.6f}",
                        f"{ey_val:.6f}",
                        f"{gxy_val:.6f}",
                        f"{confidence[i, k]:.4f}",
                    ]
                )

    print(f"Strain CSV saved: {csv_path}")
    return csv_path


def plot_strain_over_time(export_dir, base_name, point_strain, strain_mode, start_frame):
    """Save a PNG of mean strain (over all valid points) vs. frame number."""
    import matplotlib.pyplot as plt

    plot_data, plot_label = select_strain_component(point_strain, strain_mode)
    n_frames = plot_data.shape[1]
    mean_strain = np.nanmean(plot_data, axis=0)
    frame_nums = np.arange(n_frames)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(frame_nums[start_frame:], mean_strain[start_frame:], linewidth=1.5)
    ax.set_xlabel("Frame")
    ax.set_ylabel(f"Mean {plot_label}")
    ax.set_title("Strain Over Time")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    plot_path = os.path.join(export_dir, f"{base_name}_strain_over_time.png")
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)

    print(f"Strain plot saved: {plot_path}")
    return plot_path


def render_overlay_frame(img, tri, tri_strain_frame, pts_now, vmin, vmax, cmap, show_triangle_edges):
    """Render one strain-colored triangle-mesh overlay frame on top of a grayscale image.

    Returns a BGR uint8 image ready for cv2.VideoWriter or display.
    """
    img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    overlay = img_rgb.copy()

    for t, simplex in enumerate(tri.simplices):
        val = tri_strain_frame[t]
        if np.isnan(val):
            continue
        # A triangle can have a valid *strain* value averaged from only 2 of its 3
        # vertices (see strain.compute_triangle_strain's min_valid_vertices), but if any
        # vertex's tracked *position* is NaN, drawing the polygon would cast NaN -> a
        # garbage int coordinate and produce a line shooting across the frame. Skip
        # rendering (not just strain) unless every vertex position is valid this frame.
        if np.isnan(pts_now[simplex]).any():
            continue
        norm = (val - vmin) / (vmax - vmin + 1e-12)
        color = cmap(norm)[:3]
        color = tuple(int(255 * c) for c in color)
        poly_pts = pts_now[simplex].astype(int)
        cv2.fillPoly(overlay, [poly_pts], color)
        if show_triangle_edges:
            cv2.polylines(overlay, [poly_pts], True, (0, 0, 0), 1)

    blended = cv2.addWeighted(overlay, 0.45, img_rgb, 0.55, 0)
    return cv2.cvtColor(blended, cv2.COLOR_RGB2BGR)


def export_strain_video(
    export_dir,
    base_name,
    imgs,
    XA,
    YA,
    tri,
    tri_strain,
    strain_mode,
    show_triangle_edges,
    start_frame,
    fps=15,
):
    """Save an MP4 with the strain-colored mesh overlaid on every frame."""
    import matplotlib.pyplot as plt

    export_data, _ = select_strain_component(tri_strain, strain_mode)
    vmin = np.nanpercentile(export_data, 5)
    vmax = np.nanpercentile(export_data, 95)
    cmap = plt.cm.jet

    n_frames = imgs.shape[0]
    mm, nn = imgs.shape[1], imgs.shape[2]
    n_pts = XA.shape[0]

    video_path = os.path.join(export_dir, f"{base_name}_strain.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_out = cv2.VideoWriter(video_path, fourcc, fps, (nn, mm))

    total = n_frames - start_frame
    for k in range(start_frame, n_frames):
        print(f"\rExporting frame {k - start_frame + 1}/{total}", end="", flush=True)
        pts_now = np.array([[YA[i, k], XA[i, k]] for i in range(n_pts)])
        frame_out = render_overlay_frame(
            imgs[k], tri, export_data[k], pts_now, vmin, vmax, cmap, show_triangle_edges
        )
        video_out.write(frame_out)

    video_out.release()
    print(f"\nStrain video saved: {video_path}")
    return video_path
