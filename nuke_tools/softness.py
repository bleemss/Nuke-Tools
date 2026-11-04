"""Distance masks shared by the Nuke shadow branches."""

# Convert output Y distance back into travel along the cast direction. Very
# nearly horizontal projections are degenerate and use a guarded denominator.
CAST_DISTANCE = (
    "abs(y-parent.contact_y)*sqrt(1+pow(parent.reach/"
    "(max(height,1)*max(abs(parent.length),0.0001)),2))"
)
UNDER_DISTANCE = "abs(y-parent.contact_y-parent.under_offset.y)"


def distance_mask(distance):
    return ("clamp(parent.distance_softness,0,1)*clamp((%s)/"
            "max(parent.falloff_distance,1),0,1)" % distance)


def widening_mask(distance, stage):
    """Blend consecutive expansion levels over four distance intervals."""
    if stage not in range(1, 5):
        raise ValueError("Expansion stage must be 1 through 4")
    return ("clamp(4*clamp((%s)/max(parent.falloff_distance,1),0,1)-%d,0,1)"
            % (distance, stage - 1))
