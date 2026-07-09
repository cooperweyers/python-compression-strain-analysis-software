"""Tkinter settings window: file selection + all analysis parameters."""

import os
import tkinter as tk
from tkinter import filedialog, ttk

DEFAULTS = {
    "start_frame": 0,
    "end_frame": "",
    "strain_mode": "vonmises",
    "mesh_spacing": 20,
    "show_triangle_edges": True,
    "delta_x": 30,
    "delta_y": 30,
    "t_x": 25,
    "t_y": 25,
    "low_in": 28,
    "high_in": 250,
    "frame_skip": 1,
    "corr_threshold": 0.85,
    "max_disp": 30,
    "gaussian_blur": 3,
    # New: reference-frame tracking / local-strain settings.
    "reanchor_threshold": "",  # blank = auto (corr_threshold + 0.1, capped at 0.99)
    "min_neighbors": 3,
    "fill_gaps": True,  # estimate untracked points from neighbors instead of leaving gaps
}

# Keys that should be parsed as int, float, or left as string/bool.
_INT_KEYS = {"start_frame", "mesh_spacing", "delta_x", "delta_y", "t_x", "t_y",
             "low_in", "high_in", "frame_skip", "min_neighbors", "gaussian_blur"}
_FLOAT_KEYS = {"corr_threshold", "max_disp"}


def run_settings_gui():
    """Show the settings window and block until the user clicks Run Analysis.

    Returns
    -------
    settings : dict
        Fully parsed/typed settings (ints, floats, bool, strain_mode string).
    filename : str
        Path to the selected image stack or video file.
    """
    settings_result = {}
    selected_file = [None]

    root = tk.Tk()
    root.title("Strain Analysis Settings")
    root.minsize(350, 650)
    root.lift()
    root.attributes("-topmost", True)
    root.after(500, lambda: root.attributes("-topmost", False))
    root.focus_force()

    entries = {}
    row = 0

    tk.Label(root, text="— File —", font=("Helvetica", 11, "bold")).grid(
        row=row, column=0, columnspan=2, pady=(10, 3)
    )
    row += 1

    file_var = tk.StringVar(value="No file selected")
    tk.Label(root, textvariable=file_var, anchor="w", wraplength=300, fg="gray").grid(
        row=row, column=0, columnspan=2, padx=10, pady=3
    )
    row += 1

    def browse_file():
        path = filedialog.askopenfilename(
            parent=root,
            title="Select image stack or video",
            filetypes=[
                ("All supported", "*.tiff *.tif *.mov *.mp4 *.avi *.mkv"),
                ("TIFF stacks", "*.tiff *.tif"),
                ("Video files", "*.mov *.mp4 *.avi *.mkv"),
                ("All files", "*.*"),
            ],
        )
        if path:
            selected_file[0] = path
            file_var.set(os.path.basename(path))

    tk.Button(root, text="Browse...", command=browse_file).grid(
        row=row, column=0, columnspan=2, pady=(0, 5)
    )
    row += 1

    def add_entry(label, key, r):
        tk.Label(root, text=label, anchor="e").grid(row=r, column=0, sticky="e", padx=(10, 5), pady=3)
        e = tk.Entry(root, width=15)
        e.insert(0, str(DEFAULTS[key]))
        e.grid(row=r, column=1, padx=(5, 10), pady=3)
        entries[key] = e
        return r + 1

    tk.Label(root, text="— Frames —", font=("Helvetica", 11, "bold")).grid(
        row=row, column=0, columnspan=2, pady=(10, 3)
    )
    row += 1
    row = add_entry("Start Frame:", "start_frame", row)
    row = add_entry("End Frame (blank=all):", "end_frame", row)
    row = add_entry("Frame Skip:", "frame_skip", row)

    tk.Label(root, text="— Strain —", font=("Helvetica", 11, "bold")).grid(
        row=row, column=0, columnspan=2, pady=(10, 3)
    )
    row += 1
    tk.Label(root, text="Strain Mode:", anchor="e").grid(row=row, column=0, sticky="e", padx=(10, 5), pady=3)
    mode_var = tk.StringVar(value=DEFAULTS["strain_mode"])
    mode_menu = ttk.Combobox(
        root, textvariable=mode_var, values=["ex", "ey", "gxy", "vonmises"], width=12, state="readonly"
    )
    mode_menu.grid(row=row, column=1, padx=(5, 10), pady=3)
    row += 1
    row = add_entry("Min Neighbors (strain fit):", "min_neighbors", row)

    tk.Label(root, text="— Mesh —", font=("Helvetica", 11, "bold")).grid(
        row=row, column=0, columnspan=2, pady=(10, 3)
    )
    row += 1
    row = add_entry("Mesh Spacing:", "mesh_spacing", row)
    edges_var = tk.BooleanVar(value=DEFAULTS["show_triangle_edges"])
    tk.Checkbutton(root, text="Show Triangle Edges", variable=edges_var).grid(
        row=row, column=0, columnspan=2, pady=3
    )
    row += 1

    tk.Label(root, text="— Tracking —", font=("Helvetica", 11, "bold")).grid(
        row=row, column=0, columnspan=2, pady=(10, 3)
    )
    row += 1
    row = add_entry("Template Width (delta_x):", "delta_x", row)
    row = add_entry("Template Height (delta_y):", "delta_y", row)
    row = add_entry("Search Range X (t_x):", "t_x", row)
    row = add_entry("Search Range Y (t_y):", "t_y", row)
    row = add_entry("Corr Threshold:", "corr_threshold", row)
    row = add_entry("Max Displacement:", "max_disp", row)
    row = add_entry("Re-anchor Threshold (blank=auto):", "reanchor_threshold", row)
    fill_gaps_var = tk.BooleanVar(value=DEFAULTS["fill_gaps"])
    tk.Checkbutton(
        root, text="Fill Untracked Points (estimate from neighbors)", variable=fill_gaps_var
    ).grid(row=row, column=0, columnspan=2, pady=3)
    row += 1
    row = add_entry("Gaussian Blur (0=off):", "gaussian_blur", row)

    tk.Label(root, text="— Contrast —", font=("Helvetica", 11, "bold")).grid(
        row=row, column=0, columnspan=2, pady=(10, 3)
    )
    row += 1
    row = add_entry("Low In:", "low_in", row)
    row = add_entry("High In:", "high_in", row)

    def on_run():
        if not selected_file[0]:
            file_var.set("⚠ Please select a file first")
            return
        for key, e in entries.items():
            settings_result[key] = e.get()
        settings_result["strain_mode"] = mode_var.get()
        settings_result["show_triangle_edges"] = edges_var.get()
        settings_result["fill_gaps"] = fill_gaps_var.get()
        root.destroy()

    tk.Button(
        root, text="Run Analysis", command=on_run, font=("Helvetica", 12, "bold"), padx=20, pady=5
    ).grid(row=row, column=0, columnspan=2, pady=15)

    root.mainloop()

    if not settings_result:
        raise RuntimeError("Settings window closed without running")

    return _parse_settings(settings_result), selected_file[0]


def _parse_settings(raw):
    """Convert raw string GUI values into typed settings."""
    settings = {}

    for key, value in raw.items():
        if key in ("show_triangle_edges", "strain_mode", "fill_gaps"):
            settings[key] = value
            continue

        if key == "end_frame":
            settings[key] = None if str(value).strip() == "" else int(value)
            continue

        if key == "reanchor_threshold":
            settings[key] = None if str(value).strip() == "" else float(value)
            continue

        if key in _INT_KEYS:
            settings[key] = int(value)
        elif key in _FLOAT_KEYS:
            settings[key] = float(value)
        else:
            settings[key] = value

    return settings
