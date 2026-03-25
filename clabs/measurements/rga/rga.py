#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RGAMeasurement: Residual Gas Analyzer Time-Series Data

Holds pressure-vs-time data for each mass-to-charge ratio measured during
an automated RGA/TEY run at ALS beamline 12.0.1.2.
"""

import numpy as np

from clabs.measurements.measurement import Measurement

#%%

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

    def __repr__(self):
        return (f"RGAMeasurement({self._sample_name!r}, "
                f"{self.n_timepoints} timepoints, m/z 1–{self.mz[-1]})")
