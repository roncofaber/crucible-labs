"""
Measurements module for clabs

Contains the Measurement base class and instrument-specific subclasses.
Importing this module registers all built-in loaders with Dataset via
register_loaders(), which can also be called explicitly.
"""

from .measurement import Measurement
from .uvvis import NirvanaUVVis, load_uvvis
from .image import TFImage, load_image
from .rga import RGAMeasurement, load_rga


def register_loaders():
    """Register all built-in measurement loaders with Dataset.

    Called automatically on import. Can also be called explicitly to
    ensure loaders are registered (e.g. in tests or custom pipelines).
    """
    from clabs.dataset import Dataset
    Dataset.register_loader("pollux_oospec_multipos_line_scan", load_uvvis)
    Dataset.register_loader("sample well image",                load_image)
    Dataset.register_loader("automated_RGA_TEY_run",            load_rga)


register_loaders()

__all__ = ["Measurement", "NirvanaUVVis", "TFImage", "RGAMeasurement", "register_loaders"]
