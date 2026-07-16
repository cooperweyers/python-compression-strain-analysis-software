# Python Compression Strain Analysis Software

A digital image correlation (DIC) tool for computing **2D strain fields** from
compression-test image sequences. It tracks how a sample deforms across frames, builds a
Delaunay triangle mesh over a region you define, and computes per-element strain. Results
are exported as a CSV, a strain-over-time plot, a strain-overlay video, and an interactive
viewer.

All the analysis code lives in the [`python_compression_analysis/`](python_compression_analysis/)
folder.

## Contents

- [Two ways to run it](#two-ways-to-run-it)
- [Option A — Desktop app (Windows / Mac)](#option-a--desktop-app-windows--mac)
- [Option B — Web browser / Chromebook (Colab notebook)](#option-b--web-browser--chromebook-colab-notebook)
- [Workflow](#workflow)
- [Settings reference](#settings-reference)
- [Drawing / choosing the region of interest](#drawing--choosing-the-region-of-interest)
- [Outputs](#outputs)
- [Tips for good results](#tips-for-good-results)
- [How the tracking works](#how-the-tracking-works)

---

## Two ways to run it

| Your setup | Use this |
|---|---|
| A Windows or Mac computer with Python installed | **Option A** — the desktop app (double-click launcher) |
| A Chromebook, tablet, or any computer without Python | **Option B** — the Colab notebook (runs in a web browser) |

Both use the **exact same analysis code**, so they produce the same results.

---

## Option A — Desktop app (Windows / Mac)

### Requirements

- Python 3.8+
- Packages: `numpy`, `tifffile`, `opencv-python`, `scipy`, `matplotlib` (`tkinter` ships
  with most Python installs)

Install the packages once:

```bash
pip install numpy tifffile opencv-python scipy matplotlib
```

### Start it

**Easiest (Mac):** double-click **`Run Strain Analysis.command`** inside the
`python_compression_analysis` folder.

> The first time, macOS may block it as being from an "unidentified developer."
> Right-click the file → **Open** → confirm. You only need to do this once.

**From a terminal (Windows or Mac):**

```bash
cd python_compression_analysis
python -m strain_analysis_pkg
```

A settings window opens. Choose your file, adjust settings if you like, and click
**Run Analysis**. You'll then draw the region of interest, tracking runs, and an
interactive viewer opens. All outputs are saved under `python_compression_analysis/results/`.

---

## Option B — Web browser / Chromebook (Colab notebook)

No installation needed — this runs on Google's servers.

1. Go to [Google Colab](https://colab.research.google.com/).
2. **File → Upload notebook**, and upload
   [`python_compression_analysis/strain_analysis_notebook.ipynb`](python_compression_analysis/strain_analysis_notebook.ipynb).
   *(Or, if this repo is on GitHub: File → Open notebook → GitHub tab → paste the repo URL.)*
3. Run the cells from top to bottom (**Runtime → Run all**, or ▶ each cell).
4. When prompted, upload your video/stack, adjust the **Settings** and **ROI** cells, run
   tracking, view the result with the slider, and download the results zip.

You mostly interact with just the **Settings** and **ROI** cells. The full algorithm lives
in Part 1 but is **collapsed by default** — click any title bar to expand and read the code
behind each step.

---

## Workflow

Both versions follow the same steps:

1. **Load & preprocess** — the stack is loaded, contrast-adjusted, optionally blurred, and
   frame-skipped per your settings.
2. **Choose an ROI** — the area to analyze. A grid of tracking points is placed inside it
   (spaced by `mesh_spacing`) and connected into a triangle mesh.
3. **Track** — each point is followed across frames (see
   [How the tracking works](#how-the-tracking-works)).
4. **Compute strain** — per-point strain via a local least-squares fit over mesh
   neighbors, averaged to per-triangle values for display.
5. **Export & view** — CSV, plot, overlay video, and an interactive viewer.

---

## Settings reference

### Frames

| Setting | Default | Description |
|---|---|---|
| **Start Frame** | `0` | Reference frame. All strain is measured relative to this frame. Set it past any initial settling / pre-contact frames. |
| **End Frame** | *(blank = all)* | Last frame to include. Blank processes the whole stack. |
| **Frame Skip** | `1` | Use every Nth frame. Higher values speed up processing and increase per-frame motion (can help slow experiments) but reduce temporal resolution. |

### Strain

| Setting | Default | Description |
|---|---|---|
| **Strain Mode** | `vonmises` | Which strain to visualize. The CSV always contains all components. |
| **Min Neighbors** | `3` | Minimum mesh neighbors required to compute strain (and to fill a gap) at a point. |

**Strain modes:** `ex` (horizontal εx), `ey` (vertical εy), `gxy` (shear γxy),
`vonmises` (√(εx² − εx·εy + εy² + 0.75·γxy²) — a single scalar summary, best default).

### Mesh

| Setting | Default | Description |
|---|---|---|
| **Mesh Spacing** | `20` | Pixels between tracking points. Smaller = finer detail, slower. Typical 10–50. |
| **Show Triangle Edges** | `True` | Draw triangle outlines on the overlay. |

### Tracking

| Setting | Default | Description |
|---|---|---|
| **Template Width / Height (delta_x, delta_y)** | `30` | Size of the patch tracked around each point. Larger = more reliable texture but assumes strain is uniform over a bigger area. |
| **Search Range X / Y (t_x, t_y)** | `25` | How far (px) to search beyond the template edge. Must exceed the largest expected per-frame movement. Too large increases the chance of a wrong match. |
| **Corr Threshold** | `0.85` | Minimum match quality (0–1) to accept a match. Below it, the point is treated as untracked (see gap-filling). Lower = more coverage but more risk of bad matches. Typical 0.7–0.95. |
| **Max Displacement** | `30` | Largest allowed per-frame movement (px). A safety filter against false matches; keep it above real displacements and near your search range. |
| **Re-anchor Threshold** | *(blank = auto)* | When a point's match quality drops below this, its reference template advances to the current frame. Blank = automatic. |
| **Fill Untracked Points** | `True` | Estimate untrackable points from their tracked neighbors so the ROI stays fully covered. Estimated points are flagged (see [Outputs](#outputs)). |
| **Gaussian Blur** | `3` | Smoothing kernel applied before tracking (odd integer; `0` = off). 3–7 suits most microscopy. |

### Contrast

Pixel values are linearly rescaled from `[Low In, High In]` to `[0, 255]` and clipped.

| Setting | Default | Description |
|---|---|---|
| **Low In** | `28` | Intensity mapped to black. Raise to clip dark noise / boost contrast. |
| **High In** | `250` | Intensity mapped to white. Lower to brighten dim features. |

---

## Drawing / choosing the region of interest

**Desktop app:** a window shows the start frame. **Left-click** to place polygon vertices,
**Backspace** to undo, **Enter** to finish. At least 3 vertices are required.

**Colab notebook:** the start frame appears as an image you **click on directly** to draw
the polygon — click to place each corner, **Undo** / **Clear** as needed, then **Finish
ROI** (at least 3 points). A preview confirms your selection. *(A center-and-radii ellipse
fallback is included in case the click tool doesn't render in your environment.)*

Draw tightly around the specimen, and — importantly — **keep the ROI clear of the edges
where the sample contacts the grips/tweezers** (see [Tips](#tips-for-good-results)).

---

## Outputs

Saved to `results/<filename>_<timestamp>/` (desktop) or bundled into a downloadable zip
(Colab):

| File | Description |
|---|---|
| `<name>_strain.csv` | Per-point, per-frame data: `frame, point, row, col, ex, ey, gxy, confidence`. |
| `<name>_strain_over_time.png` | Mean strain (selected mode) vs. frame. |
| `<name>_strain.mp4` | Strain field overlaid on the frames (jet colormap, 5th–95th percentile range). |

**About the `confidence` column:** it's the match quality for a directly-measured point,
or **`-1` if the point was estimated from its neighbors** (gap-filling) rather than
measured. Filter out `confidence < 0` if you only want directly-measured data.

---

## Tips for good results

- **Keep the ROI off the contact edges.** This is single-camera **2D** DIC. Right where a
  curved sample meets the grips/tweezers, the surface tilts out of the camera plane and
  can bulge out-of-plane — motion that 2D tracking cannot resolve, no matter the settings.
  You'll get the cleanest, most trustworthy strain from the flatter interior of the sample,
  away from the contact points.
- **Start frame:** use a stable, undeformed frame before contact.
- **Mesh spacing:** start at 20; decrease for more detail, increase for speed.
- **Template size:** big enough to contain unique texture, small enough not to span
  regions that deform differently. ~30 px is a good start.
- **Search range vs. max displacement:** the search range must exceed the real per-frame
  motion; keep max displacement near it. If fast phases (e.g. quick release) drop out,
  raise both — but too-large a search range can cause wrong matches, so don't overshoot.
- **Correlation threshold:** raise it if you see noisy/erratic patches; lower it (toward
  ~0.75) if too many points drop out — but lowering it accepts weaker matches everywhere.
- **Gaps are honest.** A gap (or an estimated, `confidence = -1` point) means the tool
  couldn't reliably measure there — often a real, hard-to-image spot — rather than a
  silently-wrong value. That's usually more trustworthy than forcing full coverage.
- **Contrast:** adjust `Low In` / `High In` so the specimen texture is clearly visible in
  the ROI preview; poor contrast means poor tracking.

---

## How the tracking works

For each point, the tool finds where that patch of the sample moved to in the next frame:

- **Reference-frame tracking** — each point is matched to a template from an *anchor*
  frame (not merely the previous frame), which prevents small errors from compounding
  into drift over a long sequence. The anchor advances only when match quality drops.
- **Coarse match + KLT subpixel refinement** — a normalized cross-correlation search finds
  the patch, then a Lucas–Kanade (KLT) refinement locates it to a small fraction of a
  pixel.
- **Honest gaps, optional filling** — a point that can't be matched is marked missing
  rather than faked. With **Fill Untracked Points** on, its position is *estimated* from
  neighbors that did track (flagged `confidence = -1`), giving full coverage while keeping
  estimates distinguishable from real measurements.
- **Local least-squares strain** — strain at each point is fit from its mesh neighbors
  (robust to single-point noise), then averaged per triangle for the overlay.
