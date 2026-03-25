#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic models for Crucible API request and response objects.

DatasetModel and ProjectModel are imported directly from nano-crucible to avoid
duplication. SampleModel mirrors nano-crucible's Sample model but is defined here
to stay in sync with clabs field naming conventions.
"""

from typing import Optional

# Import directly from nano-crucible to avoid duplication
from crucible.models import Dataset as DatasetModel, Project as ProjectModel, Sample as SampleModel