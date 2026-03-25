#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sample: Individual Thin Film Sample Management

Class representing individual thin film samples with measurement storage,
QR code generation, and Crucible integration for metadata and analysis.

Created on Wed Jan  7 17:53:17 2026
@author: roncofaber
"""

import logging

# internal modules
from clabs.core import CruxObj
from clabs.models import SampleModel

# Set up logger for this module
logger = logging.getLogger(__name__)

#%%

class Sample(CruxObj):

    _dtype = "sample"

    def __init__(self, dst_dict=None):

        # store info using the pydantic model
        self._sample = SampleModel.model_validate(dst_dict)

        self._datasets = []  # filled in by project._setup_graph

        # initialize parent class
        super().__init__(
            timestamp         = self._sample.timestamp,
            creation_time     = self._sample.creation_time,
            modification_time = self._sample.modification_time,
            unique_id         = self._sample.unique_id,
            project_id        = self._sample.project_id,
            owner_orcid       = self._sample.owner_orcid,
            owner_user_id     = self._sample.owner_user_id,
        )

        # loaded measurements keyed by mtype — populated by dataset.load()
        self._measurements = {}
    
    @property
    def sample_name(self):
        return self._sample.sample_name
    
    @property
    def name(self):
        return self._sample.sample_name

    @property
    def sample_type(self):
        return self._sample.sample_type

    @property
    def dtype(self):
        return self._sample.sample_type
    
    @property
    def datasets(self):
        """Dataset objects linked to this sample."""
        return self._datasets

    def add_dataset(self, dataset, _skip_reciprocal=False):
        """Link a Dataset object to this sample (bidirectional)."""
        if dataset not in self._datasets:
            self._datasets.append(dataset)
            if not _skip_reciprocal:
                dataset.add_sample(self, _skip_reciprocal=True)

    @property
    def description(self):
        return self._sample.description
    
    @staticmethod
    def _resolve_attr(m, attr, sample):
        """Resolve an attribute across measurement, dataset, or sample level.

        Prefix rules:
        - ``"dataset.<attr>"``  → look on ``m.dataset``
        - ``"sample.<attr>"``   → look on ``sample``
        - ``"<attr>"``          → look on ``m`` (measurement level, default)
        """
        if attr.startswith("dataset."):
            return getattr(m.dataset, attr[8:], None)
        if attr.startswith("sample."):
            return getattr(sample, attr[7:], None)
        return getattr(m, attr, None)

    def get_measurements(self, mtype=None, exclude=None, include=None):
        """
        Return loaded measurements with optional filtering.

        Parameters
        ----------
        mtype : str, optional
            Keep only measurements with this mtype (e.g. ``"uvvis"``).
        exclude : dict, optional
            ``{attr: substring}`` — drop measurements where the resolved
            attribute contains ``substring`` (case-insensitive).
        include : dict, optional
            ``{attr: substring}`` — keep only measurements where the resolved
            attribute contains ``substring`` (case-insensitive).

        Attribute resolution order (use dot-prefix to be explicit):
            - ``"dataset.session"``    → dataset attribute
            - ``"sample.sample_type"`` → sample attribute
            - ``"tray_well"``          → measurement attribute (default)
        """
        result = list(self._measurements.values())
        if mtype is not None:
            result = [m for m in result if m.mtype == mtype]
        for attr, pattern in (exclude or {}).items():
            p = pattern.lower()
            result = [m for m in result
                      if p not in (self._resolve_attr(m, attr, self) or "").lower()]
        for attr, pattern in (include or {}).items():
            p = pattern.lower()
            result = [m for m in result
                      if p in (self._resolve_attr(m, attr, self) or "").lower()]
        return result

    def assign_measurement(self, measurement, _skip_reciprocal=False):
        """Link a Measurement to this sample (bidirectional)."""
        self._measurements[measurement.unique_id] = measurement
        if not _skip_reciprocal:
            measurement.assign_sample(self, _skip_reciprocal=True)

    @property
    def measurements(self):
        return list(self._measurements.values())

    def view(self):
        for m in self._measurements.values():
            if m.mtype == "image" and m.image is not None:
                m.view()
                return
        has_image_dataset = any(d.dtype == "sample well image" for d in self._datasets)
        if has_image_dataset:
            logger.warning(f"Image dataset found for {self.sample_name!r} but not loaded — call load_measurements('sample well image') first.")
        else:
            logger.info(f"No image dataset linked to {self.sample_name!r}.")

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r})"

    def __getattr__(self, name):
        if name == "_sample":
            raise AttributeError("_sample not initialized")
        matches = [m for m in self._measurements.values() if m.mtype == name]
        if matches:
            return matches[0] if len(matches) == 1 else matches
        try:
            return getattr(self._sample, name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")