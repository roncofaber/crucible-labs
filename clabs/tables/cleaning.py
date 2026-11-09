import re

_TEXT_NULLS = {"nan", "none", "n/a", ""}
_NUMBER = r"\s*(-?\d+(?:\.\d+)?)\s*"


def blank_text_null(value):
    """Return ``None`` for text placeholders such as ``"NaN"``; other values unchanged."""
    if isinstance(value, str) and value.strip().lower() in _TEXT_NULLS:
        return None
    return value


def parse_quantity(value, unit):
    """Parse ``"5000 rpm"`` for ``unit="rpm"`` into 5000.0; no conversion, ``None`` otherwise."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.fullmatch(_NUMBER + re.escape(unit) + r"\s*", str(value), flags=re.IGNORECASE)
    return float(match.group(1)) if match else None


def coalesce_columns(df, canonical, alias):
    """Merge ``alias`` into ``canonical`` and drop it.

    Returns the frame and the index labels where both held different values;
    the canonical value wins there.
    """
    df = df.copy()
    both = df[canonical].notna() & df[alias].notna() & (df[canonical] != df[alias])
    conflicts = list(df.index[both])
    df[canonical] = df[canonical].where(df[canonical].notna(), df[alias])
    return df.drop(columns=alias), conflicts
