#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dataset: Base Class for All dataset Types

Provides the abstract Dataset class that serves as a foundation for
specific measurement implementations like UV-Vis spectroscopy, with common
properties for sample identification and metadata management.

Created on Fri Jan 16 18:22:21 2026
@author: roncofaber
"""

import logging

# internal modules
from clabs.core import CruxObj
from clabs.models import BaseDataset

# Set up logger for this module
logger = logging.getLogger(__name__)

#%%

class Dataset(CruxObj):

    _dtype   = "dataset"
    _loaders = {}   # mtype string → loader callable (registered at import time)

    def __init__(self, dst_dict=None):
        
        # store info using the pydantic model
        self._dataset = BaseDataset.model_validate(dst_dict)
        
        # initialize parent class
        super().__init__(
            creation_time = self._dataset.creation_time,
            unique_id     = self._dataset.unique_id,
            project_id    = self._dataset.project_id,
            owner_orcid   = self._dataset.owner_orcid,
            owner_user_id = self._dataset.owner_user_id,
            )
        
        # easy way to access metadata
        try:
            self._scientific_metadata = dst_dict.get("scientific_metadata")["scientific_metadata"]
        except (TypeError, KeyError):
            self._scientific_metadata = None
        
        # a dataset can be linked to multiple samples (e.g. a tray scan)
        self._samples         = []
        self._samples_by_name = {}
        self._samples_by_id   = {}

        # parent/child dataset relationships (dataset genealogy)
        self._parents  = []
        self._children = []

        # loaded measurement objects (populated by load())
        self._measurements = []

        # pre-downloaded file paths (populated by prefetch(), consumed by load())
        self._files = None

        return

    def add_sample(self, sample, _skip_reciprocal=False):
        """Link a Sample object to this dataset (bidirectional)."""
        if sample not in self._samples:
            self._samples.append(sample)
            self._samples_by_name[sample.name]      = sample
            self._samples_by_id[sample.unique_id]   = sample
            if not _skip_reciprocal:
                sample.add_dataset(self, _skip_reciprocal=True)

    def add_parent(self, parent_dataset, _skip_reciprocal=False):
        """Link a parent dataset (bidirectional)."""
        if parent_dataset not in self._parents:
            self._parents.append(parent_dataset)
            if not _skip_reciprocal:
                parent_dataset.add_child(self, _skip_reciprocal=True)

    def add_child(self, child_dataset, _skip_reciprocal=False):
        """Link a child dataset (bidirectional)."""
        if child_dataset not in self._children:
            self._children.append(child_dataset)
            if not _skip_reciprocal:
                child_dataset.add_parent(self, _skip_reciprocal=True)

    @property
    def parents(self):
        return self._parents

    @property
    def children(self):
        return self._children

    @property
    def measurement(self):
        """Loaded measurement. Returns a single object or a list for multi-spot datasets."""
        if len(self._measurements) == 0:
            return None
        if len(self._measurements) == 1:
            return self._measurements[0]
        return self._measurements

    @property
    def is_loaded(self):
        return len(self._measurements) > 0

    @classmethod
    def register_loader(cls, mtype, loader):
        """Register a loader callable for a given measurement type string."""
        cls._loaders[mtype] = loader

    def prefetch(self, client, cache_dir, overwrite_existing=False):
        """
        Download dataset files without parsing. Thread-safe: no shared state is touched.
        Call this in a thread pool before load() to overlap network I/O.
        """
        import os
        dataset_dir = os.path.join(cache_dir, self.unique_id)
        if os.path.isdir(dataset_dir) and os.listdir(dataset_dir) and not overwrite_existing:
            self._files = [os.path.join(dataset_dir, f) for f in os.listdir(dataset_dir)]
        else:
            self._files = client.datasets.download(
                self.unique_id,
                output_dir         = cache_dir,
                overwrite_existing = overwrite_existing,
            )

    def load(self, client, cache_dir, use_cache=True, overwrite_existing=False):
        """
        Download (if needed) and parse this dataset's data files.

        If prefetch() was called beforehand, uses those files directly.
        Otherwise falls back to downloading inline.
        """
        import os

        loader = self._loaders.get(self.dtype)
        if loader is None:
            raise NotImplementedError(f"No loader registered for dtype {self.dtype!r}")

        # use pre-fetched files if available, otherwise download now
        if self._files is not None:
            files = self._files
        else:
            dataset_dir = os.path.join(cache_dir, self.unique_id)
            if use_cache and not overwrite_existing and os.path.isdir(dataset_dir) and os.listdir(dataset_dir):
                files = [os.path.join(dataset_dir, f) for f in os.listdir(dataset_dir)]
            else:
                files = client.datasets.download(
                    self.unique_id,
                    output_dir         = cache_dir,
                    overwrite_existing = overwrite_existing,
                )

        if not files:
            logger.warning(f"No files downloaded for dataset {self.name!r}")
            return None

        result = loader(self, files)
        if result is None:
            return None

        measurements = result if isinstance(result, list) else [result]
        self._measurements = measurements

        # warn if measurement count doesn't match graph-linked sample count
        if len(measurements) != len(self._samples):
            logger.warning(
                f"Dataset {self.name!r} has {len(measurements)} measurements but "
                f"{len(self._samples)} linked samples."
            )

        # attach each measurement to its sample
        for m in measurements:
            if len(self._samples) == 1 and len(measurements) == 1:
                # unambiguous: trust the graph directly
                sample = self._samples[0]
            else:
                sample = (self._samples_by_id.get(getattr(m, "sample_mfid",   None))
                          or self._samples_by_name.get(getattr(m, "sample_name", None)))
                if sample is None:
                    logger.warning(
                        f"Measurement for {getattr(m, 'sample_name', None)!r} not in "
                        f"linked samples of dataset {self.name!r} --> skipping."
                    )
                    continue
            m.assign_sample(sample)

        return self.measurement

    @property
    def session(self):
        return self._dataset.session_name

    @property
    def instrument(self):
        return self._dataset.instrument_name

    @property
    def name(self):
        return self._dataset.dataset_name

    @property
    def samples(self):
        """All samples this dataset is linked to."""
        return self._samples
    
    @property
    def dtype(self):
        return self._dataset.measurement
    
    @property
    def scientific_metadata(self):
        return self._scientific_metadata
    
    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r})"
    
    # fallback: if attribute not found on Dataset, look in _dataset
    def __getattr__(self, name):
        if name == "_dataset":
            raise AttributeError("_dataset not initialized")
        try:
            return getattr(self._dataset, name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")