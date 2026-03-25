"""
Measurements module for clabs

Contains the Measurement base class and instrument-specific subclasses.
Importing this module registers all built-in loaders with Dataset via
register_loaders(), which can also be called explicitly.
"""

from .measurement import Measurement
from .uvvis import NirvanaUVVis
from .image import TFImage
from .rga import RGAMeasurement


def register_loaders():
    """Register all built-in measurement loaders with Dataset.

    Called automatically on import. Can also be called explicitly to
    ensure loaders are registered (e.g. in tests or custom pipelines).
    """
    from clabs.dataset import Dataset
    Dataset.register_loader("pollux_oospec_multipos_line_scan", NirvanaUVVis.load)
    Dataset.register_loader("sample well image",                TFImage.load)
    Dataset.register_loader("automated_RGA_TEY_run",            RGAMeasurement.load)


register_loaders()

__all__ = ["Measurement", "NirvanaUVVis", "TFImage", "RGAMeasurement", "register_loaders"]
