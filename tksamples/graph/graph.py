#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Graph Utilities: Genealogy Graph Construction and Analysis

Functions for building and analyzing NetworkX graphs from sample genealogy data,
including graph construction, traversal, and relationship analysis.

Created on Tue Feb 4 2026
@author: roncofaber
"""

import networkx as nx
import logging

# Set up logger for this module
logger = logging.getLogger(__name__)


def build_project_graph(resources):
    """
    Build a directed genealogy graph from any mix of Sample and Dataset objects.

    Parameters
    ----------
    resources : iterable
        Sample and/or Dataset objects. Each must expose .name, .mfid,
        .kind, and .parents.

    Returns
    -------
    nx.DiGraph
        Nodes are resource objects; edges run from parent → child.
    """
    G = nx.DiGraph()

    resources = list(resources)

    for resource in resources:
        G.add_node(resource, name=resource.name, type=resource.kind,
                   mfid=resource.mfid)

    for resource in resources:
        for parent in resource.parents:
            G.add_edge(parent, resource)

    logger.info(f"Built project graph with {G.number_of_nodes()} nodes "
                f"and {G.number_of_edges()} edges")

    return G
