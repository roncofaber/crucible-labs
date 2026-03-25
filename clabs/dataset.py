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

import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# internal modules
from clabs.core import CruxObj
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
            owner_user_id     = self._dataset.owner_user_id,
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

    @staticmethod
    def _list_local_files(dataset_dir):
        """Return full file paths in dataset_dir, or [] if missing/empty."""
        if os.path.isdir(dataset_dir) and os.listdir(dataset_dir):
            return [os.path.join(dataset_dir, f) for f in os.listdir(dataset_dir)]
        return []

    @staticmethod
    def _download_file(fname, signed_url, output_dir, overwrite_existing):
        """Download a single file from a signed URL. Returns local path, or None if skipped."""
        download_path = os.path.join(output_dir, fname)
        if not overwrite_existing and os.path.exists(download_path):
            return download_path
        parent = os.path.dirname(download_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        response = requests.get(signed_url, stream=True)
        response.raise_for_status()
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return download_path

    @staticmethod
    def _parallel_download(signed_urls, output_dir, overwrite_existing=False, max_workers=16):
        """Download multiple files in parallel from signed URLs. Returns list of local paths."""
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        futures = {}
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for fname, url in signed_urls.items():
                f = pool.submit(Dataset._download_file, fname, url, output_dir, overwrite_existing)
                futures[f] = fname
            for future in as_completed(futures):
                fname = futures[future]
                try:
                    path = future.result()
                    if path is not None:
                        paths.append(path)
                except Exception as e:
                    logger.warning(f"Failed to download {fname!r}: {e}")
        return paths

    def prefetch(self, client, cache_dir, overwrite_existing=False):
        """
        Download dataset files without parsing. Thread-safe: no shared state is touched.
        Call this in a thread pool before load() to overlap network I/O.

        Files within each dataset are downloaded in parallel (via signed URLs),
        on top of the dataset-level parallelism in the caller.
        """
        dataset_dir = os.path.join(cache_dir, self.unique_id)
        local = self._list_local_files(dataset_dir)
        if local and not overwrite_existing:
            self._files = local
        else:
            signed_urls = self._get_download_links_with_retry(client)
            self._files = self._parallel_download(
                signed_urls,
                output_dir         = cache_dir,
                overwrite_existing = overwrite_existing,
            )

    def _get_download_links_with_retry(self, client, max_attempts=4, base_delay=2):
        """Call get_download_links with exponential backoff on transient failures."""
        for attempt in range(max_attempts):
            try:
                return client.datasets.get_download_links(self.unique_id)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"get_download_links failed for {self.name!r} "
                    f"(attempt {attempt + 1}/{max_attempts}): {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)

    def load(self, client, cache_dir, use_cache=True, overwrite_existing=False):
        """
        Download (if needed) and parse this dataset's data files.

        If prefetch() was called beforehand, uses those files directly.
        Otherwise falls back to downloading inline.
        """
        loader = self._loaders.get(self.dtype)
        if loader is None:
            raise NotImplementedError(f"No loader registered for dtype {self.dtype!r}")

        # use pre-fetched files if available, otherwise download now
        if self._files is not None:
            files = self._files
        else:
            dataset_dir = os.path.join(cache_dir, self.unique_id)
            local = self._list_local_files(dataset_dir)
            if use_cache and not overwrite_existing and local:
                files = local
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