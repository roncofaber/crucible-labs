"""
Measurements module for clabs

Contains the Measurement base class and instrument-specific subclasses.
Importing this module also registers all known loaders with Dataset so
that dataset.load() can dispatch by mtype automatically.
"""

from .measurement import Measurement
from .uvvis import NirvanaUVVis, load_uvvis
from .image import TFImage, load_image

# Register loaders with Dataset so dataset.load() can dispatch by mtype
from clabs.dataset import Dataset

Dataset.register_loader("pollux_oospec_multipos_line_scan", load_uvvis)
Dataset.register_loader("sample well image",                load_image)

__all__ = ["Measurement", "NirvanaUVVis", "TFImage"]
