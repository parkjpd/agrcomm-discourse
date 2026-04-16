"""
panel 3 - topic. BERTopic + all-MiniLM-L6-v2 on the combined news + reddit corpus.

two modes:
  live:  fit BERTopic, hand-label the top clusters, aggregate prevalence per year.
  demo:  if inputs have a `true_topic` column (synthetic), aggregate those directly.

the heatmap renders identically in either mode.

run:
  python -m panels.panel3_topic            # demo mode off synthetic
  python -m panels.panel3_topic --live     # actual bertopic fit
  python -m panels.panel3_topic --limit 5000   # subsample for speed
"""
from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import OUTPUT_DIR, PROCESSED_DIR, SAMPLES_DIR, load_sources
from viz.event_overlay import draw as draw_events

# ---------- topic labels (hand-curated) ----------
# when running live, bertopic will produce numeric cluster ids. after inspection we
# relabel them to these human-readable buckets. the mapping below matches the
# topic keys used by the synthetic generator so demo and live modes render comparably.

CANONICAL_TOPICS = [
    "enforcement",
    "border",
    "deportation",
    "criminal",
    "economic",
    "cropLoss",
    "essential",
    "humanitarian",
]

TOPIC_DISPLAY = {
    "enforcement":   "ICE / workplace enforcement",
    "border":        "border / migration flow",
    "deportation":   "deportation operations",
    "criminal":      "criminal framing",
    "economic":      "economic contribution",
    "cropLoss":      "crop loss / labor shortage",
    "essential":     "essential worker framing",
    "humanitarian":  "humanitarian / families",
}

# rule-based cluster labeler used when running live BERTopic. looks at the top
# representative words for each cluster and maps to one of CANONICAL_TOPICS.
TOPIC_SEED_WORDS = {
    "enforcement":  ["ice", "raid", "enforcement", "audit", "e-verify", "worksite", "workplace"],
    "border":       ["border", "crossing", "patrol", "wall", "migration"],
    "deportation":  ["deport", "deportation", "removal", "flight", "self-deport"],
    "criminal":     ["criminal", "felony", "smuggling", "prosecution", "detention"],
    "economic":     ["wage", "economy", "tax", "revenue", "employer", "cost"],
    "cropLoss":     ["rot", "crop", "harvest", "unpicked", "shortage", "field"],
    "essential":    ["essential", "pandemic", "frontline", "critical"],
    "humanitarian": ["family", "separation", "children", "dreamer", "human"],
}


def _assign_canonical(top_words: list[str]) -> str:
    """pick the canonical topic whose seed words best match the cluster's top words."""
    scores = {t: 0 for t in CANONICAL_TOPICS}
    lower = [w.lower() for w in top_words]
    for topic, seeds in TOPIC_SEED_WORDS.items():
        for s in seeds:
            if any(s in w for w in lower):
                scores[topic] += 1
    best = max(scores, key=lambda t: scores[t])
    if scores[best] == 0:
        return "other"
    return best


# ---------- data loading ----------

def load_corpus(limit: int | None = None) -> pd.DataFrame:
    """combine processed + sample data. returns df with date, text, source, [true_topic]."""
    frames = []
    cand = [
        (PROCESSED_DIR / "reddit_posts.csv", None),
        (PROCESSED_DIR / "news_articles_gdelt.csv", None),
        (SAMPLES_DIR / "reddit.csv", "synthetic_reddit"),
        (SAMPLES_DIR / "news.csv", "synthetic_news"),
    ]
    for path, fallback_source in cand:
        if path.exists():
            df = pd.read_csv(path)
            if "text" not in df.columns:
                df["text"] = df.get("title", "").fillna("")
            if "source" not in df.columns and fallback_source:
                df["source"] = fallback_source
            # dedup on any (processed) that would overlap samples
            if "synthetic" in str(fallback_source or ""):
                already = [f["source"].iloc[0] for f in frames if not f.empty and "source" in f.columns]
                if fallback_source in already:
                    continue
            frames.append(df[[c for c in ("date", "text", "source", "true_topic") if c in df.columns]].copy())
    if not frames:
        return pd.DataFrame(columns=["date", "text", "source"])
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["text"])
    df = df[df["text"].astype(str).str.strip().str.len() > 10]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if limit:
        df = df.sample(n=min(limit, len(df)), random_state=42).reset_index(drop=True)
    return df


# ---------- BERTopic fit ----------

def fit_topics(df: pd.DataFrame) -> tuple[list[int], list[list[str]]]:
    """fit BERTopic, return (topic_per_doc, top_words_per_topic)."""
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer

    cfg = load_sources()["panel3"]
    embed_model = SentenceTransformer(cfg["embedding_model"])
    model = BERTopic(
        embedding_model=embed_model,
        min_topic_size=cfg.get("min_topic_size", 30),
        calculate_probabilities=False,
        verbose=True,
    )
    texts = df["text"].astype(str).tolist()
    topics, _ = model.fit_transform(texts)
    # cache the fitted model for re-use
    out = PROCESSED_DIR / "panel3_bertopic.pkl"
    try:
        model.save(str(out), serialization="pickle")
    except Exception as e:
        print(f"  could not save model: {e}")

    top_words = []
    info = model.get_topic_info()
    for tid in info["Topic"].tolist():
        if tid == -1:
            top_words.append([])
            continue
        words = [w for w, _ in (model.get_topic(tid) or [])[:10]]
        top_words.append(words)
    return topics, top_words, info


# ---------- prevalence aggregation ----------

def _prevalence_per_year(df: pd.DataFrame, topic_col: str) -> pd.DataFrame:
    """given df with date + topic_col, return rows x topics x year-share."""
    d = df.dropna(subset=[topic_col]).copy()
    d["year"] = pd.to_datetime(d["date"]).dt.year
    counts = d.groupby(["year", topic_col]).size().unstack(fill_value=0)
    totals = counts.sum(axis=1).replace(0, pd.NA)
    share = counts.div(totals, axis=0).fillna(0)
    # keep canonical topics in stable row order, drop "other" for chart clarity
    cols = [t for t in CANONICAL_TOPICS if t in share.columns]
    share = share[cols].T  # topics x years
    return share


# ---------- heatmap ----------

def plot_heatmap(share: pd.DataFrame, ax, title: str, note: str = "", show_event_labels: bool = False):
    """heatmap uses date-based x-axis so it aligns with panels 1+2 in the combined figure."""
    from datetime import date
    import matplotlib.dates as mdates

    if share.empty:
        ax.text(0.5, 0.5, "no topics", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title)
        return

    years = share.columns.astype(int).tolist()
    x_edges = [date(y, 1, 1) for y in years] + [date(max(years) + 1, 1, 1)]
    y_edges = np.arange(len(share.index) + 1)

    mesh = ax.pcolormesh(x_edges, y_edges, share.values, cmap="viridis", shading="flat")
    ax.set_yticks(np.arange(len(share.index)) + 0.5)
    ax.set_yticklabels([TOPIC_DISPLAY.get(t, t) for t in share.index], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("year")
    ax.set_title(title)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    cbar = plt.colorbar(mesh, ax=ax, pad=0.01)
    cbar.set_label("share of year's discourse")

    draw_events(ax, show_labels=show_event_labels)

    if note:
        ax.text(1.0, -0.18, note, ha="right", va="top", transform=ax.transAxes, fontsize=7, color="#666")


def render(live: bool = False, limit: int | None = None, output: Path | None = None) -> Path:
    output = output or (OUTPUT_DIR / "panel3_topic.png")
    df = load_corpus(limit=limit)
    if df.empty:
        raise RuntimeError("no corpus data - run collectors or scripts/make_samples first")

    mode_note = ""
    if live:
        print(f"fitting bertopic on {len(df)} docs ...")
        topics, top_words, info = fit_topics(df)
        # map cluster ids to canonical topics
        tid_to_canonical = {tid: _assign_canonical(tw) for tid, tw in zip(info["Topic"].tolist(), top_words)}
        tid_to_canonical[-1] = "other"
        df = df.copy()
        df["topic"] = [tid_to_canonical.get(t, "other") for t in topics]
        share = _prevalence_per_year(df, "topic")
        mode_note = f"source: BERTopic on {len(df)} docs"
    else:
        if "true_topic" in df.columns and df["true_topic"].notna().any():
            share = _prevalence_per_year(df, "true_topic")
            mode_note = "source: synthetic truth topics (demo mode)"
        else:
            # no truth labels and not live - cheap keyword fallback so chart still renders
            from panels.panel3_topic import _rule_based_topic
            df["topic"] = df["text"].astype(str).map(_rule_based_topic)
            share = _prevalence_per_year(df, "topic")
            mode_note = "source: keyword fallback (no truth labels, not live)"

    fig, ax = plt.subplots(1, 1, figsize=(14, 5))
    plot_heatmap(share, ax, "panel 3 — topic prevalence by year", note=mode_note)
    fig.tight_layout()
    fig.savefig(output, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return output


def _rule_based_topic(text: str) -> str:
    lower = text.lower()
    best_topic = "other"
    best_hits = 0
    for topic, seeds in TOPIC_SEED_WORDS.items():
        hits = sum(1 for s in seeds if s in lower)
        if hits > best_hits:
            best_hits = hits
            best_topic = topic
    return best_topic


if __name__ == "__main__":
    matplotlib.use("Agg")
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="actually fit bertopic (slow, heavy deps)")
    ap.add_argument("--limit", type=int, default=None, help="subsample corpus for speed")
    args = ap.parse_args()
    p = render(live=args.live, limit=args.limit)
    print(f"wrote {p}")
