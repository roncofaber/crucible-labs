#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UV-Vis Loader: Crucible Dataset → NirvanaUVVis

Registered with Dataset.register_loader() in measurements/__init__.py.
Receives a Dataset object and a list of local file paths (already downloaded
by Dataset.load()) and returns a list of NirvanaUVVis objects.

@author: roncofaber
"""

import os
import logging

from tksamples.measurements.uvvis.h5reader import h5_to_samples

logger = logging.getLogger(__name__)

# Dataset names (or substrings) to skip when loading UV-Vis data.
BAD_DATASETS = {
    # Trays 3/4, repeated measurements on same tray
    "251218_130227_pollux_oospec_multipos_line_scan_TRAY3_4_1week",
    "260107_151134_pollux_oospec_multipos_line_scan__TRAY3_4_4weeks",
    "260109_111702_pollux_oospec_multipos_line_scan",
    # Trays 51/52, Tim fucked up
    "260119_183317_pollux_oospec_multipos_line_scan",
}

#%%

def load_uvvis(dataset, files):
    """Parse a UV-Vis dataset from downloaded files. Returns a list of NirvanaUVVis."""
    if any(bad in dataset.name for bad in BAD_DATASETS):
        logger.debug(f"Skipping bad UV-Vis dataset {dataset.name!r}")
        return None
    h5_files = [f for f in files if f.endswith('.h5')]
    if not h5_files:
        logger.warning(f"No .h5 file found for dataset {dataset.name!r}")
        return None
    corrected = [f for f in h5_files if "corrected" in os.path.basename(f).lower()]
    h5file = corrected[0] if corrected else h5_files[0]
    return h5_to_samples(dataset, h5file)
