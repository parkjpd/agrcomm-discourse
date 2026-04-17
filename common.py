"""shared helpers: paths, yaml loading, sqlite cache."""
import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parent

# pick up .env if present. override=True ensures a real key in .env wins over an empty
# env var from a parent shell (claude code sandbox sets ANTHROPIC_API_KEY='' for safety).
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
except ImportError:
    pass
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = ROOT / "output"
CACHE_PATH = DATA_DIR / "cache.db"


def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name) as f:
        return yaml.safe_load(f)


def load_events() -> list[dict]:
    return load_yaml("events.yaml")["events"]


def load_keywords() -> dict:
    return load_yaml("keywords.yaml")


def load_sources() -> dict:
    return load_yaml("sources.yaml")


def load_stance_rubric() -> dict:
    return load_yaml("stance_rubric.yaml")


# cache table: a single key/value store keyed by (namespace, request_hash).
# namespace lets us invalidate one source without blowing away everything.

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    namespace TEXT NOT NULL,
    req_hash TEXT NOT NULL,
    req_summary TEXT,
    response TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (namespace, req_hash)
);
CREATE INDEX IF NOT EXISTS idx_cache_ns_created ON cache(namespace, created_at);
"""


def _hash_request(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


@contextmanager
def _conn():
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(CACHE_PATH)
    try:
        con.executescript(_SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def cache_get(namespace: str, payload: Any) -> Any | None:
    key = _hash_request(payload)
    with _conn() as con:
        row = con.execute(
            "SELECT response FROM cache WHERE namespace=? AND req_hash=?",
            (namespace, key),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def cache_put(namespace: str, payload: Any, response: Any, summary: str = "") -> None:
    key = _hash_request(payload)
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO cache (namespace, req_hash, req_summary, response, created_at) VALUES (?,?,?,?,?)",
            (namespace, key, summary, json.dumps(response, default=str), int(time.time())),
        )


def cache_stats() -> dict[str, int]:
    with _conn() as con:
        rows = con.execute(
            "SELECT namespace, COUNT(*) FROM cache GROUP BY namespace"
        ).fetchall()
    return {ns: n for ns, n in rows}


def ensure_dirs():
    for d in (DATA_DIR, SAMPLES_DIR, PROCESSED_DIR, RAW_DIR, OUTPUT_DIR):
        d.mkdir(parents=True, exist_ok=True)
