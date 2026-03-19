#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualization: Genealogy Graph Plotting

Functions for visualizing sample genealogy graphs with various layouts
and highlighting options.

Created on Tue Feb 4 2026
@author: roncofaber
"""

import logging
import networkx as nx
import matplotlib.pyplot as plt

# Set up logger for this module
logger = logging.getLogger(__name__)


def plot_direct_neighbors(project, sample, figsize=None, node_size=None,
                          font_size=None, highlight_color='#f39c12'):
    """
    Plot a sample with its direct parents and children only.

    Parameters
    ----------
    project : CrucibleProject
        Project containing the graph and samples
    sample : Sample or str
        Sample object or sample name/id
    figsize : tuple, optional
        Figure size (width, height) in inches
    node_size : int, optional
        Size of nodes in the plot
    font_size : int, optional
        Font size for node labels
    highlight_color : str, optional
        Color to highlight the target sample

    Returns
    -------
    fig, ax
        Matplotlib figure and axis objects
    """
    # Get Sample object if string was passed
    if isinstance(sample, str):
        sample = project.get_sample(sample_id=sample, sample_name=sample)
        if sample is None:
            logger.error(f"Sample '{sample}' not found")
            return None, None

    if sample not in project.graph:
        logger.warning(f"Sample {sample.sample_name} not in genealogy graph")
        return None, None

    # Get direct parents and children
    parents = list(project.graph.predecessors(sample))
    children = list(project.graph.successors(sample))

    # Create subgraph with target sample, parents, and children
    nodes_to_include = [sample] + parents + children
    subgraph = project.graph.subgraph(nodes_to_include).copy()

    # Auto-size figure and nodes based on number of nodes
    n_nodes = len(nodes_to_include)
    if figsize is None:
        figsize = _calculate_figsize(n_nodes)
    if node_size is None:
        node_size = _calculate_node_size(n_nodes)
    if font_size is None:
        font_size = _calculate_font_size(n_nodes)

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Use hierarchical layout
    pos = _hierarchical_layout(subgraph)

    # Color nodes
    sample_type_colors = _get_default_colors()
    node_colors = []
    for node in subgraph.nodes():
        if node == sample:
            node_colors.append(highlight_color)  # Highlight target
        else:
            sample_type = node.sample_type
            node_colors.append(sample_type_colors.get(sample_type, '#95a5a6'))

    # Draw the graph
    nx.draw_networkx_nodes(subgraph, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(subgraph, pos, edge_color='gray', arrows=True,
                           arrowsize=20, arrowstyle='->', width=2, ax=ax)

    # Add labels
    labels = {node: node.sample_name for node in subgraph.nodes()}
    nx.draw_networkx_labels(subgraph, pos, labels, font_size=font_size, ax=ax)

    ax.set_title(f"Direct Neighbors of {sample.sample_name}\n({len(parents)} parents, {len(children)} children)")
    ax.axis('off')
    plt.tight_layout()

    return fig, ax


def plot_ancestors(project, sample, figsize=None, node_size=None,
                   font_size=None, highlight_color='#f39c12'):
    """
    Plot all ancestors of a sample.

    Parameters
    ----------
    project : CrucibleProject
        Project containing the graph and samples
    sample : Sample or str
        Sample object or sample name/id
    figsize : tuple, optional
        Figure size (width, height) in inches
    node_size : int, optional
        Size of nodes in the plot
    font_size : int, optional
        Font size for node labels
    highlight_color : str, optional
        Color to highlight the target sample

    Returns
    -------
    fig, ax
        Matplotlib figure and axis objects
    """
    # Get Sample object if string was passed
    if isinstance(sample, str):
        sample = project.get_sample(sample_id=sample, sample_name=sample)
        if sample is None:
            logger.error(f"Sample '{sample}' not found")
            return None, None

    if sample not in project.graph:
        logger.warning(f"Sample {sample.sample_name} not in genealogy graph")
        return None, None

    # Get all ancestors
    ancestors = nx.ancestors(project.graph, sample)

    if not ancestors:
        logger.info(f"Sample {sample.sample_name} has no ancestors")
        return None, None

    # Create subgraph with target sample and all ancestors
    nodes_to_include = list(ancestors) + [sample]
    subgraph = project.graph.subgraph(nodes_to_include).copy()

    # Auto-size figure and nodes based on number of nodes
    n_nodes = len(nodes_to_include)
    if figsize is None:
        figsize = _calculate_figsize(n_nodes)
    if node_size is None:
        node_size = _calculate_node_size(n_nodes)
    if font_size is None:
        font_size = _calculate_font_size(n_nodes)

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Use hierarchical layout
    pos = _hierarchical_layout(subgraph)

    # Color nodes
    sample_type_colors = _get_default_colors()
    node_colors = []
    for node in subgraph.nodes():
        if node == sample:
            node_colors.append(highlight_color)  # Highlight target
        else:
            sample_type = node.sample_type
            node_colors.append(sample_type_colors.get(sample_type, '#95a5a6'))

    # Draw the graph
    nx.draw_networkx_nodes(subgraph, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(subgraph, pos, edge_color='gray', arrows=True,
                           arrowsize=15, arrowstyle='->', width=2, ax=ax)

    # Add labels
    labels = {node: node.sample_name for node in subgraph.nodes()}
    nx.draw_networkx_labels(subgraph, pos, labels, font_size=font_size, ax=ax)

    ax.set_title(f"Ancestors of {sample.sample_name} ({len(ancestors)} ancestors)")
    ax.axis('off')
    plt.tight_layout()

    return fig, ax


def plot_descendants(project, sample, figsize=None, node_size=None,
                     font_size=None, highlight_color='#f39c12'):
    """
    Plot all descendants of a sample.

    Parameters
    ----------
    project : CrucibleProject
        Project containing the graph and samples
    sample : Sample or str
        Sample object or sample name/id
    figsize : tuple, optional
        Figure size (width, height) in inches
    node_size : int, optional
        Size of nodes in the plot
    font_size : int, optional
        Font size for node labels
    highlight_color : str, optional
        Color to highlight the target sample

    Returns
    -------
    fig, ax
        Matplotlib figure and axis objects
    """
    # Get Sample object if string was passed
    if isinstance(sample, str):
        sample = project.get_sample(sample_id=sample, sample_name=sample)
        if sample is None:
            logger.error(f"Sample '{sample}' not found")
            return None, None

    if sample not in project.graph:
        logger.warning(f"Sample {sample.sample_name} not in genealogy graph")
        return None, None

    # Get all descendants
    descendants = nx.descendants(project.graph, sample)

    if not descendants:
        logger.info(f"Sample {sample.sample_name} has no descendants")
        return None, None

    # Create subgraph with target sample and all descendants
    nodes_to_include = [sample] + list(descendants)
    subgraph = project.graph.subgraph(nodes_to_include).copy()

    # Auto-size figure and nodes based on number of nodes
    n_nodes = len(nodes_to_include)
    if figsize is None:
        figsize = _calculate_figsize(n_nodes)
    if node_size is None:
        node_size = _calculate_node_size(n_nodes)
    if font_size is None:
        font_size = _calculate_font_size(n_nodes)

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Use hierarchical layout
    pos = _hierarchical_layout(subgraph)

    # Color nodes
    sample_type_colors = _get_default_colors()
    node_colors = []
    for node in subgraph.nodes():
        if node == sample:
            node_colors.append(highlight_color)  # Highlight target
        else:
            sample_type = node.sample_type
            node_colors.append(sample_type_colors.get(sample_type, '#95a5a6'))

    # Draw the graph
    nx.draw_networkx_nodes(subgraph, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(subgraph, pos, edge_color='gray', arrows=True,
                           arrowsize=15, arrowstyle='->', width=2, ax=ax)

    # Add labels
    labels = {node: node.sample_name for node in subgraph.nodes()}
    nx.draw_networkx_labels(subgraph, pos, labels, font_size=font_size, ax=ax)

    ax.set_title(f"Descendants of {sample.sample_name} ({len(descendants)} descendants)")
    ax.axis('off')
    plt.tight_layout()

    return fig, ax


def plot_connected_component(project, sample, figsize=None, node_size=None,
                             font_size=None, highlight_color='#f39c12'):
    """
    Plot all samples connected to the given sample (full lineage tree).

    Shows all ancestors and descendants - the entire connected component
    containing the sample.

    Parameters
    ----------
    project : CrucibleProject
        Project containing the graph and samples
    sample : Sample or str
        Sample object or sample name/id
    figsize : tuple, optional
        Figure size (width, height) in inches
    node_size : int, optional
        Size of nodes in the plot
    font_size : int, optional
        Font size for node labels
    highlight_color : str, optional
        Color to highlight the target sample

    Returns
    -------
    fig, ax
        Matplotlib figure and axis objects
    """
    # Get Sample object if string was passed
    if isinstance(sample, str):
        sample = project.get_sample(sample_id=sample, sample_name=sample)
        if sample is None:
            logger.error(f"Sample '{sample}' not found")
            return None, None

    if sample not in project.graph:
        logger.warning(f"Sample {sample.sample_name} not in genealogy graph")
        return None, None

    # Get all ancestors and descendants
    ancestors = nx.ancestors(project.graph, sample)
    descendants = nx.descendants(project.graph, sample)

    # Create subgraph with target sample, ancestors, and descendants
    nodes_to_include = list(ancestors) + [sample] + list(descendants)
    subgraph = project.graph.subgraph(nodes_to_include).copy()

    # Auto-size figure and nodes based on number of nodes
    n_nodes = len(nodes_to_include)
    if figsize is None:
        figsize = _calculate_figsize(n_nodes)
    if node_size is None:
        node_size = _calculate_node_size(n_nodes)
    if font_size is None:
        font_size = _calculate_font_size(n_nodes)

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Use hierarchical layout
    pos = _hierarchical_layout(subgraph)

    # Color nodes
    sample_type_colors = _get_default_colors()
    node_colors = []
    for node in subgraph.nodes():
        if node == sample:
            node_colors.append(highlight_color)  # Highlight target
        else:
            sample_type = node.sample_type
            node_colors.append(sample_type_colors.get(sample_type, '#95a5a6'))

    # Draw the graph
    nx.draw_networkx_nodes(subgraph, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(subgraph, pos, edge_color='gray', arrows=True,
                           arrowsize=15, arrowstyle='->', width=2, ax=ax)

    # Add labels
    labels = {node: node.sample_name for node in subgraph.nodes()}
    nx.draw_networkx_labels(subgraph, pos, labels, font_size=font_size, ax=ax)

    ax.set_title(f"Full Lineage Tree of {sample.sample_name}\n"
                f"({len(ancestors)} ancestors, {len(descendants)} descendants)")
    ax.axis('off')
    plt.tight_layout()

    return fig, ax


def plot_extended_family(project, sample, figsize=None, node_size=None,
                         font_size=None, highlight_color='#f39c12'):
    """
    Plot the extended family tree (weakly connected component).

    Shows all samples reachable from the given sample when ignoring edge
    direction. This includes ancestors, descendants, siblings, cousins, etc. -
    the entire extended family tree.

    Parameters
    ----------
    project : CrucibleProject
        Project containing the graph and samples
    sample : Sample or str
        Sample object or sample name/id
    figsize : tuple, optional
        Figure size (width, height) in inches
    node_size : int, optional
        Size of nodes in the plot
    font_size : int, optional
        Font size for node labels
    highlight_color : str, optional
        Color to highlight the target sample

    Returns
    -------
    fig, ax
        Matplotlib figure and axis objects

    Examples
    --------
    >>> # Plot sample with all siblings, cousins, ancestors, etc.
    >>> fig, ax = plot_extended_family(project, "TF0001")
    """
    # Get Sample object if string was passed
    if isinstance(sample, str):
        sample = project.get_sample(sample_id=sample, sample_name=sample)
        if sample is None:
            logger.error(f"Sample '{sample}' not found")
            return None, None

    if sample not in project.graph:
        logger.warning(f"Sample {sample.sample_name} not in genealogy graph")
        return None, None

    # Convert to undirected graph to find weakly connected component
    undirected = project.graph.to_undirected()

    # Get all nodes in the same connected component
    component_nodes = nx.node_connected_component(undirected, sample)

    # Create subgraph (using original directed graph)
    subgraph = project.graph.subgraph(component_nodes).copy()

    # Auto-size figure and nodes based on number of nodes
    n_nodes = len(component_nodes)
    if figsize is None:
        figsize = _calculate_figsize(n_nodes)
    if node_size is None:
        node_size = _calculate_node_size(n_nodes)
    if font_size is None:
        font_size = _calculate_font_size(n_nodes)

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Use hierarchical layout
    pos = _hierarchical_layout(subgraph)

    # Color nodes
    sample_type_colors = _get_default_colors()
    node_colors = []
    for node in subgraph.nodes():
        if node == sample:
            node_colors.append(highlight_color)  # Highlight target
        else:
            sample_type = node.sample_type
            node_colors.append(sample_type_colors.get(sample_type, '#95a5a6'))

    # Draw the graph
    nx.draw_networkx_nodes(subgraph, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(subgraph, pos, edge_color='gray', arrows=True,
                           arrowsize=15, arrowstyle='->', width=2, ax=ax)

    # Add labels
    labels = {node: node.sample_name for node in subgraph.nodes()}
    nx.draw_networkx_labels(subgraph, pos, labels, font_size=font_size, ax=ax)

    ax.set_title(f"Extended Family Tree of {sample.sample_name}\n"
                f"({len(component_nodes)-1} related samples)")
    ax.axis('off')
    plt.tight_layout()

    return fig, ax


def plot_full_graph(project, figsize=None, node_size=None, font_size=None,
                   layout='hierarchical', sample_type_colors=None):
    """
    Plot the complete genealogy graph for the project.

    Parameters
    ----------
    project : CrucibleProject
        Project containing the graph and samples
    figsize : tuple, optional
        Figure size (width, height) in inches (auto-sized if None)
    node_size : int, optional
        Size of nodes in the plot (auto-sized if None)
    font_size : int, optional
        Font size for node labels
    layout : str, optional
        Layout algorithm: 'hierarchical', 'spring', 'circular', 'kamada_kawai'
    sample_type_colors : dict, optional
        Dictionary mapping sample_type to color

    Returns
    -------
    fig, ax
        Matplotlib figure and axis objects
    """
    graph = project.graph

    # Auto-size figure and nodes based on number of nodes
    n_nodes = graph.number_of_nodes()
    if figsize is None:
        figsize = _calculate_figsize(n_nodes)
    if node_size is None:
        node_size = _calculate_node_size(n_nodes)
    if font_size is None:
        font_size = _calculate_font_size(n_nodes)

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Choose layout
    if layout == 'hierarchical':
        pos = _hierarchical_layout(graph)
    elif layout == 'spring':
        pos = nx.spring_layout(graph, seed=42)
    elif layout == 'circular':
        pos = nx.circular_layout(graph)
    elif layout == 'kamada_kawai':
        pos = nx.kamada_kawai_layout(graph)
    else:
        logger.warning(f"Unknown layout '{layout}', using spring layout")
        pos = nx.spring_layout(graph, seed=42)

    # Set node colors by sample type
    if sample_type_colors is None:
        sample_type_colors = _get_default_colors()

    node_colors = []
    for node in graph.nodes():
        sample_type = node.sample_type
        node_colors.append(sample_type_colors.get(sample_type, '#95a5a6'))  # Gray for unknown

    # Draw the graph
    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(graph, pos, edge_color='gray', arrows=True,
                           arrowsize=10, arrowstyle='->', ax=ax)

    # Add labels (sample names)
    labels = {node: node.sample_name for node in graph.nodes()}
    nx.draw_networkx_labels(graph, pos, labels, font_size=font_size, ax=ax)

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=color, label=stype)
                      for stype, color in sample_type_colors.items()
                      if stype in project.sample_types]
    ax.legend(handles=legend_elements, loc='upper right')

    ax.set_title(f"Full Genealogy Graph ({graph.number_of_nodes()} samples, {graph.number_of_edges()} edges)")
    ax.axis('off')
    plt.tight_layout()

    return fig, ax


def _calculate_figsize(n_nodes):
    """
    Calculate appropriate figure size based on number of nodes.

    Parameters
    ----------
    n_nodes : int
        Number of nodes in the graph

    Returns
    -------
    tuple
        (width, height) in inches
    """
    # Base size
    base_width = 10
    base_height = 6

    # Scale up for larger graphs
    if n_nodes <= 10:
        return (base_width, base_height)
    elif n_nodes <= 30:
        return (14, 10)
    elif n_nodes <= 50:
        return (18, 12)
    else:
        # Scale linearly for very large graphs
        scale = (n_nodes / 50) ** 0.7  # Sub-linear scaling
        return (int(18 * scale), int(12 * scale))


def _calculate_node_size(n_nodes):
    """
    Calculate appropriate node size based on number of nodes.

    Parameters
    ----------
    n_nodes : int
        Number of nodes in the graph

    Returns
    -------
    int
        Node size in points^2
    """
    # Larger nodes for small graphs, smaller for large graphs
    if n_nodes <= 10:
        return 1200
    elif n_nodes <= 30:
        return 800
    elif n_nodes <= 50:
        return 600
    elif n_nodes <= 100:
        return 400
    else:
        return 300


def _calculate_font_size(n_nodes):
    """
    Calculate appropriate font size based on number of nodes.

    Parameters
    ----------
    n_nodes : int
        Number of nodes in the graph

    Returns
    -------
    int
        Font size in points
    """
    # Larger fonts for small graphs, smaller for large graphs
    if n_nodes <= 10:
        return 10
    elif n_nodes <= 30:
        return 9
    elif n_nodes <= 50:
        return 8
    elif n_nodes <= 100:
        return 7
    else:
        return 6


def _get_default_colors():
    """Get default color scheme for sample types."""
    return {
        'thin film': '#3498db',      # Blue
        'precursor solution': '#2ecc71',  # Green
        'stock solution': '#e74c3c',      # Red
        'substrate': '#9b59b6',           # Purple
        'solution': '#f39c12',            # Orange
    }


def _hierarchical_layout(graph):
    """
    Create a hierarchical layout for a directed acyclic graph.

    Uses graphviz dot layout if available for better results, otherwise
    falls back to custom hierarchical positioning with improved spacing.

    Parameters
    ----------
    graph : networkx.DiGraph
        Directed graph

    Returns
    -------
    dict
        Dictionary mapping nodes to (x, y) positions
    """
    # Try to use graphviz for better hierarchical layout
    try:
        pos = nx.nx_agraph.graphviz_layout(graph, prog='dot')
        # Normalize positions to 0-1 range
        if pos:
            xs = [p[0] for p in pos.values()]
            ys = [p[1] for p in pos.values()]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)

            # Avoid division by zero
            x_range = x_max - x_min if x_max != x_min else 1
            y_range = y_max - y_min if y_max != y_min else 1

            pos = {node: ((x - x_min) / x_range, (y - y_min) / y_range)
                   for node, (x, y) in pos.items()}
            return pos
    except (ImportError, AttributeError):
        logger.debug("graphviz not available, using custom hierarchical layout")

    # Fallback: Custom hierarchical layout with improved spacing
    # Find all layers (using topological generations)
    layers = {}
    for node in nx.topological_sort(graph):
        # Get the maximum layer of all parents + 1
        parents = list(graph.predecessors(node))
        if not parents:
            layers[node] = 0  # Root node
        else:
            layers[node] = max(layers[p] for p in parents) + 1

    # Group nodes by layer
    layer_nodes = {}
    for node, layer in layers.items():
        if layer not in layer_nodes:
            layer_nodes[layer] = []
        layer_nodes[layer].append(node)

    # Position nodes with better spacing
    pos = {}
    max_layer = max(layer_nodes.keys()) if layer_nodes else 0

    # Calculate maximum width needed (based on widest layer)
    max_width = max(len(nodes) for nodes in layer_nodes.values()) if layer_nodes else 1

    for layer, nodes in layer_nodes.items():
        y = 1.0 - (layer / max(max_layer, 1))  # Invert so roots are at top
        n_nodes = len(nodes)

        # Sort nodes by their average parent position for better alignment
        sorted_nodes = _sort_nodes_by_parent_position(nodes, graph, pos)

        # Use wider spacing to reduce cramming
        # Center smaller layers
        if n_nodes == 1:
            positions = [0.5]
        else:
            # Calculate spacing based on number of nodes
            # Use padding on sides and distribute evenly
            padding = 0.1  # 10% padding on each side
            available_width = 1.0 - 2 * padding
            spacing = available_width / (n_nodes - 1) if n_nodes > 1 else 0
            positions = [padding + i * spacing for i in range(n_nodes)]

        for node, x in zip(sorted_nodes, positions):
            pos[node] = (x, y)

    return pos


def _sort_nodes_by_parent_position(nodes, graph, pos):
    """
    Sort nodes by their parent positions to reduce edge crossings.

    Parameters
    ----------
    nodes : list
        Nodes to sort
    graph : networkx.DiGraph
        Graph containing the nodes
    pos : dict
        Current positions of already-placed nodes

    Returns
    -------
    list
        Sorted nodes
    """
    def get_parent_avg_x(node):
        parents = list(graph.predecessors(node))
        if not parents:
            # No parents, sort by name
            return (0, node.sample_name)
        # Average x position of parents
        parent_xs = [pos[p][0] for p in parents if p in pos]
        if parent_xs:
            return (sum(parent_xs) / len(parent_xs), node.sample_name)
        else:
            return (0, node.sample_name)

    return sorted(nodes, key=get_parent_avg_x)
