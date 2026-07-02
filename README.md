# Python Compression Strain Analysis Software

A digital image correlation (DIC) tool for computing 2D strain fields from compression test image sequences. It tracks material deformation across frames using template matching, builds a Delaunay triangle mesh over a user-defined region of interest, and computes per-element strain. Results are exported as CSV data, a strain-over-time plot, a strain overlay video, and an interactive frame viewer.

## Table of Contents

- [Which Version Should I Use?](#which-version-should-i-use)
- [Running on Windows or Mac](#running-on-windows-or-mac)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Quick Start (Windows/Mac)](#quick-start-windowsmac)
- [Running on Chromebook or Any Web Browser (Jupyter Notebook)](#running-on-chromebook-or-any-web-browser-jupyter-notebook)
  - [Supported Platforms](#supported-platforms)
  - [Quick Start (Notebook)](#quick-start-notebook)
  - [Notebook Workflow](#notebook-workflow)
  - [Downloading Your Results](#downloading-your-results)
- [Supported File Formats](#supported-file-formats)
- [Workflow Overview](#workflow-overview)
- [Settings Reference](#settings-reference)
  - [Frame Settings](#frame-settings)
  - [Strain Settings](#strain-settings)
  - [Mesh Settings](#mesh-settings)
  - [Tracking Settings](#tracking-settings)
  - [Contrast Settings](#contrast-settings)
- [Drawing the Region of Interest](#drawing-the-region-of-interest)
- [Outputs](#outputs)
- [Interactive Viewer Controls](#interactive-viewer-controls)
- [Tips for Getting Good Results](#tips-for-getting-good-results)

---

## Which Version Should I Use?

| Your setup | File to use |
|---|---|
| Windows or Mac with Python installed | `python_compression_strain_analysis_software.py` |
| Chromebook, tablet, or any device with a web browser | `strain_analysis_notebook.ipynb` (via Google Colab) |
| Any computer without Python installed | `strain_analysis_notebook.ipynb` (via Google Colab) |
| Local Jupyter / VS Code with Python installed | `strain_analysis_notebook.ipynb` |

---

## Running on Windows or Mac

### Requirements

- Python 3.8+
- numpy
- tifffile
- opencv-python (`cv2`)
- scipy
- matplotlib
- tkinter (included with most Python installations)

### Installation

```bash
pip install numpy tifffile opencv-python scipy matplotlib
```

### Quick Start (Windows/Mac)

```bash
python python_compression_strain_analysis_software.py
```

1. A settings window opens. Click **Browse...** to select your image stack or video file.
2. Adjust settings as needed (defaults work well for most cases).
3. Click **Run Analysis**.
4. Draw a polygon around the region of interest on the displayed frame, then press **Enter**.
5. Wait for tracking and strain computation to finish.
6. Browse the results in the interactive viewer and find exported files in the `results/` folder.

---

## Running on Chromebook or Any Web Browser (Jupyter Notebook)

The file `strain_analysis_notebook.ipynb` is a Jupyter notebook version of the same software. It requires no local Python installation and runs entirely in a web browser. All settings are controlled through interactive widgets instead of a desktop GUI window.

### Supported Platforms

| Platform | Notes |
|---|---|
| **Google Colab** | Recommended for Chromebooks and any device without Python. Free, no setup required. |
| **Kaggle Notebooks** | Free alternative to Colab. Upload the `.ipynb` and run it directly. |
| **JupyterLab / Jupyter Notebook (local)** | Works on Windows/Mac if you have Jupyter installed (`pip install jupyterlab`). |
| **VS Code with Jupyter extension** | Works on Windows/Mac with the Python and Jupyter extensions installed. |

### Quick Start (Notebook)

#### Google Colab (Chromebook / no Python required)

1. Go to [colab.research.google.com](https://colab.research.google.com)
2. Click **File → Upload notebook** and select `strain_analysis_notebook.ipynb`
3. Run **Cell 1** to install the required packages
4. Go to **Runtime → Restart runtime** after Cell 1 completes
5. Run cells **2 through 9** in order from top to bottom

#### Local Jupyter or VS Code

1. Open `strain_analysis_notebook.ipynb` in JupyterLab or VS Code
2. Run cells in order from top to bottom
3. A system file dialog will open for file selection (same as the `.py` version)

### Notebook Workflow

The notebook is divided into labeled steps. Run each cell in order:

| Cell | Step | What it does |
|---|---|---|
| Cell 1 | Install | Installs required packages (Colab only, run once) |
| Cell 2 | Imports | Loads all libraries and detects whether you are on Colab |
| Cell 3 | Settings | Displays interactive widgets to configure all analysis parameters |
| Cell 4 | Upload File | Opens a file picker (Colab) or system file dialog (local) |
| Cell 5 | Load Images | Reads and preprocesses the image stack using your settings |
| Cell 6 | Draw ROI | Shows the image — click to place polygon points around your specimen |
| Cell 6b | Confirm ROI | Reads the points you placed and passes them to the analysis |
| Cell 7 | Run Analysis | Builds the mesh, tracks all points, and computes strain |
| Cell 8 | Export | Saves CSV, plot, and video — downloads a single zip file on Colab |
| Cell 9 | Viewer | Interactive slider to step through frames and inspect the strain field |

### Downloading Your Results

On **Google Colab**, Cell 8 automatically packages all three output files (CSV, plot, and video) into a single `.zip` file and downloads it to your computer. Allow the download if your browser asks.

If the download does not trigger automatically, you can find the files manually:
1. Click the **folder icon** in the left sidebar of Colab
2. Navigate to the `results/` folder
3. Right-click any file and select **Download**

On **local Jupyter or VS Code**, files are saved directly to a `results/` subfolder next to the notebook file — no download step needed.

---

## Supported File Formats

| Format | Extensions |
|---|---|
| TIFF image stacks | `.tiff`, `.tif` |
| Video files | `.mov`, `.mp4`, `.avi`, `.mkv` |

TIFF stacks can be grayscale or color (color frames are automatically converted to grayscale). Video files are read frame-by-frame and converted to grayscale.

---

## Workflow Overview

The software runs through five stages in sequence:

1. **Settings & File Selection** -- Configure all analysis parameters and select the input file.
2. **Image Loading & Preprocessing** -- The image stack is loaded, contrast-adjusted, optionally blurred, and frame-skipped according to your settings.
3. **ROI Selection & Mesh Generation** -- You draw a polygon on the start frame. A regular grid of tracking points is placed inside it, spaced by `mesh_spacing` pixels, and a Delaunay triangulation connects those points into a mesh.
4. **Tracking & Strain Computation** -- Each point is tracked forward frame-by-frame using normalized cross-correlation template matching. Strain (ex, ey, gxy) is computed for every triangle element at every frame using a constant-strain triangle (CST) finite element formulation.
5. **Export & Visualization** -- Results are saved to a timestamped folder inside `results/`.

---

## Settings Reference

### Frame Settings

| Setting | Default | Description |
|---|---|---|
| **Start Frame** | `0` | The reference frame index. All strain is measured relative to this frame. Set this past any initial settling or pre-contact frames so the reference state is stable. |
| **End Frame** | *(blank = all)* | The last frame index to include in the analysis. Leave blank to process the entire stack. Useful for trimming noisy or irrelevant tail frames. |
| **Frame Skip** | `1` | Take every Nth frame from the original stack. A value of `2` uses every other frame, `3` every third, etc. `1` uses all frames. Higher values speed up processing and increase the displacement between consecutive analyzed frames, which can improve correlation in slow-moving experiments, but reduces temporal resolution. Applied before the start/end frame indices. |

### Strain Settings

| Setting | Default | Description |
|---|---|---|
| **Strain Mode** | `vonmises` | Which strain component to visualize and export in the video/plot. Does not affect the CSV, which always exports all three components. Options below. |

**Strain mode options:**

| Mode | Symbol | Meaning |
|---|---|---|
| `ex` | εx | Horizontal (x-direction) normal strain |
| `ey` | εy | Vertical (y-direction) normal strain |
| `gxy` | γxy | In-plane shear strain |
| `vonmises` | εvm | Von Mises equivalent strain, computed as √(εx² − εx·εy + εy² + 0.75·γxy²). Gives a single scalar summary of the overall strain state. Best default for most compression experiments. |

### Mesh Settings

| Setting | Default | Description |
|---|---|---|
| **Mesh Spacing** | `20` | Distance in pixels between tracking grid points inside the ROI. Smaller values give a finer mesh with more triangles (higher spatial resolution, slower processing). Larger values give a coarser mesh (faster, smoother, but less detail). Typical range: 10-50 pixels. |
| **Show Triangle Edges** | `True` (checked) | Whether to draw black triangle outlines on the strain overlay in the viewer and exported video. Disable for a cleaner heatmap look; enable to see the mesh structure. |

### Tracking Settings

These control the template matching algorithm that follows each grid point from frame to frame.

| Setting | Default | Description |
|---|---|---|
| **Template Width (delta_x)** | `40` | Width in pixels of the template patch extracted around each tracking point. The tracker cuts a rectangle of size `delta_x × delta_y` from the current frame and searches for it in the next frame. Larger templates contain more texture and correlate more reliably, but are slower and assume strain is uniform over a bigger area. |
| **Template Height (delta_y)** | `40` | Height in pixels of the template patch. See delta_x above. |
| **Search Range X (t_x)** | `15` | How far (in pixels) to search in the x-direction beyond the template edges. The search window is `(delta_x + 2·t_x) × (delta_y + 2·t_y)`. Must be larger than the maximum expected per-frame displacement in x. Increasing this allows tracking faster motion but slows processing and increases the chance of false matches. |
| **Search Range Y (t_y)** | `15` | How far to search in the y-direction. See t_x above. |
| **Corr Threshold** | `0.85` | Minimum normalized cross-correlation score (0 to 1) required to accept a match. If the best match scores below this, the point reports zero displacement for that frame. Higher values reject more noise but may lose track in low-contrast regions. Lower values tolerate worse matches but may introduce tracking errors. Typical range: 0.7-0.95. |
| **Max Displacement** | `12` | Maximum allowed displacement magnitude (in pixels) per frame. If the detected displacement exceeds this, it's rejected and set to zero. Acts as a safety filter against false correlation peaks far from the true position. Should be set above your expected real displacements but below the search range. |
| **Gaussian Blur** | `3` | Kernel size for Gaussian blur preprocessing applied to all frames before tracking. Smooths out noise that could confuse the correlator. Set to `0` to disable. Must be a positive odd integer (if even, it's rounded up to the next odd number). Values of 3-7 work well for most microscopy data. |

### Contrast Settings

These adjust the intensity range of the images before tracking. Pixel values are linearly rescaled from `[low_in, high_in]` to `[0, 255]`, with values outside the range clipped.

| Setting | Default | Description |
|---|---|---|
| **Low In** | `28` | Input intensity value mapped to 0 (black). Pixels at or below this value become black. Raising this clips dark noise and increases contrast. |
| **High In** | `250` | Input intensity value mapped to 255 (white). Pixels at or above this value become white. Lowering this brightens dim features and increases contrast. |

Adjust these if your images look too dark, washed out, or have low contrast. View the ROI selection frame to judge the effect — it shows the contrast-adjusted image.

---

## Drawing the Region of Interest

**On Windows/Mac (`.py` version):** After clicking **Run Analysis**, a matplotlib window displays the start frame.

- **Left-click** to place vertices
- **Backspace** to undo the last vertex
- **Enter** to close the polygon and proceed

**On Colab/Notebook (Cell 6):** The start frame appears as an interactive image directly in the notebook.

- **Click** on the image to place polygon points
- Click **Undo Last** to remove the most recent point
- Click **Clear All** to start over
- Click **Finish ROI** when done, then run Cell 6b to confirm

The polygon defines which area gets meshed and tracked. Points outside the ROI are ignored. You need at least 3 vertices. Draw tightly around the specimen to avoid wasting computation on background regions, but leave enough margin that the template patches around edge points don't extend outside the specimen.

---

## Outputs

All results are saved to `results/<filename>_<timestamp>/`:

| File | Description |
|---|---|
| `<name>_strain.csv` | Per-triangle strain data for every frame. Columns: `frame`, `triangle`, `ex`, `ey`, `gxy`. This always contains all three strain components regardless of the selected strain mode. |
| `<name>_strain_over_time.png` | Plot of the mean strain (in the selected mode) across all triangles vs. frame number. |
| `<name>_strain.mp4` | Video with the strain field overlaid on the original images using a jet colormap. Color range is set by the 5th-95th percentile of strain values. Plays at 15 fps. |

On **Google Colab**, these three files are bundled into a single `<name>_<timestamp>.zip` and downloaded automatically at the end of Cell 8.

---

## Interactive Viewer Controls

**Windows/Mac (`.py` version):** After export, an interactive matplotlib viewer opens.

| Key | Action |
|---|---|
| **Right arrow** or **D** | Next frame |
| **Left arrow** or **A** | Previous frame |
| **Q** or **Escape** | Close viewer |

**Notebook (Cell 9):** A slider appears in the notebook output. Drag it left or right to step through frames.

The colorbar shows the strain scale for the selected strain mode. The color range is fixed to the 5th-95th percentile of strain values across all frames.

---

## Tips for Getting Good Results

- **Start frame**: Skip past any frames where the indenter hasn't contacted the specimen yet. The start frame should show a stable, undeformed state.
- **Mesh spacing**: Start with the default (25). If the strain map looks too blocky, decrease it. If processing is too slow, increase it.
- **Template size**: Should be large enough to capture unique texture (speckle pattern, cell features, etc.) but small enough to avoid spanning regions with different deformation. 30-50 pixels is typical.
- **Search range**: Must exceed the largest per-frame displacement. If tracking fails in fast-moving regions, increase `t_x`/`t_y`. If you get spurious jumps, decrease them.
- **Correlation threshold**: Raise this if you see noisy/erratic strain patches. Lower it if too many points are dropping out.
- **Frame skip**: If the specimen barely moves between frames, increase frame skip to get larger, more trackable displacements. If motion is fast, keep it at 1 or 2.
- **Gaussian blur**: Helps with noisy microscopy images. Start with 3; increase for very noisy data, set to 0 for clean high-contrast images.
- **Contrast**: Adjust `low_in` and `high_in` so the specimen texture is clearly visible in the ROI selection window. Poor contrast leads to poor tracking.
- **Colab processing speed**: Google Colab free tier uses shared CPU resources, so analysis may be slower than running locally. If processing a long video, increase **Frame Skip** to reduce the number of frames analyzed.
