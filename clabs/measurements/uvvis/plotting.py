#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UV-Vis Plotting: Sample Visualization and Inhomogeneity Analysis

Provides plotting functions for UV-Vis sample visualization and inhomogeneity
analysis with customizable styling and scientific presentation formatting.

Created on Thu Jan  8 13:39:01 2026
@author: roncofaber
"""

# numpee
import numpy as np

# plotting stuff
import matplotlib.pyplot as plt
import seaborn as sns
cm = 1/2.54  # centimeters in inches
sns.set_theme(style="white")
sns.set_style("ticks")
fs = 10

#%%

att2label = {
    "transmissions"   : "Transmission",
    "absorbances"     : "Absorbance",
    "cor_intensities" : "Intensity",
    }

def plot_sample(value2plot, wavelengths, spots, title, erange, value):

    fig, ax = plt.subplots(figsize=(9.5*cm, 6*cm))

    for spot in spots:
        y_axis = value2plot[spot]
        ax.plot(wavelengths, y_axis, label=spot)

    ax.set_title(title)

    ax.set_xlabel("Wavelength [nm]", fontsize=fs)
    ax.set_ylabel(f"{att2label[value]} [-]", fontsize=fs)
    ax.yaxis.set_tick_params(labelsize=fs-1)
    ax.xaxis.set_tick_params(labelsize=fs-1)

    # Set scientific notation for y-axis
    ax.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))
    ax.yaxis.get_offset_text().set_fontsize(fs-1)

    ax.set_xlim(left=erange[0], right=erange[1])

    if value == "transmissions":
        ax.set_ylim(bottom=0, top=1)

    # set legend outside axes, right side, compact
    ax.legend(fontsize=fs-1, framealpha=1, edgecolor='k',
              loc="upper left", bbox_to_anchor=(1.01, 1),
              ncols=1, title=None, title_fontsize=14,
              handlelength=0.5, handletextpad=0.2, labelspacing=0.3)

    fig.tight_layout()
    fig.subplots_adjust(right=0.875)  # Make room for legend on the right
    fig.show()

    return


def plot_inhomogeneity(inhomogenity):

    mean_values = inhomogenity.mean(axis=1)
    std_values  = inhomogenity.std(axis=1)

    fig, ax = plt.subplots(figsize=(12 * cm, 8 * cm))

    x_indices = np.arange(len(inhomogenity))

    # Create an errorbar plot
    ax.errorbar(x_indices, mean_values, yerr=std_values, fmt='o', color='black',
                markersize=5, elinewidth=2, capsize=5)

    ax.set_xlabel('Sample idx [-]', fontsize=fs)
    ax.set_ylabel('Inhomogeneity [-]', fontsize=fs)
    ax.yaxis.set_tick_params(labelsize=fs-1)
    ax.xaxis.set_tick_params(labelsize=fs-1)

    ax.axhline(y=np.mean(mean_values), linestyle="--", color="gray", zorder=-10)

    ax.set_xlim(left=-0.5, right=len(inhomogenity)-0.5)
    ax.set_xticks(x_indices)

    fig.tight_layout()
    fig.show()

    return
