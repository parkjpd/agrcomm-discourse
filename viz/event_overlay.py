"""shared event overlay. every panel calls draw(ax) to get the same markers."""
from __future__ import annotations

from datetime import date, datetime

import matplotlib.dates as mdates
from matplotlib.axes import Axes

from common import load_events

CATEGORY_STYLES = {
    "election":    {"linestyle": "-",  "color": "#111111", "lw": 1.2, "alpha": 0.85},
    "enforcement": {"linestyle": "--", "color": "#c23b22", "lw": 1.0, "alpha": 0.75},
    "pandemic":    {"linestyle": "--", "color": "#2a9d8f", "lw": 1.0, "alpha": 0.75},
    "legal":       {"linestyle": "--", "color": "#6b4b9a", "lw": 1.0, "alpha": 0.75},
    "policy":      {"linestyle": ":",  "color": "#555555", "lw": 1.0, "alpha": 0.7},
}


def _parse_date(s: str | date) -> date:
    if isinstance(s, date):
        return s
    return datetime.strptime(s, "%Y-%m-%d").date()


def draw(ax: Axes, label_events: bool = True, y_label_pos: float = 0.98) -> None:
    """Overlay every event from config/events.yaml onto ax."""
    events = load_events()
    for ev in events:
        d = _parse_date(ev["date"])
        style = CATEGORY_STYLES.get(ev["category"], CATEGORY_STYLES["policy"])
        ax.axvline(d, **style)

    if label_events:
        # labels sit along the top. small rotation for readability.
        y = y_label_pos
        for ev in events:
            d = _parse_date(ev["date"])
            ax.annotate(
                ev["shown"],
                xy=(mdates.date2num(d), y),
                xycoords=("data", "axes fraction"),
                xytext=(3, -3),
                textcoords="offset points",
                fontsize=7,
                rotation=90,
                ha="left",
                va="top",
                color="#222",
            )


def event_dates() -> list[date]:
    return [_parse_date(ev["date"]) for ev in load_events()]
