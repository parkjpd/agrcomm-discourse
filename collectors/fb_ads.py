"""
meta ad library collector.

queries the public political/issue-ad archive via the graph api. requires a
META_AD_LIBRARY_TOKEN env var (any meta developer user token with ads_read scope).
see https://www.facebook.com/ads/library/api/ for how to get one.

if no token is set, falls back to synthetic samples from data/samples/fb_ads.csv
so the pipeline still renders in demo mode.
"""
from __future__ import annotations

import csv
import os
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

from common import PROCESSED_DIR, SAMPLES_DIR, cache_get, cache_put, load_sources

NAMESPACE = "fb_ads"
GRAPH_BASE = "https://graph.facebook.com/v19.0/ads_archive"

# ads library only covers political and issue ads for countries where it's enabled.
# we restrict to US. change if comparing internationally.
COUNTRY = "US"


def _token() -> str | None:
    return os.environ.get("META_AD_LIBRARY_TOKEN")


def available() -> bool:
    return _token() is not None


def _query(search_terms: str, after: str | None = None, limit: int = 100) -> dict:
    """one page of graph api results. the real api paginates with a cursor."""
    params = {
        "access_token": _token(),
        "ad_type": "POLITICAL_AND_ISSUE_ADS",
        "ad_reached_countries": f'["{COUNTRY}"]',
        "ad_active_status": "ALL",
        "search_terms": search_terms,
        "fields": ",".join([
            "id", "page_name", "ad_creative_bodies", "ad_creative_link_titles",
            "ad_delivery_start_time", "ad_delivery_stop_time",
            "spend", "impressions", "ad_snapshot_url",
        ]),
        "limit": min(limit, 100),
    }
    if after:
        params["after"] = after
    # cache the (params) tuple so repeated runs during development are free
    req = {"params": {k: v for k, v in params.items() if k != "access_token"}}
    cached = cache_get(NAMESPACE, req)
    if cached is not None:
        return cached
    for attempt in range(4):
        try:
            r = requests.get(GRAPH_BASE, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                cache_put(NAMESPACE, req, data, summary=f"{search_terms[:30]} n={len(data.get('data', []))}")
                return data
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 ** attempt)
                continue
            print(f"  fb_ads api error {r.status_code}: {r.text[:200]}")
            return {"data": []}
        except Exception as e:
            if attempt == 3:
                print(f"  fb_ads request failed: {e}")
                return {"data": []}
            time.sleep(1.5 * (attempt + 1))
    return {"data": []}


def _parse_range(v) -> tuple[int, int]:
    """meta returns spend/impressions as {'lower_bound': '1000', 'upper_bound': '4999'}."""
    if not v or not isinstance(v, dict):
        return 0, 0
    try:
        return int(v.get("lower_bound", 0) or 0), int(v.get("upper_bound", 0) or 0)
    except (TypeError, ValueError):
        return 0, 0


def pull_live(max_pages_per_term: int = 10) -> pd.DataFrame:
    """pull ads for every search term in sources.yaml. returns a standardized df."""
    if not available():
        print("  skipping fb_ads live: META_AD_LIBRARY_TOKEN not set")
        return pd.DataFrame()

    cfg = load_sources().get("fb_ads", {})
    terms = cfg.get("search_terms", ["farmworker", "H-2A", "deportation", "immigration"])

    rows: list[dict] = []
    for term in terms:
        after = None
        for _ in range(max_pages_per_term):
            page = _query(term, after=after)
            for ad in page.get("data", []):
                bodies = ad.get("ad_creative_bodies") or []
                titles = ad.get("ad_creative_link_titles") or []
                text = "\n".join(bodies)
                title = (titles[0] if titles else (bodies[0][:80] if bodies else ""))
                if not text and not title:
                    continue
                start_s = ad.get("ad_delivery_start_time", "")
                try:
                    d = datetime.strptime(start_s[:10], "%Y-%m-%d").date()
                except Exception:
                    continue
                spend_lo, spend_hi = _parse_range(ad.get("spend"))
                impr_lo, impr_hi = _parse_range(ad.get("impressions"))
                rows.append({
                    "source": "fb_ads",
                    "date": d.isoformat(),
                    "page_name": ad.get("page_name", ""),
                    "title": title,
                    "text": text,
                    "spend_lower": spend_lo, "spend_upper": spend_hi,
                    "impressions_lower": impr_lo, "impressions_upper": impr_hi,
                    "url": ad.get("ad_snapshot_url", ""),
                    "true_bucket": None, "true_stance": None, "true_topic": None,
                })
            # pagination cursor
            after = page.get("paging", {}).get("cursors", {}).get("after")
            if not after:
                break
    return pd.DataFrame(rows)


def pull(demo: bool = False) -> pd.DataFrame:
    """main entrypoint. live if token is set and not demo; otherwise synthetic fallback."""
    if not demo and available():
        live_df = pull_live()
        if not live_df.empty:
            return live_df
        print("  fb_ads: live pull returned 0 rows, falling back to synthetic")

    sample_path = SAMPLES_DIR / "fb_ads.csv"
    if sample_path.exists():
        return pd.read_csv(sample_path)
    print(f"  fb_ads: no samples at {sample_path}; run `python -m scripts.make_samples` first")
    return pd.DataFrame()


def render_processed(output: Path | None = None) -> Path:
    """write collected ads to processed/. same shape as the reddit collector."""
    output = output or (PROCESSED_DIR / "fb_ads.csv")
    df = pull(demo=not available())
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    print(f"  wrote {len(df)} fb_ads rows -> {output}")
    return output


if __name__ == "__main__":
    render_processed()
