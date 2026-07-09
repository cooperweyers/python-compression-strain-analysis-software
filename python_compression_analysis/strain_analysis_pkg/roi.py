"""Interactive polygon ROI selection."""

import matplotlib.pyplot as plt
from matplotlib.path import Path


def select_polygon_roi(image, title="Click to draw ROI | ENTER = finish | BACKSPACE = undo"):
    """Let the user click out a polygon ROI on an image.

    Parameters
    ----------
    image : np.ndarray
        Single 2D image (e.g. the start frame) to display for ROI selection.
    title : str
        Title shown above the ROI selection plot.

    Returns
    -------
    roi_path : matplotlib.path.Path
        Path object for the selected polygon (use .contains_point).
    vertices : list of (x, y) tuples
        Raw polygon vertices in click order.
    """
    plt.close("all")
    fig, ax = plt.subplots()
    ax.imshow(image, cmap="gray")
    ax.set_title(title)

    polygon_vertices = []
    line_plot, = ax.plot([], [], color="#39FF14", linewidth=2)  # neon green
    points_plot, = ax.plot([], [], "o", color="#39FF14")

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
        if event.key == "enter":
            plt.close(fig)
        elif event.key == "backspace":
            if polygon_vertices:
                polygon_vertices.pop()
                update_plot()

    fig.canvas.mpl_connect("button_press_event", onclick)
    fig.canvas.mpl_connect("key_press_event", onkey)

    plt.show()

    if len(polygon_vertices) < 3:
        raise RuntimeError("Polygon not properly defined")

    roi_path = Path(polygon_vertices)
    return roi_path, polygon_vertices
