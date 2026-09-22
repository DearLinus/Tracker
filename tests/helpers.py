import logging
from unittest.mock import create_autospec

from logic import TrackerLogic

logger = logging.getLogger(__name__)


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
            except AttributeError:
                logger.debug("Skipping helper autospec attribute %s", name, exc_info=True)

    return spec
