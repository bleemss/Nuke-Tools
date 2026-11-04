"""Host-independent contact detection from bottom-up alpha row averages."""


# Nuke Expression syntax; kept here so boundary behavior can be checked without
# a Nuke installation. Use pixel centers when evaluating the source matte.
CONTACT_MASK = "clamp(a,0,1)*(y>=parent.contact_y)*(y<parent.contact_y+max(parent.contact_band,1))"
CONTACT_ALPHA = "clamp(a*parent.contact_density*parent.contact_strength,0,1)"


def find_contact(height, sample_row, threshold):
    """Return the lowest occupied pixel edge, or None for an empty matte.

    sample_row receives a zero-based row index and returns its mean alpha.
    This detects silhouette extent, not anatomical feet or physical ground.
    """
    if height < 1:
        raise ValueError("Image height must be positive")
    if not 0 < threshold < 1:
        raise ValueError("Threshold must be between 0 and 1")
    for row in range(height):
        if sample_row(row) > threshold:
            return row
    return None
