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

LABOR_HEAVY = ["FCOJ", "milk_class_iii", "sugar_11", "coffee"]
MODERATE = ["live_cattle", "cotton"]
BASELINE = ["soybeans", "corn_baseline"]

TICKER_COLORS = {
    "FCOJ":           "#e76f51",
    "milk_class_iii": "#2a9d8f",
    "sugar_11":       "#e9c46a",
    "coffee":         "#6f4e37",
    "cotton":         "#cbd5e8",
    "live_cattle":    "#8b5a2b",
    "soybeans":       "#aaaaaa",
    "corn_baseline":  "#888888",
}
TICKER_DISPLAY = {
    "FCOJ":           "FCOJ (orange juice)",
    "milk_class_iii": "class III milk",
    "sugar_11":       "sugar #11",
    "coffee":         "coffee",
    "cotton":         "cotton",
    "live_cattle":    "live cattle",
    "soybeans":       "soybeans (baseline)",
    "corn_baseline":  "corn (baseline)",
}

# labor-exposure score 0-1: used for sorting + ranking charts.
# rough heuristic: 1 = almost all hand-picked / H-2A, 0 = fully mechanized.
LABOR_EXPOSURE = {
    "FCOJ":           0.95,  # florida citrus, H-2A heavy
    "coffee":         0.90,  # almost entirely hand-picked globally
    "sugar_11":       0.75,  # some mechanized but labor-heavy harvest crews
    "milk_class_iii": 0.70,  # dairy workers heavily immigrant
    "cotton":         0.35,  # mostly mechanized now, some hand labor
    "live_cattle":    0.30,  # moderate labor in feedlots + ranches
    "soybeans":       0.05,  # fully mechanized
    "corn_baseline":  0.05,  # fully mechanized
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


def daily_enforcement_share(method: str = "ffill") -> pd.Series:
    """expand quarterly news enforcement share into a daily series so we can
    correlate with daily futures returns. forward-fills each quarter to
    every trading day."""
    share = _enforcement_share_quarterly()
    if share.empty:
        return share
    share.index = pd.to_datetime(share.index)
    # pad to daily by reindexing onto a business-day range and forward filling
    daily_idx = pd.date_range(share.index.min(), share.index.max() + pd.offsets.QuarterEnd(1), freq="B")
    daily = share.reindex(daily_idx).ffill().bfill()
    return daily


def discourse_sensitivity() -> pd.DataFrame:
    """for every ticker, compute correlation between the 60-day rolling
    enforcement-framing share and the 60-day forward return. this gives a
    cleaner "sensitivity" score than raw correlation of quarterly levels."""
    from collectors import futures as fut_col

    enf_daily = daily_enforcement_share()
    if enf_daily.empty:
        return pd.DataFrame()

    rows = []
    daily_by_ticker = fut_col.pull_all()
    for ticker, df in daily_by_ticker.items():
        if df is None or df.empty:
            continue
        d = df.copy()
        d["date"] = pd.to_datetime(d["date"])
        d = d.sort_values("date").set_index("date")
        # forward 60-trading-day log return
        fwd_ret = (d["close"].pct_change(60).shift(-60)).dropna()
        common = enf_daily.index.intersection(fwd_ret.index)
        if len(common) < 200:
            continue
        a = enf_daily.loc[common]
        b = fwd_ret.loc[common]
        corr_p = float(a.corr(b, method="pearson"))
        corr_s = float(a.corr(b, method="spearman"))
        # regression beta: how much does 60d fwd return change per 1pp increase in enf share
        var = float(a.var())
        cov = float(((a - a.mean()) * (b - b.mean())).mean())
        beta = cov / var if var > 0 else 0.0
        rows.append({
            "ticker": ticker,
            "labor_exposure": LABOR_EXPOSURE.get(ticker, 0),
            "n_obs": int(len(common)),
            "corr_pearson":  corr_p,
            "corr_spearman": corr_s,
            "beta_per_pp":   float(beta) / 100.0,  # convert to "per pp" scale
        })
    return pd.DataFrame(rows).sort_values("labor_exposure", ascending=False)


def regime_cumulative_returns() -> pd.DataFrame:
    """split the sample into 'high enforcement framing' and 'low enforcement
    framing' quarters (above / below median) and compute geometric mean return
    for each ticker in each regime. shows whether labor-heavy commodities
    underperform when enforcement rhetoric is loud."""
    from collectors import futures as fut_col

    enf_q = _enforcement_share_quarterly()
    if enf_q.empty:
        return pd.DataFrame()
    median = enf_q.median()

    daily_by_ticker = fut_col.pull_all()
    rows = []
    for ticker, df in daily_by_ticker.items():
        if df is None or df.empty:
            continue
        d = df.copy()
        d["date"] = pd.to_datetime(d["date"])
        d = d.sort_values("date").set_index("date")
        # quarterly returns
        q_close = d["close"].resample("QS").mean()
        q_ret = q_close.pct_change().dropna()
        common = enf_q.index.intersection(q_ret.index)
        if len(common) < 10:
            continue
        e = enf_q.loc[common]
        r = q_ret.loc[common]
        hi_ret = r[e >= median]
        lo_ret = r[e < median]
        # annualized geometric mean return (4 quarters)
        hi_ann = ((1 + hi_ret).prod()) ** (4 / max(len(hi_ret), 1)) - 1 if len(hi_ret) else 0
        lo_ann = ((1 + lo_ret).prod()) ** (4 / max(len(lo_ret), 1)) - 1 if len(lo_ret) else 0
        rows.append({
            "ticker": ticker,
            "labor_exposure": LABOR_EXPOSURE.get(ticker, 0),
            "annualized_return_high_enf":  float(hi_ann),
            "annualized_return_low_enf":   float(lo_ann),
            "spread_high_minus_low":       float(hi_ann - lo_ann),
            "n_hi_quarters": int(len(hi_ret)),
            "n_lo_quarters": int(len(lo_ret)),
        })
    return pd.DataFrame(rows).sort_values("labor_exposure", ascending=False)


def event_impact_detail(window_days: int = 30) -> pd.DataFrame:
    """richer version of event_window_returns: adds labor exposure + direction + rank."""
    df = event_window_returns(window_days=window_days)
    if df.empty:
        return df
    df["labor_exposure"] = df["ticker"].map(LABOR_EXPOSURE)
    df["abs_delta"] = df["post_minus_pre"].abs()
    df = df.sort_values(["event", "abs_delta"], ascending=[True, False])
    return df


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
    return LABOR_HEAVY + MODERATE + BASELINE


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
