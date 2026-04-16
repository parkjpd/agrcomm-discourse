"""
reddit collector. PRAW for 2023+ live pulls. for 2010-2023 we rely on either the
pushshift archive dumps (you download separately and point us at them) or synthetic
samples.

PRAW requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT.
"""
from __future__ import annotations

import csv
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from common import PROCESSED_DIR, SAMPLES_DIR, cache_get, cache_put, load_sources

NAMESPACE = "reddit"


def _creds() -> tuple[str, str, str] | None:
    cid = os.environ.get("REDDIT_CLIENT_ID")
    sec = os.environ.get("REDDIT_CLIENT_SECRET")
    ua = os.environ.get("REDDIT_USER_AGENT")
    if cid and sec and ua:
        return cid, sec, ua
    return None


def available() -> bool:
    return _creds() is not None


def _praw_client():
    import praw
    cid, sec, ua = _creds()  # type: ignore[misc]
    return praw.Reddit(client_id=cid, client_secret=sec, user_agent=ua)


def pull_live(query: str, limit_per_sub: int = 500) -> pd.DataFrame:
    """pull recent posts via PRAW search. covers last ~1000 posts per sub via reddit's own limits."""
    creds = _creds()
    if not creds:
        print("  skipping reddit live: creds not set (REDDIT_CLIENT_ID etc)")
        return pd.DataFrame()

    cfg = load_sources()["reddit"]
    subs = cfg["subreddits"]

    reddit = _praw_client()
    rows = []
    for sub in subs:
        req = {"sub": sub, "q": query, "limit": limit_per_sub}
        cached = cache_get(NAMESPACE, req)
        if cached is not None:
            rows.extend(cached)
            continue

        batch = []
        try:
            for post in reddit.subreddit(sub).search(query, limit=limit_per_sub, sort="new"):
                created = datetime.fromtimestamp(post.created_utc, tz=timezone.utc).date()
                batch.append(
                    {
                        "source": "reddit",
                        "date": created.isoformat(),
                        "subreddit": sub,
                        "title": post.title or "",
                        "text": f"{post.title or ''}\n{post.selftext or ''}".strip(),
                        "url": f"https://reddit.com{post.permalink}",
                        "score": int(post.score or 0),
                    }
                )
        except Exception as e:
            print(f"  reddit pull failed r/{sub}: {e}")

        cache_put(NAMESPACE, req, batch, summary=f"r/{sub} {len(batch)}")
        rows.extend(batch)
        time.sleep(1)

    return pd.DataFrame(rows)


def load_synthetic() -> pd.DataFrame:
    """read the synthetic reddit dataset. generates it first if missing."""
    path = SAMPLES_DIR / "reddit.csv"
    if not path.exists():
        from scripts.make_samples import main as make
        make()
    return pd.read_csv(path)


def save(df: pd.DataFrame, path: Path | None = None) -> Path:
    path = path or (PROCESSED_DIR / "reddit_posts.csv")
    df.to_csv(path, index=False)
    return path


def pull(demo: bool = False) -> pd.DataFrame:
    """unified entry point - live if creds, synthetic otherwise."""
    if demo or not available():
        print("  reddit: using synthetic samples")
        return load_synthetic()
    print("  reddit: pulling live via PRAW")
    # simple combined query - matches anything about migrant farm labor
    return pull_live("farmworker OR (migrant AND farm) OR H-2A OR undocumented OR illegal")
