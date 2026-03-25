#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TFImage: Well Image Measurement

Wraps a PIL image loaded from a Crucible dataset download.

Created on Mon Jan 26 10:44:31 2026
@author: roncofaber
"""

import os
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

    def __init__(self, dataset, image_path):
        super().__init__(dataset)
        self.image = Image.open(image_path)

    @property
    def sample_name(self):
        sm = self._dataset.scientific_metadata
        return sm.get("sample_name") if sm else None

    @property
    def sample_mfid(self):
        sm = self._dataset.scientific_metadata
        return sm.get("sample_mfid") if sm else None

    @classmethod
    def load(cls, dataset, files):
        """Open a well image from downloaded files. Returns a TFImage."""
        image_exts = {'.jpeg', '.jpg', '.png', '.gif', '.bmp',
                      '.tiff', '.tif', '.webp', '.heif', '.heic'}
        img_files = [f for f in files
                     if os.path.splitext(f)[1].lower() in image_exts]
        if not img_files:
            logger.warning(f"No image file found for dataset {dataset.name!r}")
            return None
        return cls(dataset, img_files[0])

    def view(self, console=False):
        """Display the image associated with the instance."""
        if self.image is not None:
            plt.figure(figsize=(3, 3))
            plt.imshow(self.image, cmap='gray')
            plt.axis('off')
            plt.show(block=not console)
        else:
            logger.info("No image to display")
