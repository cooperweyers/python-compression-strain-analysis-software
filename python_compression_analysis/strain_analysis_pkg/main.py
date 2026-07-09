"""Thin orchestration entry point: wires gui -> io_utils -> roi -> mesh -> tracking ->
strain -> export -> viewer together. Mirrors the original single-file script's flow,
just split across modules.
"""

import os

from . import export, gui, io_utils, mesh, roi, strain, tracking, viewer


def main():
    settings, filename = gui.run_settings_gui()
    print("Using file:", filename)

    imgs = io_utils.load_image_stack(
        filename, frame_skip=settings["frame_skip"], end_frame=settings["end_frame"]
    )
    imgs = io_utils.preprocess_stack(
        imgs, settings["low_in"], settings["high_in"], settings["gaussian_blur"]
    )

    n_frames, mm, nn = imgs.shape
    start_frame = settings["start_frame"]

    roi_path, _vertices = roi.select_polygon_roi(imgs[start_frame])

    pts = mesh.generate_grid_points(roi_path, settings["mesh_spacing"])
    print("Points:", len(pts))
    tri = mesh.triangulate_points(pts)
    XA, YA = mesh.init_tracks(pts, n_frames, start_frame)

    XA, YA, CA = tracking.track_sequence(
        imgs,
        pts,
        XA,
        YA,
        start_frame,
        settings["delta_x"],
        settings["delta_y"],
        settings["t_x"],
        settings["t_y"],
        settings["corr_threshold"],
        settings["max_disp"],
        reanchor_threshold=settings["reanchor_threshold"],
        tri=tri,
        fill_gaps=settings["fill_gaps"],
        min_neighbors_fill=settings["min_neighbors"],
    )
    print("Done tracking.")

    point_strain = strain.compute_point_strain(
        pts, tri, XA, YA, start_frame, min_neighbors=settings["min_neighbors"]
    )
    tri_strain = strain.compute_triangle_strain(tri, point_strain)

    # Results go in <project_root>/results/, same as the original script -- project
    # root is one level up from this package directory.
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    export_dir, base_name = export.make_export_dir(script_dir, filename)

    export.export_strain_csv(export_dir, base_name, point_strain, CA, XA, YA, start_frame)
    export.plot_strain_over_time(export_dir, base_name, point_strain, settings["strain_mode"], start_frame)
    export.export_strain_video(
        export_dir,
        base_name,
        imgs,
        XA,
        YA,
        tri,
        tri_strain,
        settings["strain_mode"],
        settings["show_triangle_edges"],
        start_frame,
    )

    print("Done.")

    viewer.view_strain(
        imgs, XA, YA, tri, tri_strain, settings["strain_mode"], settings["show_triangle_edges"], start_frame
    )


if __name__ == "__main__":
    main()
