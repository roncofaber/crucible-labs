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


def plot_imshow(rga, log=True, mz_range=None, ax=None, cmap="magma", **kwargs):
    """
    2-D image: m/z (x) vs time (y), color = partial pressure.

    Parameters
    ----------
    rga : RGAMeasurement
    log : bool
        Use log-scale color normalization (default True).
    mz_range : (int, int), optional
        Restrict m/z axis to [lo, hi].
    ax : matplotlib Axes, optional
        Axes to draw into; creates a new figure if None.
    cmap : str
        Colormap name.
    **kwargs
        Forwarded to pcolormesh.
    """
    mz      = rga.mz
    time    = rga.time
    pressure = rga.pressure  # (T, M)

    if mz_range is not None:
        mask    = (mz >= mz_range[0]) & (mz <= mz_range[1])
        mz      = mz[mask]
        pressure = pressure[:, mask]

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(14 * cm, 8 * cm))
    else:
        fig = ax.get_figure()

    norm = mcolors.LogNorm() if log else None

    # pcolormesh handles non-uniform axes correctly
    pcm = ax.pcolormesh(mz, time, pressure, cmap=cmap, norm=norm,
                        shading="auto", **kwargs)

    cbar = fig.colorbar(pcm, ax=ax, pad=0.02)
    cbar.set_label("Partial pressure [Torr]", fontsize=fs - 1)
    cbar.ax.tick_params(labelsize=fs - 2)

    ax.set_xlabel("m/z", fontsize=fs)
    ax.set_ylabel("Time [s]", fontsize=fs)
    ax.tick_params(labelsize=fs - 1)

    title = rga.sample_name or ""
    if title:
        ax.set_title(title, fontsize=fs)

    if standalone:
        fig.tight_layout()
        fig.show()

    return ax


def plot_spectrum(rga, t=None, ax=None, **kwargs):
    """
    Mass spectrum: pressure vs m/z.

    Parameters
    ----------
    rga : RGAMeasurement
    t : int or None
        Time index. None → time-averaged spectrum.
    ax : matplotlib Axes, optional
    **kwargs
        Forwarded to bar.
    """
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(14 * cm, 6 * cm))

    spectrum = rga.get_spectrum(t)
    label    = f"t={rga.time[t]:.0f} s" if t is not None else "time-averaged"

    ax.bar(rga.mz, spectrum, width=0.8, label=label, **kwargs)
    ax.set_yscale("log")
    ax.set_xlabel("m/z", fontsize=fs)
    ax.set_ylabel("Partial pressure [Torr]", fontsize=fs)
    ax.tick_params(labelsize=fs - 1)
    ax.legend(fontsize=fs - 1)

    if standalone:
        ax.get_figure().tight_layout()
        ax.get_figure().show()

    return ax


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
                   alpha=0.15, color="gold", lw=0, label="beam on" if s == starts[0] else "")

    ax.set_xlabel("Time [s]", fontsize=fs)
    ax.set_ylabel("TEY [nA]", fontsize=fs)
    ax.tick_params(labelsize=fs - 1)
    if shutter.any():
        ax.legend(fontsize=fs - 1)

    if standalone:
        ax.get_figure().tight_layout()
        ax.get_figure().show()

    return ax
