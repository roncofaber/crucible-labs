#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import timedelta
from .specs import FieldSpec, RowSpec


def build_table(samples, rows=None, fields=None, include_ancestors=False):
    """
    Build a pandas DataFrame from a SampleCollection with configurable row
    granularity and field extraction.

    Parameters
    ----------
    samples : SampleCollection
        The collection to build the table from.
    rows : RowSpec, optional
        Defines what constitutes a row and any filters to apply.
        Defaults to ``RowSpec("sample")`` — one row per sample.
    fields : dict, optional
        Mapping of label → :class:`FieldSpec` (or plain list of key strings,
        normalised to ``FieldSpec(*keys)``).

        The label is used as the mtype filter when ``kind="dataset"``;
        for ``kind="sample"`` and ``kind="attribute"`` it is just a grouping
        name.

        ``kind="dataset"`` (default): extract keys from dataset
        ``scientific_metadata``; multiple hits across the ancestor chain get a
        numeric suffix.
        ``kind="sample"``: extract keys from ``sample.scientific_metadata``;
        first matching source wins.
        ``kind="attribute"``: call ``getattr(sample, key)``; first matching
        source wins.

    include_ancestors : bool
        If True, walk ancestor samples when extracting fields.

    Returns
    -------
    pd.DataFrame
        Indexed by ``sample_name`` (kind="sample") or
        ``dataset_name`` (kind="dataset").
    """
    import pandas as pd

    row_spec = rows if rows is not None else RowSpec("sample")

    # ------------------------------------------------------------------
    # Low-level extractors
    # ------------------------------------------------------------------

    def _get_nested(d, dotted_key):
        for part in dotted_key.split("."):
            if not isinstance(d, dict):
                return None
            d = d.get(part)
        return d

    def _extract_dataset_mtype(source, mtype, keys):
        """Youngest matching dataset on source; returns {} if none found."""
        matches = [d for d in source.datasets if d.dtype == mtype]
        if not matches:
            return {}
        sm = sorted(
            matches,
            key=lambda d: d.age if d.age is not None else timedelta.max
        )[0].scientific_metadata
        if not sm:
            return {}
        return {key.split(".")[-1]: _get_nested(sm, key) for key in keys}

    def _extract_sample_meta(source, keys):
        """Keys from source.scientific_metadata; returns {} if absent."""
        sm = getattr(source, "scientific_metadata", None)
        if not sm:
            return {}
        return {key.split(".")[-1]: _get_nested(sm, key) for key in keys}

    def _extract_attribute(source, keys):
        """getattr for each key on source."""
        return {key: getattr(source, key, None) for key in keys}

    # ------------------------------------------------------------------
    # Field collection
    # ------------------------------------------------------------------

    def _collect_fields(sample, specs, include_ancestors):
        """Walk sample (and optionally ancestors), extract all specs."""
        sources = [sample] + (list(sample.ancestors) if include_ancestors else [])
        result  = {}

        for label, spec in specs.items():
            filtered = [
                s for s in sources
                if spec.sample_type is None or s.sample_type == spec.sample_type
            ]

            if spec.kind == "dataset":
                mtype = spec.type or label
                # aggregate all hits; multiple → numeric suffix
                hits = [
                    data for s in filtered
                    for data in [_extract_dataset_mtype(s, mtype, spec.keys)]
                    if data
                ]
                if len(hits) == 1:
                    result.update(hits[0])
                elif len(hits) > 1:
                    for idx, data in enumerate(hits, 1):
                        result.update({f"{k}_{idx}": v for k, v in data.items()})

            elif spec.kind == "sample":
                # first matching source wins
                for source in filtered:
                    data = _extract_sample_meta(source, spec.keys)
                    if data:
                        result.update(data)
                        break

            elif spec.kind == "attribute":
                # first matching source wins
                for source in filtered:
                    result.update(_extract_attribute(source, spec.keys))
                    break

        return result

    # ------------------------------------------------------------------
    # Normalise fields: plain list → FieldSpec(kind="dataset")
    # ------------------------------------------------------------------

    specs = {
        label: (v if isinstance(v, FieldSpec) else FieldSpec(*v))
        for label, v in (fields or {}).items()
    }

    # ------------------------------------------------------------------
    # Build rows
    # ------------------------------------------------------------------

    result_rows = []

    if row_spec.kind == "sample":
        items = list(samples)
        if row_spec.sample_type:
            items = [s for s in items if s.sample_type == row_spec.sample_type]

        for sample in items:
            row = {"sample_name": sample.name}
            row.update(_collect_fields(sample, specs, include_ancestors))
            result_rows.append(row)

        df = pd.DataFrame(result_rows)
        if not df.empty:
            df = df.set_index("sample_name")

    else:  # kind == "dataset"
        # The row dataset's own mtype (kind="dataset") is extracted directly
        # from that dataset; all other specs go through the sample+ancestor chain.
        # Find the spec whose resolved mtype matches the row mtype
        row_dataset_spec = None
        row_label = next(
            (label for label, spec in specs.items()
             if spec.kind == "dataset" and (spec.type or label) == row_spec.mtype),
            None,
        )
        if row_label is not None:
            row_dataset_spec = specs.pop(row_label)
        remaining_specs = specs

        seen = set()
        for sample in samples:
            if row_spec.sample_type and sample.sample_type != row_spec.sample_type:
                continue
            for dataset in sample.datasets:
                if dataset.unique_id in seen:
                    continue
                if dataset.dtype != row_spec.mtype:
                    continue
                if row_spec.session and dataset.session != row_spec.session:
                    continue
                if row_spec.instrument and dataset.instrument != row_spec.instrument:
                    continue
                seen.add(dataset.unique_id)

                row     = {"dataset_name": dataset.name}
                primary = dataset.samples[0] if dataset.samples else None

                # Fields from the row dataset itself
                if row_dataset_spec:
                    sm = dataset.scientific_metadata
                    if sm:
                        row.update({
                            key.split(".")[-1]: _get_nested(sm, key)
                            for key in row_dataset_spec.keys
                        })

                # Remaining specs via sample + ancestor chain
                if primary:
                    row.update(_collect_fields(primary, remaining_specs, include_ancestors))

                result_rows.append(row)

        df = pd.DataFrame(result_rows)
        if not df.empty:
            df = df.set_index("dataset_name")

    return df
