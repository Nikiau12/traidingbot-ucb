#!/usr/bin/env python3
"""UCB_TRADING_BOT — единая система (aiogram)
Старый функционал : SMC / MTF / спайки / листинги / access control
Новый функционал  : /plan (EMA+ATR+ADX), /scan, /digest, /set, /settings, i18n x5
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ── старые модули ──
from mexc.exchange_client_mexc import ExchangeClient
from core.smc_analyzer import SMCAnalyzer
from core.spike_scanner import SpikeScanner
from core.notifier import Notifier
from core.smart_engine import SmartContextEngine, SignalType, MTFFusionEngine
from core.coin_info_service import CoinInfoService
from core.listing_watcher import MexcListingWatcher
from core.access_manager import AccessManager
from core.config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ADMIN_CHAT_IDS,
    TOP_COINS_LIMIT, TARGET_COINS,
    SMART_SPIKE_MIN_SCORE, SMART_SPIKE_MIN_QUOTE_VOLUME,
    MEXC_LISTING_SNAPSHOT_FILE, MEXC_ANNOUNCEMENTS_SNAPSHOT_FILE,
    MEXC_LISTING_CHECK_INTERVAL, MEXC_NEW_LISTINGS_URL,
    FREE_TRIAL_SIGNALS, PAID_ACCESS_HOURS,
    USDT_PAYMENT_ADDRESS, USDT_PAYMENT_AMOUNT, USDT_PAYMENT_NETWORK,
    ACCESS_STATE_FILE, USER_REGISTRY_FILE,
)

# ── наши торговые модули из trading/ ──
_TRADING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trading")
if _TRADING_DIR not in sys.path:
    sys.path.insert(0, _TRADING_DIR)

import mexc_snapshot as snap
import trade_plan as core_plan
import scanner as sc
import state as st
from i18n import LANG_BUTTONS, t as _t
from telegram_render import render_telegram_plan

# ── конфиг сканера ──
with open(os.path.join(_TRADING_DIR, "config.json")) as _f:
    _CFG = json.load(_f)
SCAN_CFG  = _CFG["scanner"]
TRADE_CFG = _CFG["trading"]

# ── Whop интеграция ──
WHOP_API_KEY = os.getenv("WHOP_API_KEY", "")
_WHOP_VALIDATE_URL = "https://api.whop.com/api/v2/memberships/validate_license"

# ── инициализация бота ──
bot_instance = Bot(token=TELEGRAM_BOT_TOKEN)
dp  = Dispatcher()
router = Router()

SPIKE_COOLDOWN = 4 * 3600
SETUP_COOLDOWN = 8 * 3600
SCAN_REFERENCE_DEPOSIT = 1000.0


class DepositSetup(StatesGroup):
    waiting_for_amount = State()

# ═══════════════════════════════════════════
# ПОЛЬЗОВАТЕЛИ
# ═══════════════════════════════════════════

def load_users():
    if os.path.exists(USER_REGISTRY_FILE):
        try:
            with open(USER_REGISTRY_FILE) as f:
                return set(json.load(f))
        except Exception:
            pass
    return {str(TELEGRAM_CHAT_ID)} if TELEGRAM_CHAT_ID else set()

def save_user(chat_id: str):
    users = load_users()
    if chat_id not in users:
        users.add(chat_id)
        with open(USER_REGISTRY_FILE, "w") as f:
            json.dump(list(users), f)
        return True
    return False

active_users = load_users()

# ── старые сервисы ──
exchange        = ExchangeClient()
smc_analyzer    = SMCAnalyzer()
spike_scanner   = SpikeScanner()
smart_engine    = SmartContextEngine()
mtf_engine      = MTFFusionEngine()
coin_info_svc   = CoinInfoService()
access_manager  = AccessManager(
    ACCESS_STATE_FILE,
    free_trial_signals=FREE_TRIAL_SIGNALS,
    paid_access_hours=PAID_ACCESS_HOURS,
    payment_address=USDT_PAYMENT_ADDRESS,
    payment_amount=USDT_PAYMENT_AMOUNT,
    payment_network=USDT_PAYMENT_NETWORK,
)
listing_watcher = MexcListingWatcher(
    MEXC_LISTING_SNAPSHOT_FILE,
    announcements_snapshot_file=MEXC_ANNOUNCEMENTS_SNAPSHOT_FILE,
    announcements_url=MEXC_NEW_LISTINGS_URL,
)
notifier = Notifier(bot_instance, active_users, access_manager=access_manager)

# ═══════════════════════════════════════════
# ХЕЛПЕРЫ
# ═══════════════════════════════════════════

def is_admin(chat_id: str) -> bool:
    return str(chat_id) in ADMIN_CHAT_IDS

def format_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "нет"

def get_lang(user_id: int) -> str:
    return st.get_user_lang(user_id)

def _lang_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    btns = [InlineKeyboardButton(text=lbl, callback_data=cb) for lbl, cb in LANG_BUTTONS]
    return InlineKeyboardMarkup(inline_keyboard=[
        btns[:3],
        btns[3:],
        [InlineKeyboardButton(text=_t(lang, "deposit_button"), callback_data="set_deposit")],
    ])


def _deposit_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=_t(lang, "deposit_button"), callback_data="set_deposit")
    ]])

def _parse_kv(parts):
    kv = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            kv[k.strip()] = v.strip()
    return kv

def _conf(plan: dict) -> float:
    if plan.get("side") == "skip":
        return float(plan.get("confidence", 0) or 0)
    return float((plan.get("primary") or {}).get("confidence", 0) or 0)

def norm_sym(s: str) -> str:
    s = s.upper().strip()
    if "_" not in s and s.endswith("USDT"):
        s = s[:-4] + "_USDT"
    return s

async def require_access(message: types.Message) -> bool:
    chat_id = str(message.chat.id)
    if is_admin(chat_id):
        return True
    allowed, _ = access_manager.consume_signal(chat_id)
    if allowed:
        return True
    await message.reply(access_manager.format_paywall(), parse_mode="HTML")
    return False

def _whop_check(license_key: str) -> dict:
    """Синхронный запрос к Whop API — запускать через run_in_executor."""
    import requests
    resp = requests.post(
        _WHOP_VALIDATE_URL,
        json={"license_key": license_key},
        headers={
            "Authorization": f"Bearer {WHOP_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    return resp.json()

# ═══════════════════════════════════════════
# КОМАНДЫ — ОБЩИЕ
# ═══════════════════════════════════════════

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    chat_id = str(message.chat.id)
    is_new = save_user(chat_id)
    access_manager.ensure_user(chat_id)
    notifier.active_users.add(chat_id)
    if is_new:
        print(f"Новый пользователь: {chat_id}")
    lang = get_lang(message.from_user.id)
    await message.reply(_t(lang, "welcome"), parse_mode="HTML", reply_markup=_lang_keyboard(lang))


@router.callback_query(lambda c: c.data.startswith("lang_"))
async def handle_lang_callback(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    st.set_user_lang(callback.from_user.id, lang)
    settings = st.get_user_settings(callback.from_user.id)
    text = _t(lang, "lang_set")
    reply_markup = None
    if not settings.get("deposit"):
        text += "\n\n" + _t(lang, "deposit_start_hint")
        reply_markup = _deposit_keyboard(lang)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await callback.answer()


@router.callback_query(F.data == "set_deposit")
async def handle_deposit_callback(callback: types.CallbackQuery, state: FSMContext):
    lang = get_lang(callback.from_user.id)
    await state.set_state(DepositSetup.waiting_for_amount)
    await callback.message.reply(_t(lang, "deposit_prompt"), parse_mode="HTML")
    await callback.answer()


@router.message(DepositSetup.waiting_for_amount)
async def handle_deposit_amount(message: types.Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    raw = (message.text or "").strip().replace(" ", "").replace(",", ".")
    try:
        deposit = float(raw)
        if deposit <= 0 or deposit > 1_000_000_000:
            raise ValueError
    except ValueError:
        await message.reply(_t(lang, "deposit_invalid"), parse_mode="HTML")
        return

    st.set_user_setting(message.from_user.id, "deposit", deposit)
    await state.clear()
    await message.reply(
        _t(lang, "deposit_saved", deposit=f"{deposit:,.2f}"),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    lang = get_lang(message.from_user.id)
    await message.reply(
        _t(lang, "help",
           top_n=SCAN_CFG["top_n_symbols"],
           digest_hour=SCAN_CFG["daily_digest_utc_hour"]),
        parse_mode="HTML",
    )


@router.message(Command("subscribe"))
async def cmd_subscribe(message: types.Message):
    await message.reply(access_manager.format_paywall(), parse_mode="HTML")


@router.message(Command("status"))
async def cmd_status(message: types.Message):
    s = access_manager.status(str(message.chat.id))
    access_text = (
        f"✅ Оплачен до: <b>{format_ts(s['paid_until'])}</b>"
        if s["has_paid_access"] else "⏳ Активной оплаты нет"
    )
    claim = s.get("payment_claim") or {}
    claim_text = (
        f"\n\nПоследняя заявка:\nTX: <code>{claim.get('tx_hash','н/д')}</code>\n"
        f"Статус: <b>{claim.get('status','pending')}</b>"
        if claim else ""
    )
    await message.reply(
        f"👤 <b>Статус доступа</b>\n\n{access_text}\n"
        f"Бесплатных сигналов: <b>{s['trial_left']}</b> из {FREE_TRIAL_SIGNALS}"
        f"{claim_text}",
        parse_mode="HTML",
    )


@router.message(Command("paid"))
async def cmd_paid(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Пришли хеш транзакции:\n<code>/paid TX_HASH</code>", parse_mode="HTML")
        return
    chat_id = str(message.chat.id)
    tx_hash = parts[1].strip()
    access_manager.record_payment_claim(chat_id, tx_hash)
    await message.reply("✅ Заявка принята. Админ проверит и включит доступ.", parse_mode="HTML")
    admin_msg = (
        f"💸 <b>Новая заявка на оплату</b>\n\nUser: <code>{chat_id}</code>\n"
        f"TX: <code>{tx_hash}</code>\n\n<code>/grant {chat_id}</code>"
    )
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await bot_instance.send_message(chat_id=admin_id, text=admin_msg, parse_mode="HTML")
        except Exception as e:
            print(f"Admin notify failed {admin_id}: {e}")


@router.message(Command("grant"))
async def cmd_grant(message: types.Message):
    if not is_admin(str(message.chat.id)):
        await message.reply("⛔️ Только для админа.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Использование: <code>/grant CHAT_ID [hours]</code>", parse_mode="HTML")
        return
    target = parts[1]
    hours = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else PAID_ACCESS_HOURS
    paid_until = access_manager.grant_access(target, hours=hours)
    await message.reply(
        f"✅ Доступ выдан <code>{target}</code> до <b>{format_ts(paid_until)}</b>",
        parse_mode="HTML",
    )
    try:
        await bot_instance.send_message(
            chat_id=target,
            text=f"✅ Оплата подтверждена. Доступ до <b>{format_ts(paid_until)}</b>.",
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.message(Command("revoke"))
async def cmd_revoke(message: types.Message):
    if not is_admin(str(message.chat.id)):
        await message.reply("⛔️ Только для админа.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Использование: <code>/revoke CHAT_ID</code>", parse_mode="HTML")
        return
    access_manager.revoke_access(parts[1])
    await message.reply(f"✅ Доступ <code>{parts[1]}</code> отключен.", parse_mode="HTML")


@router.message(Command("activate"))
async def cmd_activate(message: types.Message):
    chat_id = str(message.chat.id)
    lang    = get_lang(message.from_user.id)
    parts   = message.text.split()

    if len(parts) < 2:
        await message.reply(
            "🔑 <b>Активация Whop-доступа</b>\n\n"
            "Введи ключ из письма после покупки на Whop:\n"
            "<code>/activate ВАШ_КЛЮЧ</code>\n\n"
            "Ключ выглядит примерно так: <code>wxk_XXXXXXXXXXXX</code>",
            parse_mode="HTML",
        )
        return

    license_key = parts[1].strip()

    # Проверяем не был ли ключ уже использован
    if st.is_whop_key_used(license_key):
        await message.reply(
            "❌ Этот ключ уже был активирован ранее.\n\n"
            "Если ты активировал его сам — используй /status чтобы проверить доступ.\n"
            "Если нет — обратись к администратору.",
            parse_mode="HTML",
        )
        return

    if not WHOP_API_KEY:
        await message.reply("⚠️ Whop интеграция не настроена. Обратись к администратору.")
        return

    status_msg = await message.reply("⏳ Проверяю ключ на Whop...")
    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _whop_check, license_key)

        membership = result.get("membership") or result.get("data") or {}
        is_valid   = (
            result.get("success") is True
            or result.get("valid") is True
            or membership.get("valid") is True
            or membership.get("status") == "active"
        )

        if is_valid:
            paid_until = access_manager.grant_access(chat_id, hours=8760)  # 1 год
            st.mark_whop_key_used(license_key, chat_id)
            await status_msg.edit_text(
                f"✅ <b>Доступ активирован!</b>\n\n"
                f"Ключ Whop принят. Доступ открыт до <b>{format_ts(paid_until)}</b>.\n\n"
                f"Используй /help чтобы увидеть все команды.\n"
                f"Сначала укажи депозит: <code>/set deposit=5000</code>",
                parse_mode="HTML",
            )
            # Уведомить админа
            for admin_id in ADMIN_CHAT_IDS:
                try:
                    await bot_instance.send_message(
                        chat_id=admin_id,
                        text=(
                            f"✅ <b>Новая активация через Whop</b>\n\n"
                            f"User: <code>{chat_id}</code>\n"
                            f"Ключ: <code>{license_key}</code>"
                        ),
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
        else:
            error_detail = result.get("error") or result.get("message") or "ключ не найден"
            await status_msg.edit_text(
                f"❌ <b>Ключ не прошёл проверку</b>\n\n"
                f"Причина: {error_detail}\n\n"
                f"• Убедись что скопировал ключ полностью\n"
                f"• Купить доступ: whop.com/ucb-trading-bot\n"
                f"• Платёж TRC20: /subscribe",
                parse_mode="HTML",
            )
    except Exception as e:
        await status_msg.edit_text(
            f"⚠️ Ошибка при проверке ключа: <code>{e}</code>\n\n"
            "Попробуй позже или обратись к администратору.",
            parse_mode="HTML",
        )

# ═══════════════════════════════════════════
# КОМАНДЫ — SMC (старый функционал)
# ═══════════════════════════════════════════

@router.message(Command("setup"))
async def cmd_setup(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("ℹ️ Использование: <code>/setup BTC</code>", parse_mode="HTML")
        return
    await _handle_setup(message, parts[1].upper())


@router.message(Command("spikes"))
async def cmd_spikes(message: types.Message):
    await _handle_spikes(message)

# ═══════════════════════════════════════════
# КОМАНДЫ — ПЛАН (наш функционал)
# ═══════════════════════════════════════════

@router.message(Command("plan"))
async def cmd_plan(message: types.Message):
    if not await require_access(message):
        return
    uid  = message.from_user.id
    lang = get_lang(uid)
    parts = message.text.split()[1:]
    if not parts:
        await message.reply(_t(lang, "plan_usage"), parse_mode="HTML")
        return

    symbol   = norm_sym(parts[0])
    kv       = _parse_kv(parts[1:])
    settings = st.get_user_settings(uid)
    deposit  = float(kv["deposit"]) if "deposit" in kv else settings.get("deposit")

    if not deposit:
        await message.reply(_t(lang, "no_deposit"), parse_mode="HTML")
        return

    risk_pct = float(kv.get("risk",   settings["risk_pct"]))
    lev      = float(kv.get("lev",    settings["lev"]))
    margin   =       kv.get("margin", settings["margin"])

    status_msg = await message.reply(_t(lang, "plan_loading", symbol=symbol), parse_mode="HTML")
    try:
        loop     = asyncio.get_event_loop()
        snapshot = await loop.run_in_executor(None, snap.build_snapshot_with_fallback, symbol)
        plan     = core_plan.make_plan(snapshot, deposit=deposit, risk_pct=risk_pct, lev=lev, margin=margin)
        text     = render_telegram_plan(plan, deposit=deposit, risk_pct=risk_pct, lang=lang)
        await status_msg.edit_text(text, parse_mode="HTML")
    except Exception as e:
        await status_msg.edit_text(_t(lang, "plan_error", error=e), parse_mode="HTML")


@router.message(Command("set"))
async def cmd_set(message: types.Message):
    uid  = message.from_user.id
    lang = get_lang(uid)
    kv   = _parse_kv(message.text.split()[1:])
    if not kv:
        await message.reply(_t(lang, "set_usage"), parse_mode="HTML")
        return
    allowed = {"deposit": "deposit", "risk": "risk_pct", "lev": "lev", "margin": "margin"}
    updated = []
    for k, v in kv.items():
        if k not in allowed:
            await message.reply(_t(lang, "set_unknown", key=k), parse_mode="HTML")
            return
        val = v if k == "margin" else float(v)
        st.set_user_setting(uid, allowed[k], val)
        updated.append(f"{k}={v}")
    await message.reply(_t(lang, "set_saved", params=", ".join(updated)), parse_mode="HTML")


@router.message(Command("settings"))
async def cmd_settings(message: types.Message):
    uid      = message.from_user.id
    lang     = get_lang(uid)
    settings = st.get_user_settings(uid)
    deposit  = settings.get("deposit")
    text     = _t(lang, "settings_title")
    text    += _t(lang, "settings_deposit", val=f"{deposit:,.0f} USDT") if deposit else _t(lang, "settings_deposit_missing")
    text    += _t(lang, "settings_risk",   val=settings["risk_pct"])
    text    += _t(lang, "settings_lev",    val=settings["lev"])
    text    += _t(lang, "settings_margin", val=settings["margin"])
    text    += _t(lang, "settings_change")
    await message.reply(text, parse_mode="HTML")


@router.message(Command("scan"))
async def cmd_scan(message: types.Message):
    if not await require_access(message):
        return
    uid      = message.from_user.id
    lang     = get_lang(uid)
    settings = st.get_user_settings(uid)
    deposit = settings.get("deposit") or SCAN_REFERENCE_DEPOSIT

    if not settings.get("deposit"):
        await message.reply(
            _t(lang, "scan_reference_deposit", deposit=f"{SCAN_REFERENCE_DEPOSIT:,.0f}"),
            parse_mode="HTML",
            reply_markup=_deposit_keyboard(lang),
        )

    status_msg = await message.reply(
        _t(lang, "scan_starting", top_n=SCAN_CFG["top_n_symbols"]), parse_mode="HTML"
    )
    loop = asyncio.get_event_loop()
    try:
        symbols = await loop.run_in_executor(None, snap.top_symbols_by_volume, SCAN_CFG["top_n_symbols"])
        results = await loop.run_in_executor(
            None,
            lambda: sc.scan_all(
                symbols,
                deposit=deposit,
                risk_pct=settings["risk_pct"],
                lev=settings["lev"],
                margin=settings["margin"],
                workers=SCAN_CFG["workers"],
            ),
        )
        actionable = [r for r in results if _conf(r) >= SCAN_CFG["min_confidence"] and r.get("side") != "skip"]
        if not actionable:
            await status_msg.edit_text(_t(lang, "scan_none"), parse_mode="HTML")
            return
        await status_msg.edit_text(_t(lang, "scan_done", count=len(actionable)), parse_mode="HTML")
        for plan in actionable[:5]:
            text = render_telegram_plan(plan, deposit=deposit, risk_pct=settings["risk_pct"], lang=lang)
            await message.reply(text, parse_mode="HTML")
            await asyncio.sleep(0.4)
        if len(actionable) > 5:
            await message.reply(_t(lang, "scan_more", count=len(actionable) - 5), parse_mode="HTML")
    except Exception as e:
        await status_msg.edit_text(_t(lang, "scan_error", error=e), parse_mode="HTML")


@router.message(Command("digest"))
async def cmd_digest(message: types.Message):
    if not await require_access(message):
        return
    uid      = message.from_user.id
    lang     = get_lang(uid)
    settings = st.get_user_settings(uid)
    if not settings.get("deposit"):
        await message.reply(_t(lang, "no_deposit"), parse_mode="HTML")
        return
    status_msg = await message.reply(_t(lang, "digest_preparing"), parse_mode="HTML")
    await _run_digest(str(message.chat.id), settings, lang, status_msg=status_msg)


async def _run_digest(chat_id, settings, lang, *, status_msg=None):
    loop = asyncio.get_event_loop()
    try:
        symbols = await loop.run_in_executor(None, snap.top_symbols_by_volume, SCAN_CFG["top_n_symbols"])
        results = await loop.run_in_executor(
            None,
            lambda: sc.scan_all(
                symbols,
                deposit=settings["deposit"],
                risk_pct=settings["risk_pct"],
                lev=settings["lev"],
                margin=settings["margin"],
                workers=SCAN_CFG["workers"],
            ),
        )
        high    = [r for r in results if _conf(r) >= 0.65 and r.get("side") != "skip"]
        medium  = [r for r in results if 0.50 <= _conf(r) < 0.65 and r.get("side") != "skip"]
        skipped = len(results) - len(high) - len(medium)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        lines = [_t(lang, "digest_title", time=now_str, total=len(results)), ""]
        if high:
            lines.append(_t(lang, "digest_high", count=len(high)))
            for r in high[:15]:
                sym  = r.get("symbol", "?")
                side = str((r.get("primary") or {}).get("side", "?")).upper()
                em   = "🟩" if side == "LONG" else "🟥"
                lines.append(f"  {em} <code>{sym}</code> {side} conf={_conf(r):.2f}")
            lines.append("")
        if medium:
            lines.append(_t(lang, "digest_medium", count=len(medium)))
            for r in medium[:10]:
                sym  = r.get("symbol", "?")
                side = str((r.get("primary") or {}).get("side", "?")).upper()
                lines.append(f"  • <code>{sym}</code> {side} conf={_conf(r):.2f}")
            lines.append("")
        lines.append(_t(lang, "digest_skipped", count=skipped))
        summary = "\n".join(lines)

        if status_msg:
            await status_msg.edit_text(summary, parse_mode="HTML")
        else:
            await bot_instance.send_message(chat_id=chat_id, text=summary, parse_mode="HTML")

        for plan in high[:3]:
            full = render_telegram_plan(plan, deposit=settings["deposit"], risk_pct=settings["risk_pct"], lang=lang)
            await bot_instance.send_message(chat_id=chat_id, text=full, parse_mode="HTML")
            await asyncio.sleep(0.4)
    except Exception as e:
        err = _t(lang, "digest_error", error=e)
        if status_msg:
            await status_msg.edit_text(err, parse_mode="HTML")
        else:
            await bot_instance.send_message(chat_id=chat_id, text=err, parse_mode="HTML")

# ═══════════════════════════════════════════
# SMC / SPIKE ЛОГИКА (старый функционал)
# ═══════════════════════════════════════════

async def _fetch_mtf(symbol: str) -> dict:
    dfs = {"1w": None, "1d": None, "4h": None, "1h": None, "15m": None}
    for tf in dfs:
        df = await (exchange.fetch_historical_data(symbol, tf) if tf == "1w" else exchange.fetch_ohlcv(symbol, tf))
        if not df.empty:
            smart_engine.add_context_indicators(df)
            dfs[tf] = df
        await asyncio.sleep(0.05)
    return dfs


async def _handle_setup(message: types.Message, coin: str):
    if not await require_access(message):
        return
    symbol = await exchange.validate_symbol(coin)
    if not symbol:
        await message.reply(f"❌ {coin} не найдена на MEXC.")
        return
    await message.reply(f"🔍 Анализирую {symbol} по SMC (4h / 1d)...")
    try:
        found = False
        for tf in ["4h", "1d"]:
            df = await exchange.fetch_ohlcv(symbol, tf)
            if df.empty:
                continue
            smc_res = smc_analyzer.analyze_tf(df)
            setup = smc_analyzer.find_setup(smc_res)
            if setup:
                score = smart_engine.analyze_context(df, symbol, setup["type"])
                if score.signal != SignalType.NO_TRADE:
                    dfs = await _fetch_mtf(symbol)
                    verdict = mtf_engine.analyze(dfs)
                    if verdict.setup_type.name != "NO_TRADE":
                        msg = notifier.format_smc_setup(symbol, tf, setup, score, verdict)
                        await message.reply(msg, parse_mode="HTML")
                        found = True
        if not found:
            await message.reply(f"🤷 Нет свежих SMC сетапов по {symbol} на 4h/1d.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


async def _handle_spikes(message: types.Message):
    if not await require_access(message):
        return
    await message.reply("🚀 Сканирую всплески по Топ-250...")
    try:
        symbols = await exchange.get_top_pairs()
        found = []
        for symbol in symbols:
            df = await exchange.fetch_ohlcv(symbol, "15m")
            if df.empty:
                continue
            ticker = await exchange.fetch_ticker_cached(symbol)
            spike = spike_scanner.scan(df, ticker=ticker)
            if spike:
                found.append((symbol, spike))
            await asyncio.sleep(0.05)
        if not found:
            await message.reply("🤷 Аномалий не обнаружено.")
            return
        for sym, spk in found[:15]:
            coin_info = await coin_info_service.get_coin_info(sym)
            msg = notifier.format_spike_alert(sym, "15m", spk, coin_info=coin_info)
            await message.reply(msg, parse_mode="HTML")
            await asyncio.sleep(0.1)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

# ═══════════════════════════════════════════
# ОБРАБОТЧИК ТЕКСТА (natural language)
# ═══════════════════════════════════════════

_SKIP_WORDS = {"ПО", "НА", "ДАЙ", "И", "В", "ЗА", "THE", "A", "BY", "FOR", "OF"}

@router.message(F.text)
async def handle_text(message: types.Message):
    text  = message.text.lower()
    words = message.text.split()

    coin = next(
        (w.upper() for w in words
         if len(w) >= 2 and w.upper().isalpha() and w.upper() not in _SKIP_WORDS),
        None,
    )

    if any(kw in text for kw in ("всплеск", "памп", "дамп", "spike", "pump", "dump", "сканер")):
        await _handle_spikes(message)
    elif any(kw in text for kw in ("анализ", "analyze", "analyse")) and coin:
        if not await require_access(message):
            return
        symbol = await exchange.validate_symbol(coin)
        if not symbol:
            await message.reply(f"❌ {coin} не найдена.")
            return
        await message.reply(f"🤖 Глубокий анализ {symbol} (15m→1w)...")
        try:
            dfs = await _fetch_mtf(symbol)
            analyses = {tf: smc_analyzer.analyze_tf(df) for tf, df in dfs.items() if df is not None}
            verdict = mtf_engine.analyze(dfs)
            msg = notifier.format_full_analysis(symbol, analyses, verdict)
            await message.reply(msg, parse_mode="HTML")
        except Exception as e:
            await message.reply(f"❌ Ошибка: {e}")
    elif any(kw in text for kw in ("сетап", "setup", "сигнал", "signal")) and coin:
        await _handle_setup(message, coin)

# ═══════════════════════════════════════════
# ФОНОВЫЕ ЦИКЛЫ
# ═══════════════════════════════════════════

last_spike_alert: dict = {}
last_setup_alert: dict = {}
_last_plan_1h_block: int = -1  # сканируем каждый час, повтор одной монеты — не чаще 4h

# Токены которые не нужно торговать — стоковые и левериджные
_JUNK_SUFFIXES = ("STOCK", "BULL", "BEAR", "ETF", "UP", "DOWN", "3L", "3S")

def _is_junk_symbol(symbol: str) -> bool:
    base = symbol.replace("_USDT", "").upper()
    return any(base.endswith(s) for s in _JUNK_SUFFIXES)

def _fmt_price(p) -> str:
    if p is None or p == "?":
        return "?"
    try:
        p = float(p)
        if p >= 10000: return f"{p:,.0f}"
        if p >= 1000:  return f"{p:,.1f}"
        if p >= 10:    return f"{p:.2f}"
        if p >= 1:     return f"{p:.4f}"
        return f"{p:.6f}"
    except Exception:
        return str(p)

def _pct(a, b) -> str:
    try:
        return f"{abs(float(a) - float(b)) / float(b) * 100:.1f}%"
    except Exception:
        return ""

def _rr(entry, stop, tp) -> str:
    try:
        risk   = abs(float(entry) - float(stop))
        reward = abs(float(tp)    - float(entry))
        return f"RR {reward / risk:.1f}x" if risk else ""
    except Exception:
        return ""

def _fmt_auto_alert(plan: dict, symbol: str, side: str, conf: float) -> str:
    p       = plan.get("primary") or {}
    ctx     = plan.get("context") or {}
    tps     = p.get("tps") or []
    entry   = p.get("entry")
    stop_p  = p.get("stop")
    tp1     = tps[0]["price"] if tps else None
    tp2     = tps[1]["price"] if len(tps) > 1 else None
    price   = plan.get("price")
    regime  = str(ctx.get("regime", "")).upper() or "—"
    trend1d = str(ctx.get("trend_1d", "")).upper() or "—"
    why     = p.get("why") or []
    arrow   = "↗️" if side == "LONG" else "↘️"
    badge   = "🟢 LONG" if side == "LONG" else "🔴 SHORT"

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        f"📊 <b>СИГНАЛ — {badge}</b>",
        "━━━━━━━━━━━━━━━━━━",
        "",
        f"🪙 <b><code>{symbol}</code></b>",
        f"💵 Цена сейчас: <code>{_fmt_price(price)}</code>",
        f"🧭 Режим: <b>{regime}</b>  |  Тренд 1D: <b>{trend1d}</b>",
        f"⭐️ Уверенность: <b>{conf:.2f}</b> / 1.0",
        "",
        "─────────────────",
        f"{arrow} Вход:   <code>{_fmt_price(entry)}</code>",
        f"🛑 Стоп:  <code>{_fmt_price(stop_p)}</code>  ({_pct(stop_p, entry)} от входа)",
        f"🥅 TP1:   <code>{_fmt_price(tp1)}</code>  (+{_pct(tp1, entry)})  {_rr(entry, stop_p, tp1)}",
        f"🥅 TP2:   <code>{_fmt_price(tp2)}</code>  (+{_pct(tp2, entry)})  {_rr(entry, stop_p, tp2)}",
        "─────────────────",
    ]
    if why:
        lines.append(f"🔍 <i>{' · '.join(str(w) for w in why[:3])}</i>")
        lines.append("")
    lines.append(f"📦 Размер позиции → /plan <code>{symbol}</code>")
    return "\n".join(lines)


async def market_scanner_loop():
    """Реалтайм сканер: спайки (15m) + SMC сетапы (4h/1d)."""
    while True:
        try:
            now = time.time()
            symbols = await exchange.get_top_pairs()

            for i, symbol in enumerate(symbols):
                target_symbols = [f"{coin}/USDT" for coin in TARGET_COINS]
                is_smc = (i < TOP_COINS_LIMIT) or (symbol in target_symbols)

                for tf in ["15m", "4h", "1d"]:
                    df = await exchange.fetch_ohlcv(symbol, tf)
                    if df.empty:
                        continue

                    if tf == "15m":
                        ticker = await exchange.fetch_ticker_cached(symbol)
                        spike = spike_scanner.scan(df, ticker=ticker)
                        if spike:
                            if spike.get("score", 0) < SMART_SPIKE_MIN_SCORE:
                                continue
                            if spike.get("quote_volume", 0) and spike["quote_volume"] < SMART_SPIKE_MIN_QUOTE_VOLUME:
                                continue
                            key = f"{symbol}_{tf}_{spike['direction']}"
                            if now - last_spike_alert.get(key, 0) > SPIKE_COOLDOWN:
                                coin_info = await coin_info_service.get_coin_info(symbol)
                                await notifier.send_message(
                                    notifier.format_spike_alert(symbol, tf, spike, coin_info=coin_info)
                                )
                                last_spike_alert[key] = now
                                await asyncio.sleep(0.1)

                    if tf in ["4h", "1d"] and is_smc:
                        smc_res = smc_analyzer.analyze_tf(df)
                        setup = smc_analyzer.find_setup(smc_res)
                        if setup:
                            score = smart_engine.analyze_context(df, symbol, setup["type"])
                            if score.signal == SignalType.NO_TRADE:
                                continue
                            dfs = await _fetch_mtf(symbol)
                            verdict = mtf_engine.analyze(dfs)
                            if verdict.setup_type.name == "NO_TRADE":
                                continue
                            key = f"{symbol}_{tf}_{setup['type']}"
                            if now - last_setup_alert.get(key, 0) > SETUP_COOLDOWN:
                                await notifier.send_message(
                                    notifier.format_smc_setup(symbol, tf, setup, score, verdict)
                                )
                                last_setup_alert[key] = now
                                await asyncio.sleep(0.1)

                await asyncio.sleep(0.5)

            # чистка кэша
            now = time.time()
            last_spike_alert.update({k: v for k, v in last_spike_alert.items() if now - v <= SPIKE_COOLDOWN})
            last_setup_alert.update({k: v for k, v in last_setup_alert.items() if now - v <= SETUP_COOLDOWN})
            print("Фоновый цикл завершен. Ожидание 60 сек...")
            await asyncio.sleep(60)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"market_scanner_loop error: {e}")
            await asyncio.sleep(10)


async def plan_scanner_loop():
    """EMA/ATR планировщик — запускается через 5 мин после каждого закрытия 1h свечи.
    Повтор одной и той же монеты — не чаще раза в 4h (dedup в state.py).
    """
    global _last_plan_1h_block
    while True:
        try:
            now = datetime.now(timezone.utc)
            block = now.hour                      # 0..23, меняется каждый час
            minutes_since = now.minute

            if minutes_since >= 5 and _last_plan_1h_block != block:
                _last_plan_1h_block = block
                print(f"[PlanScanner] 1h block {block:02d}:00 — starting...")
                try:
                    loop = asyncio.get_event_loop()
                    symbols = await loop.run_in_executor(
                        None, snap.top_symbols_by_volume, SCAN_CFG["top_n_symbols"]
                    )
                    # Используем системный дефолт для автоалёртов (без депозита пользователя)
                    results = await loop.run_in_executor(
                        None,
                        lambda: sc.scan_all(
                            symbols,
                            deposit=1000,  # reference only — position sizes in auto alerts are indicative
                            risk_pct=TRADE_CFG["default_risk_pct"],
                            lev=TRADE_CFG["default_lev"],
                            margin=TRADE_CFG["default_margin"],
                            workers=SCAN_CFG["workers"],
                        ),
                    )
                    sent = 0
                    for plan in results:
                        conf   = _conf(plan)
                        symbol = plan.get("symbol", "")
                        side   = (plan.get("primary") or {}).get("side", "skip")

                        if conf < SCAN_CFG["min_confidence"] or plan.get("side") == "skip":
                            continue
                        if _is_junk_symbol(symbol):
                            continue
                        if not st.should_send_alert(symbol, side, conf):
                            continue

                        alert = _fmt_auto_alert(plan, symbol, side.upper(), conf)
                        await notifier.send_message(alert)
                        st.mark_sent(symbol, side, conf)
                        sent += 1
                        await asyncio.sleep(0.5)
                    print(f"[PlanScanner] Done: {len(results)} scanned, {sent} alerts sent")
                except Exception as e:
                    print(f"[PlanScanner] Error: {e}")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"plan_scanner_loop error: {e}")

        await asyncio.sleep(60)


async def listing_watcher_loop():
    while True:
        try:
            for item in (await listing_watcher.check_new_announcements())[:10]:
                symbol = item["symbols"][0] if item.get("symbols") else ""
                coin_info = await coin_info_service.get_coin_info(symbol) if symbol else {}
                await notifier.send_message(notifier.format_listing_news_alert(item, coin_info=coin_info))
                await asyncio.sleep(0.2)
            for symbol in (await listing_watcher.check_new_markets(exchange))[:20]:
                coin_info = await coin_info_service.get_coin_info(symbol)
                await notifier.send_message(notifier.format_listing_alert(symbol, coin_info=coin_info))
                await asyncio.sleep(0.2)
            await asyncio.sleep(MEXC_LISTING_CHECK_INTERVAL)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"listing_watcher_loop error: {e}")
            await asyncio.sleep(60)

# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

async def main():
    print("UCB_TRADING_BOT — unified system starting...")
    dp.include_router(router)
    t1 = asyncio.create_task(market_scanner_loop())
    t2 = asyncio.create_task(plan_scanner_loop())
    t3 = asyncio.create_task(listing_watcher_loop())
    try:
        await dp.start_polling(bot_instance)
    finally:
        t1.cancel(); t2.cancel(); t3.cancel()
        await exchange.close()
        await notifier.close()

if __name__ == "__main__":
    asyncio.run(main())
