# clabs Examples

This directory contains example scripts demonstrating how to use the clabs package.

## 🚀 Start Here

### `quick_start.py` - Minimal Getting Started Code
**The fastest way to get started!**

Shows the absolute minimal code for both approaches:
- Simple: Load samples and measurements
- Full: Load project with genealogy

**Start here if**: You're new to the package.

## Detailed Examples

### 1. `samples_workflow.py` - Basic Sample Loading
**Use this when**: You want to work with samples of a specific type and load measurements.

Shows how to:
- Load samples of a specific type (e.g., thin films)
- Load measurements (UV-Vis, images)
- Access and iterate over samples
- Work with measurement data

**Best for**: Simple workflows focused on one sample type.

### 2. `project_workflow.py` - Project-Level Operations
**Use this when**: You need the full project with genealogy tracking.

Shows how to:
- Load the entire project
- Filter samples by type
- Explore genealogy relationships (parents, children, ancestors, descendants)
- Find siblings and common ancestors
- Visualize genealogy graphs
- Convert to Samples collections for measurement loading

**Best for**: Working with multiple sample types, exploring sample relationships, and genealogy visualization.

### 3. `visualize_all_samples.py` - Sample Grid Visualization
Shows how to:
- Load sample images
- Create a grid visualization of all samples
- Save high-resolution figures

**Best for**: Creating overview visualizations of sample collections.

## Deprecated Examples

### `main_workflow.py`
Kept for backwards compatibility. Use `samples_workflow.py` or `project_workflow.py` instead.

## When to Use What?

### Use `Samples` class when:
- ✓ You only need samples of one type
- ✓ You want to load measurements (UV-Vis, images, etc.)
- ✓ You don't need genealogy information
- ✓ Simple, focused workflow

### Use `CrucibleProject` class when:
- ✓ You need the entire project
- ✓ You want to explore sample relationships (genealogy)
- ✓ You need to work with multiple sample types
- ✓ You want graph visualization
- ✓ You need to find ancestors, descendants, siblings, etc.

### Example: Combined Workflow

```python
from clabs.project import CrucibleProject

# Load full project with genealogy
proj = CrucibleProject("10k_perovskites")

# Filter samples by type
thin_films = proj.samples.filter(sample_type="thin film")

# Load measurements
proj.load_measurements("pollux_oospec_multipos_line_scan")
proj.load_measurements("sample well image")

# Work with genealogy
sample = thin_films[0]
ancestors = proj.graph.ancestors(sample)

# Visualize
fig, ax = proj.graph.plot_extended_family(sample)
```

## Running the Examples

Each example is designed to be run cell-by-cell in an interactive Python environment (Jupyter, Spyder, VS Code, etc.).

Look for the `#%%` markers that separate cells/sections.

## More Information

See the main README.md in the package root for installation instructions and full API documentation.
