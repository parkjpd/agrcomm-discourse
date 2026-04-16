"""
panel 2 - stance. three-way classification via claude haiku 4.5.

pipeline:
  1. collectors/reddit.pull() -> dataframe of posts
  2. classify each post via haiku (cached in sqlite - re-runs are free)
  3. aggregate by quarter -> 100% stacked area

demo mode: if the input df has a `true_stance` column (synthetic samples do),
skip classification and plot the truth labels directly. this lets the chart
render end-to-end without API cost.

run standalone:
  python -m panels.panel2_stance
  python -m panels.panel2_stance --live        # actually call haiku
  python -m panels.panel2_stance --limit 100   # only classify first N
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm

from collectors import reddit as reddit_col
from common import OUTPUT_DIR, PROCESSED_DIR, cache_get, cache_put, load_sources, load_stance_rubric
from viz.event_overlay import draw as draw_events

NAMESPACE = "panel2_stance"
LABELS = ("pro_enforcement", "pro_immigrant_labor", "neutral_mixed")
COLORS = {
    "pro_enforcement": "#c23b22",
    "pro_immigrant_labor": "#2e75b6",
    "neutral_mixed": "#bfbfbf",
}


def _build_system_prompt() -> str:
    rubric = load_stance_rubric()
    bullets = lambda key: "\n".join(f"  - {b}" for b in rubric.get(f"{key}_indicators", []))
    return rubric["prompt"].format(
        pro_enforcement_bullets=bullets("pro_enforcement"),
        pro_immigrant_labor_bullets=bullets("pro_immigrant_labor"),
        neutral_mixed_bullets=bullets("neutral_mixed"),
        post="{post}",
    )


def _normalize_label(raw: str) -> str | None:
    if not raw:
        return None
    raw = raw.strip().lower().replace("-", "_").replace(" ", "_")
    for L in LABELS:
        if L in raw:
            return L
    return None


async def _classify_one(client, prompt_template: str, post: str, model: str, sem) -> str | None:
    """one haiku call with rubric cached via cache_control."""
    async with sem:
        req = {"prompt_template": prompt_template, "post": post, "model": model}
        cached = cache_get(NAMESPACE, req)
        if cached is not None:
            return cached

        rubric_part, _, post_marker = prompt_template.partition("{post}")
        system_blocks = [
            {"type": "text", "text": rubric_part, "cache_control": {"type": "ephemeral"}},
        ]
        user_text = f"Post:\n\"\"\"\n{post}\n\"\"\"\n\nRespond with ONLY the label string. No explanation."

        for attempt in range(3):
            try:
                resp = await client.messages.create(
                    model=model,
                    max_tokens=20,
                    system=system_blocks,
                    messages=[{"role": "user", "content": user_text}],
                )
                text = resp.content[0].text if resp.content else ""
                label = _normalize_label(text)
                cache_put(NAMESPACE, req, label, summary=text[:50])
                return label
            except Exception as e:
                if attempt == 2:
                    print(f"  stance call failed: {type(e).__name__}: {e}", file=sys.stderr)
                    return None
                await asyncio.sleep(1.5 * (attempt + 1))
    return None


async def _classify_batch(texts: list[str], model: str, max_concurrency: int = 8) -> list[str | None]:
    """call haiku for every text in order. cached hits return instantly."""
    from anthropic import AsyncAnthropic

    prompt = _build_system_prompt()
    sem = asyncio.Semaphore(max_concurrency)
    client = AsyncAnthropic()
    tasks = [asyncio.create_task(_classify_one(client, prompt, t, model, sem)) for t in texts]
    # drain with a progress bar; gather preserves order
    for _ in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="haiku stance"):
        await _
    return [t.result() for t in tasks]


def classify_dataframe(df: pd.DataFrame, text_col: str = "text", limit: int | None = None, live: bool = True) -> pd.DataFrame:
    """
    return df with a new `stance` column.
    - live=True: call haiku
    - live=False: if df has `true_stance`, use it; else rule-based fallback
    """
    df = df.copy()
    if not live:
        if "true_stance" in df.columns:
            df["stance"] = df["true_stance"]
            return df
        print("  classify_dataframe(live=False) with no true_stance: using keyword fallback")
        df["stance"] = df[text_col].fillna("").astype(str).map(_rule_based_fallback)
        return df

    if limit:
        df = df.head(limit).copy()
    texts = df[text_col].fillna("").astype(str).tolist()
    cfg = load_sources()["panel2"]
    labels = asyncio.run(_classify_batch(texts, cfg["model"], cfg.get("max_concurrency", 8)))
    df["stance"] = labels
    return df


# ---------- fallback rule-based classifier ----------
# this is NOT methodology. only used when both API key and truth labels are missing
# so the pipeline still produces a chart. clearly flag it on the chart.

_FALLBACK_PRO_ENF = ["illegal alien", "illegals", "criminal", "deport", "ice should", "drain", "taking jobs", "invasion", "border crisis"]
_FALLBACK_PRO_LAB = ["essential worker", "farmworker", "undocumented worker", "path to citizenship", "legalization", "exploit", "human", "dreamers", "family"]


def _rule_based_fallback(text: str) -> str:
    lower = text.lower()
    enf_hits = sum(1 for t in _FALLBACK_PRO_ENF if t in lower)
    lab_hits = sum(1 for t in _FALLBACK_PRO_LAB if t in lower)
    if enf_hits > lab_hits:
        return "pro_enforcement"
    if lab_hits > enf_hits:
        return "pro_immigrant_labor"
    return "neutral_mixed"


# ---------- aggregation + chart ----------

def _quarter(d):
    d = pd.to_datetime(d)
    return pd.Timestamp(d.year, ((d.month - 1) // 3) * 3 + 1, 1)


def aggregate_stance(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["quarter"] = df["date"].map(_quarter)
    df = df.dropna(subset=["stance"])
    counts = df.groupby(["quarter", "stance"]).size().unstack(fill_value=0)
    for L in LABELS:
        if L not in counts.columns:
            counts[L] = 0
    counts = counts[list(LABELS)]
    totals = counts.sum(axis=1).replace(0, pd.NA)
    share = counts.div(totals, axis=0).fillna(0)
    return share.sort_index()


def plot_stance(share: pd.DataFrame, ax, title: str, note: str = ""):
    if share.empty:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title)
        return
    x = share.index
    ys = [share[L].values for L in LABELS]
    colors = [COLORS[L] for L in LABELS]
    labels_display = [L.replace("_", " ") for L in LABELS]
    ax.stackplot(x, ys, labels=labels_display, colors=colors, alpha=0.85)
    ax.set_ylim(0, 1)
    ax.set_ylabel("share of posts")
    ax.set_title(title)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", alpha=0.2)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    if note:
        ax.text(0.99, 0.02, note, ha="right", va="bottom", transform=ax.transAxes, fontsize=7, color="#666")
    draw_events(ax)


def render(df: pd.DataFrame | None = None, live: bool = False, limit: int | None = None, output: Path | None = None) -> Path:
    output = output or (OUTPUT_DIR / "panel2_stance.png")
    if df is None:
        df = reddit_col.pull(demo=not live)
    classified = classify_dataframe(df, text_col="text", limit=limit, live=live)
    share = aggregate_stance(classified)

    mode_note = "source: live haiku classification" if live else (
        "source: synthetic truth labels (demo mode)" if "true_stance" in df.columns else "source: rule-based fallback (no API, no ground truth)"
    )
    fig, ax = plt.subplots(1, 1, figsize=(14, 4))
    plot_stance(share, ax, "panel 2 — stance share on reddit (pro-enforcement vs pro-labor vs neutral)", note=mode_note)
    ax.set_xlabel("year")
    fig.tight_layout()
    fig.savefig(output, dpi=130, bbox_inches="tight")
    plt.close(fig)

    # also persist the labeled df for panel 3 + validation
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    classified.to_csv(PROCESSED_DIR / "reddit_posts_stance.csv", index=False)

    return output


if __name__ == "__main__":
    matplotlib.use("Agg")
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="call haiku instead of using truth/fallback")
    ap.add_argument("--limit", type=int, default=None, help="classify only first N posts (for smoke test)")
    args = ap.parse_args()
    p = render(live=args.live, limit=args.limit)
    print(f"wrote {p}")
