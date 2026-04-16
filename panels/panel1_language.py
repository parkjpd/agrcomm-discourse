"""
panel 1 - language. stacked area per source showing keyword-bucket share over time.

inputs:
  news volumes: data/processed/panel1_news_volumes.csv    (gdelt)
  news volumes: data/processed/panel1_news_volumes_mc.csv (media cloud, pre-2017 baseline)
  reddit posts: data/processed/reddit_posts.csv           (live reddit)
  if none exist, falls back to data/samples/*.csv

output: output/panel1_language.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from common import OUTPUT_DIR, PROCESSED_DIR, SAMPLES_DIR, load_keywords
from viz.event_overlay import draw as draw_events


def _bucket_for(text: str, buckets: dict) -> str | None:
    """return the first bucket whose terms appear in text. right > left > neutral priority
    is intentional — 'illegal alien' should count as right_loaded even if the post mentions
    'farmworker' elsewhere."""
    lower = text.lower()
    for bucket_name in ("right_loaded", "left_loaded", "neutral"):
        for term in buckets[bucket_name]["terms"]:
            if term.lower() in lower:
                return bucket_name
    return None


def _quarter_key(d: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(d.year, ((d.month - 1) // 3) * 3 + 1, 1)


def _count_keywords_in_text(df: pd.DataFrame, text_col: str = "text") -> pd.DataFrame:
    """take a df with date + text, emit (date, bucket, count) rows quarterly."""
    kw = load_keywords()
    buckets = kw["buckets"]
    df = df.copy()
    df["bucket"] = df[text_col].fillna("").astype(str).map(lambda t: _bucket_for(t, buckets))
    df = df.dropna(subset=["bucket"])
    df["date"] = pd.to_datetime(df["date"])
    df["quarter"] = df["date"].map(_quarter_key)
    out = df.groupby(["quarter", "bucket"]).size().reset_index(name="count")
    out.rename(columns={"quarter": "date"}, inplace=True)
    out["date"] = out["date"].dt.date.astype(str)
    return out


def load_news_volumes() -> pd.DataFrame:
    """combine processed volumes (gdelt + media cloud) if present, else derive from synthetic news."""
    frames = []
    gdelt_path = PROCESSED_DIR / "panel1_news_volumes.csv"
    mc_path = PROCESSED_DIR / "panel1_news_volumes_mc.csv"
    if gdelt_path.exists():
        g = pd.read_csv(gdelt_path)
        # sum across terms within bucket per quarter
        g = g.groupby(["date", "bucket"])["count"].sum().reset_index()
        g["source"] = "gdelt"
        frames.append(g)
    if mc_path.exists():
        m = pd.read_csv(mc_path)
        frames.append(m)

    if frames:
        return pd.concat(frames, ignore_index=True)

    # fallback: derive volume from synthetic news corpus
    syn_path = SAMPLES_DIR / "news.csv"
    if not syn_path.exists():
        return pd.DataFrame(columns=["date", "bucket", "count", "source"])
    syn = pd.read_csv(syn_path)
    syn["text"] = syn["title"].fillna("") + " " + syn["text"].fillna("")
    return _count_keywords_in_text(syn).assign(source="synthetic_news")


def load_reddit_volumes() -> pd.DataFrame:
    """quarterly per-bucket counts from reddit posts."""
    candidates = [PROCESSED_DIR / "reddit_posts.csv", SAMPLES_DIR / "reddit.csv"]
    for p in candidates:
        if p.exists():
            df = pd.read_csv(p)
            df["text"] = df.get("title", "").fillna("") + " " + df.get("text", "").fillna("")
            out = _count_keywords_in_text(df)
            out["source"] = df["source"].iloc[0] if "source" in df.columns else p.stem
            return out
    return pd.DataFrame(columns=["date", "bucket", "count", "source"])


def _normalize_to_share(df: pd.DataFrame) -> pd.DataFrame:
    """given (date, bucket, count), return (date, bucket, share) where share sums to 1 per date."""
    pivot = df.pivot_table(index="date", columns="bucket", values="count", aggfunc="sum", fill_value=0)
    for b in ("right_loaded", "left_loaded", "neutral"):
        if b not in pivot.columns:
            pivot[b] = 0
    pivot = pivot[["right_loaded", "left_loaded", "neutral"]]
    totals = pivot.sum(axis=1).replace(0, pd.NA)
    share = pivot.div(totals, axis=0).fillna(0)
    share.index = pd.to_datetime(share.index)
    return share.sort_index()


def _plot_stacked(ax, share_df: pd.DataFrame, title: str):
    kw = load_keywords()["buckets"]
    cols = ["right_loaded", "left_loaded", "neutral"]
    colors = [kw[c]["color"] for c in cols]
    labels = [kw[c]["display"] for c in cols]

    if share_df.empty:
        ax.text(0.5, 0.5, f"no data for {title}", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title)
        return

    x = share_df.index
    ys = [share_df[c].values for c in cols]
    ax.stackplot(x, ys, labels=labels, colors=colors, alpha=0.85)

    ax.set_ylim(0, 1)
    ax.set_ylabel("share of mentions")
    ax.set_title(title)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", alpha=0.2)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)

    draw_events(ax)


def render(output: Path | None = None) -> Path:
    output = output or (OUTPUT_DIR / "panel1_language.png")
    news = _normalize_to_share(load_news_volumes())
    reddit = _normalize_to_share(load_reddit_volumes())

    fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
    _plot_stacked(axes[0], news, "panel 1 — news: language share by bucket")
    _plot_stacked(axes[1], reddit, "panel 1 — reddit: language share by bucket")
    axes[1].set_xlabel("year")

    fig.suptitle("what words do people use? (migrant farm labor 2010-2026)", fontsize=11)
    fig.tight_layout()
    fig.savefig(output, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return output


if __name__ == "__main__":
    matplotlib.use("Agg")
    p = render()
    print(f"wrote {p}")
