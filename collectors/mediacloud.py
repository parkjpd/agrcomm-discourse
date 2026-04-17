"""
media cloud collector using the official mediacloud python sdk.
covers 2010-present. requires MEDIACLOUD_API_KEY.

returns per-term quarterly counts so panel 1 can aggregate by bucket.
"""
from __future__ import annotations

import os
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from common import PROCESSED_DIR, cache_get, cache_put, load_keywords

NAMESPACE = "mediacloud"
COLLECTION_ID = 34412234  # US mainstream political blogs / online news


def _api_key() -> str | None:
    key = os.environ.get("MEDIACLOUD_API_KEY")
    return key.strip() if key else None


def available() -> bool:
    return _api_key() is not None


def _quarter_bounds(d: date) -> tuple[date, date]:
    q = (d.month - 1) // 3
    start = date(d.year, q * 3 + 1, 1)
    if q == 3:
        end = date(d.year, 12, 31)
    else:
        end = date(d.year, q * 3 + 4, 1) - timedelta(days=1)
    return start, end


def _iter_quarters(start: date, end: date):
    qs, _ = _quarter_bounds(start)
    while qs <= end:
        qstart, qend = _quarter_bounds(qs)
        yield qstart, qend
        qs = qend + timedelta(days=1)


def _anchored_query(term: str, anchor: list[str]) -> str:
    anchor_clause = " OR ".join(f'"{a}"' for a in anchor)
    return f'"{term}" AND ({anchor_clause})'


def pull_volumes(start: date = date(2010, 1, 1), end: date | None = None) -> pd.DataFrame:
    """one row per (quarter, term, bucket)."""
    key = _api_key()
    if not key:
        print("  skipping media cloud: MEDIACLOUD_API_KEY not set")
        return pd.DataFrame(columns=["date", "term", "bucket", "count", "source"])

    if end is None:
        end = date.today()

    from mediacloud.api import SearchApi
    api = SearchApi(key)

    kw = load_keywords()
    anchor = kw["topic_anchor"]["require_any"]
    buckets = kw["buckets"]

    rows = []
    for bucket_name, bucket in buckets.items():
        for term in bucket["terms"]:
            query = _anchored_query(term, anchor)
            for qstart, qend in _iter_quarters(start, end):
                req = {"q": query, "start": qstart.isoformat(), "end": qend.isoformat()}
                cached = cache_get(NAMESPACE, req)
                if cached is not None:
                    rows.append({"date": qstart.isoformat(), "term": term, "bucket": bucket_name, "count": cached, "source": "mediacloud"})
                    continue

                count = 0
                for attempt in range(3):
                    try:
                        resp = api.story_count(query, qstart, qend, collection_ids=[COLLECTION_ID])
                        if isinstance(resp, dict):
                            count = int(resp.get("relevant", resp.get("count", 0)) or 0)
                        else:
                            count = int(resp or 0)
                        break
                    except Exception as e:
                        if attempt == 2:
                            print(f"  mc fail {term!r} {qstart}: {type(e).__name__}: {e}")
                        else:
                            time.sleep(1.0 * (attempt + 1))

                cache_put(NAMESPACE, req, count, summary=f"{term} {qstart}")
                rows.append({"date": qstart.isoformat(), "term": term, "bucket": bucket_name, "count": count, "source": "mediacloud"})
                time.sleep(0.15)

    return pd.DataFrame(rows)


def save_volumes(df: pd.DataFrame, path: Path | None = None) -> Path:
    path = path or (PROCESSED_DIR / "panel1_news_volumes_mc.csv")
    df.to_csv(path, index=False)
    return path


if __name__ == "__main__":
    df = pull_volumes(start=date(2024, 1, 1), end=date(2024, 6, 30))
    print(df.groupby("bucket")["count"].sum())
