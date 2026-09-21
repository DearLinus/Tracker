from unittest.mock import create_autospec
from logic import TrackerLogic


def autospec_tracker(obj):
    """Return an object that is a `create_autospec` of `TrackerLogic` with
    any methods from `obj` copied onto the spec. This catches API drift
    while preserving test-provided method implementations.
    """
    spec = create_autospec(TrackerLogic, instance=True)

    for name in dir(obj):
        if name.startswith("_"):
            continue
        if hasattr(spec, name):
            try:
                setattr(spec, name, getattr(obj, name))
            except Exception:
                pass

    return spec
