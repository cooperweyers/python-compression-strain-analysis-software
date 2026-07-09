"""Interactive keyboard-driven strain viewer."""

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from .export import render_overlay_frame, select_strain_component


def view_strain(imgs, XA, YA, tri, tri_strain, strain_mode, show_triangle_edges, start_frame):
    """Open an interactive window to step through frames with the strain overlay.

    Controls: right/d = next frame, left/a = previous frame, q/escape = close.
    """
    data, label = select_strain_component(tri_strain, strain_mode)
    vmin = np.nanpercentile(data, 5)
    vmax = np.nanpercentile(data, 95)
    cmap = plt.cm.jet

    n_frames = imgs.shape[0]
    n_pts = XA.shape[0]

    fig, ax = plt.subplots()

    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
    sm = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(label)

    state = {"current": start_frame}

    def show(k):
        ax.clear()
        pts_now = np.array([[YA[i, k], XA[i, k]] for i in range(n_pts)])
        frame_bgr = render_overlay_frame(
            imgs[k], tri, data[k], pts_now, vmin, vmax, cmap, show_triangle_edges
        )
        ax.imshow(frame_bgr[:, :, ::-1])  # BGR -> RGB for matplotlib
        ax.set_title(f"Frame {k} | <- -> or A/D")
        fig.canvas.draw_idle()

    def on_key(event):
        if event.key in ("right", "d"):
            state["current"] = min(state["current"] + 1, n_frames - 1)
        elif event.key in ("left", "a"):
            state["current"] = max(state["current"] - 1, start_frame)
        elif event.key in ("q", "escape"):
            plt.close(fig)
            return
        show(state["current"])

    fig.canvas.mpl_connect("key_press_event", on_key)
    show(state["current"])
    plt.show()
