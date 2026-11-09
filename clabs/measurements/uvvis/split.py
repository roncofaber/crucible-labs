#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Split a multi-sample Nirvana UV-Vis HDF5 file into one file per sample.

Reads the source arrays directly, not through NirvanaUVVis, so exported data
is not shaped by that class's corrections or blank reduction.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import h5py
import numpy as np

from clabs.utils.auxiliary import atomic_path, number_to_well

logger = logging.getLogger(__name__)

_ROOT = "measurement/pollux_oospec_multipos_line_scan"
_POSITION = re.compile(r"pos_(\d+)_TF(\d+)$")


@dataclass
class SplitResult:
    written: dict = field(default_factory=dict)
    unmatched: list = field(default_factory=list)
    missing: list = field(default_factory=list)


def _normalize_name(digits):
    return "TF" + digits.zfill(6)


def _text(value):
    return value.decode() if isinstance(value, bytes) else value


def _stored_name(group):
    """Sample name stored in the position, normalized, or None."""
    stored = group.attrs.get("sample_name")
    if stored is None and "sample_name" in group:
        stored = group["sample_name"][()]
    stored = _text(stored)
    if not stored:
        return None
    match = re.fullmatch(r"TF(\d+)", str(stored))
    return _normalize_name(match.group(1)) if match else str(stored)


def _reference(positions, keyword, poskey):
    """Reference spectra: per-position in the new format, file-level groups in the old."""
    new_key = f"{keyword.lower()}_intensities"
    if new_key in positions[poskey]:
        return positions[poskey][new_key][()]
    for key in positions:
        if keyword in key:
            return positions[key]["spectral_data"][()]
    raise KeyError(f"No {keyword} reference in file")


def _read_position(group, poskey, positions, root, settings):
    new_format = "raw_intensities" in group
    raw = group["raw_intensities" if new_format else "spectral_data"][()]
    index = int(_POSITION.match(poskey).group(1))
    if new_format:
        attrs = dict(group.attrs)
        x_center, y_center = attrs["x_center"], attrs["y_center"]
        x_positions, y_positions = attrs["x_positions"], attrs["y_positions"]
        integration_time = attrs.get("integration_time")
        tray_name = attrs.get("tray_name")
        well = number_to_well(index)
    else:
        x_center = group["x_center"][()]
        y_center = group["y_center"][()]
        y_positions = group["y_positions"][()]
        x_positions = (group["x_positions"][()] if "x_positions" in group
                       else np.full(len(y_positions), x_center))
        integration_time = (root["spec_integration_time"][()]
                            if "spec_integration_time" in root
                            else settings.get("spec_integration_time"))
        tray_name = None
        well = number_to_well(index - 2)
    return dict(
        raw=raw,
        blank=_reference(positions, "Blank", poskey),
        dark=_reference(positions, "Dark", poskey),
        x_center=x_center, y_center=y_center,
        x_positions=x_positions, y_positions=y_positions,
        integration_time=integration_time, tray_name=tray_name, well=well,
    )


def _write_sample(path, name, mfid, data, wavelengths, settings, attrs):
    with atomic_path(path) as tmp:
        with h5py.File(tmp, "w") as out:
            out.create_dataset("wavelengths", data=wavelengths, compression="gzip")
            out.create_dataset("raw_intensities", data=data["raw"], compression="gzip")
            out.create_dataset("blank_intensities", data=data["blank"], compression="gzip")
            out.create_dataset("dark_intensities", data=data["dark"], compression="gzip")
            out.create_dataset("x_positions", data=data["x_positions"])
            out.create_dataset("y_positions", data=data["y_positions"])
            group = out.create_group("settings")
            for key, value in settings.items():
                if np.ndim(value) == 0:
                    group.attrs[key] = value
            out.attrs.update({
                "sample_name": name,
                "sample_mfid": mfid,
                "tray_well": data["well"],
                "x_center": data["x_center"],
                "y_center": data["y_center"],
            })
            if data["tray_name"] is not None:
                out.attrs["tray_name"] = data["tray_name"]
            if data["integration_time"] is not None:
                out.attrs["integration_time"] = data["integration_time"]
            out.attrs.update(attrs or {})


def split_uvvis_file(source, targets, linked_ids, attrs=None, overwrite=False):
    """Write one normalized HDF5 per selected sample from a multi-sample UV-Vis file.

    Parameters
    ----------
    source : path
        Source HDF5, in either the new or the old Nirvana layout.
    targets : mapping
        Sample name to output path, for the selected samples only.
    linked_ids : mapping
        Every sample name linked to this dataset, to its MFID. A position that
        does not resolve to one of these is reported in ``unmatched``, never
        written.
    attrs : mapping, optional
        Extra root attributes, such as provenance.
    overwrite : bool
        Replace outputs that already exist.

    Returns
    -------
    SplitResult
    """
    result = SplitResult()
    with h5py.File(source, "r") as f:
        root = f[_ROOT]
        positions = root["positions"]
        wavelengths = (root if "wavelengths" in root else f)["wavelengths"][()]
        settings_group = root if "settings" in root else f
        settings = dict(settings_group["settings"].attrs) if "settings" in settings_group else {}
        keys_by_name = {}
        for poskey in positions:
            match = _POSITION.match(poskey)
            if match:
                keys_by_name.setdefault(_normalize_name(match.group(2)), []).append(poskey)
        for poskey in positions:
            match = _POSITION.match(poskey)
            if match is None:
                if "Dark" not in poskey and "Blank" not in poskey:
                    result.unmatched.append(poskey)
                continue
            name = _normalize_name(match.group(2))
            group = positions[poskey]
            uuid = _text(group.attrs.get("sample_uuid")) or None
            stored = _stored_name(group)
            if (len(keys_by_name[name]) > 1
                    or name not in linked_ids
                    or (uuid is not None and uuid != linked_ids[name])
                    or (stored is not None and stored != name)):
                result.unmatched.append(poskey)
                continue
            if name not in targets:
                continue
            path = Path(targets[name])
            data = _read_position(group, poskey, positions, root, settings)
            if overwrite or not path.exists():
                _write_sample(path, name, linked_ids[name], data, wavelengths, settings, attrs)
            result.written[name] = {"path": str(path), "n_spots": len(data["raw"]),
                                    "tray_well": data["well"]}
    result.missing = [name for name in targets if name not in result.written]
    return result
