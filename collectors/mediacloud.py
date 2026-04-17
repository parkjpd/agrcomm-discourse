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


def _one_query(api, query, qstart, qend, term, bucket_name):
    """single request with retry. returns dict suitable for the results list."""
    req = {"q": query, "start": qstart.isoformat(), "end": qend.isoformat()}
    cached = cache_get(NAMESPACE, req)
    if cached is not None:
        return {"date": qstart.isoformat(), "term": term, "bucket": bucket_name, "count": cached, "source": "mediacloud"}

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
    return {"date": qstart.isoformat(), "term": term, "bucket": bucket_name, "count": count, "source": "mediacloud"}


def pull_volumes(start: date = date(2010, 1, 1), end: date | None = None, max_workers: int = 6) -> pd.DataFrame:
    """one row per (quarter, term, bucket). parallelized via threads since mediacloud sdk is sync."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

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

    # flatten all (bucket, term, quarter) work units
    units = []
    for bucket_name, bucket in buckets.items():
        for term in bucket["terms"]:
            query = _anchored_query(term, anchor)
            for qstart, qend in _iter_quarters(start, end):
                units.append((query, qstart, qend, term, bucket_name))

    print(f"  mc: {len(units)} queries, {max_workers} workers")
    rows = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_one_query, api, *u) for u in units]
        done = 0
        for fut in as_completed(futs):
            rows.append(fut.result())
            done += 1
            if done % 100 == 0:
                print(f"    {done}/{len(units)}")

    return pd.DataFrame(rows)


def save_volumes(df: pd.DataFrame, path: Path | None = None) -> Path:
    path = path or (PROCESSED_DIR / "panel1_news_volumes_mc.csv")
    df.to_csv(path, index=False)
    return path


# ---------- pull article titles for panel 3 topic modeling ----------

def _one_story_pull(api, query, qstart, qend, limit):
    req = {"q": query, "start": qstart.isoformat(), "end": qend.isoformat(), "list": True, "limit": limit}
    cached = cache_get(NAMESPACE, req)
    if cached is not None:
        return cached
    out: list[dict] = []
    try:
        result = api.story_list(query, qstart, qend, collection_ids=[COLLECTION_ID])
        # sdk may return (stories, meta) tuple
        stories = result[0] if isinstance(result, tuple) else result
        for s in (stories or [])[:limit]:
            out.append({
                "source": "mediacloud",
                "date": str(s.get("publish_date", qstart))[:10],
                "title": s.get("title", "") or "",
                "text": s.get("title", "") or "",  # MC v4 sdk metadata-only; title is our text signal
                "url": s.get("url", ""),
                "media": s.get("media_name", ""),
            })
    except Exception as e:
        print(f"  mc story_list fail {qstart}: {type(e).__name__}: {e}")
    cache_put(NAMESPACE, req, out, summary=f"{len(out)} stories {qstart}")
    return out


def pull_articles(
    start: date = date(2010, 1, 1),
    end: date | None = None,
    max_workers: int = 6,
    per_quarter: int = 100,
) -> pd.DataFrame:
    """pull up to per_quarter article titles per quarter for panel 3 topic modeling.
    uses a combined OR-query for speed (one call per quarter rather than per term)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    key = _api_key()
    if not key:
        return pd.DataFrame()
    if end is None:
        end = date.today()

    from mediacloud.api import SearchApi
    api = SearchApi(key)

    kw = load_keywords()
    anchor = kw["topic_anchor"]["require_any"]
    all_terms = []
    for b in kw["buckets"].values():
        all_terms.extend(b["terms"])
    term_clause = " OR ".join(f'"{t}"' for t in all_terms)
    anchor_clause = " OR ".join(f'"{a}"' for a in anchor)
    query = f"({term_clause}) AND ({anchor_clause})"

    quarters = list(_iter_quarters(start, end))
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_one_story_pull, api, query, qs, qe, per_quarter): qs for qs, qe in quarters}
        for fut in as_completed(futs):
            rows.extend(fut.result())
    return pd.DataFrame(rows)


def save_articles(df: pd.DataFrame, path: Path | None = None) -> Path:
    path = path or (PROCESSED_DIR / "news_articles_mc.csv")
    df.to_csv(path, index=False)
    return path


if __name__ == "__main__":
    df = pull_volumes(start=date(2024, 1, 1), end=date(2024, 6, 30))
    print(df.groupby("bucket")["count"].sum())
