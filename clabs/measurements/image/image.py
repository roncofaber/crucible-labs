#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TFImage: Well Image Measurement

Wraps a PIL image loaded from a Crucible dataset download.

Created on Mon Jan 26 10:44:31 2026
@author: roncofaber
"""

import logging

# image stuff
from PIL import Image
import matplotlib.pyplot as plt

# internal modules
from clabs.measurements.measurement import Measurement

# Set up logger for this module
logger = logging.getLogger(__name__)

#%%

class TFImage(Measurement):

    _mtype = "image"

    def __init__(self, image=None, dataset=None):

        # initialize base Measurement (links back to the Dataset)
        super().__init__(dataset)

        self.image = Image.open(image)

    @property
    def sample_name(self):
        sm = self._dataset.scientific_metadata
        return sm.get("sample_name") if sm else None

    @property
    def sample_mfid(self):
        sm = self._dataset.scientific_metadata
        return sm.get("sample_mfid") if sm else None

    def view(self, console=False):
        """Display the image associated with the instance."""
        if self.image is not None:
            plt.figure(figsize=(3, 3))
            plt.imshow(self.image, cmap='gray')
            plt.axis('off')
            plt.show(block=not console)
        else:
            logger.info("No image to display")
