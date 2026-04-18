"""
render the three dashboard charts that answer david's row of the agcomm 2330
assignment. outputs to output/assignment_*.png at 1.5x device scale (good for
slide decks + docs).

run: python -m scripts.export_assignment_charts
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from common import OUTPUT_DIR, PROCESSED_DIR
from panels.panel1_language import _normalize_to_share, load_news_volumes
from panels.panel2_stance import aggregate_stance
from viz import plotly_charts as pc


def _png(fig, path: Path, width: int = 1400, height: int = 520, scale: float = 2.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(path), format="png", width=width, height=height, scale=scale)
    return path


def export_reddit_opinions() -> Path:
    df = pd.read_csv(PROCESSED_DIR / "reddit_posts_stance.csv")
    share = aggregate_stance(df)
    fig = pc.stance_stacked_area(share, "Reddit stance on migrant farm labor, 2015–2026 (share of posts)")
    # inline a taller subtitle-style annotation explaining the key finding
    fig.add_annotation(
        xref="paper", yref="paper", x=0.0, y=1.13, showarrow=False, xanchor="left",
        text="Pro-enforcement share (red) ~17% during Obama/COVID/Biden, jumps to ~27% during both Trump terms",
        font=dict(size=11, color="#333"),
    )
    fig.update_layout(margin=dict(t=110, b=40, l=60, r=20))
    return _png(fig, OUTPUT_DIR / "assignment_reddit_opinions.png", width=1400, height=560)


def export_platform_comparison() -> Path:
    fb = pd.read_csv(PROCESSED_DIR / "fb_ads.csv")
    yt = pd.read_csv(PROCESSED_DIR / "youtube_comments.csv")
    reddit = pd.read_csv(PROCESSED_DIR / "reddit_posts_stance.csv")
    dfs = {"reddit": reddit, "fb_ads": fb, "youtube": yt}
    fig = pc.platform_stance_comparison(dfs, "Stance mix by platform — same topic, different audiences")
    fig.add_annotation(
        xref="paper", yref="paper", x=0.0, y=1.13, showarrow=False, xanchor="left",
        text="Facebook ads are most polarized (paid sponsors pick a side); Reddit has the biggest neutral middle",
        font=dict(size=11, color="#333"),
    )
    fig.update_layout(margin=dict(t=110, b=40, l=60, r=20))
    return _png(fig, OUTPUT_DIR / "assignment_platform_comparison.png", width=1200, height=520)


def export_event_waterfall() -> Path:
    news = _normalize_to_share(load_news_volumes())
    fig = pc.event_discourse_waterfall(news, window_days=90, title="Change in enforcement framing, 90 days after each policy event")
    fig.add_annotation(
        xref="paper", yref="paper", x=0.0, y=1.06, showarrow=False, xanchor="left",
        text="Most events move framing <2 pp; biggest movers are election results + major ICE actions",
        font=dict(size=11, color="#333"),
    )
    fig.update_layout(margin=dict(t=90, b=60, l=280, r=60))
    return _png(fig, OUTPUT_DIR / "assignment_event_waterfall.png", width=1400, height=720)


def main():
    paths = [
        export_reddit_opinions(),
        export_platform_comparison(),
        export_event_waterfall(),
    ]
    print("wrote:")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
