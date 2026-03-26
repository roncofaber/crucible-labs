"""
clabs: Sample and Dataset management with Crucible integration.

Provides core classes for working with samples, datasets, and collections
backed by the Crucible data lakehouse (via nano-crucible).
"""

import logging

# Configuration utilities — imported directly from nano-crucible
from crucible.config import get_crucible_api_key, create_config_file, get_config_file_path

# Core classes
from .sample import Sample
from .dataset import Dataset
from .collection import SampleCollection, DatasetCollection, FieldSpec

# Data reading and measurements
from .measurements import Measurement, NirvanaUVVis, TFImage, RGAMeasurement

# Genealogy module (import as submodule)
from . import graph

__version__ = "0.1.2"
__author__ = "roncofaber"

__all__ = [
    "Sample",
    "Dataset",
    "SampleCollection",
    "DatasetCollection",
    "FieldSpec",
    "Measurement",
    "NirvanaUVVis",
    "TFImage",
    "RGAMeasurement",
    "get_crucible_api_key",
    "create_config_file",
    "get_config_file_path",
    "setup_logging",
]


class _TqdmHandler(logging.StreamHandler):
    """Log handler that writes through tqdm.write() to avoid clashing with progress bars."""

    def emit(self, record):
        import sys
        from tqdm import tqdm
        try:
            tqdm.write(self.format(record), file=sys.stderr)
        except Exception:
            self.handleError(record)


def setup_logging(level=logging.INFO, format_string=None):
    """
    Configure logging for the clabs package.

    Parameters
    ----------
    level : int, optional
        Logging level (e.g., logging.DEBUG, logging.INFO, logging.WARNING).
        Default is logging.INFO.
    format_string : str, optional
        Custom format string for log messages. If None, uses a default format.

    Examples
    --------
    >>> import clabs
    >>> clabs.setup_logging(level=logging.DEBUG)  # Show all messages
    >>> clabs.setup_logging(level=logging.WARNING)  # Only warnings and errors
    """
    if format_string is None:
        format_string = '%(levelname)s | %(message)s'

    logger = logging.getLogger('clabs')
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    handler = _TqdmHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(handler)

    return logger


# Auto-configure logging with a reasonable default when package is imported
setup_logging(level=logging.WARNING)