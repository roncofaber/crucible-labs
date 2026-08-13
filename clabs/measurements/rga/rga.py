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
import warnings
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
    return float(m.group(1).rstrip('.')) if m else None


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
    data    = np.loadtxt(path, skiprows=1, delimiter='\t', dtype=float)
    time    = data[:, 0]
    signal  = data[:, 1]
    shutter = data[:, 2] if data.shape[1] > 2 else np.zeros(len(time))

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
    pressure = data[:, 1:].astype(float)        # shape (T, M)
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

    # Properties
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

    # Basic accessors
    def get_trace(self, mz_val):
        """Return raw pressure vs time for a single m/z value."""
        idx = np.searchsorted(self.mz, mz_val)
        if idx >= len(self.mz) or self.mz[idx] != mz_val:
            raise ValueError(f"m/z {mz_val} not in dataset")
        return self.pressure[:, idx]

    def get_spectrum(self, t=None, t_start=None, t_end=None):
        """
        Mass spectrum (pressure vs m/z).

        Parameters
        ----------
        t : int or None
            Single time index.  When set, t_start/t_end are ignored.
        t_start, t_end : float or None
            Time range in seconds to average over.  When both are None and no
            single index is given, defaults to the shutter-open window (set by
            background_correct), or all time points if that is unavailable.
        """
        if t is not None:
            return self.pressure[t, :]

        if t_start is not None or t_end is not None:
            lo   = t_start if t_start is not None else self.time[0]
            hi   = t_end   if t_end   is not None else self.time[-1]
            mask = (self.time >= lo) & (self.time <= hi)
            if not mask.any():
                raise ValueError(f"No RGA scans in range [{lo:.1f}, {hi:.1f}] s.")
            return np.nanmean(self.pressure[mask, :], axis=0)

        if hasattr(self, "open_time") and hasattr(self, "close_time"):
            mask = (self.time >= self.open_time) & (self.time <= self.close_time)
            if mask.any():
                return np.nanmean(self.pressure[mask, :], axis=0)

        return np.nanmean(self.pressure, axis=0)

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot_imshow(self, **kwargs):
        """2-D pressure map (m/z vs time). Returns (fig, ax). See plotting.plot_imshow for kwargs."""
        from .plotting import plot_imshow
        return plot_imshow(self, **kwargs)

    def plot_spectrum(self, **kwargs):
        """Mass spectrum (pressure vs m/z). Returns (fig, ax). See plotting.plot_spectrum for kwargs."""
        from .plotting import plot_spectrum
        return plot_spectrum(self, **kwargs)

    def plot_tey(self, **kwargs):
        """TEY signal vs time with shutter shading. Returns (fig, ax). See plotting.plot_tey for kwargs."""
        from .plotting import plot_tey
        return plot_tey(self, **kwargs)

    def plot_background(self, mz_val=None, ax=None):
        """
        Visualise background correction effect.
        mz_val=int → (fig, ax) time trace for that channel;
        None → (fig, axes) spectrum comparison.
        See plotting.plot_background for details.
        """
        from .plotting import plot_background
        return plot_background(self, mz_val=mz_val, ax=ax)

    def background_correct(self,
                           window=30.0,
                           gap_before=5.0,
                           gap_after=10.0):
        """
        Per-channel linear background subtraction (in place).

        Selects two fixed-duration beam-off windows anchored to the shutter
        edges, fits a linear baseline through them for each m/z channel, and
        subtracts it.  The original pressure array is preserved as
        ``self._raw_pressure``.

        Windows
        -------
        Before : [open_time  - gap_before - window,  open_time  - gap_before]
        After  : [close_time + gap_after,             close_time + gap_after  + window]

        Parameters
        ----------
        window     : float
            Duration (s) of each background window (default 30 s).
        gap_before : float
            Gap (s) between the end of the pre-shutter window and shutter open
            (default 5 s).
        gap_after  : float
            Gap (s) between shutter close and the start of the post-shutter
            window (default 10 s).

        Returns
        -------
        self  (for chaining)
        """
        edges     = np.diff(self.shutter.astype(int))
        open_idx  = np.where(edges > 0)[0]
        close_idx = np.where(edges < 0)[0]
        if len(open_idx) == 0 or len(close_idx) == 0:
            raise ValueError("Could not detect shutter open/close edges.")

        open_time  = self.tey_time[open_idx[0] + 1]
        close_time = self.tey_time[close_idx[0]]

        # Pre-shutter window: ends gap_before before open, spans window seconds
        off1_end   = open_time  - gap_before
        off1_start = off1_end   - window
        off1_mask  = (self.time >= off1_start) & (self.time <= off1_end)

        # Post-shutter window: starts gap_after after close, spans window seconds
        off2_start = close_time + gap_after
        off2_end   = off2_start + window
        off2_mask  = (self.time >= off2_start) & (self.time <= off2_end)

        n1, n2 = off1_mask.sum(), off2_mask.sum()
        if n1 + n2 < 2:
            raise ValueError(
                f"Not enough background points (before={n1}, after={n2}). "
                f"Try increasing 'window' or reducing 'gap_before'/'gap_after'."
            )
        if n1 == 0:
            warnings.warn(
                f"No RGA scans in pre-shutter window "
                f"[{off1_start:.1f}, {off1_end:.1f}] s — using post-close only.",
                stacklevel=2,
            )
        if n2 == 0:
            warnings.warn(
                f"No RGA scans in post-shutter window "
                f"[{off2_start:.1f}, {off2_end:.1f}] s — using pre-open only.",
                stacklevel=2,
            )

        bg_mask = off1_mask | off2_mask
        x_bg    = self.time[bg_mask]

        # Preserve the original on first call; on re-runs, correct from raw
        if not hasattr(self, "_raw_pressure"):
            self._raw_pressure = self.pressure.copy()
        source = self._raw_pressure
        corrected = np.zeros_like(source)
        for mz_idx in range(source.shape[1]):
            col    = source[:, mz_idx]
            coeffs = np.polyfit(x_bg, col[bg_mask], 1)
            corrected[:, mz_idx] = col - np.polyval(coeffs, self.time)

        self.pressure   = corrected
        self.open_time  = open_time
        self.close_time = close_time
        self._bg_off1   = (off1_start, off1_end)
        self._bg_off2   = (off2_start, off2_end)
        return self

    # ------------------------------------------------------------------
    # rgakit integration
    # ------------------------------------------------------------------

    def to_rgakit(self) -> "rgakit.SpectrumStack":
        """
        Convert this measurement to a :class:`rgakit.SpectrumStack`.

        If ``background_correct()`` has already been called, the corrected
        pressures and shutter window are preserved in the returned stack.
        Otherwise, the raw pressures are wrapped and background correction
        can be applied later via :meth:`~rgakit.SpectrumStack.background_correct`.

        Returns
        -------
        rgakit.SpectrumStack
        """
        try:
            from rgakit import SpectrumStack
        except ImportError as e:
            raise ImportError(
                "rgakit is required for to_rgakit(): pip install rgakit"
            ) from e
        return SpectrumStack.from_rga(self)

    # ------------------------------------------------------------------
    # Loader
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, dataset, files, background_correct=True,
             window=30.0, gap_before=5.0, gap_after=10.0):
        """Parse raw TEY + RGA histogram files and return an RGAMeasurement.

        Parameters
        ----------
        background_correct : bool
            If True (default), apply per-channel linear background subtraction
            on load.  Set to False to keep raw pressures.
        window, gap_before, gap_after : float
            Forwarded to background_correct().  See that method for details.
        """
        tey_file = _find_file(files, r'_TEY_DarkPD_',               ext='.txt')
        rga_file = _find_file(files, r'_RGA_histogram_scanspeed_',  ext='.txt')

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

        obj = cls(dataset, sample_name,
                  time, mz, pressure,
                  tey_time, tey_signal, shutter,
                  pd_ua, dark_pd_ua,
                  x=x, y=y, scan_settings=scan_settings)

        if background_correct:
            try:
                obj.background_correct(window=window,
                                       gap_before=gap_before,
                                       gap_after=gap_after)
            except Exception as e:
                logger.warning(f"Background correction failed for {sample_name!r}: {e}")

        return obj
