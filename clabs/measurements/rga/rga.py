#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RGAMeasurement: Residual Gas Analyzer Time-Series Data

Holds pressure-vs-time data for each mass-to-charge ratio measured during
an automated RGA/TEY run at ALS beamline 12.0.1.2.
"""

import os
import re
import logging

import numpy as np
import pandas as pd

from clabs.measurements.measurement import Measurement

logger = logging.getLogger(__name__)

#%%

def _pick_ms_t_file(files):
    """Return the best MS_t file: prefer *_averaged, fall back to plain."""
    averaged = [f for f in files if re.search(r'_MS_t_averaged\.txt$', f)]
    if averaged:
        return averaged[0]
    plain = [f for f in files if re.search(r'_MS_t\.txt$', f)]
    return plain[0] if plain else None


def _sample_name_from_path(path):
    """Extract sample name from filename prefix, e.g. 'TF002140_MS_t.txt' → 'TF002140'."""
    basename = os.path.basename(path)
    match = re.match(r'^([^_]+(?:_[^_]+)*?)_MS_t', basename)
    return match.group(1) if match else None


class RGAMeasurement(Measurement):

    _mtype = "rga"

    def __init__(self, dataset, sample_name, time, mz, pressure, std):
        """
        Parameters
        ----------
        dataset : Dataset
        sample_name : str
            Sample name extracted from the filename prefix (e.g. 'TF002140').
        time : np.ndarray, shape (T,)
            Time axis in seconds.
        mz : np.ndarray, shape (M,)
            Mass-to-charge ratios (integer m/z values).
        pressure : np.ndarray, shape (T, M)
            Partial pressure in Torr for each (time, m/z) point.
        std : np.ndarray, shape (T, M)
            Standard deviation of pressure.
        """
        super().__init__(dataset)
        self._sample_name = sample_name
        self.time     = time
        self.mz       = mz
        self.pressure = pressure
        self.std      = std

    @property
    def sample_name(self):
        return self._sample_name

    @property
    def sample_mfid(self):
        return None  # single-sample datasets match by name via Dataset.load()

    @property
    def n_timepoints(self):
        return len(self.time)

    @property
    def n_mz(self):
        return len(self.mz)

    def get_trace(self, mz):
        """Return pressure vs time for a single m/z value."""
        idx = np.searchsorted(self.mz, mz)
        if idx >= len(self.mz) or self.mz[idx] != mz:
            raise ValueError(f"m/z {mz} not found in dataset")
        return self.pressure[:, idx]

    def get_spectrum(self, t=None):
        """
        Return the mass spectrum (pressure vs m/z) at a given time index.
        If t is None, returns the time-averaged spectrum.
        """
        if t is None:
            return np.nanmean(self.pressure, axis=0)
        return self.pressure[t, :]

    @classmethod
    def load(cls, dataset, files):
        """Parse an RGA dataset from downloaded files. Returns an RGAMeasurement."""
        ms_t_file = _pick_ms_t_file(files)
        if ms_t_file is None:
            logger.warning(f"No MS_t file found for dataset {dataset.name!r}")
            return None

        sample_name = _sample_name_from_path(ms_t_file)
        if sample_name is None:
            logger.warning(f"Could not extract sample name from {ms_t_file!r}")

        df       = pd.read_csv(ms_t_file, sep='\t')
        time     = df["Time(s)"].to_numpy()
        mz_cols  = [c for c in df.columns if re.match(r'^MZ\d+\(Torr\)$',  c)]
        std_cols = [c for c in df.columns if re.match(r'^Std\d+\(Torr\)$', c)]
        mz       = np.array([int(re.search(r'\d+', c).group()) for c in mz_cols])
        pressure = df[mz_cols].to_numpy()
        std      = df[std_cols].to_numpy()

        return cls(dataset, sample_name, time, mz, pressure, std)

    # def __repr__(self):
    #     return (f"RGAMeasurement({self._sample_name!r}, "
    #             f"{self.n_timepoints} timepoints, m/z 1–{self.mz[-1]})")
