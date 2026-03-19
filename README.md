# crucible-labs

`clabs` is a Python interface for managing and analysing multimodal datasets stored in [Crucible](https://crucible.lbl.gov/). It handles sample/dataset graphs, measurement loading, and export workflows.

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

# load project — fetches all samples, datasets, and relationships
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

## Requirements

- Python ≥ 3.8
- [nano-crucible](https://github.com/MolecularFoundryCrucible/nano-crucible)

See `pyproject.toml` for full dependency list.

## License

MIT — see LICENSE file for details.
