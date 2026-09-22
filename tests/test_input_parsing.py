import pytest

from handlers.utils import parse_date, parse_int


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


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1403-09-10", "1403-09-10"),
        ("۱۴۰۳-۰۹-۱۰", "1403-09-10"),
        ("2026-09-10", "2026-09-10"),
    ],
)
def test_parse_date_normalizes_persian_digits_and_keeps_iso_format(text, expected):
    assert parse_date(text).isoformat() == expected


@pytest.mark.parametrize(
    "text",
    [
        "2026/09/10",
        "10-09-2026",
        "2026-9-10",
        "0000-01-01",
        "99999-01-01",
        "2026-13-01",
        "2026-02-30",
        "2026-00-01",
        "ab-cd-ef",
    ],
)
def test_parse_date_rejects_invalid_years_and_unsupported_formats(text):
    with pytest.raises(ValueError):
        parse_date(text)
