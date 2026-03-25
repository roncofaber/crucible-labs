#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Metadata + UV-Vis Summary Table

Demonstrates how to combine sample genealogy metadata with per-sample
UV-Vis inhomogeneity statistics into a single DataFrame.
"""

import numpy as np
import pandas as pd

from clabs import FieldSpec as F
from clabs.project import CrucibleProject


#%% Load project and filter thin films

proj = CrucibleProject("10k_perovskites")
tfilms = proj.samples.filter(sample_type="thin film")

#%% Load measurements

# proj.load_measurements("pollux_oospec_multipos_line_scan")
# proj.load_measurements("sample well image")

#%% Build metadata table from datasets and ancestor chain

fields = {
    "spin_run":                     ["precursor_solution_name", "heater_sv_temp"],
    "Precursor Solution synthesis": F("target_stoichiometry", "component_a_ss-id",
                                      "component_b_ss-id", "mixing_ratio",
                                      sample_type="precursor solution"),
    "Stock Solution synthesis":     F("solvent", sample_type="stock solution"),
}
df = tfilms.to_dataframe(fields=fields, include_ancestors=True)

#%% Compute per-sample UV-Vis inhomogeneity (exclude RGA sessions)

# rows = []
# for uvvis in tfilms.get_measurements(mtype="uvvis", exclude={"dataset.session": "RGA"}):
#     spots = list(range(1, uvvis.nspots - 1))
#     rows.append({
#         "sample_name":   uvvis.sample.name,
#         "inhomogeneity": np.mean(uvvis.get_inhomogeneity(spots=spots)),
#     })

# # Average across multiple measurements per sample
# uvvis_df = pd.DataFrame(rows).groupby("sample_name").mean()

# #%% Merge and compute per-precursor-solution average inhomogeneity

# full_df = df.join(uvvis_df)
# full_df["ps_avg_inhomogeneity"] = (
#     full_df.groupby("precursor_solution_name")["inhomogeneity"].transform("mean")
# )
