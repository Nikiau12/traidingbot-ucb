#!/usr/bin/env python3
import json
import sys
import time
from urllib.parse import urlencode
from typing import Optional, Dict, Any

import warnings
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL*")

import os
import requests

BASE = "https://api.mexc.com"
CACHE_DIR = os.path.expanduser("~/.openclaw/trading/cache")

def http_get(path: str, params: Optional[Dict[str, Any]] = None, timeout: int = 10):
    url = f"{BASE}{path}"
    if params:
        url = url + "?" + urlencode(params)
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "openclaw-mexc-snapshot/1.1"})
    r.raise_for_status()
    return r.json()

def futures_contracts():
    return http_get("/api/v1/contract/detail")

def futures_ticker(symbol: str):
    return http_get("/api/v1/contract/ticker", {"symbol": symbol}, timeout=10)

def futures_funding(symbol: str):
    return http_get(f"/api/v1/contract/funding_rate/{symbol}", timeout=10)

def interval_seconds(interval: str) -> int:
    m = {
        "Min1": 60,
        "Min5": 5 * 60,
        "Min15": 15 * 60,
        "Min30": 30 * 60,
        "Min60": 60 * 60,
        "Hour4": 4 * 60 * 60,
        "Hour8": 8 * 60 * 60,
        "Day1": 24 * 60 * 60,
        "Day2": 2 * 24 * 60 * 60,
        "Week1": 7 * 24 * 60 * 60,
        "Month1": 30 * 24 * 60 * 60,
    }
    return m.get(interval, 60)

def futures_kline(symbol: str, interval: str, limit: int = 200):
    end = int(time.time())
    start = end - interval_seconds(interval) * limit
    return http_get(
        f"/api/v1/contract/kline/{symbol}",
        {"interval": interval, "start": start, "end": end},
        timeout=15
    )

def extract_contract_symbols(payload) -> list:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("data", payload)
    else:
        items = payload

    if isinstance(items, dict):
        for key in ("contracts", "symbols", "rows", "items", "list"):
            v = items.get(key)
            if isinstance(v, list):
                items = v
                break

    out = []
    if isinstance(items, list):
        for it in items:
            if isinstance(it, str):
                out.append(it)
            elif isinstance(it, dict):
                sym = it.get("symbol") or it.get("contractCode") or it.get("name")
                if sym:
                    out.append(str(sym))
    return sorted(set(out))

def cache_path(symbol: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = symbol.replace("/", "_")
    return os.path.join(CACHE_DIR, f"{safe}.snapshot.json")

def load_cache(symbol: str):
    p = cache_path(symbol)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_cache(symbol: str, payload: dict):
    p = cache_path(symbol)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, p)

def cmd_symbols():
    payload = futures_contracts()
    syms = extract_contract_symbols(payload)
    print(json.dumps({"ts": int(time.time() * 1000), "count": len(syms), "symbols": syms}, ensure_ascii=False))

def build_snapshot(symbol: str) -> dict:
    return {
        "ts": int(time.time() * 1000),
        "symbol": symbol,
        "ticker": futures_ticker(symbol),
        "funding": futures_funding(symbol),
        "kline_15m": futures_kline(symbol, "Min15", 200),
        "kline_1h": futures_kline(symbol, "Min60", 200),
        "kline_4h": futures_kline(symbol, "Hour4", 200),
        "kline_1d": futures_kline(symbol, "Day1", 200),
        "kline_2d": futures_kline(symbol, "Day2", 200),
        "kline_1w": futures_kline(symbol, "Week1", 200),
        "stale": False,
    }

def build_snapshot_with_fallback(symbol: str) -> dict:
    try:
        out = build_snapshot(symbol)
        save_cache(symbol, out)
        return out
    except Exception as e:
        cached = load_cache(symbol)
        if cached:
            cached["stale"] = True
            cached["stale_reason"] = str(e)
            cached["ts"] = int(time.time() * 1000)
            return cached
        raise

def futures_all_tickers():
    return http_get("/api/v1/contract/ticker")

def top_symbols_by_volume(n: int = 250) -> list:
    try:
        data = futures_all_tickers()
        items = data.get("data", []) if isinstance(data, dict) else (data or [])
        if not isinstance(items, list) or not items:
            raise ValueError("unexpected ticker format")
        tickers = []
        for t in items:
            if not isinstance(t, dict):
                continue
            sym = t.get("symbol", "")
            if not sym:
                continue
            vol = 0.0
            for key in ("amount24", "volume24", "turnover", "amount"):
                v = t.get(key)
                if v is not None:
                    try:
                        vol = float(v)
                        break
                    except Exception:
                        pass
            tickers.append((sym, vol))
        tickers.sort(key=lambda x: x[1], reverse=True)
        return [sym for sym, _ in tickers[:n]]
    except Exception:
        payload = futures_contracts()
        return extract_contract_symbols(payload)[:n]

def cmd_snapshot(symbol: str):
    out = build_snapshot_with_fallback(symbol)
    print(json.dumps(out, ensure_ascii=False))

def main():
    if len(sys.argv) < 2:
        print("usage: mexc_snapshot.py symbols | snapshot SYMBOL", file=sys.stderr)
        sys.exit(2)

    cmd = sys.argv[1].strip().lower()

    if cmd == "symbols":
        cmd_symbols()
        return

    if cmd == "snapshot":
        if len(sys.argv) < 3:
            print("usage: mexc_snapshot.py snapshot BTC_USDT", file=sys.stderr)
            sys.exit(2)
        symbol = sys.argv[2].strip().upper()
        cmd_snapshot(symbol)
        return

    print("unknown command. use: symbols | snapshot SYMBOL", file=sys.stderr)
    sys.exit(2)

if __name__ == "__main__":
    main()
