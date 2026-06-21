#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, time as dtime, timezone
from typing import Any, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import mexc_snapshot as snap
import trade_plan as core
import scanner as sc
import state as st
from i18n import LANG_BUTTONS, t
from telegram_render import render_telegram_plan

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config() -> Dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_lang(user_id: int) -> str:
    return st.get_user_lang(user_id)


def norm_sym(s: str) -> str:
    s = s.upper().strip()
    if "_" not in s and s.endswith("USDT"):
        s = s[:-4] + "_USDT"
    return s


def _conf(plan: Dict) -> float:
    if plan.get("side") == "skip":
        return float(plan.get("confidence", 0) or 0)
    return float((plan.get("primary") or {}).get("confidence", 0) or 0)


def _parse_kv(args) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    for a in args:
        if "=" in a:
            k, v = a.split("=", 1)
            kv[k.strip()] = v.strip()
    return kv


def _lang_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(label, callback_data=data)
        for label, data in LANG_BUTTONS
    ]
    # 3 + 2 layout
    return InlineKeyboardMarkup([buttons[:3], buttons[3:]])


# ───────────────────────── /start ─────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid  = update.effective_user.id
    lang = get_lang(uid)
    await update.message.reply_html(
        t(lang, "welcome"),
        reply_markup=_lang_keyboard(),
    )


async def handle_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    lang_map = {data: data.split("_")[1] for _, data in LANG_BUTTONS}
    chosen = lang_map.get(query.data)
    if not chosen:
        return

    uid = query.from_user.id
    st.set_user_lang(uid, chosen)

    await query.edit_message_text(
        t(chosen, "lang_set"),
        parse_mode=ParseMode.HTML,
    )


# ───────────────────────── /help ─────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid  = update.effective_user.id
    lang = get_lang(uid)
    cfg  = load_config()
    s_cfg = cfg["scanner"]

    await update.message.reply_html(
        t(lang, "help",
          top_n=s_cfg["top_n_symbols"],
          digest_hour=s_cfg["daily_digest_utc_hour"],
          ),
    )


# ───────────────────────── /set ─────────────────────────

async def cmd_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid  = update.effective_user.id
    lang = get_lang(uid)
    args = context.args or []
    kv   = _parse_kv(args)

    if not kv:
        await update.message.reply_html(t(lang, "set_usage"))
        return

    allowed = {"deposit": "deposit", "risk": "risk_pct", "lev": "lev", "margin": "margin"}
    updated = []

    for k, v in kv.items():
        if k not in allowed:
            await update.message.reply_html(t(lang, "set_unknown", key=k))
            return
        val = v if k == "margin" else float(v)
        st.set_user_setting(uid, allowed[k], val)
        updated.append(f"{k}={v}")

    await update.message.reply_html(t(lang, "set_saved", params=", ".join(updated)))


# ───────────────────────── /settings ─────────────────────────

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid      = update.effective_user.id
    lang     = get_lang(uid)
    settings = st.get_user_settings(uid)
    deposit  = settings.get("deposit")

    text = t(lang, "settings_title")
    if deposit:
        text += t(lang, "settings_deposit", val=f"{deposit:,.0f} USDT")
    else:
        text += t(lang, "settings_deposit_missing")
    text += t(lang, "settings_risk",   val=settings["risk_pct"])
    text += t(lang, "settings_lev",    val=settings["lev"])
    text += t(lang, "settings_margin", val=settings["margin"])
    text += t(lang, "settings_change")

    await update.message.reply_html(text)


# ───────────────────────── /plan ─────────────────────────

async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid  = update.effective_user.id
    lang = get_lang(uid)
    args = context.args or []

    if not args:
        await update.message.reply_text(t(lang, "plan_usage"))
        return

    symbol   = norm_sym(args[0])
    kv       = _parse_kv(args[1:])
    settings = st.get_user_settings(uid)

    deposit = float(kv["deposit"]) if "deposit" in kv else settings.get("deposit")
    if not deposit:
        await update.message.reply_html(t(lang, "no_deposit"))
        return

    risk_pct = float(kv.get("risk",   settings["risk_pct"]))
    lev      = float(kv.get("lev",    settings["lev"]))
    margin   =       kv.get("margin", settings["margin"])

    status = await update.message.reply_text(t(lang, "plan_loading", symbol=symbol))
    try:
        loop     = asyncio.get_event_loop()
        snapshot = await loop.run_in_executor(None, snap.build_snapshot_with_fallback, symbol)
        plan     = core.make_plan(snapshot, deposit=deposit, risk_pct=risk_pct, lev=lev, margin=margin)
        text     = render_telegram_plan(plan, deposit=deposit, risk_pct=risk_pct, lang=lang)
        await status.edit_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await status.edit_text(t(lang, "plan_error", error=e))


# ───────────────────────── /scan ─────────────────────────

async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid  = update.effective_user.id
    lang = get_lang(uid)
    cfg  = load_config()
    s_cfg, t_cfg = cfg["scanner"], cfg["trading"]

    status = await update.message.reply_text(t(lang, "scan_starting", top_n=s_cfg["top_n_symbols"]))
    loop = asyncio.get_event_loop()
    try:
        symbols = await loop.run_in_executor(None, snap.top_symbols_by_volume, s_cfg["top_n_symbols"])
        results = await loop.run_in_executor(
            None,
            lambda: sc.scan_all(
                symbols,
                deposit=t_cfg["deposit"],
                risk_pct=t_cfg["risk_pct"],
                lev=t_cfg["lev"],
                margin=t_cfg["margin"],
                workers=s_cfg["workers"],
            ),
        )

        actionable = [
            r for r in results
            if _conf(r) >= s_cfg["min_confidence"] and r.get("side") != "skip"
        ]

        if not actionable:
            await status.edit_text(t(lang, "scan_none"))
            return

        await status.edit_text(t(lang, "scan_done", count=len(actionable)))
        for plan in actionable[:5]:
            text = render_telegram_plan(plan, deposit=t_cfg["deposit"], risk_pct=t_cfg["risk_pct"], lang=lang)
            await update.message.reply_html(text)
            await asyncio.sleep(0.4)

        if len(actionable) > 5:
            await update.message.reply_text(t(lang, "scan_more", count=len(actionable) - 5))

    except Exception as e:
        await status.edit_text(t(lang, "scan_error", error=e))


# ───────────────────────── /digest ─────────────────────────

async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid  = update.effective_user.id
    lang = get_lang(uid)
    cfg  = load_config()
    status = await update.message.reply_text(t(lang, "digest_preparing"))
    await _run_digest(context.bot, update.effective_chat.id, cfg, lang=lang, status_msg=status)


async def _run_digest(
    bot, chat_id: Any, cfg: Dict, *, lang: str = "en", status_msg=None
) -> None:
    s_cfg, t_cfg = cfg["scanner"], cfg["trading"]
    loop = asyncio.get_event_loop()
    try:
        symbols = await loop.run_in_executor(None, snap.top_symbols_by_volume, s_cfg["top_n_symbols"])
        results = await loop.run_in_executor(
            None,
            lambda: sc.scan_all(
                symbols,
                deposit=t_cfg["deposit"],
                risk_pct=t_cfg["risk_pct"],
                lev=t_cfg["lev"],
                margin=t_cfg["margin"],
                workers=s_cfg["workers"],
            ),
        )

        high    = [r for r in results if _conf(r) >= 0.65 and r.get("side") != "skip"]
        medium  = [r for r in results if 0.50 <= _conf(r) < 0.65 and r.get("side") != "skip"]
        skipped = len(results) - len(high) - len(medium)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        lines = [
            t(lang, "digest_title", time=now_str, total=len(results)),
            "",
        ]

        if high:
            lines.append(t(lang, "digest_high", count=len(high)))
            for r in high[:15]:
                sym  = r.get("symbol", "?")
                side = str((r.get("primary") or {}).get("side", "?")).upper()
                c    = _conf(r)
                em   = "🟩" if side == "LONG" else "🟥"
                lines.append(f"  {em} <code>{sym}</code> {side} conf={c:.2f}")
            lines.append("")

        if medium:
            lines.append(t(lang, "digest_medium", count=len(medium)))
            for r in medium[:10]:
                sym  = r.get("symbol", "?")
                side = str((r.get("primary") or {}).get("side", "?")).upper()
                c    = _conf(r)
                lines.append(f"  • <code>{sym}</code> {side} conf={c:.2f}")
            lines.append("")

        lines.append(t(lang, "digest_skipped", count=skipped))
        summary = "\n".join(lines)

        if status_msg:
            await status_msg.edit_text(summary, parse_mode=ParseMode.HTML)
        else:
            await bot.send_message(chat_id=chat_id, text=summary, parse_mode=ParseMode.HTML)

        for plan in high[:3]:
            full = render_telegram_plan(plan, deposit=t_cfg["deposit"], risk_pct=t_cfg["risk_pct"], lang=lang)
            await bot.send_message(chat_id=chat_id, text=full, parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.4)

    except Exception as e:
        err = t(lang, "digest_error", error=e)
        if status_msg:
            await status_msg.edit_text(err)
        else:
            await bot.send_message(chat_id=chat_id, text=err)


# ───────────────────────── scheduled jobs ─────────────────────────

async def job_auto_scan(context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    s_cfg, t_cfg = cfg["scanner"], cfg["trading"]
    chat_id = cfg["telegram"]["chat_id"]
    lang = "en"  # auto alerts always in English (no user context in scheduled jobs)
    loop = asyncio.get_event_loop()

    logger.info("Auto-scan started")
    try:
        symbols = await loop.run_in_executor(None, snap.top_symbols_by_volume, s_cfg["top_n_symbols"])
        results = await loop.run_in_executor(
            None,
            lambda: sc.scan_all(
                symbols,
                deposit=t_cfg["deposit"],
                risk_pct=t_cfg["risk_pct"],
                lev=t_cfg["lev"],
                margin=t_cfg["margin"],
                workers=s_cfg["workers"],
            ),
        )

        sent = 0
        for plan in results:
            conf = _conf(plan)
            if conf < s_cfg["min_confidence"] or plan.get("side") == "skip":
                continue

            symbol = plan.get("symbol", "")
            side   = (plan.get("primary") or {}).get("side", "skip")

            if not st.should_send_alert(symbol, side, conf):
                continue

            text = render_telegram_plan(plan, deposit=t_cfg["deposit"], risk_pct=t_cfg["risk_pct"], lang=lang)
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
            st.mark_sent(symbol, side, conf)
            sent += 1
            await asyncio.sleep(0.5)

        logger.info("Auto-scan done: %d scanned, %d alerts sent", len(results), sent)

    except Exception as e:
        logger.error("Auto-scan error: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=t(lang, "autoscan_error", error=e),
        )


async def job_daily_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    await _run_digest(context.bot, cfg["telegram"]["chat_id"], cfg, lang="en")


# ───────────────────────── main ─────────────────────────

def main() -> None:
    cfg   = load_config()
    token = cfg["telegram"]["token"]
    s_cfg = cfg["scanner"]

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("plan",     cmd_plan))
    app.add_handler(CommandHandler("scan",     cmd_scan))
    app.add_handler(CommandHandler("digest",   cmd_digest))
    app.add_handler(CommandHandler("set",      cmd_set))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CallbackQueryHandler(handle_lang_callback, pattern=r"^lang_"))

    jq    = app.job_queue
    delay = s_cfg.get("scan_delay_after_4h_close_min", 5)

    for hour in (0, 4, 8, 12, 16, 20):
        jq.run_daily(job_auto_scan, time=dtime(hour, delay, 0, tzinfo=timezone.utc))

    jq.run_daily(
        job_daily_digest,
        time=dtime(s_cfg.get("daily_digest_utc_hour", 8), 0, 0, tzinfo=timezone.utc),
    )

    logger.info("UCB_TRADING_BOT started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
