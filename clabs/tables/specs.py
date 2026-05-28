#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class FieldSpec:
    """
    Specification for a field group to extract in build_table().

    Parameters
    ----------
    *keys : str
        Keys to extract. Column name is the leaf key.
        Dot notation supported for nested dict access when
        ``kind`` is ``"dataset"`` or ``"sample"``
        (e.g. ``"composition.Pb"`` → column ``"Pb"``).
    kind : str
        Where to look for the keys:

        * ``"dataset"`` *(default)* — dataset ``scientific_metadata`` dict.
          The dataset mtype filter is taken from ``type`` if given, otherwise
          falls back to the label (dict key) in the ``fields`` mapping.
          Multiple hits across the ancestor chain get a numeric suffix
          (``value_1``, ``value_2``, …).
        * ``"sample"`` — ``sample.scientific_metadata`` dict. First
          matching source wins; no suffix produced.
        * ``"attribute"`` — plain Python attribute on the sample object
          (e.g. ``"sample_type"``, ``"unique_id"``). First matching
          source wins; no suffix produced.

    type : str, optional
        ``kind="dataset"`` only. Explicit dataset mtype to filter on.
        When provided, the dict key in ``fields`` is treated as a pure label,
        allowing two specs with the same underlying mtype or avoiding
        collisions when a mtype shares a name with a ``kind="sample"`` group.
    sample_type : str, optional
        If given, restrict the lookup to sources whose ``sample_type``
        matches this string. Useful for targeting a specific level of the
        genealogy (e.g. ``"precursor solution"``).

    Examples
    --------
    >>> from clabs.tables import FieldSpec as F, RowSpec as R
    >>> df = project.to_dataframe(
    ...     rows=R("sample", sample_type="thin film"),
    ...     fields={
    ...         "spin_run":   F("spin_speed", "annealing_duration"),
    ...         "precursor":  F("target_stoichiometry", kind="dataset",
    ...                         sample_type="precursor solution"),
    ...         "comp_ds":    F("Pb", kind="dataset", type="composition"),
    ...         "comp_sm":    F("Pb", kind="sample"),
    ...         "anc_meta":   F("solvent", kind="sample",
    ...                         sample_type="stock solution"),
    ...         "attrs":      F("sample_type", "unique_id", kind="attribute"),
    ...         "anc_attr":   F("description", kind="attribute",
    ...                         sample_type="precursor solution"),
    ...     },
    ...     include_ancestors=True,
    ... )
    """

    _KINDS = ("dataset", "sample", "attribute")

    def __init__(self, *keys, kind="dataset", type=None, sample_type=None):
        if kind not in self._KINDS:
            raise ValueError(
                f"kind must be one of {self._KINDS}, got {kind!r}"
            )
        self.keys        = list(keys)
        self.kind        = kind
        self.type        = type        # explicit mtype override (kind="dataset" only)
        self.sample_type = sample_type

    def __repr__(self):
        parts = [repr(k) for k in self.keys]
        if self.kind != "dataset":
            parts.append(f"kind={self.kind!r}")
        if self.type is not None:
            parts.append(f"type={self.type!r}")
        if self.sample_type is not None:
            parts.append(f"sample_type={self.sample_type!r}")
        return f"FieldSpec({', '.join(parts)})"


class RowSpec:
    """
    Specification for what constitutes a row in build_table().

    Parameters
    ----------
    kind : str
        ``"sample"`` — one row per sample.
        ``"dataset"`` — one row per dataset of the given *mtype*.
    mtype : str, optional
        Required when ``kind="dataset"``. The measurement type that defines rows.
    sample_type : str, optional
        Filter rows to samples whose ``sample_type`` matches this string.
    session : str, optional
        ``kind="dataset"`` only. Restrict to datasets in this session.
    instrument : str, optional
        ``kind="dataset"`` only. Restrict to datasets from this instrument.

    Examples
    --------
    >>> from clabs.tables import RowSpec as R, FieldSpec as F
    >>> # one row per thin-film sample
    >>> df = project.to_dataframe(rows=R("sample", sample_type="thin film"), fields={...})
    >>> # one row per spin_run dataset linked to a thin-film sample
    >>> df = project.to_dataframe(rows=R("dataset", "spin_run", sample_type="thin film"), fields={...})
    """

    def __init__(self, kind, mtype=None, *, sample_type=None, session=None, instrument=None):
        if kind not in ("sample", "dataset"):
            raise ValueError(f"kind must be 'sample' or 'dataset', got {kind!r}")
        if kind == "dataset" and mtype is None:
            raise ValueError("mtype is required when kind='dataset'")
        self.kind        = kind
        self.mtype       = mtype
        self.sample_type = sample_type
        self.session     = session
        self.instrument  = instrument

    def __repr__(self):
        parts = [repr(self.kind)]
        if self.mtype is not None:
            parts.append(repr(self.mtype))
        for attr in ("sample_type", "session", "instrument"):
            val = getattr(self, attr)
            if val is not None:
                parts.append(f"{attr}={val!r}")
        return f"RowSpec({', '.join(parts)})"
