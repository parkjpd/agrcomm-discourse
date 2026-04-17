"""
orchestrator. runs collectors + panels + combined figure.

examples:
  python run.py                         # full demo mode off synthetic samples
  python run.py --collect               # pull fresh data from live sources (needs creds)
  python run.py --only panel1           # just panel 1
  python run.py --live-stance           # panel 2 with real haiku calls
  python run.py --live-topic            # panel 3 with real bertopic fit
  python run.py --live                  # shortcut for --live-stance --live-topic --collect
  python run.py --limit 5000            # subsample for speed
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

from common import OUTPUT_DIR, cache_stats, ensure_dirs


def _collect(skip_if_present: bool = True):
    """run live collectors where creds are available. falls back silently otherwise."""
    from collectors import gdelt, mediacloud, reddit

    print("collectors -------------------------------------------")
    from common import PROCESSED_DIR

    # GDELT (free, no auth)
    gdelt_out = PROCESSED_DIR / "panel1_news_volumes.csv"
    if not (skip_if_present and gdelt_out.exists()):
        print(f"  gdelt: pulling volumes {date(2017,2,1)} -> today")
        try:
            df = gdelt.pull_volumes()
            gdelt.save_volumes(df)
            print(f"    wrote {len(df)} rows")
        except Exception as e:
            print(f"    gdelt failed: {e}")
    else:
        print(f"  gdelt: skipping (already have {gdelt_out.name})")

    # media cloud (optional)
    if mediacloud.available():
        mc_out = PROCESSED_DIR / "panel1_news_volumes_mc.csv"
        if not (skip_if_present and mc_out.exists()):
            print("  media cloud: pulling 2010-2016 baseline")
            try:
                df = mediacloud.pull_volumes()
                mediacloud.save_volumes(df)
                print(f"    wrote {len(df)} rows")
            except Exception as e:
                print(f"    media cloud failed: {e}")
        else:
            print(f"  media cloud: skipping (already have {mc_out.name})")
    else:
        print("  media cloud: no API key, skipping (pre-2017 baseline will use synthetic)")

    # reddit (live requires creds)
    if reddit.available():
        reddit_out = PROCESSED_DIR / "reddit_posts.csv"
        if not (skip_if_present and reddit_out.exists()):
            print("  reddit: live pull via praw")
            df = reddit.pull(demo=False)
            if not df.empty:
                reddit.save(df)
                print(f"    wrote {len(df)} posts")
        else:
            print(f"  reddit: skipping (already have {reddit_out.name})")
    else:
        print("  reddit: no creds, using synthetic samples")


def _panel1(live: bool):
    from panels import panel1_language
    print("panel 1 ------------------------------------------------")
    p = panel1_language.render()
    print(f"  wrote {p}")


def _panel2(live: bool, limit: int | None):
    from panels import panel2_stance
    print("panel 2 ------------------------------------------------")
    p = panel2_stance.render(live=live, limit=limit)
    print(f"  wrote {p}")


def _panel3(live: bool, limit: int | None):
    from panels import panel3_topic
    print("panel 3 ------------------------------------------------")
    p = panel3_topic.render(live=live, limit=limit)
    print(f"  wrote {p}")


def _panel4():
    from panels import panel4_futures
    print("panel 4 (bonus) ----------------------------------------")
    try:
        p = panel4_futures.render()
        print(f"  wrote {p}")
    except Exception as e:
        print(f"  panel 4 skipped: {e}")


def _combined(live_stance: bool, live_topic: bool, limit: int | None):
    from viz import three_panel
    print("combined -----------------------------------------------")
    p = three_panel.render(live_stance=live_stance, live_topic=live_topic, limit=limit)
    print(f"  wrote {p}")


def _findings():
    """auto-generate a draft findings.md with era-level stats from whatever data is loaded."""
    from panels.panel1_language import _normalize_to_share, load_news_volumes, load_reddit_volumes
    from panels.panel2_stance import aggregate_stance
    from panels.panel3_topic import _prevalence_per_year, load_corpus
    from common import PROCESSED_DIR
    import pandas as pd

    out = OUTPUT_DIR / "findings.md"
    L = []
    L.append("# discourse-shift findings\n")
    L.append("auto-generated summary from `run.py`. numbers refresh on every run.\n\n")

    # ERAS for comparison
    eras = [
        ("pre_trump",  "2010-01-01", "2016-10-31"),
        ("trump_1",    "2016-11-01", "2020-02-29"),
        ("covid",      "2020-03-01", "2021-01-19"),
        ("biden",      "2021-01-20", "2024-11-04"),
        ("trump_2",    "2024-11-05", "2026-06-30"),
    ]

    def era_mean(series, start, end):
        if series.empty: return None
        s = series.loc[start:end]
        return float(s.mean()) if len(s) else None

    # --- panel 1 news language ---
    L.append("## panel 1 — news language (real media cloud data)\n\n")
    try:
        news = _normalize_to_share(load_news_volumes())
        if not news.empty:
            L.append("| era | enforcement-framed | labor-framed | neutral |\n")
            L.append("|---|---|---|---|\n")
            for name, start, end in eras:
                r = era_mean(news.get("right_loaded"), start, end)
                l_ = era_mean(news.get("left_loaded"), start, end)
                n = era_mean(news.get("neutral"), start, end)
                fmt = lambda v: f"{v:.1%}" if v is not None else "—"
                L.append(f"| {name} | {fmt(r)} | {fmt(l_)} | {fmt(n)} |\n")
            # biggest shift
            right = [(n, era_mean(news.get("right_loaded"), s, e)) for n, s, e in eras]
            right = [(n, v) for n, v in right if v is not None]
            if len(right) >= 2:
                maxp = max(right, key=lambda x: x[1])
                minp = min(right, key=lambda x: x[1])
                L.append(f"\n- enforcement-framing **max** era = `{maxp[0]}` ({maxp[1]:.1%}), **min** era = `{minp[0]}` ({minp[1]:.1%})\n")
                L.append(f"- headline takeaway: mainstream news framing of migrant farm labor has been {'remarkably stable' if (maxp[1] - minp[1]) < 0.1 else 'clearly era-dependent'} — enforcement-framing range is {(maxp[1] - minp[1]) * 100:.1f} percentage points across the 5 eras.\n")
    except Exception as e:
        L.append(f"- could not summarize news panel: {e}\n")

    # --- panel 2 stance ---
    L.append("\n## panel 2 — reddit stance (live haiku classification)\n\n")
    try:
        df = pd.read_csv(PROCESSED_DIR / "reddit_posts_stance.csv")
        share = aggregate_stance(df)
        L.append(f"- corpus: {len(df):,} posts, {df['stance'].notna().sum():,} with haiku label\n")
        if not share.empty:
            L.append("\n| era | pro-enforcement | pro-labor | neutral-mixed |\n")
            L.append("|---|---|---|---|\n")
            for name, start, end in eras:
                e = era_mean(share.get("pro_enforcement"), start, end)
                p = era_mean(share.get("pro_immigrant_labor"), start, end)
                nm = era_mean(share.get("neutral_mixed"), start, end)
                fmt = lambda v: f"{v:.1%}" if v is not None else "—"
                L.append(f"| {name} | {fmt(e)} | {fmt(p)} | {fmt(nm)} |\n")
    except Exception as e:
        L.append(f"- could not summarize stance panel: {e}\n")

    # --- panel 3 topic ---
    L.append("\n## panel 3 — topic prevalence\n\n")
    try:
        corpus = load_corpus()
        if not corpus.empty and "true_topic" in corpus.columns:
            share = _prevalence_per_year(corpus, "true_topic")
            if not share.empty:
                for topic in share.index:
                    s = share.loc[topic]
                    peak_year = s.idxmax()
                    peak_val = s.max()
                    L.append(f"- **{topic}** peaked in {peak_year} at {peak_val:.1%} of that year's discourse\n")
    except Exception as e:
        L.append(f"- could not summarize topic panel: {e}\n")

    # --- panel 4 futures ---
    L.append("\n## panel 4 (bonus) — ag futures event windows\n\n")
    try:
        from panels.panel4_futures import event_window_returns
        ew = event_window_returns(window_days=30)
        if not ew.empty:
            # pick out extreme post-minus-pre moves
            ew_sorted = ew.reindex(ew["post_minus_pre"].abs().sort_values(ascending=False).index).head(5)
            L.append("biggest 30-day post-vs-pre return shifts across all events × tickers:\n\n")
            for _, row in ew_sorted.iterrows():
                L.append(f"- **{row['event']}** ({row['date']}) → {row['ticker']}: {row['post_minus_pre']:+.1%}\n")
    except Exception as e:
        L.append(f"- futures summary skipped: {e}\n")

    # --- interpretation bucket ---
    L.append("\n## interpretation (pick the pattern that fits, write a paragraph)\n")
    L.append("- [ ] **all three panels break at same events** → regime-driven discourse. strongest finding.\n")
    L.append("- [ ] **language + topic break, stance stable** → identity-level positions are sticky, surface framing is reactive.\n")
    L.append("- [ ] **stance breaks, lang + topic stable** → actual positions move with events even when media frames them the same. rare.\n")
    L.append("- [ ] **nothing breaks cleanly** → continuous discourse, events trigger volume not structural shifts.\n")
    L.append("\n---\n_generated by `run.py`. edit this file — next run will overwrite, so save final writeup elsewhere before submitting._\n")

    out.write_text("".join(L))
    return out


def main(argv: list[str] | None = None) -> int:
    ensure_dirs()
    ap = argparse.ArgumentParser(description="discourse-shift pipeline")
    ap.add_argument("--collect", action="store_true", help="run live collectors before panels")
    ap.add_argument("--only", choices=["panel1", "panel2", "panel3", "panel4", "combined"], default=None)
    ap.add_argument("--live", action="store_true", help="enable live stance + topic (implies --collect)")
    ap.add_argument("--live-stance", action="store_true")
    ap.add_argument("--live-topic", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force-collect", action="store_true", help="re-pull even if processed files exist")
    args = ap.parse_args(argv)

    if args.live:
        args.live_stance = True
        args.live_topic = True
        args.collect = True

    t0 = time.time()

    if args.collect or args.force_collect:
        _collect(skip_if_present=not args.force_collect)

    if args.only in (None, "panel1"):
        _panel1(live=False)
    if args.only in (None, "panel2"):
        _panel2(live=args.live_stance, limit=args.limit)
    if args.only in (None, "panel3"):
        _panel3(live=args.live_topic, limit=args.limit)
    if args.only in (None, "panel4"):
        _panel4()
    if args.only in (None, "combined"):
        _combined(live_stance=args.live_stance, live_topic=args.live_topic, limit=args.limit)

    findings = _findings()
    print(f"\nwrote findings skeleton -> {findings}")
    print(f"cache stats: {cache_stats()}")
    print(f"total time: {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
