"""
Unit tests for create_graph().

The main goal: make sure the red dashed guide lines are never cut short.
  - horizontal line: from the Y axis (left edge)  -> latest point
  - vertical line:   from the X axis (bottom edge) -> latest point

create_graph() only returns a PNG, so we spy on the Figure it creates and
inspect the matplotlib objects directly (no image comparison needed).
By the time we inspect them, savefig() has already run, so the axis limits
are the final ones.

Run:  pytest -v
"""

from datetime import date, timedelta
from io import BytesIO

import pytest
from matplotlib.figure import Figure
import matplotlib.dates as mdates

import graph  # <-- change this if your module has a different name/path
from graph import create_graph, TIMELINE_DAYS


TODAY = date(2026, 9, 19)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

class FakeLogic:
    def __init__(self, records):
        self._records = records

    def get_records(self, user_id):
        return self._records


def make_records(offsets_to_counts, today=TODAY):
    """{days_before_today: count} -> {date: count}"""
    return {
        today - timedelta(days=offset): count
        for offset, count in offsets_to_counts.items()
    }


@pytest.fixture
def figures(monkeypatch):
    """Records every Figure created by create_graph()."""
    created = []

    class SpyFigure(Figure):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created.append(self)

    monkeypatch.setattr(graph, "Figure", SpyFigure)
    return created


def build(records, figures, timeline="Monthly", theme="dark", today=TODAY):
    """Runs create_graph and returns (ax, image)."""
    image = create_graph(
        FakeLogic(records),
        user_id=1,
        timeline=timeline,
        theme=theme,
        today=today,
    )
    assert figures, "create_graph did not create a Figure"
    ax = figures[-1].axes[0]
    return ax, image


def get_guides(ax):
    """
    Returns (hline, vline):
      hline = (x_start, x_end, y)
      vline = (x, y_start, y_end)
    Guide lines are the only LineCollections on the axes.
    """
    hline = vline = None

    for collection in ax.collections:
        for segment in collection.get_segments():
            (x0, y0), (x1, y1) = segment

            if y0 == y1:
                hline = (x0, x1, y0)
            elif x0 == x1:
                vline = (x0, y0, y1)

    return hline, vline


def last_plotted_point(ax):
    """The last non-NaN point of the main data line."""
    line = ax.lines[0]
    xs = list(line.get_xdata())
    ys = list(line.get_ydata())

    points = [(x, y) for x, y in zip(xs, ys) if y == y]  # drop NaN
    return points[-1]


# Same shape as the screenshot: 6 days, big jump at the end
SCREENSHOT_RECORDS = make_records({
    6: 3,
    5: 3,
    4: 6,
    3: 5,
    2: 10,
    1: 54,
})


# ------------------------------------------------------------------
# Guide lines reach the axes and the latest point
# ------------------------------------------------------------------

def test_both_guide_lines_exist(figures):
    ax, _ = build(SCREENSHOT_RECORDS, figures)
    hline, vline = get_guides(ax)

    assert hline is not None, "horizontal guide line missing"
    assert vline is not None, "vertical guide line missing"


def test_horizontal_line_starts_exactly_at_y_axis(figures):
    ax, _ = build(SCREENSHOT_RECORDS, figures)
    hline, _ = get_guides(ax)

    x_start, _, _ = hline
    assert x_start == pytest.approx(ax.get_xlim()[0])


def test_horizontal_line_ends_exactly_at_latest_point(figures):
    ax, _ = build(SCREENSHOT_RECORDS, figures)
    hline, _ = get_guides(ax)

    _, x_end, y = hline
    px, py = last_plotted_point(ax)

    assert x_end == pytest.approx(px)
    assert y == pytest.approx(py)


def test_vertical_line_starts_exactly_at_x_axis(figures):
    ax, _ = build(SCREENSHOT_RECORDS, figures)
    _, vline = get_guides(ax)

    _, y_start, _ = vline
    assert y_start == pytest.approx(ax.get_ylim()[0])


def test_vertical_line_ends_exactly_at_latest_point(figures):
    ax, _ = build(SCREENSHOT_RECORDS, figures)
    _, vline = get_guides(ax)

    x, _, y_end = vline
    px, py = last_plotted_point(ax)

    assert x == pytest.approx(px)
    assert y_end == pytest.approx(py)


def test_guide_lines_stay_inside_axes(figures):
    """A line that goes past the limits would be clipped -> looks cut."""
    ax, _ = build(SCREENSHOT_RECORDS, figures)
    hline, vline = get_guides(ax)
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()

    hx0, hx1, hy = hline
    vx, vy0, vy1 = vline

    assert x_min <= hx0 <= hx1 <= x_max
    assert y_min <= hy <= y_max
    assert x_min <= vx <= x_max
    assert y_min <= vy0 <= vy1 <= y_max


# ------------------------------------------------------------------
# Regression: y-axis does not start at 0
# (the original bug: vline started at 0 instead of the real bottom)
# ------------------------------------------------------------------

def test_vertical_line_reaches_bottom_when_ylim_is_not_zero(figures):
    records = make_records({2: 50, 1: 55, 0: 60})
    ax, _ = build(records, figures)
    _, vline = get_guides(ax)

    y_min = ax.get_ylim()[0]
    assert y_min > 0, "test data should produce a non-zero lower limit"

    _, y_start, _ = vline
    assert y_start == pytest.approx(y_min)


def test_all_values_equal(figures):
    records = make_records({2: 5, 1: 5, 0: 5})
    ax, _ = build(records, figures)
    hline, vline = get_guides(ax)

    assert hline[2] == pytest.approx(5)
    assert vline[1] == pytest.approx(ax.get_ylim()[0])
    assert vline[2] == pytest.approx(5)


# ------------------------------------------------------------------
# Right side spacing
# ------------------------------------------------------------------

def test_right_margin_is_small(figures):
    ax, _ = build(SCREENSHOT_RECORDS, figures)
    latest_x = last_plotted_point(ax)[0]

    assert ax.get_xlim()[1] - latest_x <= 1.0


def test_no_tick_after_latest_record(figures):
    """
    Regression: a tick on 'today' (after the latest record) used to
    stretch the axis and leave empty space on the right.
    """
    ax, _ = build(SCREENSHOT_RECORDS, figures, timeline="Weekly")
    latest_x = last_plotted_point(ax)[0]

    assert max(ax.get_xticks()) <= latest_x + 1e-9


def test_latest_record_not_today(figures):
    records = make_records({6: 2, 5: 4, 4: 3, 3: 7})  # last record: 3 days ago
    ax, _ = build(records, figures, timeline="Weekly")

    latest_date = TODAY - timedelta(days=3)
    latest_x = mdates.date2num(latest_date)

    hline, vline = get_guides(ax)

    assert hline[1] == pytest.approx(latest_x)
    assert vline[0] == pytest.approx(latest_x)
    assert ax.get_xlim()[1] - latest_x <= 1.0


# ------------------------------------------------------------------
# Gaps in the data
# ------------------------------------------------------------------

def test_missing_days_do_not_break_guides(figures):
    records = make_records({20: 3, 15: 8, 9: 1, 0: 12})
    ax, _ = build(records, figures)
    hline, vline = get_guides(ax)

    assert hline[2] == pytest.approx(12)
    assert vline[2] == pytest.approx(12)
    assert hline[0] == pytest.approx(ax.get_xlim()[0])
    assert vline[1] == pytest.approx(ax.get_ylim()[0])


def test_records_outside_timeline_are_ignored(figures):
    records = make_records({100: 999, 2: 4, 1: 6})
    ax, _ = build(records, figures, timeline="Weekly")
    hline, _ = get_guides(ax)

    assert hline[2] == pytest.approx(6)
    assert ax.get_ylim()[1] < 999


# ------------------------------------------------------------------
# Every timeline, both themes
# ------------------------------------------------------------------

@pytest.mark.parametrize("timeline", list(TIMELINE_DAYS))
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_guides_are_complete_for_every_timeline(figures, timeline, theme):
    records = make_records({5: 3, 3: 8, 1: 5, 0: 11})
    ax, _ = build(records, figures, timeline=timeline, theme=theme)
    hline, vline = get_guides(ax)

    x_min, _ = ax.get_xlim()
    y_min, _ = ax.get_ylim()
    px, py = last_plotted_point(ax)

    assert hline == pytest.approx((x_min, px, py))
    assert vline == pytest.approx((px, y_min, py))


# ------------------------------------------------------------------
# Basic behaviour
# ------------------------------------------------------------------

def test_returns_none_without_records(figures):
    image = create_graph(FakeLogic({}), 1, today=TODAY)
    assert image is None


def test_returns_none_when_nothing_in_range(figures):
    records = make_records({200: 5})
    image = create_graph(FakeLogic(records), 1, timeline="Weekly", today=TODAY)
    assert image is None


def test_today_is_required():
    with pytest.raises(ValueError):
        create_graph(FakeLogic(SCREENSHOT_RECORDS), 1)


def test_returns_valid_png(figures):
    _, image = build(SCREENSHOT_RECORDS, figures)

    assert isinstance(image, BytesIO)
    assert image.name == "daily_tracker.png"
    assert image.read(8) == b"\x89PNG\r\n\x1a\n"