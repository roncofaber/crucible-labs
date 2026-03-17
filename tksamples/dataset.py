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
from tksamples.core import CruxObj

# Set up logger for this module
logger = logging.getLogger(__name__)

#%%

class Dataset(CruxObj):
    
    def __init__(self, data):
        
        # store dataset information of the sample
        dataset = dataset.copy()
        
        self._dataset = dataset
        
        # initialize parent class
        super().__init__(mfid          = dataset["unique_id"],
                         project_id    = dataset["project_id"],
                         creation_time = dataset["date_created"],
                         dtype         = "sample",
                         )

        # Set to track measurement types
        self._measurements = {}
        self._mtypes       = {}
        if measurements is not None:
            for measurement in measurements.copy():
                self.add_measurement(measurement)

        # Initialize parent/child relationships for genealogy tracking
        self._parents = []
        self._children = []

        return