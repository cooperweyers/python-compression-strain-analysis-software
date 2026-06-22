import numpy as np
import tifffile as tiff
import os
import cv2
from scipy.spatial import Delaunay
import matplotlib.pyplot as plt
from matplotlib.widgets import PolygonSelector
from matplotlib.path import Path
import tkinter as tk
from tkinter import filedialog, ttk


# ======================
# SETTINGS GUI & FILE SELECTION
# ======================

defaults = {
    "start_frame": 0,
    "end_frame": "",
    "strain_mode": "vonmises",
    "mesh_spacing": 20,
    "show_triangle_edges": True,
    "delta_x": 30,
    "delta_y": 30,
    "t_x": 15,
    "t_y": 15,
    "low_in": 28,
    "high_in": 250,
    "frame_skip": 1,
    "corr_threshold": 0.85,
    "max_disp": 12,
    "gaussian_blur": 3,
}

settings_result = {}
selected_file = [None]

root = tk.Tk()
root.title("Strain Analysis Settings")
root.minsize(350, 600)
root.lift()

entries = {}
row = 0

tk.Label(root, text="— File —", font=("Helvetica", 11, "bold")).grid(row=row, column=0, columnspan=2, pady=(10,3))
row += 1

file_var = tk.StringVar(value="No file selected")
tk.Label(root, textvariable=file_var, anchor="w", wraplength=300, fg="gray").grid(row=row, column=0, columnspan=2, padx=10, pady=3)
row += 1

def browse_file():
    path = filedialog.askopenfilename(
        parent=root,
        title="Select image stack or video",
        filetypes=[
            ("All supported", "*.tiff *.tif *.mov *.mp4 *.avi *.mkv"),
            ("TIFF stacks", "*.tiff *.tif"),
            ("Video files", "*.mov *.mp4 *.avi *.mkv"),
            ("All files", "*.*")
        ]
    )
    if path:
        selected_file[0] = path
        file_var.set(os.path.basename(path))

tk.Button(root, text="Browse...", command=browse_file).grid(row=row, column=0, columnspan=2, pady=(0,5))
row += 1

def add_entry(label, key, r):
    tk.Label(root, text=label, anchor="e").grid(row=r, column=0, sticky="e", padx=(10,5), pady=3)
    e = tk.Entry(root, width=15)
    e.insert(0, str(defaults[key]))
    e.grid(row=r, column=1, padx=(5,10), pady=3)
    entries[key] = e
    return r + 1

tk.Label(root, text="— Frames —", font=("Helvetica", 11, "bold")).grid(row=row, column=0, columnspan=2, pady=(10,3))
row += 1
row = add_entry("Start Frame:", "start_frame", row)
row = add_entry("End Frame (blank=all):", "end_frame", row)
row = add_entry("Frame Skip:", "frame_skip", row)

tk.Label(root, text="— Strain —", font=("Helvetica", 11, "bold")).grid(row=row, column=0, columnspan=2, pady=(10,3))
row += 1
tk.Label(root, text="Strain Mode:", anchor="e").grid(row=row, column=0, sticky="e", padx=(10,5), pady=3)
mode_var = tk.StringVar(value=defaults["strain_mode"])
mode_menu = ttk.Combobox(root, textvariable=mode_var, values=["ex", "ey", "gxy", "vonmises"], width=12, state="readonly")
mode_menu.grid(row=row, column=1, padx=(5,10), pady=3)
row += 1

tk.Label(root, text="— Mesh —", font=("Helvetica", 11, "bold")).grid(row=row, column=0, columnspan=2, pady=(10,3))
row += 1
row = add_entry("Mesh Spacing:", "mesh_spacing", row)
edges_var = tk.BooleanVar(value=defaults["show_triangle_edges"])
tk.Checkbutton(root, text="Show Triangle Edges", variable=edges_var).grid(row=row, column=0, columnspan=2, pady=3)
row += 1

tk.Label(root, text="— Tracking —", font=("Helvetica", 11, "bold")).grid(row=row, column=0, columnspan=2, pady=(10,3))
row += 1
row = add_entry("Template Width (delta_x):", "delta_x", row)
row = add_entry("Template Height (delta_y):", "delta_y", row)
row = add_entry("Search Range X (t_x):", "t_x", row)
row = add_entry("Search Range Y (t_y):", "t_y", row)
row = add_entry("Corr Threshold:", "corr_threshold", row)
row = add_entry("Max Displacement:", "max_disp", row)
row = add_entry("Gaussian Blur (0=off):", "gaussian_blur", row)

tk.Label(root, text="— Contrast —", font=("Helvetica", 11, "bold")).grid(row=row, column=0, columnspan=2, pady=(10,3))
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
    root.destroy()

tk.Button(root, text="Run Analysis", command=on_run,
          font=("Helvetica", 12, "bold"), padx=20, pady=5).grid(row=row, column=0, columnspan=2, pady=15)

root.mainloop()

if not settings_result:
    raise RuntimeError("Settings window closed without running")

filename = selected_file[0]
print("Using file:", filename)

start_frame = int(settings_result["start_frame"])
end_frame = None if settings_result["end_frame"].strip() == "" else int(settings_result["end_frame"])
strain_mode = settings_result["strain_mode"]
mesh_spacing = int(settings_result["mesh_spacing"])
show_triangle_edges = settings_result["show_triangle_edges"]
target_triangles = None
delta_x = int(settings_result["delta_x"])
delta_y = int(settings_result["delta_y"])
t_x = int(settings_result["t_x"])
t_y = int(settings_result["t_y"])
low_in = int(settings_result["low_in"])
high_in = int(settings_result["high_in"])
frame_skip = int(settings_result["frame_skip"])
corr_threshold = float(settings_result["corr_threshold"])
max_disp = float(settings_result["max_disp"])
gaussian_blur = int(settings_result["gaussian_blur"])


# ======================
# LOAD IMAGE STACK
# ======================

ext = os.path.splitext(filename)[1].lower()

if ext in ('.tiff', '.tif'):
    imgs = tiff.imread(filename)
    if imgs.ndim == 4:
        imgs = np.array([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in imgs])
    if imgs.ndim != 3:
        raise ValueError("TIFF must be a grayscale image stack")
else:
    cap = cv2.VideoCapture(filename)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {filename}")
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    cap.release()
    if len(frames) == 0:
        raise ValueError(f"No frames read from: {filename}")
    imgs = np.array(frames)

if frame_skip > 1:
    imgs = imgs[::frame_skip]

if end_frame is not None:
    imgs = imgs[:end_frame+1]

Nf, mm, nn = imgs.shape


def adjust(img):
    img = np.clip((img - low_in)/(high_in-low_in), 0, 1)
    return (img*255).astype(np.uint8)

imgs = np.array([adjust(f) for f in imgs])

if gaussian_blur > 0:
    ksize = gaussian_blur if gaussian_blur % 2 == 1 else gaussian_blur + 1
    imgs = np.array([cv2.GaussianBlur(f, (ksize, ksize), 0) for f in imgs])


# ======================
# TRACKING FUNCTION
# ======================

def track(img1, img2, x, y):
    target = img1[x:x+delta_x, y:y+delta_y]
    scan = img2[x-t_x:x+delta_x+t_x, y-t_y:y+delta_y+t_y]

    if target.size == 0 or scan.shape[0] < delta_x or scan.shape[1] < delta_y:
        return 0, 0
    if np.all(target == 0):
        return 0, 0

    result = cv2.matchTemplate(scan, target, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < corr_threshold:
        return 0, 0

    mx = max_loc[1]
    my = max_loc[0]

    h, w = result.shape
    sub_mx, sub_my = float(mx), float(my)

    if 0 < mx < h - 1:
        a, b, c = result[mx-1, my], result[mx, my], result[mx+1, my]
        denom = 2*b - a - c
        if abs(denom) > 1e-12:
            sub_mx = mx + (a - c) / (2 * denom)

    if 0 < my < w - 1:
        a, b, c = result[mx, my-1], result[mx, my], result[mx, my+1]
        denom = 2*b - a - c
        if abs(denom) > 1e-12:
            sub_my = my + (a - c) / (2 * denom)

    dx = -t_x + sub_mx
    dy = -t_y + sub_my

    if dx*dx + dy*dy > max_disp*max_disp:
        return 0, 0

    return dx, dy


# ======================
# ROI (ROBUST VERSION)
# ======================

plt.close('all')
fig, ax = plt.subplots()
ax.imshow(imgs[start_frame], cmap='gray')
ax.set_title("Click to draw ROI | ENTER = finish | BACKSPACE = undo")

polygon_vertices = []
line_plot, = ax.plot([], [], color='#39FF14', linewidth=2)  # neon green
points_plot, = ax.plot([], [], 'o', color='#39FF14')

def update_plot():
    if len(polygon_vertices) > 0:
        xs, ys = zip(*polygon_vertices)
        line_plot.set_data(xs + (xs[0],), ys + (ys[0],))
        points_plot.set_data(xs, ys)
    else:
        line_plot.set_data([], [])
        points_plot.set_data([])

    fig.canvas.draw_idle()


def onclick(event):
    if event.inaxes != ax:
        return

    polygon_vertices.append((event.xdata, event.ydata))
    update_plot()


def onkey(event):
    if event.key == 'enter':
        plt.close(fig)

    elif event.key == 'backspace':
        if polygon_vertices:
            polygon_vertices.pop()
            update_plot()


fig.canvas.mpl_connect('button_press_event', onclick)
fig.canvas.mpl_connect('key_press_event', onkey)

plt.show()

if len(polygon_vertices) < 3:
    raise RuntimeError("Polygon not properly defined")

roi_path = Path(polygon_vertices)
roi = roi_path
poly = np.array(polygon_vertices)

# ======================
# GRID
# ======================

poly = np.array(poly)
xmin, ymin = np.min(poly, axis=0)
xmax, ymax = np.max(poly, axis=0)

spacing = mesh_spacing

pts = []
for r in np.arange(int(ymin), int(ymax), spacing):
    for c in np.arange(int(xmin), int(xmax), spacing):
        if roi.contains_point((c, r)):
            pts.append((int(r), int(c)))

Nx = len(pts)
print("Points:", Nx)

XA = np.full((Nx, Nf), np.nan)
YA = np.full((Nx, Nf), np.nan)

for i,(r,c) in enumerate(pts):
    XA[i,start_frame]=r
    YA[i,start_frame]=c


# ======================
# TRIANGULATION
# ======================

tri = Delaunay(np.array([[p[1],p[0]] for p in pts]))

# ======================
# TRACK
# ======================

total_frames = Nf - 1 - start_frame
for k in range(start_frame, Nf-1):
    print(f"\rTracking frame {k - start_frame + 1}/{total_frames}", end="", flush=True)
    for i in range(Nx):
        x=int(XA[i,k])
        y=int(YA[i,k])

        x=max(t_x,min(x,mm-delta_x-t_x-1))
        y=max(t_y,min(y,nn-delta_y-t_y-1))

        dx,dy = track(imgs[k], imgs[k+1], x, y)

        XA[i,k+1]=x+dx
        YA[i,k+1]=y+dy

print()


# ======================
# STRAIN
# ======================

strain = np.full((Nf,len(tri.simplices),3),np.nan)

for k in range(start_frame,Nf):
    for t,s in enumerate(tri.simplices):

        n1,n2,n3=s

        x1r,y1r=YA[n1,start_frame],XA[n1,start_frame]
        x2r,y2r=YA[n2,start_frame],XA[n2,start_frame]
        x3r,y3r=YA[n3,start_frame],XA[n3,start_frame]

        x1,y1=YA[n1,k],XA[n1,k]
        x2,y2=YA[n2,k],XA[n2,k]
        x3,y3=YA[n3,k],XA[n3,k]

        if np.isnan(x1) or np.isnan(x2) or np.isnan(x3):
            continue

        u=np.array([x1-x1r,y1-y1r,x2-x2r,y2-y2r,x3-x3r,y3-y3r])

        x13,x23=x1r-x3r,x2r-x3r
        y13,y23=y1r-y3r,y2r-y3r

        det=x13*y23-y13*x23
        if abs(det)<1e-8:
            continue

        B=(1/det)*np.array([
            [y23,0,y3r-y1r,0,y1r-y2r,0],
            [0,x3r-x2r,0,x1r-x3r,0,x2r-x1r],
            [x3r-x2r,y23,x1r-x3r,y3r-y1r,x2r-x1r,y1r-y2r]
        ])

        strain[k,t,:]=B@u


print("Done.")


# ======================
# EXPORT RESULTS
# ======================

from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
base_name = os.path.splitext(os.path.basename(filename))[0]
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
run_name = f"{base_name}_{timestamp}"
export_dir = os.path.join(script_dir, "results", run_name)
os.makedirs(export_dir, exist_ok=True)

import csv

csv_path = os.path.join(export_dir, f"{base_name}_strain.csv")
with open(csv_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["frame", "triangle", "ex", "ey", "gxy"])
    for k in range(start_frame, Nf):
        for t in range(len(tri.simplices)):
            ex_val, ey_val, gxy_val = strain[k, t, :]
            if not np.isnan(ex_val):
                writer.writerow([k, t, f"{ex_val:.6f}", f"{ey_val:.6f}", f"{gxy_val:.6f}"])

print(f"Strain CSV saved: {csv_path}")

if strain_mode == "ey":
    plot_data = strain[:,:,1]
    plot_label = "εy (Vertical Strain)"
elif strain_mode == "ex":
    plot_data = strain[:,:,0]
    plot_label = "εx (Horizontal Strain)"
elif strain_mode == "gxy":
    plot_data = strain[:,:,2]
    plot_label = "γxy (Shear Strain)"
else:
    s_ex0, s_ey0, s_g0 = strain[:,:,0], strain[:,:,1], strain[:,:,2]
    plot_data = np.sqrt(s_ex0**2 - s_ex0*s_ey0 + s_ey0**2 + 0.75*s_g0**2)
    plot_label = "Von Mises Strain"

mean_strain = np.nanmean(plot_data, axis=1)
frame_nums = np.arange(Nf)

fig_plot, ax_plot = plt.subplots(figsize=(8, 4))
ax_plot.plot(frame_nums[start_frame:], mean_strain[start_frame:], linewidth=1.5)
ax_plot.set_xlabel("Frame")
ax_plot.set_ylabel(f"Mean {plot_label}")
ax_plot.set_title("Strain Over Time")
ax_plot.grid(True, alpha=0.3)
fig_plot.tight_layout()

plot_path = os.path.join(export_dir, f"{base_name}_strain_over_time.png")
fig_plot.savefig(plot_path, dpi=150)
print(f"Strain plot saved: {plot_path}")

if strain_mode == "ey":
    export_data = strain[:,:,1]
elif strain_mode == "ex":
    export_data = strain[:,:,0]
elif strain_mode == "gxy":
    export_data = strain[:,:,2]
else:
    s_ex, s_ey, s_g = strain[:,:,0], strain[:,:,1], strain[:,:,2]
    export_data = np.sqrt(s_ex**2 - s_ex*s_ey + s_ey**2 + 0.75*s_g**2)

export_vmin = np.nanpercentile(export_data, 5)
export_vmax = np.nanpercentile(export_data, 95)
export_cmap = plt.cm.jet

video_path = os.path.join(export_dir, f"{base_name}_strain.mp4")
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video_out = cv2.VideoWriter(video_path, fourcc, 15, (nn, mm))

for k in range(start_frame, Nf):
    print(f"\rExporting frame {k - start_frame + 1}/{Nf - start_frame}", end="", flush=True)
    img = cv2.cvtColor(imgs[k], cv2.COLOR_GRAY2RGB)
    overlay = img.copy()
    pts_now = np.array([[YA[i, k], XA[i, k]] for i in range(Nx)])

    for t, s in enumerate(tri.simplices):
        val = export_data[k, t]
        if np.isnan(val):
            continue
        n = (val - export_vmin) / (export_vmax - export_vmin + 1e-12)
        color = export_cmap(n)[:3]
        color = tuple(int(255 * c) for c in color)
        poly_pts = pts_now[s].astype(int)
        cv2.fillPoly(overlay, [poly_pts], color)
        if show_triangle_edges:
            cv2.polylines(overlay, [poly_pts], True, (0, 0, 0), 1)

    frame_out = cv2.addWeighted(overlay, 0.45, img, 0.55, 0)
    frame_out = cv2.cvtColor(frame_out, cv2.COLOR_RGB2BGR)
    video_out.write(frame_out)

video_out.release()
print(f"\nStrain video saved: {video_path}")


# ======================
# VIEWER (FINAL FIXED)
# ======================

fig, ax = plt.subplots()

if strain_mode=="ey":
    data=strain[:,:,1]
elif strain_mode=="ex":
    data=strain[:,:,0]
elif strain_mode=="gxy":
    data=strain[:,:,2]
else:
    ex,ey,g=strain[:,:,0],strain[:,:,1],strain[:,:,2]
    data=np.sqrt(ex**2-ex*ey+ey**2+0.75*g**2)

vmin=np.nanpercentile(data,5)
vmax=np.nanpercentile(data,95)

import matplotlib as mpl

cmap = plt.cm.jet
norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)

sm = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])

cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)

# Label depending on strain mode
if strain_mode == "ex":
    cbar.set_label("εx (Horizontal Strain)")
elif strain_mode == "ey":
    cbar.set_label("εy (Vertical Strain)")
elif strain_mode == "gxy":
    cbar.set_label("γxy (Shear Strain)")
else:
    cbar.set_label("Von Mises Strain")

current=start_frame

def show(k):
    ax.clear()

    img=cv2.cvtColor(imgs[k],cv2.COLOR_GRAY2RGB)
    overlay=img.copy()

    pts_now=np.array([[YA[i,k],XA[i,k]] for i in range(Nx)])

    for t,s in enumerate(tri.simplices):
        val=data[k,t]
        if np.isnan(val):
            continue

        norm=(val-vmin)/(vmax-vmin+1e-12)
        color=cmap(norm)[:3]
        color=tuple(int(255*c) for c in color)

        poly=pts_now[s].astype(int)
        cv2.fillPoly(overlay,[poly],color)

        if show_triangle_edges:
            cv2.polylines(overlay,[poly],True,(0,0,0),1)

    img=cv2.addWeighted(overlay,0.45,img,0.55,0)

    ax.imshow(img)
    ax.set_title(f"Frame {k} | ← → or A/D")

    fig.canvas.draw_idle()


def key(event):
    global current

    if event.key in ['right','d']:
        current=min(current+1,Nf-1)
    elif event.key in ['left','a']:
        current=max(current-1,start_frame)
    elif event.key in ['q','escape']:
        plt.close(fig)
        return

    show(current)


fig.canvas.mpl_connect('key_press_event',key)

show(current)
plt.show()