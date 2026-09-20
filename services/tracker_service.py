from logic import TrackerLogic


_tracker = None


def get_tracker():
    global _tracker

    if _tracker is None:
        _tracker = TrackerLogic()

    return _tracker


class LazyTrackerProxy:
    def __getattr__(self, name):
        return getattr(get_tracker(), name)

    def __setattr__(self, name, value):
        if name == "_tracker":
            object.__setattr__(self, name, value)
            return
        setattr(get_tracker(), name, value)


tracker = LazyTrackerProxy()