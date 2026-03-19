#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 30 15:40:15 2026

@author: roncofaber
"""

import numpy as np
import matplotlib.pyplot as plt

#%%

def best_grid(n, target_ratio=16/9, w_ratio=10.0, w_empty=0.5):
    """
    Returns (rows, cols) such that rows*cols >= n and cols/rows ~ target_ratio.
    Minimizes: w_ratio*abs(cols/rows - target_ratio) + w_empty*(rows*cols - n)
    """
    if n <= 0:
        return 0, 0

    rows = np.arange(1, n + 1)                         # 1..n
    cols_min = (n + rows - 1) // rows                   # ceil(n/rows) (int math)

    # candidates for cols near the target aspect, but never below cols_min
    cols_floor = np.floor(rows * target_ratio).astype(int)
    cols_ceil  = np.ceil(rows * target_ratio).astype(int)
    cols_round = np.rint(rows * target_ratio).astype(int)

    cand = np.stack([
        cols_min,
        np.maximum(cols_min, cols_floor),
        np.maximum(cols_min, cols_ceil),
        np.maximum(cols_min, cols_round),
    ], axis=0)

    r = rows[None, :]                                   # shape (1, n)
    empty = r * cand - n                                # shape (k, n)
    mismatch = np.abs(cand / r - target_ratio)
    score = w_ratio * mismatch + w_empty * empty

    k, j = np.unravel_index(np.argmin(score), score.shape)
    return int(rows[j]), int(cand[k, j])

def center_crop_square(img, side):
    """Center-crop a 2D (H,W) or 3D (H,W,C) numpy array to (side, side[, C])."""
    h, w = img.shape[:2]
    if side > min(h, w):
        raise ValueError(f"side={side} is larger than image ({h}, {w})")

    y0 = (h - side) // 2
    x0 = (w - side) // 2
    return img[y0:y0 + side, x0:x0 + side, ...]

def plot_tfilms_grid(
    tfilms,
    crop_side=None,              # int (pixels) or None => auto (min over all images)
    target_ratio=16/9,
    fig_width=16,                # inches; height computed from target_ratio
    facecolor="black",
    cmap="viridis",
    show_label=True,
):
    """
    Collects images from tfilms, center-crops to a common square, and plots on a grid
    whose rows/cols approximate target_ratio.

    Returns: (fig, axes, valid_idxs, images_data)
    """
    # Collect images + indices
    images_data, valid_idxs = [], []
    for cc, tf in enumerate(tfilms):
        if getattr(tf, "image", None) is None:
            continue
        images_data.append(np.array(tf.image.image))
        valid_idxs.append(cc)

    nimages = len(images_data)
    if nimages == 0:
        raise ValueError("No images found (all tf.image are None).")

    # Decide crop size (square)
    if crop_side is None:
        side = min(min(img.shape[0], img.shape[1]) for img in images_data)
    else:
        side = int(crop_side)
        max_allowed = min(min(img.shape[0], img.shape[1]) for img in images_data)
        if side > max_allowed:
            raise ValueError(f"crop_side={side} exceeds smallest image side={max_allowed}.")

    # Crop all to common centered square
    images_data = [center_crop_square(img, side) for img in images_data]

    # Grid dims near target_ratio
    nrows, ncols = best_grid(nimages, target_ratio=target_ratio)

    # Figure size consistent with target_ratio
    figsize = (fig_width, fig_width / target_ratio)

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, facecolor=facecolor)
    axes = np.atleast_1d(axes).ravel()

    # turn off everything by default
    for ax in axes:
        ax.set_axis_off()
        ax.set_facecolor(facecolor)

    # Plot
    for cc, (idx, img) in enumerate(zip(valid_idxs, images_data)):
        ax = axes[cc]
        if img.ndim == 3:
            ax.imshow(img)
        else:
            ax.imshow(img, cmap=cmap)
        
        if show_label:
            tf_idx = int(tfilms[idx].sample_name[2:])
            ax.text(
                0.02, 0.02, f"TF#{tf_idx}",
                transform=ax.transAxes,
                fontsize=4, color="black", weight="bold",
                va="bottom", ha="left",
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.8, edgecolor="none"),
            )

    # Hide unused slots completely
    for ax in axes[nimages:]:
        ax.set_visible(False)

    plt.subplots_adjust(left=0, bottom=0, right=1, top=1, hspace=0, wspace=0)
    fig.patch.set_facecolor(facecolor)
    plt.show()

    return fig