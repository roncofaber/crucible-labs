#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic models for Crucible API request and response objects.

BaseDataset and BaseProject are imported directly from nano-crucible to avoid
duplication. BaseSample is defined here because it normalizes the 'date_created'
field (used by the samples API) to 'creation_time' via AliasChoices.
"""

from pydantic import BaseModel, ConfigDict, Field, AliasChoices
from typing import Optional

# Import directly from nano-crucible to avoid duplication
from crucible.models import BaseDataset, Project as BaseProject

#%%

class BaseSample(BaseModel):
    unique_id: Optional[str] = None
    sample_name: Optional[str] = None
    sample_type: Optional[str] = None
    owner_orcid: Optional[str] = None
    owner_user_id: Optional[int] = None
    # The samples API returns 'date_created'; datasets use 'creation_time'
    # AliasChoices normalizes both to 'creation_time' for consistency
    creation_time: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("creation_time", "date_created")
    )
    project_id: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)