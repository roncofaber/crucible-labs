#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Start

Minimal example to get started with clabs.
"""

from clabs import FieldSpec as F
from clabs.project import CrucibleProject

#%% Load project and filter by sample type

proj = CrucibleProject("10k_perovskites")

tfilms = proj.samples.filter(sample_type="thin film")
print(f"Found {tfilms.nsamples} thin films")

#%% Load measurements (downloaded and cached automatically)

proj.load_measurements("pollux_oospec_multipos_line_scan")
proj.load_measurements("sample well image")

#%% Build a metadata DataFrame with ancestor fields

fields = {
    "spin_run":                     ["precursor_solution_name", "heater_sv_temp"],
    "Precursor Solution synthesis": F("target_stoichiometry", "mixing_ratio",
                                      sample_type="precursor solution"),
    "Stock Solution synthesis":     F("solvent", sample_type="stock solution"),
}
df = tfilms.to_dataframe(fields=fields, include_ancestors=True)
print(df.head())

#%% Filter measurements with exclusion rules

uvvis = tfilms.get_measurements(mtype="uvvis", exclude={"dataset.session": "RGA"})
print(f"UV-Vis measurements: {len(uvvis)}")
