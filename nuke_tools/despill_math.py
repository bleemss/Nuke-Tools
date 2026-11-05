"""Host-independent expressions used by the despill graph."""


def green_expression(strength):
    """Remove only excess green; leave red, blue, alpha and HDR range alone."""
    if strength not in ("core_strength", "edge_strength"):
        raise ValueError("Unknown despill region")
    return (
        "g-max(g-(r*(1-clamp(parent.balance,0,1))+"
        "b*clamp(parent.balance,0,1))-max(parent.threshold,0),0)"
        "*clamp(parent.%s,0,1)" % strength
    )


NORMALIZE = "a>0.000001 ? {channel}/a : 0"

# Input alpha here is the eroded core mask, not the foreground alpha.
EDGE_OPACITY_FACTOR = (
    "1-(1-clamp(a,0,1))*(1-clamp(parent.extend_opacity,0,1))"
)
