"""
generate validation/stance_labels.csv - a stratified sample of 200 posts for hand-labeling.

spec section 6 requires:
  - 200 posts
  - stratified across years (2015, 2018, 2020, 2022, 2024, 2026)
  - labeled blind (no source/year visible)
  - split 67/67/66 across David/Ella/Sydney

run: python -m validation.make_hand_label_template
"""
from __future__ import annotations

import random
from datetime import date
from pathlib import Path

import pandas as pd

from common import PROCESSED_DIR, ROOT, SAMPLES_DIR

TARGET_YEARS = [2015, 2018, 2020, 2022, 2024, 2026]
PER_YEAR = 34  # 34 * 6 = 204, trim to 200
TOTAL = 200
REVIEWERS = ["david", "ella", "sydney"]


def build_template(source_path: Path | None = None, out: Path | None = None, seed: int = 42) -> Path:
    random.seed(seed)

    # prefer real reddit data if collected, fall back to samples
    if source_path is None:
        candidates = [PROCESSED_DIR / "reddit_posts.csv", SAMPLES_DIR / "reddit.csv"]
        source_path = next((p for p in candidates if p.exists()), None)
        if source_path is None:
            raise FileNotFoundError("no reddit data found - run collectors or scripts/make_samples first")

    out = out or (ROOT / "validation" / "stance_labels.csv")

    df = pd.read_csv(source_path)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    picks = []
    for y in TARGET_YEARS:
        slice_ = df[df["year"] == y]
        if slice_.empty:
            continue
        n = min(PER_YEAR, len(slice_))
        picks.append(slice_.sample(n=n, random_state=seed + y))

    sample = pd.concat(picks, ignore_index=True)
    sample = sample.sample(n=min(TOTAL, len(sample)), random_state=seed).reset_index(drop=True)

    # blind: strip identifying cols. keep id+text for the labeler, year hidden.
    sample["id"] = range(1, len(sample) + 1)
    sample["reviewer"] = [REVIEWERS[i % 3] for i in range(len(sample))]
    sample["human_label"] = ""  # to be filled by reviewer
    sample["notes"] = ""

    cols = ["id", "reviewer", "text", "human_label", "notes"]
    # stash hidden metadata in a sibling file so we can join back later
    sample[cols].to_csv(out, index=False)

    hidden = out.with_name("stance_labels_hidden.csv")
    sample[["id", "date", "subreddit", "source", "url"] + [c for c in ("true_stance",) if c in sample.columns]].to_csv(hidden, index=False)

    print(f"wrote {len(sample)} rows -> {out}")
    print(f"hidden metadata -> {hidden}")
    return out


if __name__ == "__main__":
    build_template()
