#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CrucibleProject Workflow

Demonstrates how to use CrucibleProject to work with the full project:
genealogy tracking, sample type filtering, and graph visualization.
"""

from clabs.project import CrucibleProject

#%% Load the entire project

proj = CrucibleProject("10k_perovskites")

print(f"Loaded project: {proj.title!r}")
print(f"Total samples: {len(proj.samples)}")
print(f"Sample types: {proj.samples.sample_types}")

#%% Filter by sample type

tfilms = proj.samples.filter(sample_type="thin film")
print(f"Found {tfilms.nsamples} thin films")

precursor_solutions = proj.samples.filter(sample_type="precursor solution")
print(f"Found {precursor_solutions.nsamples} precursor solutions")

#%% Load measurements

proj.load_measurements("pollux_oospec_multipos_line_scan")
proj.load_measurements("sample well image")

#%% Access individual samples

tf = tfilms[0]
print(f"Sample: {tf.sample_name}")
print(f"Measurements: {len(tf.measurements)}")

# By name or ID
tf = proj["TF000001"]

#%% Explore genealogy — direct relationships

print(f"Direct parents:  {[p.sample_name for p in tf.parents]}")
print(f"Direct children: {[c.sample_name for c in tf.children]}")
print(f"All ancestors:   {len(tf.ancestors)}")

#%% Explore genealogy — graph-based queries

ancestors   = proj.get_ancestors(tf)
descendants = proj.get_descendants(tf)
siblings    = proj.get_siblings(tf)
print(f"Ancestors: {len(ancestors)}, Descendants: {len(descendants)}, Siblings: {len(siblings)}")

tf2    = proj["TF000002"]
common = proj.get_common_ancestors(tf, tf2)
print(f"Common ancestors with TF000002: {len(common)}")

#%% Visualize genealogy

from clabs.graph import (
    plot_direct_neighbors,
    plot_ancestors,
    plot_descendants,
    plot_connected_component,
    plot_extended_family,
    plot_full_graph,
)

fig, ax = plot_direct_neighbors(proj, tf)
fig, ax = plot_ancestors(proj, tf)
fig, ax = plot_descendants(proj, tf)
fig, ax = plot_connected_component(proj, tf)
fig, ax = plot_extended_family(proj, tf)
fig, ax = plot_full_graph(proj)

#%% Save a plot

fig, ax = plot_extended_family(proj, tf)
fig.savefig("sample_extended_family.png", dpi=300, bbox_inches="tight")
