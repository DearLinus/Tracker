from zoneinfo import ZoneInfoNotFoundError

import pytest

from logic import TrackerLogic


def test_validate_timezone_name_raises_on_unknown():
    tl = TrackerLogic(db_path=":memory:")

    with pytest.raises(ZoneInfoNotFoundError):
        tl._validate_timezone_name("NoSuch/Timezone")
