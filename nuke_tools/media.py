"""Media inspection without a dependency on Nuke."""

import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Audit:
    checked: int
    missing: tuple


def audit_frames(resolve, first, last):
    """Check unique resolved filenames over an inclusive frame range."""
    if last < first:
        raise ValueError("Last frame must be greater than or equal to first frame")
    paths = dict.fromkeys(resolve(frame) for frame in range(first, last + 1))
    return Audit(len(paths), tuple(path for path in paths if not os.path.isfile(path)))


def replace_prefix(path, old, new):
    """Replace a whole directory prefix, accepting Windows or POSIX separators.

    Windows drive and UNC paths compare case-insensitively. Other paths retain
    case sensitivity. Expressions are deliberately left untouched.
    """
    if not old or not new:
        raise ValueError("Both folder prefixes are required")
    if any(char in path + old + new for char in "[]"):
        raise ValueError("Expression paths must be relinked manually")
    path = path.replace("\\", "/")
    old = old.replace("\\", "/").rstrip("/")
    new = new.replace("\\", "/").rstrip("/")
    if not old or not new:
        raise ValueError("Use a named folder rather than a filesystem root")
    windows = bool(re.match(r"^[A-Za-z]:/", path) or path.startswith("//"))
    candidate, prefix = (path.casefold(), old.casefold()) if windows else (path, old)
    if candidate.startswith(prefix + "/"):
        return new + path[len(old):]
    return path
