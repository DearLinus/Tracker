import math
from datetime import timedelta
from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

TIMELINE_DAYS = {
    "Weekly": 7,
    "Monthly": 30,
    "3 Months": 90,
    "6 Months": 180,
    "1 Year": 365,
}


def create_graph(
    logic,
    user_id,
    timeline="Monthly",
    theme="dark",
    today=None,
):
    """
    Returns:
      - BytesIO image when the graph can be rendered
      - None when the user has no records at all
      - "empty_range" (str) when the user has records but none inside the
        requested timeline range
    """

    records = logic.get_records(user_id)

    # No records for the user at all
    if not records:
        return None

    if today is None:
        raise ValueError("today must be provided")

    days = TIMELINE_DAYS.get(timeline, 30)
    start_date = today - timedelta(days=days - 1)

    filtered = {
        d: count
        for d, count in records.items()
        if start_date <= d <= today
    }

    # User has records, but none in the selected range
    if not filtered:
        return "empty_range"

    dates = [start_date + timedelta(days=i) for i in range(days)]
    counts = [filtered.get(d, float("nan")) for d in dates]

    # -------------------------------
    # Theme
    # -------------------------------

    dark = theme.lower() == "dark"

    background = "#1f2937" if dark else "#ffffff"
    text_color = "#ffffff" if dark else "#111827"
    secondary_color = "#ffffff" if dark else "#6b7280"
    border_color = "#374151" if dark else "#d1d5db"
    accent = "#6366f1"

    # -------------------------------
    # Figure
    # -------------------------------

    width = max(9, min(20, len(dates) * 0.6))

    fig = Figure(figsize=(width, 4.7), dpi=100)
    ax = fig.add_subplot(111)

    fig.patch.set_facecolor(background)
    ax.set_facecolor(background)

    # -------------------------------
    # Numeric values / latest record
    # -------------------------------

    x_num = mdates.date2num(dates)

    latest_date = max(filtered.keys())
    latest_count = filtered[latest_date]
    latest_x = mdates.date2num(latest_date)

    # -------------------------------
    # Axis limits
    # -------------------------------

    # X: small margin on the left, small margin on the right of the last record
    span = latest_x - x_num[0]
    pad_left = max(0.5, span * 0.02)
    pad_right = 0.5

    x_min = x_num[0] - pad_left
    x_max = latest_x + pad_right

    # Y
    valid_counts = [c for c in counts if not math.isnan(c)]

    max_count = max(valid_counts)
    min_count = min(valid_counts)

    if max_count == min_count:
        y_min = max(0, min_count - 1)
        y_max = max_count + 1
    else:
        padding = max(1, (max_count - min_count) * 0.12)
        y_min = max(0, min_count - padding)
        y_max = max_count + padding

    # -------------------------------
    # Title
    # -------------------------------

    ax.set_title(
        "Masturbation Trend",
        fontsize=16,
        fontweight="bold",
        color=text_color,
        pad=18,
    )

    # -------------------------------
    # Main line
    # -------------------------------

    ax.plot(
        x_num,
        counts,
        marker="o",
        markersize=7,
        linewidth=2.4,
        color=accent,
        zorder=3,
    )

    # -------------------------------
    # Guide lines (axis -> latest point)
    # -------------------------------

    # Y axis -> latest point
    ax.hlines(
        latest_count,
        x_min,
        latest_x,
        colors="red",
        linestyles="--",
        linewidth=1.2,
        alpha=0.75,
        zorder=2,
    )

    # X axis -> latest point
    ax.vlines(
        latest_x,
        y_min,
        latest_count,
        colors="red",
        linestyles="--",
        linewidth=1.2,
        alpha=0.75,
        zorder=2,
    )

    # -------------------------------
    # X axis labels
    # -------------------------------

    if len(dates) <= 30:
        # ticks only up to the latest record so the axis is not stretched
        ax.set_xticks([x for x in x_num if x <= latest_x])
    else:
        ax.xaxis.set_major_locator(
            mdates.AutoDateLocator(minticks=5, maxticks=12)
        )

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    if len(dates) <= 10:
        rotation, size = 0, 9
    elif len(dates) <= 18:
        rotation, size = 25, 8
    elif len(dates) <= 30:
        rotation, size = 35, 7
    else:
        rotation, size = 45, 6

    ax.tick_params(
        axis="x",
        colors=secondary_color,
        labelsize=size,
        rotation=rotation,
        pad=8,
    )

    ax.tick_params(
        axis="y",
        colors=secondary_color,
        labelsize=9,
    )

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    # -------------------------------
    # Apply limits (AFTER ticks are set)
    # -------------------------------

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    # -------------------------------
    # Grid
    # -------------------------------

    ax.grid(
        axis="both",
        linestyle="--",
        linewidth=0.8,
        alpha=0.25,
        zorder=0,
    )

    # -------------------------------
    # Borders
    # -------------------------------

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(border_color)
    ax.spines["bottom"].set_color(border_color)

    ax.set_xlabel(
        "Date",
        fontsize=10,
        fontweight="bold",
        color=text_color,
        labelpad=12,
    )

    ax.set_ylabel(
        "Count",
        fontsize=10,
        fontweight="bold",
        color=text_color,
        labelpad=12,
    )

    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")

    fig.tight_layout()

    # -------------------------------
    # Export
    # -------------------------------

    image = BytesIO()
    image.name = "daily_tracker.png"

    fig.savefig(
        image,
        format="png",
        dpi=120,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
    )

    image.seek(0)

    return image