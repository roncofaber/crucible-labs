#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Workflow Example - DEPRECATED

This example is deprecated. Please use:
- samples_workflow.py for working with Samples class
- project_workflow.py for working with CrucibleProject class

The code below still works but is kept for backwards compatibility.

Created on Thu Jan 22 14:05:48 2026
@author: roncofaber
"""

# Load relevant modules
from tksamples import Samples

#%%
# Initialize the Samples object
# Use cache to avoid redundant downloads and set overwrite_cache to False
samples = Samples(use_cache=True, overwrite_cache=False, from_crucible=True,
                  project_id="10k_perovskites", sample_type="thin film")

print(f"Loaded {samples.nsamples} samples")

#%%

# Retrieve well images for the thin films
samples.get_well_images()

# Retrieve UV-Vis data for the thin films
samples.get_uvvis_data()

#%%

