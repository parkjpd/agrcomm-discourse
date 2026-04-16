"""
combined three-panel figure. the money shot.

layout (top to bottom):
  panel 1: news language share (stacked area)
  panel 2: reddit stance mix   (stacked area)
  panel 3: topic prevalence    (heatmap)

all share a 2010-2026 x-axis. event markers overlaid on all three but only
labeled on the top panel to avoid visual clutter.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from common import OUTPUT_DIR
from panels import panel1_language as p1
from panels import panel2_stance as p2
from panels import panel3_topic as p3

X_MIN = date(2010, 1, 1)
X_MAX = date(2026, 12, 31)


def render(output: Path | None = None, live_stance: bool = False, live_topic: bool = False, limit: int | None = None) -> Path:
    output = output or (OUTPUT_DIR / "three_panel.png")

    # ---- load / compute data for each panel ----
    news_share = p1._normalize_to_share(p1.load_news_volumes())
    reddit_share = p1._normalize_to_share(p1.load_reddit_volumes())  # not used in combined but keeps panel 1 module warm

    from collectors import reddit as reddit_col
    reddit_df = reddit_col.pull(demo=not live_stance)
    classified = p2.classify_dataframe(reddit_df, text_col="text", limit=limit, live=live_stance)
    stance_share = p2.aggregate_stance(classified)

    corpus = p3.load_corpus(limit=limit)
    if live_topic:
        topics, top_words, info = p3.fit_topics(corpus)
        tid_to_canonical = {tid: p3._assign_canonical(tw) for tid, tw in zip(info["Topic"].tolist(), top_words)}
        tid_to_canonical[-1] = "other"
        corpus = corpus.copy()
        corpus["topic"] = [tid_to_canonical.get(t, "other") for t in topics]
        topic_share = p3._prevalence_per_year(corpus, "topic")
        topic_note = f"source: BERTopic on {len(corpus)} docs"
    elif "true_topic" in corpus.columns and corpus["true_topic"].notna().any():
        topic_share = p3._prevalence_per_year(corpus, "true_topic")
        topic_note = "source: synthetic truth topics (demo)"
    else:
        corpus = corpus.copy()
        corpus["topic"] = corpus["text"].astype(str).map(p3._rule_based_topic)
        topic_share = p3._prevalence_per_year(corpus, "topic")
        topic_note = "source: keyword fallback"

    stance_note = "source: live haiku" if live_stance else (
        "source: synthetic truth stance (demo)" if "true_stance" in classified.columns else "source: rule-based fallback"
    )
    lang_note = "source: " + ", ".join(sorted(set(p1.load_news_volumes().get("source", pd.Series(["none"])).unique().tolist())))

    # ---- figure ----
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True, gridspec_kw={"height_ratios": [1, 1, 1.2]})

    # top: language (shows event labels)
    p1._plot_stacked(axes[0], news_share, "panel 1 — language share (news)", show_event_labels=True)
    axes[0].text(0.99, 0.04, lang_note, ha="right", va="bottom", transform=axes[0].transAxes, fontsize=7, color="#666")

    # middle: stance (labels already on top panel so suppress here)
    p2.plot_stance(stance_share, axes[1], "panel 2 — stance mix (reddit)", note=stance_note, show_event_labels=False)

    # bottom: topic heatmap (labels suppressed)
    p3.plot_heatmap(topic_share, axes[2], "panel 3 — topic prevalence", note=topic_note, show_event_labels=False)

    for ax in axes:
        ax.set_xlim(X_MIN, X_MAX)

    fig.suptitle(
        "public discourse on migrant farm labor, 2010-2026 — language / stance / topic",
        fontsize=13,
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(output, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return output


if __name__ == "__main__":
    import argparse

    matplotlib.use("Agg")
    ap = argparse.ArgumentParser()
    ap.add_argument("--live-stance", action="store_true")
    ap.add_argument("--live-topic", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    p = render(live_stance=args.live_stance, live_topic=args.live_topic, limit=args.limit)
    print(f"wrote {p}")
