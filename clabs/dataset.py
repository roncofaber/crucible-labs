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
import os

import requests

# internal modules
from clabs.core import CruxObj
from clabs.export import DatasetFileError, ensure_dataset_files
from clabs.models import DatasetModel

# Set up logger for this module
logger = logging.getLogger(__name__)

#%%

class Dataset(CruxObj):

    _dtype   = "dataset"
    _loaders = {}   # mtype string → loader callable (registered at import time)

    def __init__(self, dst_dict=None):
        
        # store info using the pydantic model
        self._dataset = DatasetModel.model_validate(dst_dict)
        
        # initialize parent class
        super().__init__(
            timestamp         = self._dataset.timestamp,
            creation_time     = self._dataset.creation_time,
            modification_time = self._dataset.modification_time,
            unique_id         = self._dataset.unique_id,
            project_id        = self._dataset.project_id,
            owner_orcid       = self._dataset.owner_orcid,
        )
        
        # easy way to access metadata
        self._scientific_metadata = self._dataset.scientific_metadata
        
        # a dataset can be linked to multiple samples (e.g. a tray scan)
        self._samples         = []
        self._samples_by_name = {}
        self._samples_by_id   = {}

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

    @property
    def data(self):
        """Loaded measurement data. Returns a single object or a list for multi-spot datasets."""
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
        Call this in a thread pool before load() to overlap network I/O with parsing.
        """
        self._files = self._fetch(client, cache_dir, overwrite_existing=overwrite_existing)

    def _local_files(self, cache_dir):
        folder = os.path.join(cache_dir, self.unique_id)
        return [os.path.join(root, name) for root, _, names in os.walk(folder) for name in names]

    def _fetch(self, client, cache_dir, use_cache=True, overwrite_existing=False):
        """Paths of this dataset's current files, downloading what is missing or invalid.

        The dataset's file list decides what is current, because a re-uploaded
        file can leave its predecessor behind in the cache.
        """
        if use_cache and not overwrite_existing:
            try:
                files = ensure_dataset_files(client, self.unique_id, cache_dir, check_hash=False)
            except DatasetFileError as error:
                logger.warning(f"{self.name!r}: {error}")
                return []
            except requests.exceptions.RequestException as error:
                logger.warning(f"{self.name!r}: could not check files ({error}), using local copies")
                return self._local_files(cache_dir)
            return [str(f.path) for f in files]
        return client.datasets.download(
            self.unique_id,
            output_dir         = cache_dir,
            overwrite_existing = overwrite_existing,
            no_record          = True,
        )

    def load(self, client, cache_dir, use_cache=True, overwrite_existing=False, **kwargs):
        """
        Download (if needed) and parse this dataset's data files.

        If prefetch() was called beforehand, uses those files directly.
        Otherwise falls back to downloading inline.
        """
        loader = self._loaders.get(self.dtype)
        if loader is None:
            raise NotImplementedError(f"No loader registered for dtype {self.dtype!r}")

        if self._files is not None:
            files = self._files
        else:
            files = self._fetch(client, cache_dir, use_cache, overwrite_existing)

        if not files:
            logger.warning(f"No files downloaded for dataset {self.name!r}")
            return None

        result = loader(self, files, **kwargs)
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

        return self.data

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
    def data_type(self):
        return self._dataset.data_type

    @property
    def links(self):
        return self._dataset.links

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
