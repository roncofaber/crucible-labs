# clabs examples

These scripts demonstrate live Crucible workflows. They require Nano configuration, API access, permission to read the example project, and enough local space for downloaded measurement files. Run them cell by cell in an interactive Python environment using the `#%%` markers.

## Inventory

- `quick_start.py`: Load a project, filter samples, load measurements, and build a metadata table.
- `project_workflow.py`: Explore project metadata, sample genealogy, and graph visualizations.
- `build_table.py`: Build tables from dataset fields and ancestor sample metadata.
- `visualize_all_samples.py`: Download well images and render a thin-film image grid.

All examples use the `10k_perovskites` project identifier. Replace it with a project you are authorized to access when appropriate.

Start with `quick_start.py`. See the root [README](../README.md) for installation and configuration, and [architecture documentation](../docs/architecture.md) for internal data flow.
