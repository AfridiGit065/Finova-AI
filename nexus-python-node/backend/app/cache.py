import os
import json
import time
from typing import Any, Dict, Optional, List

# L1 Cache Store
_L1_STORE: Dict[str, Dict[str, Any]] = {}

def get_cached(ns: str, key: str) -> Optional[Any]:
    cache_key = f"{ns}:{key}"
    entry = _L1_STORE.get(cache_key)
    if entry:
        if entry["expiry"] > time.time():
            return entry["data"]
        # Delete if expired
        _L1_STORE.pop(cache_key, None)
    return None

def set_cached(ns: str, key: str, data: Any, ttl_ms: int) -> None:
    cache_key = f"{ns}:{key}"
    _L1_STORE[cache_key] = {
        "data": data,
        "expiry": time.time() + (ttl_ms / 1000.0)
    }


# L2 Candle Cache Store (24h TTL)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDLE_CACHE_DIR = os.path.join(BACKEND_DIR, "data", "candles")
CANDLE_TTL_SECONDS = 24 * 60 * 60  # 24 hours

def _ensure_candle_dir():
    if not os.path.exists(CANDLE_CACHE_DIR):
        os.makedirs(CANDLE_CACHE_DIR, exist_ok=True)

def _candle_file_path(symbol: str) -> str:
    return os.path.join(CANDLE_CACHE_DIR, f"{symbol.upper()}.json")

def get_cached_candles(symbol: str) -> Optional[List[Dict[str, Any]]]:
    fp = _candle_file_path(symbol)
    if not os.path.exists(fp):
        return None
    try:
        with open(fp, "r", encoding="utf-8") as f:
            entry = json.load(f)
        
        fetched_at = entry.get("fetchedAt", 0)
        # Check TTL (24h)
        if time.time() * 1000 - fetched_at > CANDLE_TTL_SECONDS * 1000:
            try:
                os.remove(fp)
            except Exception:
                pass
            return None
        return entry.get("data")
    except Exception:
        return None

def set_cached_candles(symbol: str, data: List[Dict[str, Any]]) -> None:
    try:
        _ensure_candle_dir()
        fp = _candle_file_path(symbol)
        entry = {
            "symbol": symbol.upper(),
            "fetchedAt": int(time.time() * 1000),
            "data": data
        }
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to write candle cache for {symbol}: {e}")

def clear_candle_cache() -> int:
    cleared = 0
    if os.path.exists(CANDLE_CACHE_DIR):
        for filename in os.listdir(CANDLE_CACHE_DIR):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(CANDLE_CACHE_DIR, filename))
                    cleared += 1
                except Exception:
                    pass
    return cleared
