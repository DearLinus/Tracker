import pytest
from handlers.utils import parse_int


@pytest.mark.parametrize(
    "text,expected",
    [
        ("8", 8),
        ("+5", 5),
        ("-5", -5),
        ("٠", 0),
        ("۱", 1),
        ("۱۲", 12),
    ],
)
def test_parse_int_accepts_various_digits(text, expected):
    assert parse_int(text) == expected


@pytest.mark.parametrize("text", ["1_0", "3.5", "abc", "", " "])
def test_parse_int_rejects_invalid_formats(text):
    with pytest.raises(ValueError):
        parse_int(text)
