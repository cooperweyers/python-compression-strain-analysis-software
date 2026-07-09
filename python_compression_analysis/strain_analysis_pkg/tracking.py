"""Point tracking: reference-frame anchored coarse match + KLT subpixel refinement.

Design (vs. the original single-file script's frame-to-frame block matching):

1. Reference-frame tracking. Each point is matched against a template taken from an
   "anchor" frame (initially the start frame), not the previous frame. This avoids the
   drift that comes from compounding frame-to-frame errors. The anchor is only moved
   forward ("re-anchored") when match confidence drops, so the template stays valid
   without accumulating error every single frame.

2. KLT translation subpixel refinement. A coarse integer/parabolic match
   (cv2.matchTemplate, same idea as the original script) gives a starting guess, which
   is then refined with a Lucas-Kanade (KLT) translation-only Newton iteration. This
   converges to a small fraction of a pixel, well beyond the accuracy of a 3-point
   parabola fit alone. (A full affine per-point refinement was evaluated first but is
   ill-conditioned at typical patch sizes and diverges; local strain is instead computed
   from the tracked point mesh in strain.py.)

3. Explicit confidence, no silent failures. A failed or low-confidence match produces
   NaN, not a fake (0, 0) displacement -- so it can be excluded from strain computation
   instead of silently corrupting neighboring triangles.

4. Optional gap-filling via neighbor extrapolation. If a point can't find a real match,
   its position can instead be *estimated* from a local affine fit over its mesh
   neighbors that DID track successfully that frame (see `_extrapolate_position`). This
   is flagged with confidence -1 (never a value a real match can produce) so estimated
   points remain distinguishable from measured ones downstream -- full ROI coverage
   without silently pretending an estimate is a measurement.
"""

import cv2
import numpy as np
from scipy.ndimage import map_coordinates, spline_filter

from .strain import build_neighbor_lists

ESTIMATED_CONFIDENCE = -1.0  # sentinel: position is a neighbor-extrapolated estimate,
                             # not a real match. Real confidences are always >= corr_threshold > 0.


def _extract_patch(img, r0, c0, half_h, half_w):
    """Extract an axis-aligned, odd-sized patch centered exactly on the pixel nearest
    (r0, c0). Size is (2*half_h+1, 2*half_w+1) so the center pixel is unambiguous --
    an even-sized patch has no single center pixel, which introduces a systematic
    0.5px bias into any refinement anchored on it. Returns None if out of bounds.
    """
    r0i, c0i = int(round(r0)), int(round(c0))
    r_start, r_end = r0i - half_h, r0i + half_h + 1
    c_start, c_end = c0i - half_w, c0i + half_w + 1

    if r_start < 0 or c_start < 0 or r_end > img.shape[0] or c_end > img.shape[1]:
        return None

    return img[r_start:r_end, c_start:c_end]


def _extrapolate_position(ref_row_i, ref_col_i, ref_rows_nbrs, ref_cols_nbrs, cur_rows_nbrs, cur_cols_nbrs):
    """Estimate point i's current position from a local affine fit over neighbors that
    DID track successfully this frame.

    Fits current = A @ [ref_row, ref_col, 1] (least squares) using the neighbors' own
    reference -> current mappings, then evaluates that fit at point i's reference
    position. Requires >=3 non-collinear neighbors; returns None if the fit is
    degenerate (e.g. neighbors happen to be collinear).
    """
    ones = np.ones_like(ref_rows_nbrs, dtype=np.float64)
    design = np.column_stack([ref_rows_nbrs, ref_cols_nbrs, ones])
    query = np.array([ref_row_i, ref_col_i, 1.0])

    try:
        row_coef, *_ = np.linalg.lstsq(design, cur_rows_nbrs, rcond=None)
        col_coef, *_ = np.linalg.lstsq(design, cur_cols_nbrs, rcond=None)
    except np.linalg.LinAlgError:
        return None

    est_row = float(query @ row_coef)
    est_col = float(query @ col_coef)

    if not (np.isfinite(est_row) and np.isfinite(est_col)):
        return None

    return est_row, est_col


def _prefilter_frame(img):
    """Precompute cubic-spline coefficients for a whole frame, once, for reuse across
    every point's KLT refinement on that frame (see `_translation_refine`).
    """
    return spline_filter(img.astype(np.float64), order=3)


def _coarse_match(template, search_patch, t_x, t_y, corr_threshold):
    """Integer + parabolic-subpixel template match, in the spirit of the original script.

    Returns (dr, dc, confidence) offset of the template center within search_patch,
    or None if the match is unreliable.
    """
    h, w = template.shape
    if search_patch.shape[0] < h or search_patch.shape[1] < w:
        return None
    if np.all(template == 0):
        return None

    result = cv2.matchTemplate(search_patch, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < corr_threshold:
        return None

    mc, mr = max_loc  # cv2 returns (x=col, y=row)
    rh, rw = result.shape
    sub_r, sub_c = float(mr), float(mc)

    if 0 < mr < rh - 1:
        a, b, c = result[mr - 1, mc], result[mr, mc], result[mr + 1, mc]
        denom = 2 * b - a - c
        if abs(denom) > 1e-12:
            sub_r = mr + (a - c) / (2 * denom)

    if 0 < mc < rw - 1:
        a, b, c = result[mr, mc - 1], result[mr, mc], result[mr, mc + 1]
        denom = 2 * b - a - c
        if abs(denom) > 1e-12:
            sub_c = mc + (a - c) / (2 * denom)

    dr = -t_x + sub_r
    dc = -t_y + sub_c
    return dr, dc, float(max_val)


def _translation_refine(template, cur_img_coeffs, guess_row, guess_col, max_iters=20, eps=1e-3):
    """Lucas-Kanade (KLT) translation-only subpixel refinement.

    Fits a subpixel translation (d_row, d_col) so that sampling cur_img at
    (guess_row + d_row, guess_col + d_col) best matches `template`, using the classic
    KLT normal-equations update (Newton step on local image gradients).

    A full affine (6-parameter) formulation was tried first but is ill-conditioned for
    small patches -- the translation/shear/scale terms are too correlated at this patch
    size and it diverges instead of converging. Translation-only is well-conditioned and
    standard practice for DIC subpixel refinement; per-triangle strain is computed
    separately (see strain.py) from the resulting point positions, so nothing is lost.

    `cur_img_coeffs` must already be the cubic-spline-prefiltered coefficients of the
    current frame (see `_prefilter_frame`) -- computing that filter is O(image size), so
    it must be done once per frame by the caller, not once per point/iteration here
    (map_coordinates' default `prefilter=True` would otherwise silently redo it on the
    full image on every single call, which for a few hundred points times ~20 iterations
    each turns into the dominant cost of the whole tracking pass).

    Returns ((d_row, d_col), zncc) or None on failure/non-convergence, where zncc is the
    final zero-normalized cross-correlation (comparable in scale to
    cv2.TM_CCOEFF_NORMED's output).
    """
    h, w = template.shape
    rc = (h - 1) / 2.0
    cc_ = (w - 1) / 2.0
    rr, cc = np.meshgrid(np.arange(h) - rc, np.arange(w) - cc_, indexing="ij")

    d_row, d_col = 0.0, 0.0
    sampled = None

    for _ in range(max_iters):
        Wr = guess_row + d_row + rr
        Wc = guess_col + d_col + cc
        sampled = map_coordinates(
            cur_img_coeffs, [Wr.ravel(), Wc.ravel()], order=3, mode="constant", cval=np.nan,
            prefilter=False,
        ).reshape(h, w)
        if np.isnan(sampled).any():
            return None

        gr, gc = np.gradient(sampled)
        A = np.array(
            [
                [np.sum(gr * gr), np.sum(gr * gc)],
                [np.sum(gr * gc), np.sum(gc * gc)],
            ]
        )
        b = np.array([np.sum(gr * (template - sampled)), np.sum(gc * (template - sampled))])

        try:
            delta = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            return None

        d_row += float(delta[0])
        d_col += float(delta[1])

        if np.linalg.norm(delta) < eps:
            break

    if sampled is None:
        return None

    t_mean, t_std = template.mean(), template.std() + 1e-8
    s_mean, s_std = sampled.mean(), sampled.std() + 1e-8
    zncc = float(np.mean((sampled - s_mean) * (template - t_mean)) / (s_std * t_std))

    return (d_row, d_col), zncc


def track_point(
    ref_img,
    ref_row,
    ref_col,
    cur_img,
    cur_img_coeffs,
    guess_row,
    guess_col,
    half_h,
    half_w,
    t_x,
    t_y,
    corr_threshold,
    max_disp,
    lk_max_iters=20,
    lk_eps=1e-3,
):
    """Track one point from a reference-frame template into cur_img.

    Combines a coarse cv2.matchTemplate search (bounded by +-t_x/+-t_y) with a KLT
    translation subpixel refinement. `cur_img_coeffs` is cur_img's precomputed
    spline-filter coefficients (see `_prefilter_frame`) -- pass the same one in for every
    point tracked against this frame. Returns a dict with the new position and match
    confidence, or None if the point could not be reliably tracked.
    """
    template = _extract_patch(ref_img, ref_row, ref_col, half_h, half_w)
    if template is None or template.size == 0 or np.all(template == 0):
        return None

    search_patch = _extract_patch(cur_img, guess_row, guess_col, half_h + t_x, half_w + t_y)
    if search_patch is None:
        return None

    coarse = _coarse_match(template, search_patch, t_x, t_y, corr_threshold)
    if coarse is None:
        return None
    dr_coarse, dc_coarse, coarse_conf = coarse

    coarse_row = guess_row + dr_coarse
    coarse_col = guess_col + dc_coarse

    refined = _translation_refine(
        template.astype(np.float64),
        cur_img_coeffs,
        coarse_row,
        coarse_col,
        max_iters=lk_max_iters,
        eps=lk_eps,
    )

    if refined is None or refined[1] < corr_threshold:
        new_row, new_col, confidence = coarse_row, coarse_col, coarse_conf
    else:
        (d_row, d_col), zncc = refined
        new_row, new_col, confidence = coarse_row + d_row, coarse_col + d_col, zncc

    step_disp = float(np.hypot(new_row - guess_row, new_col - guess_col))
    if step_disp > max_disp:
        return None

    return {"row": new_row, "col": new_col, "confidence": confidence}


def track_sequence(
    imgs,
    pts,
    XA,
    YA,
    start_frame,
    delta_x,
    delta_y,
    t_x,
    t_y,
    corr_threshold,
    max_disp,
    reanchor_threshold=None,
    lk_max_iters=20,
    tri=None,
    fill_gaps=True,
    min_neighbors_fill=3,
    verbose=True,
):
    """Track all points across the full image sequence, in place on XA/YA.

    Points are tracked against a reference-frame template that only moves forward
    ("re-anchors") once its match confidence drops below `reanchor_threshold`.

    If `tri` (the mesh's Delaunay triangulation) is given and `fill_gaps=True`, a point
    that fails a real match is NOT immediately left as a permanent gap: its position is
    instead *estimated* via `_extrapolate_position` from whichever of its mesh neighbors
    DID get a real match this frame (never from other estimated neighbors, so estimates
    never chain off of other estimates). This gives full ROI coverage, but an estimated
    point is flagged with confidence == ESTIMATED_CONFIDENCE (-1) rather than looking
    like a real measurement, and it keeps using its last real anchor template next
    frame -- so if real tracking becomes possible again later, it can recover on its
    own instead of being reseeded from a guess. A point only ends up NaN if it fails a
    real match AND doesn't have >= min_neighbors_fill real neighbors to extrapolate
    from (or `tri` wasn't provided / `fill_gaps=False`).

    Returns
    -------
    XA, YA : the same arrays passed in, updated in place
    CA : np.ndarray, shape (n_pts, n_frames)
        Per-point, per-frame confidence: real match confidence (>= corr_threshold),
        ESTIMATED_CONFIDENCE (-1) if extrapolated, or 0 if neither was possible.
    """
    n_pts, n_frames = XA.shape
    half_h, half_w = delta_x // 2, delta_y // 2

    if reanchor_threshold is None:
        reanchor_threshold = min(0.99, corr_threshold + 0.1)

    do_fill = fill_gaps and tri is not None
    neighbor_lists = build_neighbor_lists(n_pts, tri) if do_fill else None

    CA = np.zeros((n_pts, n_frames))
    CA[:, start_frame] = 1.0

    anchor_frame = np.full(n_pts, start_frame, dtype=int)

    total = n_frames - 1 - start_frame
    for k in range(start_frame, n_frames - 1):
        if verbose:
            print(f"\rTracking frame {k - start_frame + 1}/{total}", end="", flush=True)

        cur_img = imgs[k + 1]
        cur_img_coeffs = _prefilter_frame(cur_img)  # once per frame, not once per point

        failed = []

        for i in range(n_pts):
            guess_row, guess_col = XA[i, k], YA[i, k]
            if np.isnan(guess_row) or np.isnan(guess_col):
                failed.append(i)
                continue

            af = anchor_frame[i]
            ref_row, ref_col = XA[i, af], YA[i, af]
            ref_img = imgs[af]

            result = track_point(
                ref_img,
                ref_row,
                ref_col,
                cur_img,
                cur_img_coeffs,
                guess_row,
                guess_col,
                half_h,
                half_w,
                t_x,
                t_y,
                corr_threshold,
                max_disp,
                lk_max_iters=lk_max_iters,
            )

            if result is None:
                failed.append(i)
                continue

            XA[i, k + 1] = result["row"]
            YA[i, k + 1] = result["col"]
            CA[i, k + 1] = result["confidence"]

            if result["confidence"] < reanchor_threshold:
                anchor_frame[i] = k + 1

        if do_fill:
            for i in failed:
                nbrs = neighbor_lists[i]
                if nbrs.size == 0:
                    XA[i, k + 1], YA[i, k + 1], CA[i, k + 1] = np.nan, np.nan, 0.0
                    continue

                real = nbrs[CA[nbrs, k + 1] > 0]  # only real matches, never estimates
                if real.size < min_neighbors_fill:
                    XA[i, k + 1], YA[i, k + 1], CA[i, k + 1] = np.nan, np.nan, 0.0
                    continue

                est = _extrapolate_position(
                    XA[i, start_frame], YA[i, start_frame],
                    XA[real, start_frame], YA[real, start_frame],
                    XA[real, k + 1], YA[real, k + 1],
                )
                if est is None:
                    XA[i, k + 1], YA[i, k + 1], CA[i, k + 1] = np.nan, np.nan, 0.0
                    continue

                XA[i, k + 1], YA[i, k + 1] = est
                CA[i, k + 1] = ESTIMATED_CONFIDENCE
                # anchor_frame[i] is deliberately left untouched: an estimate isn't a
                # real texture confirmation, so the next frame still tries to match
                # against the last genuinely-confirmed template.
        else:
            for i in failed:
                XA[i, k + 1], YA[i, k + 1], CA[i, k + 1] = np.nan, np.nan, 0.0

    if verbose:
        print()

    return XA, YA, CA
