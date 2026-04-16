"""
cohen's kappa validation of the stance classifier per spec section 6.

pipeline:
  1. load stance_labels.csv (hand labels) and reddit_posts_stance.csv (model labels)
  2. join on id
  3. compute cohen's kappa + confusion matrix + per-class precision/recall
  4. print verdict (ship / iterate / stop)

run: python -m validation.validate_stance
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report, cohen_kappa_score, confusion_matrix

from common import PROCESSED_DIR, ROOT, load_sources

LABELS = ("pro_enforcement", "pro_immigrant_labor", "neutral_mixed")


def validate(
    hand_path: Path | None = None,
    hidden_path: Path | None = None,
    model_path: Path | None = None,
) -> dict:
    hand_path = hand_path or (ROOT / "validation" / "stance_labels.csv")
    hidden_path = hidden_path or (ROOT / "validation" / "stance_labels_hidden.csv")
    model_path = model_path or (PROCESSED_DIR / "reddit_posts_stance.csv")

    if not hand_path.exists():
        raise FileNotFoundError(f"missing {hand_path} - run validation.make_hand_label_template first")
    if not model_path.exists():
        raise FileNotFoundError(f"missing {model_path} - run panel 2 first")

    hand = pd.read_csv(hand_path)
    hidden = pd.read_csv(hidden_path) if hidden_path.exists() else None
    model_df = pd.read_csv(model_path)

    hand = hand[hand["human_label"].notna() & (hand["human_label"].astype(str).str.strip() != "")]
    if hand.empty:
        print("no human labels yet. fill in the human_label column of stance_labels.csv and re-run.")
        return {}

    # join hand labels back to the original model labels by text match
    # (url is safer but may have been stripped in the blind template)
    merged = hand.merge(model_df[["text", "stance"]].drop_duplicates("text"), on="text", how="left")
    merged = merged.dropna(subset=["stance"])

    y_true = merged["human_label"].str.strip().str.lower()
    y_pred = merged["stance"].str.strip().str.lower()

    kappa = cohen_kappa_score(y_true, y_pred, labels=list(LABELS))
    cm = confusion_matrix(y_true, y_pred, labels=list(LABELS))
    report = classification_report(y_true, y_pred, labels=list(LABELS), zero_division=0)

    cfg = load_sources()["panel2"]
    ship = cfg.get("kappa_ship", 0.6)
    iterate = cfg.get("kappa_iterate", 0.4)

    print(f"n labeled:   {len(merged)}")
    print(f"cohen kappa: {kappa:.3f}")
    print()
    print("confusion matrix (rows=truth, cols=pred):")
    print("labels:", LABELS)
    print(cm)
    print()
    print(report)

    if kappa >= ship:
        verdict = "SHIP"
        print(f"\nkappa >= {ship} -> SHIP the classifier as-is")
    elif kappa >= iterate:
        verdict = "ITERATE"
        print(f"\nkappa in [{iterate}, {ship}) -> rewrite rubric and re-run")
    else:
        verdict = "STOP"
        print(f"\nkappa < {iterate} -> stance is not reliably detectable. report that honestly.")

    return {"kappa": kappa, "n": len(merged), "verdict": verdict}


if __name__ == "__main__":
    validate()
