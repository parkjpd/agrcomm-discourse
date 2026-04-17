"""
youtube data api v3 collector.

searches for immigration/farmworker videos, then pulls top comments from each.
requires a YOUTUBE_API_KEY env var (create one at console.cloud.google.com,
enable "YouTube Data API v3", then make a public api key — no oauth needed).

free tier: 10,000 quota units/day. a search costs 100 units, each commentThread
page costs 1 unit, so this is very cheap compared to reddit/meta.

falls back to data/samples/youtube.csv when no key is present.
"""
from __future__ import annotations

import csv
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from common import PROCESSED_DIR, SAMPLES_DIR, cache_get, cache_put, load_sources

NAMESPACE = "youtube"
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
COMMENTS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _key() -> str | None:
    return os.environ.get("YOUTUBE_API_KEY")


def available() -> bool:
    return _key() is not None


def _get(url: str, params: dict) -> dict:
    """cached GET with backoff. cache key excludes the api key itself."""
    req = {"url": url, "params": {k: v for k, v in params.items() if k != "key"}}
    cached = cache_get(NAMESPACE, req)
    if cached is not None:
        return cached
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                cache_put(NAMESPACE, req, data, summary=f"{url.split('/')[-1]} q={params.get('q','')[:30]}")
                return data
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 ** attempt)
                continue
            # quotaExceeded (403) is the most common real-world failure
            print(f"  youtube api error {r.status_code}: {r.text[:200]}")
            return {}
        except Exception as e:
            if attempt == 3:
                print(f"  youtube request failed: {e}")
                return {}
            time.sleep(1.5 * (attempt + 1))
    return {}


def _search_videos(query: str, published_after: str, published_before: str, max_per_query: int = 25) -> list[dict]:
    """return a list of (video_id, title, channel, published_at)."""
    params = {
        "key": _key(),
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max_per_query, 50),
        "publishedAfter": published_after,
        "publishedBefore": published_before,
        "relevanceLanguage": "en",
        "regionCode": "US",
        "order": "relevance",
    }
    data = _get(SEARCH_URL, params)
    out = []
    for item in data.get("items", []):
        vid = item.get("id", {}).get("videoId")
        sn = item.get("snippet", {})
        if not vid:
            continue
        out.append({
            "video_id": vid,
            "title": sn.get("title", ""),
            "channel": sn.get("channelTitle", ""),
            "published_at": sn.get("publishedAt", ""),
        })
    return out


def _fetch_comments(video_id: str, max_comments: int = 100) -> list[dict]:
    """fetch top-level comments for one video. real api paginates 100 per page."""
    params = {
        "key": _key(),
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(max_comments, 100),
        "order": "relevance",
        "textFormat": "plainText",
    }
    data = _get(COMMENTS_URL, params)
    out = []
    for item in data.get("items", []):
        top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        text = top.get("textDisplay", "") or top.get("textOriginal", "")
        if not text:
            continue
        published = top.get("publishedAt", "")
        try:
            d = datetime.strptime(published[:10], "%Y-%m-%d").date()
        except Exception:
            continue
        out.append({
            "text": text,
            "date": d.isoformat(),
            "likes": top.get("likeCount", 0),
            "author": top.get("authorDisplayName", ""),
        })
    return out


def pull_live(max_videos_per_query: int = 10, max_comments_per_video: int = 50) -> pd.DataFrame:
    if not available():
        print("  skipping youtube live: YOUTUBE_API_KEY not set")
        return pd.DataFrame()
    cfg = load_sources().get("youtube", {})
    queries = cfg.get("queries", ["farmworker immigration", "H-2A visa", "ICE raid farm", "migrant labor deportation"])
    # sweep yearly windows so we aren't capped at youtube's default relevance ordering
    windows = []
    for y in range(2012, date.today().year + 1):
        windows.append((f"{y}-01-01T00:00:00Z", f"{y}-12-31T23:59:59Z"))
    rows: list[dict] = []
    for q in queries:
        for after, before in windows:
            vids = _search_videos(q, after, before, max_per_query=max_videos_per_query)
            for v in vids:
                comments = _fetch_comments(v["video_id"], max_comments=max_comments_per_video)
                for c in comments:
                    rows.append({
                        "source": "youtube",
                        "date": c["date"],
                        "channel": v["channel"],
                        "video_title": v["title"],
                        "video_id": v["video_id"],
                        "title": v["title"],
                        "text": c["text"],
                        "likes": c["likes"],
                        "url": f"https://www.youtube.com/watch?v={v['video_id']}",
                        "true_bucket": None, "true_stance": None, "true_topic": None,
                    })
    return pd.DataFrame(rows)


def pull(demo: bool = False) -> pd.DataFrame:
    if not demo and available():
        live_df = pull_live()
        if not live_df.empty:
            return live_df
        print("  youtube: live pull returned 0 rows, falling back to synthetic")
    sample_path = SAMPLES_DIR / "youtube.csv"
    if sample_path.exists():
        return pd.read_csv(sample_path)
    print(f"  youtube: no samples at {sample_path}; run `python -m scripts.make_samples` first")
    return pd.DataFrame()


def render_processed(output: Path | None = None) -> Path:
    output = output or (PROCESSED_DIR / "youtube_comments.csv")
    df = pull(demo=not available())
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    print(f"  wrote {len(df)} youtube rows -> {output}")
    return output


if __name__ == "__main__":
    render_processed()
