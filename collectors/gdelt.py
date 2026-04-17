"""
GDELT DOC 2.0 collector. free, no-auth. coverage starts ~feb 2017.

two modes:
- volumes: per-term article counts per quarter (feeds panel 1)
- articles: actual article text (feeds panel 3)

DOC 2.0 has a short query length limit so we query each term separately and
combine counts in python instead of one big boolean query.
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from common import PROCESSED_DIR, cache_get, cache_put, load_keywords

NAMESPACE = "gdelt"
GDELT_START = date(2017, 2, 1)


def _anchored_query(term: str) -> str:
    """bucket term AND any anchor term. keeps counts scoped to migrant farm labor discourse."""
    anchor = load_keywords()["topic_anchor"]["require_any"]
    anchor_clause = " OR ".join(f'"{a}"' for a in anchor)
    return f'"{term}" AND ({anchor_clause})'


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


def _filter(query: str, qstart: date, qend: date):
    from gdeltdoc import Filters
    return Filters(
        keyword=query,
        start_date=qstart.isoformat(),
        end_date=qend.isoformat(),
        country="US",
    )


def _gd():
    from gdeltdoc import GdeltDoc
    return GdeltDoc()


def pull_volumes(start: date = GDELT_START, end: date | None = None) -> pd.DataFrame:
    """
    one row per (quarter, term, bucket). counts approximated by article_search result count
    (capped at DOC 2.0's max 250, so near that ceiling treat as "high volume" rather than exact).
    """
    if end is None:
        end = date.today()
    if start < GDELT_START:
        start = GDELT_START

    kw = load_keywords()
    buckets = kw["buckets"]

    gd = _gd()
    rows = []

    for bucket_name, bucket in buckets.items():
        for term in bucket["terms"]:
            query = _anchored_query(term)
            for qstart, qend in _iter_quarters(start, end):
                req = {"q": query, "start": qstart.isoformat(), "end": qend.isoformat()}
                cached = cache_get(NAMESPACE, req)
                if cached is not None:
                    rows.append({"date": qstart.isoformat(), "term": term, "bucket": bucket_name, "count": cached, "source": "gdelt"})
                    continue

                count = None
                for attempt in range(3):
                    try:
                        f = _filter(query, qstart, qend)
                        articles = gd.article_search(f)
                        count = len(articles) if articles is not None else 0
                        break
                    except Exception as e:
                        if attempt == 2:
                            print(f"  gdelt fail {term!r} {qstart}: {type(e).__name__}: {e}")
                            count = 0
                        else:
                            time.sleep(1.5 * (attempt + 1))
                cache_put(NAMESPACE, req, count, summary=f"{term} {qstart}")
                rows.append({"date": qstart.isoformat(), "term": term, "bucket": bucket_name, "count": count, "source": "gdelt"})
                time.sleep(0.4)

    return pd.DataFrame(rows)


def pull_articles(start: date = GDELT_START, end: date | None = None, terms: list[str] | None = None) -> pd.DataFrame:
    """pull article text for panel 3. one query per term to stay within query-length limits."""
    if end is None:
        end = date.today()
    if start < GDELT_START:
        start = GDELT_START

    if terms is None:
        kw = load_keywords()
        terms = []
        for b in kw["buckets"].values():
            terms.extend(b["terms"])

    gd = _gd()
    rows: list[dict] = []

    for term in terms:
        for qstart, qend in _iter_quarters(start, end):
            req = {"term": term, "start": qstart.isoformat(), "end": qend.isoformat(), "mode": "arts"}
            cached = cache_get(NAMESPACE, req)
            if cached is not None:
                rows.extend(cached)
                continue

            try:
                f = _filter(term, qstart, qend)
                articles = gd.article_search(f)
                if articles is None or (hasattr(articles, "empty") and articles.empty):
                    records = []
                elif hasattr(articles, "to_dict"):
                    records = articles.to_dict(orient="records")
                else:
                    records = list(articles)
            except Exception as e:
                print(f"  gdelt article fail {term!r} {qstart}: {e}")
                records = []

            out = []
            for r in records:
                title = r.get("title", "") or ""
                out.append(
                    {
                        "source": "gdelt",
                        "date": str(r.get("seendate", qstart))[:10],
                        "title": title,
                        "text": title,  # DOC 2.0 returns metadata only, no fulltext
                        "url": r.get("url", ""),
                        "term": term,
                    }
                )
            cache_put(NAMESPACE, req, out, summary=f"arts {term} {qstart}")
            rows.extend(out)
            time.sleep(0.25)

    return pd.DataFrame(rows)


def save_volumes(df: pd.DataFrame, path: Path | None = None) -> Path:
    path = path or (PROCESSED_DIR / "panel1_news_volumes.csv")
    df.to_csv(path, index=False)
    return path


def save_articles(df: pd.DataFrame, path: Path | None = None) -> Path:
    path = path or (PROCESSED_DIR / "news_articles_gdelt.csv")
    df.to_csv(path, index=False)
    return path


if __name__ == "__main__":
    df = pull_volumes(start=date(2024, 1, 1), end=date(2024, 6, 30))
    print(df.groupby("bucket")["count"].sum())
