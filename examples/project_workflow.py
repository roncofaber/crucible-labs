#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CrucibleProject Workflow Example

Demonstrates how to use the CrucibleProject class to work with the entire
project, including genealogy tracking, sample type filtering, and graph
visualization.

Created on Thu Feb 6 2026
@author: roncofaber
"""

import tksamples
tksamples.setup_logging(level=100)  # Suppress most logging
from tksamples.project import CrucibleProject

#%% Load the entire project

project_id = "10k_perovskites"
proj = CrucibleProject(project_id)

print(f"Loaded project with {proj.nsamples} samples")
print(f"Sample types in project: {proj.sample_types}")

#%% Get samples by type

# Get all thin films as a Samples collection (enables measurement loading)
thin_films = proj.get_samples_collection("thin film")
print(f"Found {thin_films.nsamples} thin films")

# Get precursor solutions
precursor_solutions = proj.get_samples_collection('precursor solution')
print(f"Found {precursor_solutions.nsamples} precursor solutions")

#%% Load measurements for thin films

# Now you can use all the Samples methods on the filtered collection
thin_films.get_uvvis_data()
thin_films.get_well_images()

#%% Work with individual samples

# Access samples by index
tf = thin_films[0]
print(f"Sample: {tf.sample_name}")

# Or by name/ID from the project
tf = proj["TF000001"]  # by name
# tf = proj[sample_unique_id]  # or by ID

#%% Explore genealogy - direct relationships

# Get direct parents and children
print(f"Direct parents: {[p.sample_name for p in tf.parents]}")
print(f"Direct children: {[c.sample_name for c in tf.children]}")

# Get all ancestors (recursive)
ancestors = tf.get_all_ancestors()
print(f"Total ancestors: {len(ancestors)}")

#%% Explore genealogy - graph-based queries

# Get all ancestors using the project graph (more efficient for complex queries)
ancestors = proj.get_ancestors(tf)
print(f"Ancestors from graph: {len(ancestors)}")

# Get all descendants
descendants = proj.get_descendants(tf)
print(f"Descendants: {len(descendants)}")

# Get siblings (samples sharing parents)
siblings = proj.get_siblings(tf)
print(f"Siblings: {len(siblings)}")

# Find common ancestors between two samples
tf2 = proj["TF000002"]
common = proj.get_common_ancestors(tf, tf2)
print(f"Common ancestors: {len(common)}")

#%% Visualize genealogy

from tksamples.graph import (
    plot_direct_neighbors,
    plot_ancestors,
    plot_descendants,
    plot_connected_component,
    plot_extended_family,
    plot_full_graph
)

# Plot just direct relationships (parents and children)
fig, ax = plot_direct_neighbors(proj, tf)

# Plot all ancestors
fig, ax = plot_ancestors(proj, tf)

# Plot all descendants
fig, ax = plot_descendants(proj, tf)

# Plot complete lineage (ancestors + descendants)
fig, ax = plot_connected_component(proj, tf)

# Plot extended family (siblings, cousins, etc. - everything connected)
fig, ax = plot_extended_family(proj, tf)

# Plot the entire project graph
fig, ax = plot_full_graph(proj)

#%% Save a plot

fig, ax = plot_extended_family(proj, tf)
fig.savefig('sample_extended_family.png', dpi=300, bbox_inches='tight')
