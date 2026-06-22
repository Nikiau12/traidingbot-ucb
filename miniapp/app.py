from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl

import psycopg
import requests
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DEMO_USER_ID = int(os.getenv("DEMO_USER_ID", "10001"))
PAYMENT_AMOUNT = os.getenv("SUBSCRIPTION_PRICE_USDT", "29.99")
PAYMENT_DAYS = int(os.getenv("SUBSCRIPTION_DAYS", "30"))
PAYMENT_NETWORK = os.getenv("USDT_PAYMENT_NETWORK", "TRC20 (Tron)")
PAYMENT_WALLET = os.getenv("USDT_PAYMENT_ADDRESS", "TBkS2PU1STndH6hsRGCHT2CE2ZyUDfsZ1c")
FREE_TRIAL_SIGNALS = int(os.getenv("FREE_TRIAL_SIGNALS", "5"))
SUPPORTED_LANGUAGES = {"en", "ru", "de", "fr", "es"}


def normalize_usdt_symbol(symbol: str) -> Optional[str]:
    market = str(symbol or "").upper().strip().split(":", 1)[0]
    normalized = market.replace("/", "_").replace("-", "_")
    return normalized if normalized.endswith("_USDT") else None

PAYMENT_MESSAGES = {
    "en": (
        "🔒 <b>Monthly access</b>\n\nAccess for <b>{days} days</b>: <b>{amount} USDT</b>.\n"
        "Network: <b>{network}</b>\nWallet:\n<code>{wallet}</code>\n\n"
        "After payment, send:\n<code>/paid TX_HASH</code>\n\n"
        "The bot will verify the transaction and activate access automatically."
    ),
    "ru": (
        "🔒 <b>Месячный доступ</b>\n\nДоступ на <b>{days} дней</b>: <b>{amount} USDT</b>.\n"
        "Сеть: <b>{network}</b>\nКошелёк:\n<code>{wallet}</code>\n\n"
        "После перевода отправь:\n<code>/paid TX_HASH</code>\n\n"
        "Бот проверит транзакцию и автоматически активирует доступ."
    ),
    "de": (
        "🔒 <b>Monatlicher Zugang</b>\n\nZugang für <b>{days} Tage</b>: <b>{amount} USDT</b>.\n"
        "Netzwerk: <b>{network}</b>\nWallet:\n<code>{wallet}</code>\n\n"
        "Sende nach der Zahlung:\n<code>/paid TX_HASH</code>\n\n"
        "Der Bot prüft die Transaktion und aktiviert den Zugang automatisch."
    ),
    "fr": (
        "🔒 <b>Accès mensuel</b>\n\nAccès pendant <b>{days} jours</b> : <b>{amount} USDT</b>.\n"
        "Réseau : <b>{network}</b>\nPortefeuille :\n<code>{wallet}</code>\n\n"
        "Après le paiement, envoie :\n<code>/paid TX_HASH</code>\n\n"
        "Le bot vérifiera la transaction et activera automatiquement l'accès."
    ),
    "es": (
        "🔒 <b>Acceso mensual</b>\n\nAcceso durante <b>{days} días</b>: <b>{amount} USDT</b>.\n"
        "Red: <b>{network}</b>\nBilletera:\n<code>{wallet}</code>\n\n"
        "Después del pago, envía:\n<code>/paid TX_HASH</code>\n\n"
        "El bot verificará la transacción y activará el acceso automáticamente."
    ),
}

app = FastAPI(title="UCB Trading Mini App", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class SettingsUpdate(BaseModel):
    language: Optional[str] = None
    deposit: Optional[float] = Field(default=None, gt=0, le=1_000_000_000)
    risk_pct: Optional[float] = Field(default=None, ge=0.1, le=5)
    leverage: Optional[float] = Field(default=None, ge=1, le=100)
    margin: Optional[str] = None


@contextmanager
def db():
    if not DATABASE_URL:
        yield None
        return
    with psycopg.connect(DATABASE_URL) as connection:
        yield connection


def init_db() -> None:
    if not DATABASE_URL:
        print("[MiniApp] DATABASE_URL missing; demo data will be used")
        return
    with db() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                telegram_user_id BIGINT PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'en',
                deposit NUMERIC,
                risk_pct NUMERIC NOT NULL DEFAULT 1,
                leverage NUMERIC NOT NULL DEFAULT 10,
                margin TEXT NOT NULL DEFAULT 'cross',
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS subscriptions (
                telegram_user_id BIGINT PRIMARY KEY,
                trial_used INTEGER NOT NULL DEFAULT 0,
                paid_until TIMESTAMPTZ,
                payment_status TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS signals (
                id BIGSERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                confidence NUMERIC NOT NULL,
                price NUMERIC,
                entry NUMERIC,
                stop NUMERIC,
                tp1 NUMERIC,
                tp2 NUMERIC,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS signals_created_at_idx ON signals (created_at DESC);
            CREATE TABLE IF NOT EXISTS user_signal_access (
                telegram_user_id BIGINT NOT NULL,
                signal_id BIGINT NOT NULL,
                granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (telegram_user_id, signal_id)
            );
            """
        )
        connection.commit()


@app.on_event("startup")
def startup() -> None:
    init_db()


def normalize_language(value: Optional[str]) -> str:
    language = (value or "en").split("-")[0].lower()
    return language if language in SUPPORTED_LANGUAGES else "en"


def telegram_user(init_data: str) -> dict:
    if not init_data:
        if BOT_TOKEN:
            raise HTTPException(401, "Open this app from Telegram")
        return {"id": DEMO_USER_ID, "first_name": "Nikita", "language_code": "en"}

    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", "")
    auth_date = int(values.get("auth_date", "0") or 0)
    if not received_hash or abs(time.time() - auth_date) > 86400:
        raise HTTPException(401, "Telegram session expired")

    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(401, "Invalid Telegram signature")

    try:
        user = json.loads(values["user"])
        int(user["id"])
        return user
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(401, "Telegram user missing") from exc


def get_user(x_telegram_init_data: str = Header(default="")) -> dict:
    return telegram_user(x_telegram_init_data)


def demo_profile(user: dict) -> dict:
    return {
        "telegram_user_id": int(user["id"]),
        "first_name": user.get("first_name", "Trader"),
        "language": normalize_language(user.get("language_code")),
        "deposit": 400.0,
        "risk_pct": 1.0,
        "leverage": 10.0,
        "margin": "cross",
        "trial_left": 3,
        "trial_total": FREE_TRIAL_SIGNALS,
        "has_paid_access": False,
        "paid_until": None,
        "payment_status": None,
        "bot_username": bot_username(),
    }


@lru_cache(maxsize=1)
def bot_username() -> str:
    if not BOT_TOKEN:
        return ""
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getMe",
            timeout=8,
        )
        response.raise_for_status()
        result = response.json().get("result") or {}
        return str(result.get("username") or "")
    except (requests.RequestException, ValueError, TypeError):
        return ""


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "database": bool(DATABASE_URL)}


@app.get("/api/me")
def me(x_telegram_init_data: str = Header(default="")):
    user = get_user(x_telegram_init_data)
    if not DATABASE_URL:
        return demo_profile(user)

    user_id = int(user["id"])
    fallback_language = normalize_language(user.get("language_code"))
    with db() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO user_profiles (telegram_user_id, language)
            VALUES (%s, %s)
            ON CONFLICT (telegram_user_id) DO NOTHING
            """,
            (user_id, fallback_language),
        )
        cursor.execute(
            "INSERT INTO subscriptions (telegram_user_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (user_id,),
        )
        cursor.execute(
            """
            SELECT p.language, p.deposit, p.risk_pct, p.leverage, p.margin,
                   s.trial_used, s.paid_until, s.payment_status
            FROM user_profiles p
            JOIN subscriptions s USING (telegram_user_id)
            WHERE p.telegram_user_id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        connection.commit()

    return {
        "telegram_user_id": user_id,
        "first_name": user.get("first_name", "Trader"),
        "language": row[0],
        "deposit": float(row[1]) if row[1] is not None else None,
        "risk_pct": float(row[2]),
        "leverage": float(row[3]),
        "margin": row[4],
        "trial_left": max(0, FREE_TRIAL_SIGNALS - int(row[5])),
        "trial_total": FREE_TRIAL_SIGNALS,
        "has_paid_access": bool(row[6] and row[6] > datetime.now(timezone.utc)),
        "paid_until": row[6].isoformat() if row[6] else None,
        "payment_status": row[7],
        "bot_username": bot_username(),
    }


@app.patch("/api/settings")
def update_settings(payload: SettingsUpdate, x_telegram_init_data: str = Header(default="")):
    user = get_user(x_telegram_init_data)
    if payload.language is not None and payload.language not in SUPPORTED_LANGUAGES:
        raise HTTPException(422, "Unsupported language")
    if payload.margin is not None and payload.margin not in {"cross", "isolated"}:
        raise HTTPException(422, "Unsupported margin mode")
    if not DATABASE_URL:
        return {"ok": True}

    updates = payload.model_dump(exclude_none=True)
    if not updates:
        return {"ok": True}
    columns = {"leverage": "leverage", **{key: key for key in ("language", "deposit", "risk_pct", "margin")}}
    assignments = ", ".join(f"{columns[key]} = %s" for key in updates)
    values = list(updates.values())
    with db() as connection, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO user_profiles (telegram_user_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (int(user["id"]),),
        )
        cursor.execute(
            f"UPDATE user_profiles SET {assignments}, updated_at = NOW() WHERE telegram_user_id = %s",
            (*values, int(user["id"])),
        )
        connection.commit()
    return {"ok": True}


@app.post("/api/payment-instructions")
def payment_instructions(x_telegram_init_data: str = Header(default="")):
    user = get_user(x_telegram_init_data)
    language = normalize_language(user.get("language_code"))
    if DATABASE_URL:
        with db() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT language FROM user_profiles WHERE telegram_user_id = %s",
                (int(user["id"]),),
            )
            row = cursor.fetchone()
            if row:
                language = normalize_language(row[0])
    if not BOT_TOKEN:
        raise HTTPException(503, "Telegram bot is not configured")
    text = PAYMENT_MESSAGES[language].format(
        days=PAYMENT_DAYS,
        amount=PAYMENT_AMOUNT,
        network=PAYMENT_NETWORK,
        wallet=PAYMENT_WALLET,
    )
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": int(user["id"]), "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        response.raise_for_status()
        if not response.json().get("ok"):
            raise HTTPException(502, "Telegram rejected the message")
    except requests.RequestException as exc:
        raise HTTPException(502, "Could not send payment instructions") from exc
    return {"ok": True}


@app.get("/api/signals")
def signals(x_telegram_init_data: str = Header(default="")):
    user = get_user(x_telegram_init_data)
    if not DATABASE_URL:
        return [
            {"id": 3, "symbol": "BTC_USDT", "side": "LONG", "confidence": 0.78, "price": 64120, "entry": 64000, "stop": 62800, "tp1": 65500, "tp2": 67000, "created_at": "2026-06-22T08:25:00Z"},
            {"id": 2, "symbol": "SOL_USDT", "side": "SHORT", "confidence": 0.69, "price": 147.9, "entry": 148.2, "stop": 152.6, "tp1": 141.5, "tp2": 136.8, "created_at": "2026-06-22T07:05:00Z"},
            {"id": 1, "symbol": "ETH_USDT", "side": "LONG", "confidence": 0.66, "price": 3551, "entry": 3540, "stop": 3448, "tp1": 3695, "tp2": 3820, "created_at": "2026-06-22T05:05:00Z"},
        ]
    user_id = int(user["id"])
    usdt_only = "UPPER(symbol) ~ '(_USDT|/USDT)(:USDT)?$'"
    usdt_only_aliased = "UPPER(s.symbol) ~ '(_USDT|/USDT)(:USDT)?$'"
    with db() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_signal_access (
                telegram_user_id BIGINT NOT NULL,
                signal_id BIGINT NOT NULL,
                granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (telegram_user_id, signal_id)
            )
            """
        )
        cursor.execute(
            "SELECT trial_used, paid_until FROM subscriptions WHERE telegram_user_id = %s",
            (user_id,),
        )
        access = cursor.fetchone() or (0, None)
        has_paid_access = bool(access[1] and access[1] > datetime.now(timezone.utc))
        if has_paid_access:
            cursor.execute(
                f"""
                SELECT id, symbol, side, confidence, price, entry, stop, tp1, tp2, created_at
                FROM signals WHERE {usdt_only} ORDER BY created_at DESC LIMIT 30
                """
            )
            rows = cursor.fetchall()
        else:
            cursor.execute(
                f"""
                SELECT s.id, s.symbol, s.side, s.confidence, s.price, s.entry,
                       s.stop, s.tp1, s.tp2, s.created_at
                FROM signals s
                JOIN user_signal_access a ON a.signal_id = s.id
                WHERE a.telegram_user_id = %s AND {usdt_only_aliased}
                ORDER BY s.created_at DESC LIMIT %s
                """,
                (user_id, FREE_TRIAL_SIGNALS),
            )
            rows = cursor.fetchall()
            # Existing users predate per-user signal grants. Seed their already-used trial once.
            if not rows and int(access[0] or 0) > 0:
                cursor.execute(
                    f"SELECT id FROM signals WHERE {usdt_only} ORDER BY created_at DESC LIMIT %s",
                    (min(int(access[0]), FREE_TRIAL_SIGNALS),),
                )
                for (signal_id,) in cursor.fetchall():
                    cursor.execute(
                        """
                        INSERT INTO user_signal_access (telegram_user_id, signal_id)
                        VALUES (%s, %s) ON CONFLICT DO NOTHING
                        """,
                        (user_id, signal_id),
                    )
                cursor.execute(
                    f"""
                    SELECT s.id, s.symbol, s.side, s.confidence, s.price, s.entry,
                           s.stop, s.tp1, s.tp2, s.created_at
                    FROM signals s
                    JOIN user_signal_access a ON a.signal_id = s.id
                    WHERE a.telegram_user_id = %s AND {usdt_only_aliased}
                    ORDER BY s.created_at DESC LIMIT %s
                    """,
                    (user_id, FREE_TRIAL_SIGNALS),
                )
                rows = cursor.fetchall()
        connection.commit()
    return [
        {"id": row[0], "symbol": normalize_usdt_symbol(row[1]), "side": row[2], "confidence": float(row[3]),
         "price": float(row[4]) if row[4] is not None else None,
         "entry": float(row[5]) if row[5] is not None else None,
         "stop": float(row[6]) if row[6] is not None else None,
         "tp1": float(row[7]) if row[7] is not None else None,
         "tp2": float(row[8]) if row[8] is not None else None,
         "created_at": row[9].isoformat()}
        for row in rows
    ]


@app.get("/api/market/{symbol}")
def market(symbol: str, timeframe: str = "1h", x_telegram_init_data: str = Header(default="")):
    get_user(x_telegram_init_data)
    normalized = symbol.upper().replace("_", "")
    if not normalized.endswith("USDT") or not normalized.isalnum():
        raise HTTPException(422, "Invalid symbol")
    intervals = {
        "15m": ("Min15", 15 * 60),
        "1h": ("Min60", 60 * 60),
        "4h": ("Hour4", 4 * 60 * 60),
        "1d": ("Day1", 24 * 60 * 60),
    }
    if timeframe not in intervals:
        raise HTTPException(422, "Invalid timeframe")
    mexc_interval, candle_seconds = intervals[timeframe]
    contract_symbol = normalized[:-4] + "_USDT"
    try:
        end = int(time.time())
        response = requests.get(
            f"https://contract.mexc.com/api/v1/contract/kline/{contract_symbol}",
            params={"interval": mexc_interval, "start": end - 180 * candle_seconds, "end": end},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json().get("data") or {}
        volumes = data.get("vol") or data.get("volume") or []
        return [
            {"time": int(timestamp), "open": float(data["open"][index]),
             "high": float(data["high"][index]), "low": float(data["low"][index]),
             "close": float(data["close"][index]),
             "volume": float(volumes[index]) if index < len(volumes) else 0.0}
            for index, timestamp in enumerate(data.get("time", []))
        ]
    except (requests.RequestException, ValueError, TypeError, IndexError) as exc:
        raise HTTPException(502, "MEXC market data unavailable") from exc
