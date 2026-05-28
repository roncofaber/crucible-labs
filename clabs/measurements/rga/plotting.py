#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RGA Plotting: 2-D pressure map, mass spectrum, and TEY trace.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

cm = 1 / 2.54
fs = 10


def plot_imshow(rga, log=True, mz_range=None, ax=None, cmap="viridis",
               show_shutter=True, raw=False, **kwargs):
    """
    2-D image: time (x) vs m/z (y), color = partial pressure.

    Parameters
    ----------
    rga : RGAMeasurement
    log : bool
        Use log-scale color normalization (default True).
        Automatically falls back to linear if the data contain negative values.
    mz_range : (int, int), optional
        Restrict m/z axis to [lo, hi].
    ax : matplotlib Axes, optional
        Axes to draw into; creates a new figure if None.
    cmap : str
        Colormap name.
    show_shutter : bool
        Overlay dashed lines at the shutter open and close times (default True).
        Requires background_correct() to have been called, or falls back to
        the TEY shutter signal edges.
    raw : bool
        Plot the uncorrected raw pressure instead of the background-corrected
        data (default False). Requires background_correct() to have been called.
    **kwargs
        Forwarded to pcolormesh.
    """
    mz       = rga.mz
    time     = rga.time
    if raw:
        if not hasattr(rga, "_raw_pressure"):
            raise RuntimeError("No raw data found. Call background_correct() first, or use raw=False.")
        pressure = rga._raw_pressure
    else:
        pressure = rga.pressure  # (T, M)

    if mz_range is not None:
        mask     = (mz >= mz_range[0]) & (mz <= mz_range[1])
        mz       = mz[mask]
        pressure = pressure[:, mask]

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(14 * cm, 8 * cm))
    else:
        fig = ax.get_figure()

    # Log norm: clip=True maps negatives to the lowest colormap color
    if log:
        pos = pressure[pressure > 0]
        if pos.size:
            norm = mcolors.LogNorm(vmin=pos.min(), vmax=pressure.max(), clip=True)
        else:
            norm = None   # no positive values at all — fall back to linear
    else:
        norm = None

    pcm = ax.pcolormesh(time, mz, pressure.T, cmap=cmap, norm=norm,
                        shading="auto", **kwargs)

    cbar = fig.colorbar(pcm, ax=ax, pad=0.02)
    cbar.set_label("Partial pressure [Torr]", fontsize=fs - 1)
    cbar.ax.tick_params(labelsize=fs - 2)

    ax.set_xlabel("Time [s]", fontsize=fs)
    ax.set_ylabel("m/z", fontsize=fs)
    ax.tick_params(labelsize=fs - 1)

    if show_shutter:
        # Prefer open_time/close_time set by background_correct; fall back to
        # the raw TEY shutter edges.
        if hasattr(rga, "open_time") and hasattr(rga, "close_time"):
            open_t, close_t = rga.open_time, rga.close_time
        else:
            shutter = rga.shutter.astype(int)
            edges   = np.diff(shutter)
            open_idx  = np.where(edges > 0)[0]
            close_idx = np.where(edges < 0)[0]
            open_t  = rga.tey_time[open_idx[0]  + 1] if len(open_idx)  else None
            close_t = rga.tey_time[close_idx[0]]      if len(close_idx) else None

        line_kw = dict(color="red", linestyle="--", linewidth=1.5, alpha=0.8)
        if open_t is not None:
            ax.axvline(open_t,  **line_kw, label="shutter open")
        if close_t is not None:
            ax.axvline(close_t, **line_kw, label="shutter close")

        if hasattr(rga, "_bg_off1"):
            ax.axvspan(*rga._bg_off1, color="white", alpha=0.10, label="BG window")
            ax.axvspan(*rga._bg_off2, color="white", alpha=0.10)

    title = rga.sample_name or ""
    if title:
        ax.set_title(title, fontsize=fs)

    if standalone:
        fig.tight_layout()
        fig.show()

    return ax


def plot_spectrum(rga, t=None, t_start=None, t_end=None,
                 log=False, normalize=True, ax=None, **kwargs):
    """
    Mass spectrum: intensity vs m/z.

    Parameters
    ----------
    rga : RGAMeasurement
    t : int or None
        Single time index.
    t_start, t_end : float or None
        Average over this time range (seconds).  When both are None and t is
        None, defaults to the shutter-open window.
    log : bool
        Log-scale y-axis (default False; auto-disabled when data have negatives).
    normalize : bool
        Normalise the spectrum to its maximum (default True).
    ax : matplotlib Axes, optional
    **kwargs
        Forwarded to bar.
    """
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(14 * cm, 6 * cm))

    spectrum = rga.get_spectrum(t, t_start=t_start, t_end=t_end)
    if t is not None:
        label = f"t={rga.time[t]:.0f} s"
    elif t_start is not None or t_end is not None:
        lo = t_start if t_start is not None else rga.time[0]
        hi = t_end   if t_end   is not None else rga.time[-1]
        label = f"{lo:.0f}–{hi:.0f} s"
    else:
        label = "shutter open" if hasattr(rga, "open_time") else "time-averaged"

    if normalize:
        peak = spectrum.max()
        if peak > 0:
            spectrum = spectrum / peak
        ylabel = "Relative intensity"
    else:
        ylabel = "Partial pressure [Torr]"

    ax.bar(rga.mz, spectrum, width=1.0, label=label, **kwargs)

    if log and spectrum.min() > 0:
        ax.set_yscale("log")

    ax.set_xlabel("m/z", fontsize=fs)
    ax.set_ylabel(ylabel, fontsize=fs)
    ax.tick_params(labelsize=fs - 1)
    ax.legend(fontsize=fs - 1)

    if standalone:
        ax.get_figure().tight_layout()
        ax.get_figure().show()

    return ax


def plot_background(rga, mz_val=None, ax=None):
    """
    Visualise the effect of background correction.

    Two modes depending on *mz_val*:

    *mz_val* is an integer m/z
        Single-channel time trace showing the raw signal, the fitted linear
        baseline, and the corrected (background-subtracted) signal.

    *mz_val* is None (default)
        Spectrum comparison: raw vs corrected mean over the shutter-open
        window, plus their difference (= the subtracted baseline spectrum).

    Requires background_correct() to have been called (needs _raw_pressure).
    """
    if not hasattr(rga, "_raw_pressure"):
        raise RuntimeError(
            "No background correction data found. "
            "Call rga.background_correct() first."
        )

    if mz_val is not None:
        # ── single m/z time-trace view ──────────────────────────────────
        idx = np.searchsorted(rga.mz, mz_val)
        if idx >= len(rga.mz) or rga.mz[idx] != mz_val:
            raise ValueError(f"m/z {mz_val} not found in dataset.")

        raw       = rga._raw_pressure[:, idx]
        corrected = rga.pressure[:, idx]
        baseline  = raw - corrected

        standalone = ax is None
        if standalone:
            fig, ax = plt.subplots(figsize=(14 * cm, 6 * cm))

        ax.plot(rga.time, raw,       color="steelblue",   lw=1.2, label="Raw")
        ax.plot(rga.time, baseline,  color="darkorange",  lw=1.2,
                linestyle="--", label="Baseline")
        ax.plot(rga.time, corrected, color="seagreen",    lw=1.2, label="Corrected")

        if hasattr(rga, "open_time"):
            ax.axvline(rga.open_time,  color="gray", lw=0.8, linestyle=":")
            ax.axvline(rga.close_time, color="gray", lw=0.8, linestyle=":")

        # shade the windows used for the linear baseline fit
        if hasattr(rga, "_bg_off1"):
            ax.axvspan(*rga._bg_off1, color="darkorange", alpha=0.12,
                       label="BG window")
            ax.axvspan(*rga._bg_off2, color="darkorange", alpha=0.12)

        ax.set_xlabel("Time [s]", fontsize=fs)
        ax.set_ylabel("Partial pressure [Torr]", fontsize=fs)
        ax.set_title(f"m/z = {mz_val}", fontsize=fs)
        ax.tick_params(labelsize=fs - 1)
        ax.legend(fontsize=fs - 1)

        if standalone:
            ax.get_figure().tight_layout()
            ax.get_figure().show()

        return ax

    else:
        # ── spectrum comparison view ─────────────────────────────────────
        if hasattr(rga, "open_time") and hasattr(rga, "close_time"):
            mask = (rga.time >= rga.open_time) & (rga.time <= rga.close_time)
        else:
            mask = slice(None)

        raw_spec  = np.nanmean(rga._raw_pressure[mask, :], axis=0)
        corr_spec = np.nanmean(rga.pressure[mask, :],      axis=0)
        diff_spec = raw_spec - corr_spec   # baseline that was removed

        # normalise for display
        peak = raw_spec.max() or 1.0
        raw_n  = raw_spec  / peak
        corr_n = corr_spec / peak
        diff_n = diff_spec / peak

        standalone = ax is None
        if standalone:
            fig, axes = plt.subplots(2, 1, figsize=(14 * cm, 10 * cm),
                                     sharex=True)
        else:
            # ax can be a single Axes or a list of two
            axes = ax if hasattr(ax, "__len__") else [ax, ax]
            fig  = axes[0].get_figure()

        axes[0].bar(rga.mz, raw_n,  width=1.0, color="steelblue",
                    alpha=0.7, label="Raw")
        axes[0].bar(rga.mz, corr_n, width=1.0, color="seagreen",
                    alpha=0.7, label="Corrected")
        axes[0].set_ylabel("Relative intensity", fontsize=fs)
        axes[0].legend(fontsize=fs - 1)
        axes[0].tick_params(labelsize=fs - 1)

        axes[1].bar(rga.mz, diff_n, width=1.0, color="darkorange",
                    alpha=0.8, label="Baseline removed")
        axes[1].set_xlabel("m/z", fontsize=fs)
        axes[1].set_ylabel("Relative intensity", fontsize=fs)
        axes[1].legend(fontsize=fs - 1)
        axes[1].tick_params(labelsize=fs - 1)

        if rga.sample_name:
            axes[0].set_title(rga.sample_name, fontsize=fs)

        if standalone:
            fig.tight_layout()
            fig.show()

        return axes


def plot_tey(rga, ax=None, **kwargs):
    """
    TEY signal vs time, with shutter state shaded.

    Parameters
    ----------
    rga : RGAMeasurement
    ax : matplotlib Axes, optional
    **kwargs
        Forwarded to ax.plot for the TEY trace.
    """
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(14 * cm, 5 * cm))

    ax.plot(rga.tey_time, rga.tey_signal * 1e9, color="steelblue",
            lw=1, **kwargs)

    # shade beam-on intervals
    shutter = rga.shutter.astype(bool)
    edges   = np.diff(shutter.astype(int), prepend=0, append=0)
    starts  = np.where(edges == 1)[0]
    ends    = np.where(edges == -1)[0]
    for s, e in zip(starts, ends):
        ax.axvspan(rga.tey_time[s], rga.tey_time[min(e, len(rga.tey_time) - 1)],
                   alpha=0.15, color="gold", lw=0,
                   label="beam on" if s == starts[0] else "")

    ax.set_xlabel("Time [s]", fontsize=fs)
    ax.set_ylabel("TEY [nA]", fontsize=fs)
    ax.tick_params(labelsize=fs - 1)
    if shutter.any():
        ax.legend(fontsize=fs - 1)

    if standalone:
        ax.get_figure().tight_layout()
        ax.get_figure().show()

    return ax
