#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Samples Workflow Example

Demonstrates how to use the Samples class to work with samples of a specific
type, load measurements, and analyze data. This is the simpler approach when
you don't need genealogy tracking.

Created on Thu Jan 22 14:05:48 2026
@author: roncofaber
"""

# Load relevant modules
from tksamples import Samples

#%% Initialize the Samples collection for thin films

# Load all thin film samples from Crucible
# Use cache to avoid redundant downloads
samples = Samples(use_cache=True, overwrite_cache=False, from_crucible=True,
                  project_id="10k_perovskites", sample_type="thin film")

print(f"Loaded {samples.nsamples} thin film samples")

#%% Load measurements

# Retrieve well images for the thin films
samples.get_well_images()

# Retrieve UV-Vis data for the thin films
samples.get_uvvis_data()

#%% Access individual samples

# By index
sample = samples[0]
print(f"Sample: {sample.sample_name}")
print(f"Measurements: {len(sample.measurements)}")

# By name
sample = samples["TF0001"]

# By unique ID
# sample = samples[unique_id]

#%% Work with measurements

# Access specific measurement types
if hasattr(sample, 'image'):
    sample.view()  # Display the well image

if hasattr(sample, 'nirvana_uvvis'):
    uvvis = sample.nirvana_uvvis
    print(f"UV-Vis wavelength range: {uvvis.wavelength.min():.1f} - {uvvis.wavelength.max():.1f} nm")

#%% Filter and analyze

# Get all measurements of a specific type
all_uvvis = samples.get_measurements('nirvana_uvvis')
print(f"Total UV-Vis measurements: {len(all_uvvis)}")

# Iterate over samples
for sample in samples[:5]:  # First 5 samples
    print(f"{sample.sample_name}: {sample.sample_type}")

#%% Slicing creates new Samples collections

# Get a subset of samples
subset = samples[10:20]
print(f"Subset contains {subset.nsamples} samples")

#%% When to use Samples vs CrucibleProject

# Use Samples when:
# - You only need samples of one type
# - You want to load measurements
# - You don't need genealogy/graph information

# Use CrucibleProject when:
# - You need the entire project
# - You want to explore genealogy relationships
# - You need to work with multiple sample types
# - You want graph visualization

# Example: Use CrucibleProject to get Samples collection
# from tksamples.project import CrucibleProject
# proj = CrucibleProject("10k_perovskites")
# thin_films = proj.get_samples_collection("thin film")
# thin_films.get_uvvis_data()
