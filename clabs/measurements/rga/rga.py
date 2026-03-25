#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RGAMeasurement: Residual Gas Analyzer Time-Series Data

Parses raw RGA + TEY files from the automated RGA/TEY pipeline at ALS BL12.0.1.2.

Raw files expected per dataset:
  *_TEY_DarkPD_*uA_PD_*uA_*_X_*_Y_*.txt   — TEY / shutter time-series
  *_RGA_histogram_*_X_*_Y_*.txt            — mass-spectrum time-series
"""

import os
import re
import logging
from datetime import datetime

import numpy as np

from clabs.measurements.measurement import Measurement

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private parsing helpers
# ---------------------------------------------------------------------------

def _find_file(files, pattern, ext=None):
    """Return first file whose basename matches *pattern* (regex), or None.
    Optionally restrict to files with the given extension (e.g. '.txt').
    """
    for f in files:
        bn = os.path.basename(f)
        if ext and not bn.lower().endswith(ext):
            continue
        if re.search(pattern, bn):
            return f
    return None


def _extract_float(text, pattern):
    """Return float from first capture group of *pattern* in *text*, or None."""
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def _parse_tey_file(path):
    """
    Parse a TEY file.  Returns
        time    : np.ndarray (T,)  – seconds
        signal  : np.ndarray (T,)  – TEY in Amperes
        shutter : np.ndarray (T,)  – 1 = beam on, 0 = beam off
        pd_ua   : float            – photodiode current (µA)
        dark_pd_ua : float         – dark PD current (µA)
        x, y    : float            – stage coordinates
    """
    data   = np.loadtxt(path, skiprows=1, delimiter='\t', dtype=float)
    time   = data[:, 0]
    signal = data[:, 1]
    shutter = data[:, 2]

    bn = os.path.basename(path)
    pd_ua      = _extract_float(bn, r'_PD_([-\d.]+)uA')
    dark_pd_ua = _extract_float(bn, r'DarkPD_([-\d.]+)uA')
    x          = _extract_float(bn, r'_X_([-\d.]+)')
    y          = _extract_float(bn, r'_Y_([-\d.]+)')

    return time, signal, shutter, pd_ua, dark_pd_ua, x, y


def _parse_rga_file(path):
    """
    Parse an RGA histogram file.  Returns
        time_str  : list[str]         – raw timestamp strings
        mz        : np.ndarray (M,)   – m/z values (1-based)
        pressure  : np.ndarray (T, M) – raw partial pressures (Torr)
        scan_settings : dict
        sample_name   : str or None
    """
    data     = np.loadtxt(path, skiprows=2, delimiter='\t', dtype=str)
    time_str = data[:, 0].tolist()
    pressure = data[:, 1:].astype(float)
    mz       = np.arange(1, pressure.shape[1] + 1)

    bn = os.path.basename(path)
    scan_settings = dict(
        scanspeed  = _extract_float(bn, r'scanspeed_(\d+)'),
        finalmass  = _extract_float(bn, r'finalmass_(\d+)'),
        scantime   = _extract_float(bn, r'scantime_(\d+)'),
    )
    sample_name = bn.split('_RGA_')[0] if '_RGA_' in bn else None

    return time_str, mz, pressure, scan_settings, sample_name


def _timestamps_to_seconds(time_str_list):
    """Convert '%Y/%m/%d %H:%M:%S.%f' strings to seconds relative to first."""
    t0 = datetime.strptime(time_str_list[0], '%Y/%m/%d %H:%M:%S.%f')
    return np.array([
        (datetime.strptime(t, '%Y/%m/%d %H:%M:%S.%f') - t0).total_seconds()
        for t in time_str_list
    ])


# ---------------------------------------------------------------------------
# Measurement class
# ---------------------------------------------------------------------------

class RGAMeasurement(Measurement):
    """
    Raw RGA + TEY data from one automated RGA/TEY run.

    Attributes
    ----------
    time : np.ndarray (T,)
        RGA time axis in seconds (relative to first scan).
    mz : np.ndarray (M,)
        Mass-to-charge values.
    pressure : np.ndarray (T, M)
        Raw partial pressures in Torr.
    tey_time : np.ndarray
        TEY time axis in seconds.
    tey_signal : np.ndarray
        Raw TEY signal in Amperes.
    shutter : np.ndarray
        Shutter state (1 = beam on, 0 = off).
    pd, dark_pd : float
        Photodiode and dark-PD currents in µA.
    x, y : float
        Stage coordinates.
    scan_settings : dict
    """

    _mtype = "rga"

    def __init__(self, dataset, sample_name,
                 time, mz, pressure,
                 tey_time, tey_signal, shutter,
                 pd_ua, dark_pd_ua,
                 x=None, y=None, scan_settings=None):

        super().__init__(dataset)
        self._sample_name = sample_name
        self.time         = time
        self.mz           = mz
        self.pressure     = pressure
        self.tey_time     = tey_time
        self.tey_signal   = tey_signal
        self.shutter      = shutter
        self.pd           = pd_ua
        self.dark_pd      = dark_pd_ua
        self.x            = x
        self.y            = y
        self.scan_settings = scan_settings or {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def sample_name(self):
        return self._sample_name

    @property
    def sample_mfid(self):
        return None

    @property
    def n_timepoints(self):
        return len(self.time)

    @property
    def n_mz(self):
        return len(self.mz)

    # ------------------------------------------------------------------
    # Basic accessors
    # ------------------------------------------------------------------

    def get_trace(self, mz_val):
        """Return raw pressure vs time for a single m/z value."""
        idx = np.searchsorted(self.mz, mz_val)
        if idx >= len(self.mz) or self.mz[idx] != mz_val:
            raise ValueError(f"m/z {mz_val} not in dataset")
        return self.pressure[:, idx]

    def get_spectrum(self, t=None):
        """
        Raw mass spectrum (pressure vs m/z).
        *t* = time index; None → time-averaged over all points.
        """
        if t is None:
            return np.nanmean(self.pressure, axis=0)
        return self.pressure[t, :]

    # ------------------------------------------------------------------
    # Loader
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, dataset, files):
        """Parse raw TEY + RGA histogram files and return an RGAMeasurement."""
        tey_file = _find_file(files, r'_TEY_',           ext='.txt')
        rga_file = _find_file(files, r'_RGA_histogram_', ext='.txt')

        if tey_file is None:
            logger.warning(f"No TEY file for dataset {dataset.name!r}")
            return None
        if rga_file is None:
            logger.warning(f"No RGA histogram file for dataset {dataset.name!r}")
            return None

        tey_time, tey_signal, shutter, pd_ua, dark_pd_ua, x, y = _parse_tey_file(tey_file)
        time_str, mz, pressure, scan_settings, sample_name = _parse_rga_file(rga_file)

        if sample_name is None:
            sample_name = os.path.basename(tey_file).split('_TEY_')[0]

        time = _timestamps_to_seconds(time_str)

        return cls(dataset, sample_name,
                   time, mz, pressure,
                   tey_time, tey_signal, shutter,
                   pd_ua, dark_pd_ua,
                   x=x, y=y, scan_settings=scan_settings)
