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


def _build_nx_graph(resources):
    """Build a raw nx.DiGraph from an iterable of Sample/Dataset objects."""
    G = nx.DiGraph()
    resources = list(resources)
    for r in resources:
        G.add_node(r, name=r.name, type=r.kind, mfid=r.mfid)
    for r in resources:
        for parent in r.parents:
            G.add_edge(parent, r)
    logger.info(f"Built project graph with {G.number_of_nodes()} nodes "
                f"and {G.number_of_edges()} edges")
    return G


class Graph:
    """Genealogy graph wrapping a networkx DiGraph.

    Provides query methods (ancestors, descendants, siblings, common_ancestors)
    and plot methods directly on the object. Unknown attribute access is
    proxied to the underlying nx.DiGraph so networkx idioms still work.

    Parameters
    ----------
    resources : iterable
        Sample and/or Dataset objects with .name, .unique_id, .kind, .parents.
    """

    def __init__(self, resources):
        resources = list(resources)
        self._nx = _build_nx_graph(resources)
        self._by_name = {r.name:      r for r in resources}
        self._by_id   = {r.unique_id: r for r in resources}

    # ------------------------------------------------------------------
    # Node resolution
    # ------------------------------------------------------------------

    def resolve(self, node):
        """Return the node object for a string name/id, or return node as-is."""
        if isinstance(node, str):
            return self._by_name.get(node) or self._by_id.get(node)
        return node

    # ------------------------------------------------------------------
    # Raw networkx access
    # ------------------------------------------------------------------

    @property
    def nx(self):
        """The underlying networkx DiGraph."""
        return self._nx

    # ------------------------------------------------------------------
    # Collection protocol (proxy to nx)
    # ------------------------------------------------------------------

    def __contains__(self, node):
        return node in self._nx

    def __len__(self):
        return len(self._nx)

    def __iter__(self):
        return iter(self._nx)

    def __getattr__(self, name):
        if name == "_nx":
            raise AttributeError("_nx not initialized")
        return getattr(self._nx, name)

    def __repr__(self):
        return (f"Graph({self._nx.number_of_nodes()} nodes, "
                f"{self._nx.number_of_edges()} edges)")

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def ancestors(self, node):
        """Return all ancestor nodes of *node*."""
        node = self.resolve(node)
        if node is None or node not in self._nx:
            return []
        return list(nx.ancestors(self._nx, node))

    def descendants(self, node):
        """Return all descendant nodes of *node*."""
        node = self.resolve(node)
        if node is None or node not in self._nx:
            return []
        return list(nx.descendants(self._nx, node))

    def common_ancestors(self, node1, node2):
        """Return nodes that are ancestors of both *node1* and *node2*."""
        node1, node2 = self.resolve(node1), self.resolve(node2)
        if node1 is None or node2 is None:
            return []
        if node1 not in self._nx or node2 not in self._nx:
            return []
        return list(nx.ancestors(self._nx, node1) & nx.ancestors(self._nx, node2))

    def siblings(self, node):
        """Return nodes that share at least one parent with *node*."""
        node = self.resolve(node)
        if node is None or node not in self._nx:
            return []
        parents = list(self._nx.predecessors(node))
        result = set()
        for parent in parents:
            result.update(self._nx.successors(parent))
        result.discard(node)
        return list(result)

    # ------------------------------------------------------------------
    # Visualization methods
    # ------------------------------------------------------------------

    def plot(self, **kwargs):
        """Plot the full graph."""
        from clabs.graph.visualization import plot_full_graph
        return plot_full_graph(self, **kwargs)

    def plot_neighbors(self, node, **kwargs):
        """Plot direct neighbors (parents + children) of *node*."""
        from clabs.graph.visualization import plot_direct_neighbors
        return plot_direct_neighbors(self, self.resolve(node), **kwargs)

    def plot_ancestors(self, node, **kwargs):
        """Plot all ancestors of *node*."""
        from clabs.graph.visualization import plot_ancestors
        return plot_ancestors(self, self.resolve(node), **kwargs)

    def plot_descendants(self, node, **kwargs):
        """Plot all descendants of *node*."""
        from clabs.graph.visualization import plot_descendants
        return plot_descendants(self, self.resolve(node), **kwargs)

    def plot_connected_component(self, node, **kwargs):
        """Plot the full lineage tree (ancestors + descendants) of *node*."""
        from clabs.graph.visualization import plot_connected_component
        return plot_connected_component(self, self.resolve(node), **kwargs)

    def plot_extended_family(self, node, **kwargs):
        """Plot the weakly connected component containing *node*."""
        from clabs.graph.visualization import plot_extended_family
        return plot_extended_family(self, self.resolve(node), **kwargs)


# ---------------------------------------------------------------------------
# Convenience free functions (take a Graph object)
# ---------------------------------------------------------------------------

def ancestors(graph, node):
    """Return all ancestor nodes of *node* in *graph*."""
    return graph.ancestors(node)


def descendants(graph, node):
    """Return all descendant nodes of *node* in *graph*."""
    return graph.descendants(node)


def common_ancestors(graph, node1, node2):
    """Return nodes that are ancestors of both *node1* and *node2*."""
    return graph.common_ancestors(node1, node2)


def siblings(graph, node):
    """Return nodes that share at least one parent with *node*."""
    return graph.siblings(node)


# kept for backwards-compat / internal use
build_project_graph = Graph
