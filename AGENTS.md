# Crucible Labs agent guide

## Scope

`crucible-labs` is the scientific analysis layer over `nano-crucible`. It materializes project resources and relationships, manages local analysis caches, parses measurement files, builds tables, and provides scientific plotting and export behavior.

Do not add authentication, HTTP transport, retries, pagination, API response normalization, server resource schemas, or file-transfer implementations here. Those belong to `nano-crucible` or the Crucible API. Do not modify companion repositories as part of a Labs change.

## Repository map

- `clabs/project.py`: Loads a project, its datasets and samples, and the project relationship graph.
- `clabs/core.py`: Shared resource identity, genealogy, links, QR codes, and direct resource graph access.
- `clabs/sample.py` and `clabs/dataset.py`: Labs domain objects, resource associations, cache selection, downloads, and measurement attachment.
- `clabs/collection.py`: Collection lookup, filtering, measurement aggregation, and table entry points.
- `clabs/graph/`: In-memory NetworkX graph queries and visualization.
- `clabs/measurements/`: Loader registration and UV-Vis, image, and RGA implementations.
- `clabs/tables/`: Row and field specifications plus DataFrame construction.
- `clabs/plot/`: Analysis plotting helpers.
- `examples/`: Live, credentialed workflows. They are not offline validation commands.
- `docs/architecture.md`: Component boundaries and data flow.
- `docs/nano-compatibility.md`: Current dependency policy and unresolved compatibility decisions.

## Public package surface

`clabs.__init__` exports `Sample`, `Dataset`, both collection types, table specifications and construction, measurement classes, selected Nano configuration helpers, and `setup_logging`. `CrucibleProject` is imported from `clabs.project`. Preserve these imports and documented behavior unless a compatibility change is intentional.

## Nano boundary

Use public `nano-crucible` operations for configuration, normalized records, project and graph reads, pagination, and downloads. Labs may convert Nano-normalized records into its own analysis objects, but it must not reproduce Nano transport or server models. `CrucibleProject` accepts an injected client and should retain that seam. Prefer extending that narrow injection pattern over introducing another HTTP client.

`Dataset.prefetch()` uses `client.datasets.download(..., no_record=True)` so Nano owns file transfer while Labs owns cache selection and parsing. Do not call private Nano methods.

## Architecture invariants

- `CrucibleProject` creates every dataset and sample before linking graph edges.
- Same-kind directed edges establish parent and child genealogy.
- Cross-kind edges establish bidirectional sample-dataset associations; their direction is not retained as genealogy.
- The project resource map is keyed by each resource's `unique_id`.
- Measurement loaders are registered by dataset measurement type and return one measurement, multiple measurements, or `None`.
- Measurement attachment uses the graph directly for an unambiguous one-to-one association and identifiers or names for multi-sample datasets.
- Tables extract fields from a selected sample, its linked datasets, and optionally its sample ancestors.

## Safe local workflow

Use an isolated environment when changing dependencies:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .
```

Safe checks that do not access Crucible data:

```bash
python -c "import clabs; import clabs.tables; from clabs.project import CrucibleProject"
python -m build --wheel --no-isolation
```

There is currently no repository test suite. Do not represent imports or wheel construction as behavioral validation.

## Side effects and safety

Constructing `CrucibleProject` performs live API reads for project, dataset, sample, metadata, and graph records. `load_measurements()`, `Sample.load_measurements()`, `Dataset.load()`, and `Dataset.prefetch()` may download files and write persistent cache data. Project measurement loading performs concurrent downloads. Plotting can create figures or output files, `open_in_browser()` launches a browser, and QR functions write terminal output.

Do not use live projects, credentials, network access, browser interaction, or large scientific downloads for ordinary validation. Use temporary directories and synthetic records if isolated checks are added later. Never commit credentials, signed URLs, sensitive scientific data, generated plots, or cache contents.

## Documentation and compatibility

Update documentation with behavior changes. Keep README content user-focused and internal behavior in `docs/`. Do not claim support for a Nano version range until compatibility evidence supports the bounds. Package versions come from `clabs.__version__`; update that value only as part of an intentional release. No changelog or automated release process is currently maintained.

There are no repository-local development skills. Add one only after a repeated workflow, such as measurement-loader development, is documented and supported by stable local validation.
