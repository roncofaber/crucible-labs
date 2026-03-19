#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Loader: Crucible Dataset → TFImage

Registered with Dataset.register_loader() in measurements/__init__.py.
Receives a Dataset object and a list of local file paths (already downloaded
by Dataset.load()) and returns a TFImage object.

@author: roncofaber
"""

import os
import logging

from tksamples.measurements.image.image import TFImage

logger = logging.getLogger(__name__)

#%%

def load_image(dataset, files):
    """Open a well image from downloaded files. Returns a TFImage."""
    image_exts = {'.jpeg', '.jpg', '.png', '.gif', '.bmp',
                  '.tiff', '.tif', '.webp', '.heif', '.heic'}
    img_files = [f for f in files if os.path.splitext(f)[1].lower() in image_exts]
    if not img_files:
        logger.warning(f"No image file found for dataset {dataset.name!r}")
        return None
    return TFImage(image=img_files[0], dataset=dataset)
