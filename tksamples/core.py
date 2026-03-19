#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core: Base Classes and Crucible Integration

Provides CruxObj base class with Crucible API client setup and QR code
generation functionality for sample identification and tracking.

Created on Thu Jan 22 17:34:02 2026
@author: roncofaber
"""

# handy packages
import qrcode
import webbrowser
from datetime import datetime, timezone

# import client from nano-crucible
from crucible.config import get_client
from tksamples.utils.auxiliary import parse_datetime

#%%

dtype2ext = {
    "sample"  : "sample-graph",
    "dataset" : "dataset",
    "main"    : "",
    }

class CruxObj(object):

    # Class variable for the client
    _client = get_client()
    
    __slots__ = ["_creation_time", "_qr_code", "_unique_id", "_project_id", "_owner_orcid", "_owner_user_id"]
    
    def __init__(self, creation_time=None, unique_id=None, project_id=None,
                 owner_orcid=None, owner_user_id=None, **kwargs):
        
        self._unique_id = unique_id
        self._project_id = project_id
        self._owner_orcid = owner_orcid
        self._owner_user_id = owner_user_id
        
        self._creation_time = parse_datetime(creation_time)
            
        # initialize QR code
        self._qr_code = qrcode.QRCode(border=1)
        self._qr_code.add_data(self.mfid)
    
    @property
    def unique_id(self):
        return self._unique_id
    
    @property
    def project_id(self):
        return self._project_id
    
    @property
    def owner_orcid(self):
        return self._owner_orcid
    
    @property
    def owner_user_id(self):
        return self._owner_user_id

    @property
    def client(self):
        return self._client

    @property
    def mfid(self):
        return self._unique_id  # no longer relies on subclass
    
    @property
    def print_qr(self):
        self._qr_code.print_ascii(invert=True)
    
    # Subclasses set this to 'sample' or 'dataset' for graph explorer links
    _dtype = None

    @property
    def kind(self):
        return self._dtype

    @property
    def link(self):
        from crucible.config import config
        crux_explorer = config.graph_explorer_url.rstrip('/')
        ext = dtype2ext.get(self._dtype, "")
        url = f"{crux_explorer}/{self._project_id}/{ext}/{self.mfid}"
        return url

    def open_in_browser(self):
        webbrowser.open(self.link)

    @property
    def age(self):
        """Returns the age of the object as a timedelta, or None if creation_time is unknown."""
        if self._creation_time is None:
            return None
        if self._creation_time.tzinfo is None:
            now = datetime.now()
        else:
            now = datetime.now(timezone.utc)
        return now - self._creation_time