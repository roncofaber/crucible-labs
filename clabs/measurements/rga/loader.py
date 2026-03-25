#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RGA Loader: Crucible Dataset → RGAMeasurement

Registered with Dataset.register_loader() in measurements/__init__.py.
Parses *_MS_t_averaged.txt (preferred) or *_MS_t.txt files produced by the
automated RGA/TEY pipeline at ALS BL12.0.1.2.

File format: tab-separated, 601 columns:
    Time(s) | MZ1(Torr) | Std1(Torr) | MZ2(Torr) | Std2(Torr) | ...
"""

import os
import re
import logging

import numpy as np
import pandas as pd

from clabs.measurements.rga.rga import RGAMeasurement

logger = logging.getLogger(__name__)

#%%

def _pick_ms_t_file(files):
    """Return the best MS_t file: prefer *_averaged, fall back to plain."""
    averaged = [f for f in files if re.search(r'_MS_t_averaged\.txt$', f)]
    if averaged:
        return averaged[0]
    plain = [f for f in files if re.search(r'_MS_t\.txt$', f)]
    if plain:
        return plain[0]
    return None


def _sample_name_from_path(path):
    """Extract sample name from filename prefix, e.g. 'TF002140_MS_t.txt' → 'TF002140'."""
    basename = os.path.basename(path)
    match = re.match(r'^([^_]+(?:_[^_]+)*?)_MS_t', basename)
    return match.group(1) if match else None


def load_rga(dataset, files):
    """Parse an RGA dataset from downloaded files. Returns an RGAMeasurement."""
    ms_t_file = _pick_ms_t_file(files)
    if ms_t_file is None:
        logger.warning(f"No MS_t file found for dataset {dataset.name!r}")
        return None

    sample_name = _sample_name_from_path(ms_t_file)
    if sample_name is None:
        logger.warning(f"Could not extract sample name from {ms_t_file!r}")

    df = pd.read_csv(ms_t_file, sep='\t')

    time = df["Time(s)"].to_numpy()

    # Column names: MZ1(Torr), Std1(Torr), MZ2(Torr), ...
    mz_cols  = [c for c in df.columns if re.match(r'^MZ\d+\(Torr\)$',  c)]
    std_cols = [c for c in df.columns if re.match(r'^Std\d+\(Torr\)$', c)]

    mz       = np.array([int(re.search(r'\d+', c).group()) for c in mz_cols])
    pressure = df[mz_cols].to_numpy()
    std      = df[std_cols].to_numpy()

    return RGAMeasurement(dataset, sample_name, time, mz, pressure, std)
