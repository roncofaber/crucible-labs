#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Plotting: Carrier Visualization

Provides plotting functions for visualizing well/carrier images.

Created on Thu Jan  8 13:39:01 2026
@author: roncofaber
"""

import matplotlib.pyplot as plt
cm = 1/2.54  # centimeters in inches
fs = 10

#%%

def visualize_carrier(image, fname):

    fig, ax = plt.subplots(figsize=(18 * cm, 12 * cm))

    ax.imshow(image)
    ax.set_title(f'{fname}', fontsize=fs)
    ax.axis('off')  # Remove axes for cleaner look
    fig.tight_layout()
    fig.show()

    return
