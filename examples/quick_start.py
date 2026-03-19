#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Start Example

The absolute minimal code to get started with tksamples.
Choose your approach based on your needs.

@author: roncofaber
"""

#%% APPROACH 1: Simple - Just load samples and measurements

from tksamples import Samples

# Load thin film samples
samples = Samples(project_id="10k_perovskites", sample_type="thin film")

# Load measurements
samples.get_uvvis_data()
samples.get_well_images()

# Access a sample
sample = samples[0]
print(sample.sample_name)

#%% APPROACH 2: Full - Project with genealogy

from tksamples.project import CrucibleProject

# Load entire project
proj = CrucibleProject("10k_perovskites")

# Get samples by type
thin_films = proj.get_samples_collection("thin film")
thin_films.get_uvvis_data()

# Explore genealogy
sample = thin_films[0]
ancestors = proj.get_ancestors(sample)
siblings = proj.get_siblings(sample)

# Visualize
from tksamples.graph import plot_extended_family
fig, ax = plot_extended_family(proj, sample)

#%% That's it! See other examples for more details.
