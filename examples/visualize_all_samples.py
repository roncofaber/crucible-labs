#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sample Grid Visualization Example

Demonstrates how to create a grid visualization of all sample well images.

Created on Fri Jan 30 14:32:30 2026
@author: roncofaber
"""

# Load relevant modules
from tksamples import Samples  # Import the Samples class from the tksamples package
import matplotlib.pyplot as plt

#%%
# Initialize the Samples object
# Use cache to avoid redundant downloads and set overwrite_cache to False
samples = Samples(use_cache=True, overwrite_cache=False, from_crucible=True,
                  project_id="10k_perovskites", sample_type="thin film")

# # Retrieve well images for the thin films
samples.get_well_images()

#%% Plot the grid

from tksamples.plot.tfgrid import plot_tfilms_grid

fig_width = 16
target_ratio = 16/9

fig = plot_tfilms_grid(samples, target_ratio=target_ratio, fig_width=fig_width,
                       show_label=False)


#%% To save the figure:
    
fig.savefig('all_tfilm_images_16x9.png', dpi=200, bbox_inches=None,
            facecolor='black', edgecolor='none', pad_inches=0)