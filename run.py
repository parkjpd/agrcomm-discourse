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
    """write a short findings skeleton that summarizes which panels broke at which events."""
    from panels.panel1_language import _normalize_to_share, load_news_volumes, load_reddit_volumes
    from panels.panel2_stance import aggregate_stance
    from common import PROCESSED_DIR
    import pandas as pd

    out = OUTPUT_DIR / "findings.md"
    lines = []
    lines.append("# discourse shift findings - draft\n")
    lines.append("one-page writeup, data-driven. fill in interpretation before submission.\n")
    lines.append("## panel-level summary\n")

    try:
        news_share = _normalize_to_share(load_news_volumes())
        if not news_share.empty:
            # check whether right_loaded share jumped at the trump-2016 hinge
            pre = news_share.loc[:"2016-10-31", "right_loaded"].mean()
            post = news_share.loc["2016-11-01":"2020-02-29", "right_loaded"].mean()
            lines.append(f"- panel 1 news: enforcement-framed share went from {pre:.2f} (2010-Q4 to 2016-Q3) to {post:.2f} (Trump-1 era). delta {post-pre:+.2f}.\n")
    except Exception as e:
        lines.append(f"- panel 1 news: could not summarize ({e})\n")

    try:
        import pandas as pd
        df = pd.read_csv(PROCESSED_DIR / "reddit_posts_stance.csv")
        share = aggregate_stance(df)
        pre = share.loc[:"2020-02-29", "pro_enforcement"].mean() if not share.empty else 0
        covid = share.loc["2020-03-01":"2021-01-19", "pro_enforcement"].mean() if not share.empty else 0
        lines.append(f"- panel 2 stance: pro-enforcement share averaged {pre:.2f} pre-pandemic vs {covid:.2f} during COVID. delta {covid-pre:+.2f}.\n")
    except Exception as e:
        lines.append(f"- panel 2 stance: could not summarize ({e})\n")

    lines.append("- panel 3 topic: see heatmap - check for deportation/essential-worker cell intensity at the 2020 and 2024-25 columns.\n\n")

    lines.append("## interpretation outcomes (pick one, write paragraph):\n")
    lines.append("- [ ] all three panels break at same events -> discourse is regime-driven\n")
    lines.append("- [ ] language + topic break, stance stable -> same positions in new words\n")
    lines.append("- [ ] stance breaks but lang/topic don't -> public positions move with events even when media frames same\n")
    lines.append("- [ ] nothing breaks cleanly -> continuous discourse, events trigger volume not structure\n")
    out.write_text("".join(lines))
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
