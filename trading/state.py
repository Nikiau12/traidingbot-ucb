from __future__ import annotations

import json
import os
import time
from typing import Dict

try:
    import psycopg
except ImportError:
    psycopg = None

STATE_PATH = os.path.expanduser("~/.openclaw/trading/bot_state.json")
DATABASE_URL = os.getenv("DATABASE_URL", "")


def _db_ready() -> bool:
    return bool(DATABASE_URL and psycopg)


def _ensure_profiles_table(connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            telegram_user_id BIGINT PRIMARY KEY,
            language TEXT NOT NULL DEFAULT 'en',
            deposit NUMERIC,
            risk_pct NUMERIC NOT NULL DEFAULT 1,
            leverage NUMERIC NOT NULL DEFAULT 10,
            margin TEXT NOT NULL DEFAULT 'cross',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


def _load() -> Dict:
    if not os.path.exists(STATE_PATH):
        return {"alerts": {}}
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"alerts": {}}


def _save(state: Dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


def should_send_alert(symbol: str, side: str, conf: float,
                       cooldown_secs: int = 4 * 3600) -> bool:
    prev = _load().get("alerts", {}).get(symbol)
    if prev is None:
        return True
    if prev.get("side") != side:
        return True
    if time.time() - prev.get("ts", 0) > cooldown_secs:
        return True
    if abs(conf - prev.get("conf", 0)) >= 0.10:
        return True
    return False


def mark_sent(symbol: str, side: str, conf: float) -> None:
    state = _load()
    state.setdefault("alerts", {})[symbol] = {
        "side": side,
        "conf": conf,
        "ts": time.time(),
    }
    _save(state)


def get_user_lang(user_id: int) -> str:
    if _db_ready():
        try:
            with psycopg.connect(DATABASE_URL) as connection:
                _ensure_profiles_table(connection)
                row = connection.execute(
                    "SELECT language FROM user_profiles WHERE telegram_user_id = %s", (user_id,)
                ).fetchone()
                if row:
                    return row[0]
        except Exception as exc:
            print(f"[state] database language read failed: {exc}")
    return _load().get("user_langs", {}).get(str(user_id), "en")


def set_user_lang(user_id: int, lang: str) -> None:
    if _db_ready():
        try:
            with psycopg.connect(DATABASE_URL) as connection:
                _ensure_profiles_table(connection)
                connection.execute(
                    """
                    INSERT INTO user_profiles (telegram_user_id, language) VALUES (%s, %s)
                    ON CONFLICT (telegram_user_id) DO UPDATE
                    SET language = EXCLUDED.language, updated_at = NOW()
                    """,
                    (user_id, lang),
                )
                connection.commit()
        except Exception as exc:
            print(f"[state] database language write failed: {exc}")
    state = _load()
    state.setdefault("user_langs", {})[str(user_id)] = lang
    _save(state)


_USER_DEFAULTS = {"deposit": None, "risk_pct": 1.0, "lev": 10.0, "margin": "cross"}


def get_user_settings(user_id: int) -> dict:
    if _db_ready():
        try:
            with psycopg.connect(DATABASE_URL) as connection:
                _ensure_profiles_table(connection)
                row = connection.execute(
                    """
                    SELECT deposit, risk_pct, leverage, margin
                    FROM user_profiles WHERE telegram_user_id = %s
                    """,
                    (user_id,),
                ).fetchone()
                if row:
                    return {
                        "deposit": float(row[0]) if row[0] is not None else None,
                        "risk_pct": float(row[1]),
                        "lev": float(row[2]),
                        "margin": row[3],
                    }
        except Exception as exc:
            print(f"[state] database settings read failed: {exc}")
    saved = _load().get("user_settings", {}).get(str(user_id), {})
    return {**_USER_DEFAULTS, **saved}


def set_user_setting(user_id: int, key: str, value) -> None:
    db_column = {"deposit": "deposit", "risk_pct": "risk_pct", "lev": "leverage", "margin": "margin"}.get(key)
    if _db_ready() and db_column:
        try:
            with psycopg.connect(DATABASE_URL) as connection:
                _ensure_profiles_table(connection)
                connection.execute(
                    "INSERT INTO user_profiles (telegram_user_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (user_id,),
                )
                connection.execute(
                    f"UPDATE user_profiles SET {db_column} = %s, updated_at = NOW() WHERE telegram_user_id = %s",
                    (value, user_id),
                )
                connection.commit()
        except Exception as exc:
            print(f"[state] database setting write failed: {exc}")
    state = _load()
    state.setdefault("user_settings", {}).setdefault(str(user_id), {})[key] = value
    _save(state)


def save_signal(plan: dict, symbol: str, side: str, confidence: float) -> None:
    if not _db_ready():
        return
    primary = plan.get("primary") or {}
    tps = primary.get("tps") or []
    try:
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id BIGSERIAL PRIMARY KEY, symbol TEXT NOT NULL, side TEXT NOT NULL,
                    confidence NUMERIC NOT NULL, price NUMERIC, entry NUMERIC, stop NUMERIC,
                    tp1 NUMERIC, tp2 NUMERIC, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            connection.execute(
                """
                INSERT INTO signals (symbol, side, confidence, price, entry, stop, tp1, tp2)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (symbol, side.upper(), confidence, plan.get("price"), primary.get("entry"),
                 primary.get("stop"), tps[0].get("price") if tps else None,
                 tps[1].get("price") if len(tps) > 1 else None),
            )
            connection.commit()
    except Exception as exc:
        print(f"[state] signal history write failed: {exc}")


def is_whop_key_used(key: str) -> bool:
    return key in _load().get("whop_keys", {})


def mark_whop_key_used(key: str, chat_id: str) -> None:
    state = _load()
    state.setdefault("whop_keys", {})[key] = {"chat_id": chat_id, "ts": time.time()}
    _save(state)
