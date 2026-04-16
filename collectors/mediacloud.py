"""
media cloud collector - 2010-2016 baseline window.
requires MEDIACLOUD_API_KEY. returns empty DataFrame if not set (pipeline continues).

media cloud moved their API a couple times. this uses the v4/search endpoint -
update ENDPOINT if the institution gave you a different base url.
"""
from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from common import PROCESSED_DIR, cache_get, cache_put, load_keywords

NAMESPACE = "mediacloud"
ENDPOINT = "https://search.mediacloud.org/api/search/total-count"
# ENDPOINT_ARTICLES = "https://search.mediacloud.org/api/search/story-list"


def _api_key() -> str | None:
    key = os.environ.get("MEDIACLOUD_API_KEY")
    return key.strip() if key else None


def _q_for(terms: list[str], anchor: list[str]) -> str:
    t = " OR ".join(f'"{x}"' for x in terms)
    a = " OR ".join(f'"{x}"' for x in anchor)
    return f"({t}) AND ({a})"


def available() -> bool:
    return _api_key() is not None


def pull_volumes(start: date = date(2010, 1, 1), end: date = date(2016, 12, 31)) -> pd.DataFrame:
    """per-quarter article counts per bucket, media cloud side."""
    key = _api_key()
    if not key:
        print("  skipping media cloud: MEDIACLOUD_API_KEY not set")
        return pd.DataFrame(columns=["date", "bucket", "count", "source"])

    kw = load_keywords()
    anchor = kw["topic_anchor"]["require_any"]
    rows = []

    q = start
    while q <= end:
        # quarterly window
        q_end = date(q.year, min(q.month + 2, 12), 28)
        for bucket_name, bucket in kw["buckets"].items():
            query = _q_for(bucket["terms"], anchor)
            req = {"q": query, "start": q.isoformat(), "end": q_end.isoformat()}
            cached = cache_get(NAMESPACE, req)
            if cached is not None:
                rows.append({"date": q.isoformat(), "bucket": bucket_name, "count": cached, "source": "mediacloud"})
                continue

            count = None
            for attempt in range(3):
                try:
                    r = requests.get(
                        ENDPOINT,
                        params={
                            "q": query,
                            "start_date": q.isoformat(),
                            "end_date": q_end.isoformat(),
                            "collections": "34412234",
                            "platform": "online_news",
                        },
                        headers={"Authorization": f"Token {key}"},
                        timeout=60,
                    )
                    r.raise_for_status()
                    data = r.json()
                    # v4 api: {"count": {"relevant": N, "total": N}}
                    cf = data.get("count", {})
                    if isinstance(cf, dict):
                        count = int(cf.get("relevant", 0))
                    else:
                        count = int(cf or data.get("total", 0))
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"  media cloud failed {q} {bucket_name}: {type(e).__name__}: {e}")
                    else:
                        time.sleep(2.0 * (attempt + 1))

            # only cache real responses; leave failures uncached so re-runs can retry
            if count is not None:
                cache_put(NAMESPACE, req, count, summary=f"{bucket_name} {q}")
                rows.append({"date": q.isoformat(), "bucket": bucket_name, "count": count, "source": "mediacloud"})
            else:
                rows.append({"date": q.isoformat(), "bucket": bucket_name, "count": 0, "source": "mediacloud"})
            time.sleep(0.5)

        # advance to next quarter
        if q.month >= 10:
            q = date(q.year + 1, 1, 1)
        else:
            q = date(q.year, q.month + 3, 1)

    return pd.DataFrame(rows)


def save_volumes(df: pd.DataFrame, path: Path | None = None) -> Path:
    path = path or (PROCESSED_DIR / "panel1_news_volumes_mc.csv")
    df.to_csv(path, index=False)
    return path
