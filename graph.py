from io import BytesIO

from datetime import timedelta
from timezone import today as get_today

import matplotlib
matplotlib.use("Agg")

from matplotlib.figure import Figure
import matplotlib.dates as mdates
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
    theme="dark"
):

    records = logic.get_records(user_id)

    if not records:
        return None


    days = TIMELINE_DAYS.get(
        timeline,
        30
    )


    # -------------------------------
    # Filter timeline
    # -------------------------------

    today = get_today()

    start_date = (
        today
        - timedelta(days=days - 1)
    )

    filtered = {
        d: count
        for d, count in records.items()
        if start_date <= d <= today
    }

    if not filtered:
        return None

    # Keep every day in the selected range.
    # Missing days are represented by None so matplotlib
    # leaves gaps instead of drawing misleading lines.
    dates = [
        start_date + timedelta(days=i)
        for i in range(days)
    ]

    counts = [
        filtered.get(d)
        for d in dates
    ]
    # -------------------------------
    # Theme
    # -------------------------------

    dark = theme.lower() == "dark"

    background = (
        "#1f2937"
        if dark
        else "#ffffff"
    )

    text_color = (
        "#ffffff"
        if dark
        else "#111827"
    )

    secondary_color = (
        "#ffffff"
        if dark
        else "#6b7280"
    )

    border_color = (
        "#374151"
        if dark
        else "#d1d5db"
    )


    accent = "#6366f1"


    # -------------------------------
    # Figure
    # -------------------------------

    width = max(
        9,
        min(
            20,
            len(dates) * 0.6
        )
    )


    fig = Figure(
        figsize=(width, 4.7),
        dpi=100
    )


    ax = fig.add_subplot(111)


    fig.patch.set_facecolor(
        background
    )

    ax.set_facecolor(
        background
    )


    # -------------------------------
    # Title
    # -------------------------------

    ax.set_title(
        "Masturbation Trend",
        fontsize=16,
        fontweight="bold",
        color=text_color,
        pad=18
    )


    # -------------------------------
    # Line
    # -------------------------------

    ax.plot(
        dates,
        counts,
        marker="o",
        markersize=7,
        linewidth=2.4,
        color=accent,
        zorder=3
    )


    # -------------------------------
    # X axis
    # -------------------------------

    if len(dates) <= 30:

        ax.set_xticks(
            dates
    )

    else:

        ax.xaxis.set_major_locator(
        mdates.AutoDateLocator(
            minticks=5,
            maxticks=12
        )
    )


    ax.xaxis.set_major_formatter(
    mdates.DateFormatter("%b %d")
)


    if len(dates) <= 10:
        rotation = 0
        size = 9

    elif len(dates) <= 18:
        rotation = 25
        size = 8

    elif len(dates) <= 30:
        rotation = 35
        size = 7

    else:
        rotation = 45
        size = 6



    ax.tick_params(
        axis="x",
        colors=secondary_color,
        labelsize=size,
        rotation=rotation,
        pad=8
    )


    ax.tick_params(
        axis="y",
        colors=secondary_color,
        labelsize=9
    )


    for label in (
        ax.get_xticklabels()
        +
        ax.get_yticklabels()
    ):
        label.set_fontweight(
            "bold"
        )


    # -------------------------------
    # Y axis
    # -------------------------------

    ax.yaxis.set_major_locator(
    MaxNLocator(integer=True)
    )

    valid_counts = [
        count
    for count in counts
    if count is not None
    ]

    valid_counts = [
        count
        for count in counts
        if count is not None
    ]

    max_count = max(valid_counts)
    min_count = min(valid_counts)


    if max_count == min_count:

        lower = max(
            0,
            min_count - 1
        )

        upper = max_count + 1

    else:

        padding = max(
            1,
            (max_count - min_count)
            * 0.12
        )

        lower = max(
            0,
            min_count - padding
        )

        upper = max_count + padding



    ax.set_ylim(
        lower,
        upper
    )


    # -------------------------------
    # Today guide
    # -------------------------------

    if (
        today in records
        and today in filtered
    ):

        today_count = records[today]

        # Convert today's date to its position
        # inside the X-axis (0 = Y-axis, 1 = right edge)
        x_min, x_max = ax.get_xlim()

        today_x = mdates.date2num(today)

        today_position = (
            (today_x - x_min)
            / (x_max - x_min)
        )

        ax.hlines(
        today_count,
        0,
        today_position,
        transform=ax.get_yaxis_transform(),
        colors="red",
        linestyles="--",
        linewidth=1.2,
        alpha=0.65,
        zorder=2
    )

    ax.vlines(
        today,
        lower,
        today_count,
        colors="red",
        linestyles="--",
        linewidth=1.2,
        alpha=0.65,
        zorder=2
    )
    # -------------------------------
    # Grid and borders
    # -------------------------------

    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.2
    )


    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


    ax.spines["left"].set_color(
        border_color
    )

    ax.spines["bottom"].set_color(
        border_color
    )


    ax.set_xlabel(
        "Date",
        fontsize=10,
        fontweight="bold",
        color=text_color,
        labelpad=12
    )


    ax.set_ylabel(
        "Count",
        fontsize=10,
        fontweight="bold",
        color=text_color,
        labelpad=12
    )


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
        bbox_inches="tight"
    )


    image.seek(0)

    return image