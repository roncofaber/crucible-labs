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
from collections import deque
from datetime import datetime, timezone

# import client from nano-crucible
from crucible.config import get_client
from clabs.utils.auxiliary import parse_datetime

#%%

dtype2ext = {
    "sample"  : "sample-graph",
    "dataset" : "dataset",
    "main"    : "",
    }

class CruxObj(object):

    def __init__(self, timestamp=None, creation_time=None, modification_time=None,
                 unique_id=None, project_id=None,
                 owner_orcid=None, owner_user_id=None, **kwargs):

        self._unique_id = unique_id
        self._project_id = project_id
        self._owner_orcid = owner_orcid
        self._owner_user_id = owner_user_id

        # user-settable date (e.g. when the measurement was taken)
        self._timestamp = parse_datetime(timestamp)
        # server-assigned dates (backfilled; may be None for older records)
        self._creation_time = parse_datetime(creation_time)
        self._modification_time = parse_datetime(modification_time)

        # genealogy (same-type parent/child relationships)
        self._parents  = []
        self._children = []

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
        return get_client()

    @property
    def mfid(self):
        return self._unique_id  # no longer relies on subclass
    
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
    def timestamp(self):
        """User-settable date (e.g. when the measurement was taken)."""
        return self._timestamp

    @property
    def creation_time(self):
        """Server-assigned creation time (backfilled; may be None for older records)."""
        return self._creation_time

    @property
    def modification_time(self):
        """Server-assigned last-modification time (backfilled; may be None for older records)."""
        return self._modification_time

    # ------------------------------------------------------------------
    # Genealogy — same-type parent/child relationships
    # ------------------------------------------------------------------

    def add_parent(self, parent, _skip_reciprocal=False):
        """Link a parent object (bidirectional)."""
        if parent not in self._parents:
            self._parents.append(parent)
            if not _skip_reciprocal:
                parent.add_child(self, _skip_reciprocal=True)

    def add_child(self, child, _skip_reciprocal=False):
        """Link a child object (bidirectional)."""
        if child not in self._children:
            self._children.append(child)
            if not _skip_reciprocal:
                child.add_parent(self, _skip_reciprocal=True)

    @property
    def parents(self):
        return self._parents

    @property
    def children(self):
        return self._children

    @property
    def ancestors(self):
        """All ancestors via BFS over parent relationships."""
        result, visited = [], set()
        queue = deque(self._parents)
        while queue:
            current = queue.popleft()
            if id(current) not in visited:
                visited.add(id(current))
                result.append(current)
                queue.extend(current.parents)
        return result

    @property
    def descendants(self):
        """All descendants via BFS over child relationships."""
        result, visited = [], set()
        queue = deque(self._children)
        while queue:
            current = queue.popleft()
            if id(current) not in visited:
                visited.add(id(current))
                result.append(current)
                queue.extend(current.children)
        return result

    @property
    def age(self):
        """Returns the age of the object as a timedelta based on timestamp, or None if unknown."""
        if self._timestamp is None:
            return None
        if self._timestamp.tzinfo is None:
            now = datetime.now()
        else:
            now = datetime.now(timezone.utc)
        return now - self._timestamp