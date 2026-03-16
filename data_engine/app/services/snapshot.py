# app/services/snapshot.py
from __future__ import annotations
import os, json, hashlib
from datetime import datetime
from typing import Any

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def _key(ticker: str, start_iso: str|None, end_iso: str|None) -> str:
    raw = f"{ticker.upper()}|{start_iso or ''}|{end_iso or ''}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def snapshot_path(ticker: str, start_iso: str|None, end_iso: str|None) -> str:
    return os.path.join(CACHE_DIR, f"news_{_key(ticker, start_iso, end_iso)}.json")

def load_snapshot(ticker: str, start_iso: str|None, end_iso: str|None) -> dict|None:
    p = snapshot_path(ticker, start_iso, end_iso)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_snapshot(ticker: str, start_iso: str|None, end_iso: str|None, rows: list[dict[str,Any]]) -> dict:
    p = snapshot_path(ticker, start_iso, end_iso)
    payload = {
        "ticker": ticker.upper(),
        "start": start_iso,
        "end": end_iso,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(rows),
        "rows": rows,
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    return payload
