"""
agricultural futures collector (panel 4 experimental).

pulls daily close prices via yfinance for migrant-labor-exposed commodities and
returns them quarterized so they line up with panel 1 keyword buckets.

tickers picked for migrant-labor exposure:
- OJ=F   frozen concentrated orange juice (florida citrus, H-2A heavy)
- DC=F   class III milk (dairy labor heavy)
- SB=F   sugar #11 (louisiana / florida sugar cane, migrant crew labor)
- LE=F   live cattle (moderate labor exposure)
- ZC=F   corn (low labor, mechanized - included as baseline, should NOT correlate much)
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from common import PROCESSED_DIR, cache_get, cache_put

NAMESPACE = "futures"

TICKERS = {
    "FCOJ":            "OJ=F",   # frozen concentrated orange juice
    "milk_class_iii":  "DC=F",   # class III milk
    "sugar_11":        "SB=F",   # sugar no. 11
    "live_cattle":     "LE=F",   # live cattle
    "corn_baseline":   "ZC=F",   # corn (baseline, low labor exposure)
}


def _fetch_ticker(ticker: str, start: date, end: date) -> pd.DataFrame:
    """daily close prices. cached in sqlite."""
    import yfinance as yf

    req = {"ticker": ticker, "start": start.isoformat(), "end": end.isoformat()}
    cached = cache_get(NAMESPACE, req)
    if cached is not None:
        df = pd.DataFrame(cached)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df

    df = yf.download(ticker, start=start.isoformat(), end=end.isoformat(), progress=False, auto_adjust=True)
    if df is None or df.empty:
        cache_put(NAMESPACE, req, [])
        return pd.DataFrame(columns=["date", "close"])

    # flatten multi-index columns that newer yfinance sometimes returns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    out = pd.DataFrame({"date": df.index, "close": df["Close"].values})
    cache_put(NAMESPACE, req, out.assign(date=out["date"].dt.date.astype(str)).to_dict(orient="records"), summary=f"{ticker} {len(out)}d")
    return out


def pull_all(start: date = date(2010, 1, 1), end: date | None = None) -> dict[str, pd.DataFrame]:
    if end is None:
        end = date.today()
    return {name: _fetch_ticker(t, start, end) for name, t in TICKERS.items()}


def quarterly_average(daily: pd.DataFrame) -> pd.DataFrame:
    """resample daily closes to quarterly mean. returns date (quarter start) + close."""
    if daily.empty:
        return daily
    df = daily.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    q = df["close"].resample("QS").mean().reset_index()
    q.columns = ["date", "close"]
    return q


def save_panel4(tickers: dict[str, pd.DataFrame], path: Path | None = None) -> Path:
    path = path or (PROCESSED_DIR / "panel4_futures_quarterly.csv")
    rows = []
    for name, df in tickers.items():
        q = quarterly_average(df)
        q["ticker"] = name
        rows.append(q)
    if rows:
        pd.concat(rows, ignore_index=True).to_csv(path, index=False)
    return path


if __name__ == "__main__":
    data = pull_all()
    for name, df in data.items():
        print(f"{name}: {len(df)} daily rows")
    save_panel4(data)
    print(f"wrote {PROCESSED_DIR}/panel4_futures_quarterly.csv")
