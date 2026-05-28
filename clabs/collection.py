#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CrucibleCollection, SampleCollection, DatasetCollection

CrucibleCollection is the shared base providing iteration, indexing, and
lookup by name/id. SampleCollection and DatasetCollection add type-specific
properties, filtering, and analysis methods.

Created on Thu Feb  6 2026
@author: roncofaber
"""

import logging
from crucible.config import get_client
from .tables import FieldSpec, RowSpec, build_table

logger = logging.getLogger(__name__)

#%%

#%%

class CrucibleCollection:
    """Base class for Sample and Dataset collections."""

    _itemtype  = "items"

    def __init__(self, items, project_id=None):
        self._project_id    = project_id
        self._items         = items if items is not None else []
        self._items_by_id   = {i.unique_id: i for i in self._items}
        self._items_by_name = {i.name:      i for i in self._items}

    @property
    def client(self):
        return get_client()

    @property
    def project_id(self):
        return self._project_id

    def _make_collection(self, items):
        raise NotImplementedError

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __contains__(self, item):
        return item in self._items

    def __getitem__(self, index):
        if isinstance(index, str):
            item = self._items_by_id.get(index) or self._items_by_name.get(index)
            if item is None:
                raise KeyError(f"'{index}' not found")
            return item
        if isinstance(index, slice):
            return self._make_collection(self._items[index])
        if isinstance(index, int):
            return self._items[index]
        raise TypeError(f"Index must be str, int, or slice, not {type(index).__name__}")

    def __repr__(self):
        return f"{self.__class__.__name__}({len(self._items)} {self._itemtype})"


#%%

class SampleCollection(CrucibleCollection):
    """
    Container for a collection of Sample objects.

    Provides iteration, indexing by position/name/ID, filtering, and
    ML-ready table export via to_dataframe().
    """

    _itemtype = "samples"

    def __init__(self, samples=None, project_id=None):
        super().__init__(samples or [], project_id)
        # named aliases used externally (e.g. project._build_resource_map)
        self._samples         = self._items
        self._samples_by_id   = self._items_by_id
        self._samples_by_name = self._items_by_name

    @property
    def samples(self):
        return self._items

    @property
    def nsamples(self):
        return len(self._items)

    @property
    def sample_types(self):
        """Unique sample types present in this collection."""
        return list({s.sample_type for s in self._items})

    @property
    def samples_datasets(self):
        """All unique Dataset objects linked to any sample in this collection."""
        seen   = set()
        result = []
        for sample in self._items:
            for dataset in sample.datasets:
                if dataset.unique_id not in seen:
                    seen.add(dataset.unique_id)
                    result.append(dataset)
        return DatasetCollection(datasets=result, project_id=self._project_id)

    def get_sample(self, sample_id=None, sample_name=None):
        """Get a sample by unique_id or sample_name. Returns None if not found."""
        if sample_id is not None:
            return self._items_by_id.get(sample_id)
        if sample_name is not None:
            return self._items_by_name.get(sample_name)
        logger.warning("get_sample called without sample_id or sample_name")
        return None

    def get_measurements(self, mtype=None, exclude=None, include=None):
        """Get measurements across all samples, with optional filtering.

        Parameters are forwarded to :meth:`Sample.get_measurements` — see
        that method for full documentation on ``exclude`` / ``include`` and
        attribute prefix rules.
        """
        return [m for s in self._items
                for m in s.get_measurements(mtype=mtype, exclude=exclude, include=include)]

    def filter(self, sample_type=None, name=None, has_measurement=None):
        """
        Return a new SampleCollection filtered by sample attributes.
        Multiple criteria are ANDed together.

        Parameters
        ----------
        sample_type : str, optional
            Exact match on sample_type.
        name : str, optional
            Case-insensitive substring match on sample_name.
        has_measurement : str, optional
            Keep only samples that have at least one measurement of this mtype.
        """
        result = self._items
        if sample_type is not None:
            result = [s for s in result if s.sample_type == sample_type]
        if name is not None:
            name_lower = name.lower()
            result = [s for s in result if name_lower in s.sample_name.lower()]
        if has_measurement is not None:
            result = [s for s in result if any(m.mtype == has_measurement for m in s.measurements)]
        return SampleCollection(samples=result, project_id=self._project_id)

    def to_dataframe(self, rows=None, fields=None, include_ancestors=False):
        """Build a DataFrame from this collection. See :func:`clabs.tables.build_table`."""
        return build_table(self, rows=rows, fields=fields,
                           include_ancestors=include_ancestors)

    def _make_collection(self, items):
        return SampleCollection(samples=items, project_id=self._project_id)


#%%

class DatasetCollection(CrucibleCollection):
    """
    Container for a collection of Dataset objects.

    Provides iteration, indexing by position/name/ID, and filtering by
    measurement type, instrument, or session.
    """

    _itemtype = "datasets"

    def __init__(self, datasets=None, project_id=None):
        super().__init__(datasets or [], project_id)
        # named aliases used externally (e.g. project._build_resource_map)
        self._datasets         = self._items
        self._datasets_by_id   = self._items_by_id
        self._datasets_by_name = self._items_by_name

    @property
    def datasets(self):
        return self._items

    @property
    def ndatasets(self):
        return len(self._items)

    @property
    def dataset_types(self):
        """Unique measurement types present in this collection."""
        return list({d.dtype for d in self._items})

    def get_dataset(self, dataset_id=None, dataset_name=None):
        """Get a dataset by unique_id or dataset_name. Returns None if not found."""
        if dataset_id is not None:
            return self._items_by_id.get(dataset_id)
        if dataset_name is not None:
            return self._items_by_name.get(dataset_name)
        logger.warning("get_dataset called without dataset_id or dataset_name")
        return None

    def filter(self, measurement=None, instrument=None, session=None):
        """
        Return a new DatasetCollection filtered by measurement type, instrument,
        or session name. Multiple criteria are ANDed together.
        """
        result = self._items
        if measurement is not None:
            result = [d for d in result if d.dtype == measurement]
        if instrument is not None:
            result = [d for d in result if d.instrument == instrument]
        if session is not None:
            result = [d for d in result if d.session == session]
        return DatasetCollection(datasets=result, project_id=self._project_id)

    def _make_collection(self, items):
        return DatasetCollection(datasets=items, project_id=self._project_id)
