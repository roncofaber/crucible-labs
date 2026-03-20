#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sample Grid Visualization

Creates a grid of all thin film well images arranged to approximate a 16:9
aspect ratio.
"""

from clabs.project import CrucibleProject
from clabs.plot import plot_tfilms_grid

#%% Load project and thin films

proj = CrucibleProject("10k_perovskites")
tfilms = proj.samples.filter(sample_type="thin film")

#%% Load well images

proj.load_measurements("sample well image")

#%% Plot grid

fig = plot_tfilms_grid(tfilms, target_ratio=16/9, fig_width=16, show_label=False)

#%% Save

fig.savefig("all_tfilm_images_16x9.png", dpi=200, bbox_inches=None,
            facecolor="black", edgecolor="none", pad_inches=0)
