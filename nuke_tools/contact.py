"""Host-independent contact detection from bottom-up alpha row averages."""


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
