#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualization: Genealogy Graph Plotting

Functions for visualizing sample genealogy graphs with various layouts
and highlighting options.

All public functions accept a Graph object as first argument and an already-
resolved node object (not a string) as second argument. String resolution and
the convenience wrappers live on Graph.plot_*().

Created on Tue Feb 4 2026
@author: roncofaber
"""

import logging
import networkx as nx
import matplotlib.pyplot as plt

# Set up logger for this module
logger = logging.getLogger(__name__)


def plot_direct_neighbors(graph, node, figsize=None, node_size=None,
                          font_size=None, highlight_color='#f39c12'):
    """Plot a node with its direct parents and children only."""
    if node is None or node not in graph:
        logger.warning(f"Node not in graph")
        return None, None

    parents  = list(graph.predecessors(node))
    children = list(graph.successors(node))
    nodes_to_include = [node] + parents + children
    subgraph = graph.nx.subgraph(nodes_to_include).copy()

    n_nodes  = len(nodes_to_include)
    figsize  = figsize  or _calculate_figsize(n_nodes)
    node_size = node_size or _calculate_node_size(n_nodes)
    font_size = font_size or _calculate_font_size(n_nodes)

    fig, ax = plt.subplots(figsize=figsize)
    pos = _hierarchical_layout(subgraph)

    type_colors = _get_default_colors()
    node_colors = [highlight_color if n == node
                   else type_colors.get(n.dtype, '#95a5a6')
                   for n in subgraph.nodes()]

    nx.draw_networkx_nodes(subgraph, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(subgraph, pos, edge_color='gray', arrows=True,
                           arrowsize=20, arrowstyle='->', width=2, ax=ax)
    nx.draw_networkx_labels(subgraph, pos, {n: n.name for n in subgraph.nodes()},
                            font_size=font_size, ax=ax)

    ax.set_title(f"Direct Neighbors of {node.name}\n"
                 f"({len(parents)} parents, {len(children)} children)")
    ax.axis('off')
    plt.tight_layout()
    return fig, ax


def plot_ancestors(graph, node, figsize=None, node_size=None,
                   font_size=None, highlight_color='#f39c12'):
    """Plot all ancestors of *node*."""
    if node is None or node not in graph:
        logger.warning(f"Node not in graph")
        return None, None

    ancs = nx.ancestors(graph.nx, node)
    if not ancs:
        logger.info(f"{node.name} has no ancestors")
        return None, None

    nodes_to_include = list(ancs) + [node]
    subgraph = graph.nx.subgraph(nodes_to_include).copy()

    n_nodes   = len(nodes_to_include)
    figsize   = figsize   or _calculate_figsize(n_nodes)
    node_size = node_size or _calculate_node_size(n_nodes)
    font_size = font_size or _calculate_font_size(n_nodes)

    fig, ax = plt.subplots(figsize=figsize)
    pos = _hierarchical_layout(subgraph)

    type_colors = _get_default_colors()
    node_colors = [highlight_color if n == node
                   else type_colors.get(n.dtype, '#95a5a6')
                   for n in subgraph.nodes()]

    nx.draw_networkx_nodes(subgraph, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(subgraph, pos, edge_color='gray', arrows=True,
                           arrowsize=15, arrowstyle='->', width=2, ax=ax)
    nx.draw_networkx_labels(subgraph, pos, {n: n.name for n in subgraph.nodes()},
                            font_size=font_size, ax=ax)

    ax.set_title(f"Ancestors of {node.name} ({len(ancs)} ancestors)")
    ax.axis('off')
    plt.tight_layout()
    return fig, ax


def plot_descendants(graph, node, figsize=None, node_size=None,
                     font_size=None, highlight_color='#f39c12'):
    """Plot all descendants of *node*."""
    if node is None or node not in graph:
        logger.warning(f"Node not in graph")
        return None, None

    descs = nx.descendants(graph.nx, node)
    if not descs:
        logger.info(f"{node.name} has no descendants")
        return None, None

    nodes_to_include = [node] + list(descs)
    subgraph = graph.nx.subgraph(nodes_to_include).copy()

    n_nodes   = len(nodes_to_include)
    figsize   = figsize   or _calculate_figsize(n_nodes)
    node_size = node_size or _calculate_node_size(n_nodes)
    font_size = font_size or _calculate_font_size(n_nodes)

    fig, ax = plt.subplots(figsize=figsize)
    pos = _hierarchical_layout(subgraph)

    type_colors = _get_default_colors()
    node_colors = [highlight_color if n == node
                   else type_colors.get(n.dtype, '#95a5a6')
                   for n in subgraph.nodes()]

    nx.draw_networkx_nodes(subgraph, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(subgraph, pos, edge_color='gray', arrows=True,
                           arrowsize=15, arrowstyle='->', width=2, ax=ax)
    nx.draw_networkx_labels(subgraph, pos, {n: n.name for n in subgraph.nodes()},
                            font_size=font_size, ax=ax)

    ax.set_title(f"Descendants of {node.name} ({len(descs)} descendants)")
    ax.axis('off')
    plt.tight_layout()
    return fig, ax


def plot_connected_component(graph, node, figsize=None, node_size=None,
                             font_size=None, highlight_color='#f39c12'):
    """Plot the full lineage tree (all ancestors + descendants) of *node*."""
    if node is None or node not in graph:
        logger.warning(f"Node not in graph")
        return None, None

    ancs  = nx.ancestors(graph.nx, node)
    descs = nx.descendants(graph.nx, node)
    nodes_to_include = list(ancs) + [node] + list(descs)
    subgraph = graph.nx.subgraph(nodes_to_include).copy()

    n_nodes   = len(nodes_to_include)
    figsize   = figsize   or _calculate_figsize(n_nodes)
    node_size = node_size or _calculate_node_size(n_nodes)
    font_size = font_size or _calculate_font_size(n_nodes)

    fig, ax = plt.subplots(figsize=figsize)
    pos = _hierarchical_layout(subgraph)

    type_colors = _get_default_colors()
    node_colors = [highlight_color if n == node
                   else type_colors.get(n.dtype, '#95a5a6')
                   for n in subgraph.nodes()]

    nx.draw_networkx_nodes(subgraph, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(subgraph, pos, edge_color='gray', arrows=True,
                           arrowsize=15, arrowstyle='->', width=2, ax=ax)
    nx.draw_networkx_labels(subgraph, pos, {n: n.name for n in subgraph.nodes()},
                            font_size=font_size, ax=ax)

    ax.set_title(f"Full Lineage Tree of {node.name}\n"
                 f"({len(ancs)} ancestors, {len(descs)} descendants)")
    ax.axis('off')
    plt.tight_layout()
    return fig, ax


def plot_extended_family(graph, node, figsize=None, node_size=None,
                         font_size=None, highlight_color='#f39c12'):
    """Plot the extended family (weakly connected component) of *node*."""
    if node is None or node not in graph:
        logger.warning(f"Node not in graph")
        return None, None

    undirected = graph.nx.to_undirected()
    component_nodes = nx.node_connected_component(undirected, node)
    subgraph = graph.nx.subgraph(component_nodes).copy()

    n_nodes   = len(component_nodes)
    figsize   = figsize   or _calculate_figsize(n_nodes)
    node_size = node_size or _calculate_node_size(n_nodes)
    font_size = font_size or _calculate_font_size(n_nodes)

    fig, ax = plt.subplots(figsize=figsize)
    pos = _hierarchical_layout(subgraph)

    type_colors = _get_default_colors()
    node_colors = [highlight_color if n == node
                   else type_colors.get(n.dtype, '#95a5a6')
                   for n in subgraph.nodes()]

    nx.draw_networkx_nodes(subgraph, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(subgraph, pos, edge_color='gray', arrows=True,
                           arrowsize=15, arrowstyle='->', width=2, ax=ax)
    nx.draw_networkx_labels(subgraph, pos, {n: n.name for n in subgraph.nodes()},
                            font_size=font_size, ax=ax)

    ax.set_title(f"Extended Family Tree of {node.name}\n"
                 f"({len(component_nodes) - 1} related nodes)")
    ax.axis('off')
    plt.tight_layout()
    return fig, ax


def plot_full_graph(graph, figsize=None, node_size=None, font_size=None,
                    layout='hierarchical', node_type_colors=None):
    """Plot the complete genealogy graph."""
    n_nodes   = graph.nx.number_of_nodes()
    figsize   = figsize   or _calculate_figsize(n_nodes)
    node_size = node_size or _calculate_node_size(n_nodes)
    font_size = font_size or _calculate_font_size(n_nodes)

    fig, ax = plt.subplots(figsize=figsize)

    if layout == 'hierarchical':
        pos = _hierarchical_layout(graph.nx)
    elif layout == 'spring':
        pos = nx.spring_layout(graph.nx, seed=42)
    elif layout == 'circular':
        pos = nx.circular_layout(graph.nx)
    elif layout == 'kamada_kawai':
        pos = nx.kamada_kawai_layout(graph.nx)
    else:
        logger.warning(f"Unknown layout '{layout}', using spring layout")
        pos = nx.spring_layout(graph.nx, seed=42)

    if node_type_colors is None:
        node_type_colors = _get_default_colors()

    node_colors = [node_type_colors.get(n.dtype, '#95a5a6') for n in graph.nx.nodes()]

    nx.draw_networkx_nodes(graph.nx, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(graph.nx, pos, edge_color='gray', arrows=True,
                           arrowsize=10, arrowstyle='->', ax=ax)
    nx.draw_networkx_labels(graph.nx, pos, {n: n.name for n in graph.nx.nodes()},
                            font_size=font_size, ax=ax)

    from matplotlib.patches import Patch
    node_types = {n.dtype for n in graph.nx.nodes()}
    legend_elements = [Patch(facecolor=color, label=stype)
                       for stype, color in node_type_colors.items()
                       if stype in node_types]
    ax.legend(handles=legend_elements, loc='upper right')

    ax.set_title(f"Full Genealogy Graph ({n_nodes} nodes, "
                 f"{graph.nx.number_of_edges()} edges)")
    ax.axis('off')
    plt.tight_layout()
    return fig, ax


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _calculate_figsize(n_nodes):
    if n_nodes <= 10:  return (10, 6)
    if n_nodes <= 30:  return (14, 10)
    if n_nodes <= 50:  return (18, 12)
    scale = (n_nodes / 50) ** 0.7
    return (int(18 * scale), int(12 * scale))


def _calculate_node_size(n_nodes):
    if n_nodes <= 10:  return 1200
    if n_nodes <= 30:  return 800
    if n_nodes <= 50:  return 600
    if n_nodes <= 100: return 400
    return 300


def _calculate_font_size(n_nodes):
    if n_nodes <= 10:  return 10
    if n_nodes <= 30:  return 9
    if n_nodes <= 50:  return 8
    if n_nodes <= 100: return 7
    return 6


def _get_default_colors():
    return {
        'thin film':          '#3498db',
        'precursor solution': '#2ecc71',
        'stock solution':     '#e74c3c',
        'substrate':          '#9b59b6',
        'solution':           '#f39c12',
    }


def _hierarchical_layout(graph):
    """Hierarchical layout using graphviz dot if available, else custom BFS."""
    try:
        pos = nx.nx_agraph.graphviz_layout(graph, prog='dot')
        if pos:
            xs = [p[0] for p in pos.values()]
            ys = [p[1] for p in pos.values()]
            x_range = max(xs) - min(xs) or 1
            y_range = max(ys) - min(ys) or 1
            return {n: ((x - min(xs)) / x_range, (y - min(ys)) / y_range)
                    for n, (x, y) in pos.items()}
    except (ImportError, AttributeError):
        logger.debug("graphviz not available, using custom hierarchical layout")

    layers = {}
    for node in nx.topological_sort(graph):
        parents = list(graph.predecessors(node))
        layers[node] = 0 if not parents else max(layers[p] for p in parents) + 1

    layer_nodes = {}
    for node, layer in layers.items():
        layer_nodes.setdefault(layer, []).append(node)

    pos = {}
    max_layer = max(layer_nodes) if layer_nodes else 0

    for layer, nodes in layer_nodes.items():
        y = 1.0 - (layer / max(max_layer, 1))
        sorted_nodes = _sort_nodes_by_parent_position(nodes, graph, pos)
        n = len(sorted_nodes)
        if n == 1:
            positions = [0.5]
        else:
            padding = 0.1
            spacing = (1.0 - 2 * padding) / (n - 1)
            positions = [padding + i * spacing for i in range(n)]
        for node, x in zip(sorted_nodes, positions):
            pos[node] = (x, y)

    return pos


def _sort_nodes_by_parent_position(nodes, graph, pos):
    def avg_parent_x(node):
        parents = list(graph.predecessors(node))
        xs = [pos[p][0] for p in parents if p in pos]
        return (sum(xs) / len(xs) if xs else 0, node.name)
    return sorted(nodes, key=avg_parent_x)
