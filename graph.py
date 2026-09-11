from io import BytesIO
from datetime import timedelta

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


def create_graph(logic, timeline="Monthly", theme="dark"):
    records = logic.get_records()

    if not records:
        return None

    days = TIMELINE_DAYS.get(timeline, 30)

    all_dates = sorted(records.keys())
    latest_date = all_dates[-1]
    start_date = latest_date - timedelta(days=days - 1)

    filtered = {
        d: count
        for d, count in records.items()
        if start_date <= d <= latest_date
    }

    if not filtered:
        filtered = {latest_date: records[latest_date]}

    dates = sorted(filtered.keys())
    counts = [filtered[d] for d in dates]

    dark = theme.lower() == "dark"

    card_bg = "#1f2937" if dark else "#ffffff"
    text = "#ffffff" if dark else "#111827"
    secondary_text = "#ffffff" if dark else "#6b7280"
    border = "#374151" if dark else "#d1d5db"
    accent = "#6366f1"
    ax.set_title(
    "Masturbation Trend",
    fontsize=16,
    fontweight="bold",
    color=text,
    pad=18,
    )

    fig = Figure(figsize=(9.2, 4.7), dpi=100)
    ax = fig.add_subplot(111)

    ax.set_facecolor(card_bg)
    fig.patch.set_facecolor(card_bg)

    ax.plot(
        dates,
        counts,
        marker="o",
        markersize=7.5,
        linewidth=2.4,
        color=accent,
        markeredgecolor=accent,
        markerfacecolor=accent,
    )

    ax.set_xticks(dates)
    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%b %d")
    )

    date_count = len(dates)

    if date_count <= 10:
        label_size, rotation = 9, 0
    elif date_count <= 18:
        label_size, rotation = 8, 25
    elif date_count <= 30:
        label_size, rotation = 7, 35
    else:
        label_size, rotation = 6.5, 45

    ax.tick_params(
        axis="x",
        labelsize=label_size,
        pad=8,
        colors=secondary_text,
        rotation=rotation,
    )

    ax.tick_params(
        axis="y",
        labelsize=9,
        colors=secondary_text,
    )

    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_color(secondary_text)
        label.set_fontweight("normal")

    ax.yaxis.set_major_locator(
        MaxNLocator(integer=True)
    )

    x_num = mdates.date2num(dates)

    if len(x_num) == 1:
        ax.set_xlim(
            x_num[0] - 1,
            x_num[0] + 1
        )
    else:
        span = x_num[-1] - x_num[0]
        padding = max(0.75, span * 0.03)

        ax.set_xlim(
            x_num[0] - padding,
            x_num[-1] + padding
        )

    max_count = max(counts)
    min_count = min(counts)

    if max_count == min_count:
        lower = max(0, min_count - 1)
        upper = max_count + 1
    else:
        padding = max(
            1,
            (max_count - min_count) * 0.12
        )

        lower = max(
            0,
            min_count - padding
        )

        upper = max_count + padding

    ax.set_ylim(lower, upper)

    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.20,
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.spines["left"].set_color(border)
    ax.spines["bottom"].set_color(border)

    ax.set_xlabel(
        "Date",
        fontsize=10,
        fontweight="bold",
        labelpad=12,
        color=text,
    )

    ax.set_ylabel(
        "Count",
        fontsize=10,
        fontweight="bold",
        labelpad=12,
        color=text,
    )

    fig.tight_layout()

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