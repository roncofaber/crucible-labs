# crucible-labs

`clabs` is a Python analysis interface for multimodal datasets stored in [Crucible](https://crucible.lbl.gov/). It materializes project sample and dataset graphs, loads scientific measurements, builds analysis tables, and supports plotting and export workflows. Authentication, API transport, and file transfer are provided by [nano-crucible](https://github.com/MolecularFoundryCrucible/nano-crucible).

## Installation

```bash
git clone https://github.com/roncofaber/crucible-labs.git
cd crucible-labs
pip install -e .
```

## Configuration

API access is managed by [nano-crucible](https://github.com/MolecularFoundryCrucible/nano-crucible):

```bash
crucible config init   # interactive setup
```

Or set `CRUCIBLE_API_KEY` as an environment variable.

## Quick start

```python
import clabs
from clabs import FieldSpec as F
from clabs.project import CrucibleProject

# load project - fetches all samples, datasets, and relationships
proj = CrucibleProject("10k_perovskites")

# filter by sample type
tfilms = proj.samples.filter(sample_type="thin film")

# load measurements (downloaded and cached automatically)
proj.load_measurements("pollux_oospec_multipos_line_scan")

# build a dataframe with ancestor metadata
fields = {
    "spin_run":                     ["precursor_solution_name", "heater_sv_temp"],
    "Precursor Solution synthesis": F("target_stoichiometry", "mixing_ratio",
                                      sample_type="precursor solution"),
    "Stock Solution synthesis":     F("solvent", sample_type="stock solution"),
}
df = tfilms.to_dataframe(fields=fields, include_ancestors=True)

# filter measurements with exclusion rules
uvvis = tfilms.get_measurements(mtype="uvvis", exclude={"dataset.session": "RGA"})
```

## Image analysis

Loaded sample-well images expose perceptual color and spatial inhomogeneity methods directly on `TFImage`:

```python
proj.load_measurements("sample well image", samples=["TF000849"])
image = proj.get_sample(sample_name="TF000849").get_measurements(mtype="image")[0]

roi = image.get_roi()
metrics = image.get_inhomogeneity()
delta_e = metrics["delta_e_2000_median"]
hue_dispersion = metrics["hue_circular_dispersion"]
morphology = image.get_morphology_metrics()
spatial = image.get_spatial_metrics(grid=(8, 8))

fig, axes = image.plot_inhomogeneity()
fig, axes = image.plot_morphology()
```

The default region of interest is a centered square spanning 40% of the shorter image dimension. `get_inhomogeneity()` returns separate CIELAB lightness, chroma, circular hue, CIEDE2000, spatial-block, gradient, saturation, and image-QC metrics. `get_morphology_metrics()` describes robust local-color anomalies, connected-component shapes, edge density, high-pass lightness energy, and directional color differences. These unsupervised regions should not be interpreted as physical defects without validation. Use `get_color_maps()`, `get_morphology_maps()`, `get_anomaly_map()`, `get_spatial_metrics()`, and `get_histogram()` when pixel-level or grid-resolved outputs are needed.

## Requirements

- Python ≥ 3.8
- [nano-crucible](https://github.com/MolecularFoundryCrucible/nano-crucible)

See `pyproject.toml` for full dependency list.

## Documentation

- [Examples](examples/README.md)
- [Architecture](docs/architecture.md)
- [Nano compatibility policy](docs/nano-compatibility.md)
- [Agent and developer guidance](AGENTS.md)

Creating a `CrucibleProject` reads project data from the live Crucible API. Measurement loading can download files and populate the persistent Nano cache. The example scripts are live workflows and are not safe offline checks.

## License

MIT - see [LICENSE](LICENSE) for details.
