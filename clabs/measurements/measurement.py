#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Measurement: Base Class for Loaded Dataset Data

A Measurement wraps a Dataset and holds the actual downloaded/parsed data.
Subclasses (NirvanaUVVis, TFImage, ...) add instrument-specific attributes
and analysis methods. Metadata is always delegated to the underlying Dataset.

Created on 2026
@author: roncofaber
"""

import logging
logger = logging.getLogger(__name__)

#%%

class Measurement:
    """
    Base class for all loaded measurement data.

    A Measurement is created when a Dataset's data file is downloaded and
    parsed. It holds a back-reference to its Dataset so that Crucible
    metadata (name, unique_id, linked samples) is always consistent.

    Subclasses must set ``_mtype`` (e.g. ``_mtype = "uvvis"``) and expose
    ``sample_name`` and ``sample_mfid`` so that Dataset.load() can match
    the measurement to the correct Sample object.
    """

    _mtype = None  # overridden by subclasses

    def __init__(self, dataset):
        self._dataset = dataset
        self._sample  = None   # set by Dataset.load() after sample matching

    # dataset delegation

    @property
    def dataset(self):
        return self._dataset

    @property
    def mtype(self):
        return self._mtype

    @property
    def name(self):
        return self._dataset.name

    @property
    def unique_id(self):
        return self._dataset.unique_id

    @property
    def sample(self):
        """The specific Sample this measurement was matched to."""
        return self._sample

    @property
    def samples(self):
        """All samples linked to the parent dataset (graph-level)."""
        return self._dataset.samples

    def assign_sample(self, sample, _skip_reciprocal=False):
        """Link this measurement to a Sample (bidirectional)."""
        self._sample = sample
        if not _skip_reciprocal:
            sample.assign_measurement(self, _skip_reciprocal=True)

    # to be defined by subclasses

    @property
    def sample_name(self):
        """Name of the sample this measurement belongs to."""
        return None

    @property
    def sample_mfid(self):
        """Unique ID of the sample this measurement belongs to."""
        return None

    # misc methods

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r})"
