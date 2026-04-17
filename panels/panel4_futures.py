"""
panel 4 (bonus / experimental) - discourse vs agricultural futures.

two renderings:
  plot_overlay    : futures prices (normalized) overlaid on panel 1 enforcement-framed share
  plot_correlation: rolling correlation matrix between discourse and each ticker

hypothesis: spikes in enforcement-framed discourse or pro-enforcement stance
should precede / coincide with moves in labor-heavy commodity futures
(FCOJ, class III milk, sugar) but not in low-labor corn.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from collectors import futures
from common import OUTPUT_DIR, PROCESSED_DIR
from panels.panel1_language import _normalize_to_share, load_news_volumes
from viz.event_overlay import draw as draw_events

LABOR_HEAVY = ["FCOJ", "milk_class_iii", "sugar_11"]
BASELINE = ["corn_baseline"]

TICKER_COLORS = {
    "FCOJ":           "#e76f51",
    "milk_class_iii": "#2a9d8f",
    "sugar_11":       "#e9c46a",
    "live_cattle":    "#8b5a2b",
    "corn_baseline":  "#888888",
}
TICKER_DISPLAY = {
    "FCOJ":           "FCOJ (orange juice)",
    "milk_class_iii": "class III milk",
    "sugar_11":       "sugar #11",
    "live_cattle":    "live cattle",
    "corn_baseline":  "corn (baseline)",
}


def load_futures_quarterly() -> pd.DataFrame:
    path = PROCESSED_DIR / "panel4_futures_quarterly.csv"
    if not path.exists():
        data = futures.pull_all()
        futures.save_panel4(data)
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


def _normalize_series(s: pd.Series) -> pd.Series:
    """index to 100 at first non-null value."""
    s = s.dropna()
    if s.empty:
        return s
    return s / s.iloc[0] * 100


def _enforcement_share_quarterly() -> pd.Series:
    share = _normalize_to_share(load_news_volumes())
    if share.empty or "right_loaded" not in share.columns:
        return pd.Series(dtype=float)
    return share["right_loaded"]


def event_window_returns(window_days: int = 30) -> pd.DataFrame:
    """
    for each event in events.yaml, compute cumulative return for each ticker
    over [-window, 0] (pre) and [0, +window] (post) trading-day windows.
    returns long-form df: (event, ticker, pre_return, post_return, diff).
    """
    from common import load_events
    from collectors import futures as fut_col

    daily = fut_col.pull_all()
    rows = []
    for ev in load_events():
        ev_date = pd.to_datetime(str(ev["date"])[:10])
        for ticker, df in daily.items():
            if df is None or df.empty:
                continue
            d = df.copy()
            d["date"] = pd.to_datetime(d["date"])
            d = d.sort_values("date").set_index("date")
            # pick window of trading days around the event
            pre = d.loc[ev_date - pd.Timedelta(days=window_days * 2):ev_date].tail(window_days)
            post = d.loc[ev_date:ev_date + pd.Timedelta(days=window_days * 2)].head(window_days)
            if len(pre) < 5 or len(post) < 5:
                continue
            pre_ret = (pre["close"].iloc[-1] / pre["close"].iloc[0]) - 1 if len(pre) else None
            post_ret = (post["close"].iloc[-1] / post["close"].iloc[0]) - 1 if len(post) else None
            rows.append({
                "event": ev["shown"],
                "date": ev_date.date().isoformat(),
                "category": ev.get("category", ""),
                "ticker": ticker,
                "pre_return": pre_ret,
                "post_return": post_ret,
                "post_minus_pre": (post_ret or 0) - (pre_ret or 0),
            })
    return pd.DataFrame(rows)


def correlation_table() -> pd.DataFrame:
    """correlation between enforcement-framed share and each ticker's quarterly returns."""
    fut = load_futures_quarterly()
    enf = _enforcement_share_quarterly()
    if enf.empty or fut.empty:
        return pd.DataFrame()

    rows = []
    enf.index = pd.to_datetime(enf.index)
    for ticker in TICKERS_ALL():
        sub = fut[fut["ticker"] == ticker].set_index("date")["close"]
        if sub.empty:
            continue
        # quarterly returns (pct change)
        sub_ret = sub.pct_change().dropna()
        # align indices
        common = enf.index.intersection(sub_ret.index)
        if len(common) < 5:
            rows.append({"ticker": ticker, "n": len(common), "corr_pearson": None, "corr_spearman": None})
            continue
        a = enf.loc[common]
        b = sub_ret.loc[common]
        rows.append({
            "ticker": ticker,
            "n": len(common),
            "corr_pearson":  float(a.corr(b, method="pearson")),
            "corr_spearman": float(a.corr(b, method="spearman")),
        })
    return pd.DataFrame(rows)


def TICKERS_ALL():
    return LABOR_HEAVY + ["live_cattle"] + BASELINE


def plot_overlay(output: Path | None = None) -> Path:
    output = output or (OUTPUT_DIR / "panel4_futures_overlay.png")
    fut = load_futures_quarterly()
    enf = _enforcement_share_quarterly()

    fig, ax1 = plt.subplots(1, 1, figsize=(14, 5))

    # left y-axis: enforcement-framed share
    if not enf.empty:
        ax1.fill_between(enf.index, enf.values, color="#c23b22", alpha=0.35, label="enforcement-framed share (news)")
        ax1.set_ylabel("enforcement-framed share", color="#c23b22")
        ax1.tick_params(axis="y", labelcolor="#c23b22")
    ax1.set_ylim(0, max(0.25, enf.max() * 1.2) if not enf.empty else 0.25)

    # right y-axis: futures prices, normalized to 100 at start
    ax2 = ax1.twinx()
    for ticker in TICKERS_ALL():
        sub = fut[fut["ticker"] == ticker].set_index("date")["close"]
        norm = _normalize_series(sub)
        if norm.empty:
            continue
        ax2.plot(
            norm.index, norm.values,
            color=TICKER_COLORS[ticker],
            label=TICKER_DISPLAY[ticker],
            lw=1.4,
            alpha=0.9 if ticker in LABOR_HEAVY else 0.6,
        )
    ax2.set_ylabel("ag futures, indexed to 100 @ 2010-01", color="#333")
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    draw_events(ax1)

    # combined legend
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8, framealpha=0.85)

    ax1.set_title("panel 4 (bonus) — enforcement-framed discourse vs ag futures")
    fig.tight_layout()
    fig.savefig(output, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return output


def render(output: Path | None = None) -> Path:
    return plot_overlay(output)


if __name__ == "__main__":
    matplotlib.use("Agg")
    p = render()
    print(f"wrote {p}")
    corr = correlation_table()
    print("\ncorrelation: enforcement-framed share vs quarterly returns")
    print(corr.to_string(index=False))
