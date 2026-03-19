#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auxiliary Utilities: Helper Functions

Contains utility functions for datetime parsing, well position conversion,
and data filtering used across the clabs package.

Created on Fri Jan 16 17:32:08 2026
@author: roncofaber
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Ordered list of (format_string, description) fallbacks tried after isoformat
_DATETIME_FALLBACKS = [
    ("%Y%m%d_%p", "YYYYMMDD_AM/PM"),  # e.g. '20251209_am', '20251209_pm'
    ("%Y%m%d",    "YYYYMMDD"),         # e.g. '20251209'
    ("%Y-%m-%d",  "YYYY-MM-DD"),       # e.g. '2025-12-09'
    ("%d/%m/%Y",  "DD/MM/YYYY"),       # e.g. '09/12/2025'
    ("%m/%d/%Y",  "MM/DD/YYYY"),       # e.g. '12/09/2025'
]


def parse_datetime(value):
    """
    Parse a datetime string, handling both ISO 8601 and known non-standard formats.

    Tries datetime.fromisoformat() first, then falls back through a list of
    common patterns. Returns None (with a warning) if nothing matches.

    Parameters
    ----------
    value : str or None

    Returns
    -------
    datetime or None
    """
    if value is None:
        return None

    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        pass

    # Normalise to uppercase so %p matches both 'am'/'pm' and 'AM'/'PM'
    normalised = value.strip().upper()
    for fmt, _ in _DATETIME_FALLBACKS:
        try:
            return datetime.strptime(normalised, fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse datetime {value!r} — stored as None")
    return None

def number_to_well(n):
    """
    Convert number 0-15 to well position (A1, A2, ..., D4)
    
    Args:
        n: Integer from 0-15
    
    Returns:
        Well position string (e.g., 'A1', 'B3')
    """
    if not 0 <= n <= 15:
        raise ValueError("Number must be between 0 and 15")
    
    row = chr(65 + n // 4)  # 65 is ASCII for 'A'
    col = (n % 4) + 1
    
    return f"{row}{col}"

#%%

def filter_links(links):
    """
    If multiple links are provided, return the dict entry containing 'corrected', ignoring any links with 'thumbnail' in the key.
    Otherwise, return the single link dict or string.
    Returns empty dict if no links found.
    """
    
    if isinstance(links, str):
        return links  # Return the single string link directly
    
    if isinstance(links, dict):
        if len(links) == 0:
            return {}
        
        if len(links) == 1:
            return links  # Return the single link dict
        
        # Filter out links with 'thumbnail' in the key
        filtered_links = {key: url for key, url in links.items() if 'thumbnail' not in key.lower()}
        
        if len(filtered_links) == 0:  # No valid links left
            return {}
        
        # Look for the 'corrected' link
        for key, url in filtered_links.items():
            if 'corrected' in key.lower():
                return {key: url}  # Immediately return if 'corrected' found
        
        # Fallback to the first valid entry
        first_key = next(iter(filtered_links))  # Get the first key
        return {first_key: filtered_links[first_key]}
    
    if isinstance(links, list):
        if len(links) == 0:
            return []  # Return empty list
        
        # Filter out links containing 'thumbnail'
        filtered_links = [link for link in links if 'thumbnail' not in link.lower()]
        
        if len(filtered_links) == 0:  # No valid links left
            return []  # Return empty list if nothing remains
        
        if len(filtered_links) == 1:
            return filtered_links[0]  # Return the single valid link
        
        # Search for a 'corrected' link
        for link in filtered_links:
            if 'corrected' in link.lower():
                return link
        
        return filtered_links[0]  # Return the first valid link
    
    return {}  # Return empty dict for unsupported types
