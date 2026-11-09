# Nano compatibility

## Current policy

`pyproject.toml` currently declares `nano-crucible` without a version bound. This reflects an unresolved compatibility policy, not a promise that every Nano release is supported.

Labs currently consumes these Nano contracts:

- Configuration through `get_client()`, `get_cache_dir()`, and selected public configuration helpers re-exported by `clabs`.
- Project, dataset, and sample normalized records.
- Nano `Project`, `Dataset`, and `Sample` model classes.
- Project, resource, and relationship graph reads.
- Dataset and sample listing with metadata and unbounded pagination.
- Dataset downloads through the public `datasets.download()` operation, including `no_record`, `overwrite_existing`, and `include` behavior.
- Dataset file records from `datasets.list_files()`, including `size` and `sha256_hash`, and `crucible.utils.io.storage_display_name()` for local file names.

## Version bounds

Do not add a lower or upper Nano bound based only on the version installed in one development environment. Choose bounds only after validating the consumed contracts against candidate Nano releases. Record the validated versions and the reason for both bounds in the same change.

Until that work is done, Nano upgrades require manual review of the contracts above plus a wheel import check. Live project access is not an ordinary compatibility check and should only be performed as an explicitly authorized integration workflow.

## Package lifecycle

The Labs version is defined by `clabs.__version__` and exposed through package metadata. Change it only for an intentional release. The repository does not currently maintain a changelog, compatibility matrix, automated release process, or formal deprecation window. Establish those policies before claiming a stable Nano compatibility range.
