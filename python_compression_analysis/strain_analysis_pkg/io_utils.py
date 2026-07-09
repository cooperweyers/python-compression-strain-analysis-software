"""Image stack loading and preprocessing."""

import os

import cv2
import numpy as np
import tifffile as tiff


def load_image_stack(filename, frame_skip=1, end_frame=None):
    """Load a grayscale image stack from a TIFF file or a video file.

    Parameters
    ----------
    filename : str
        Path to a .tif/.tiff stack or a video file (.mov/.mp4/.avi/.mkv).
    frame_skip : int
        Keep every Nth frame.
    end_frame : int or None
        If given, trim the stack to frames [0, end_frame] after skipping.

    Returns
    -------
    imgs : np.ndarray, shape (n_frames, height, width), dtype matches source
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext in (".tiff", ".tif"):
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
        imgs = imgs[: end_frame + 1]

    return imgs


def adjust_contrast(img, low_in, high_in):
    """Linearly rescale [low_in, high_in] to [0, 255] and clip, as uint8."""
    img = np.clip((img.astype(np.float32) - low_in) / (high_in - low_in), 0, 1)
    return (img * 255).astype(np.uint8)


def preprocess_stack(imgs, low_in, high_in, gaussian_blur=0):
    """Apply contrast adjustment and optional Gaussian blur to every frame."""
    imgs = np.array([adjust_contrast(f, low_in, high_in) for f in imgs])

    if gaussian_blur > 0:
        ksize = gaussian_blur if gaussian_blur % 2 == 1 else gaussian_blur + 1
        imgs = np.array([cv2.GaussianBlur(f, (ksize, ksize), 0) for f in imgs])

    return imgs
