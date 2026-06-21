#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, time as dtime, timezone
from typing import Any, Dict

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

import mexc_snapshot as snap
import trade_plan as core
import scanner as sc
import state as st
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


# ───────────────────────── команды ─────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    t, s = cfg["trading"], cfg["scanner"]
    text = (
        "🤖 <b>OpenClaw Trading Bot</b>\n\n"
        "<b>Команды:</b>\n"
        "/plan BTC_USDT — план по монете\n"
        "/plan BTC_USDT lev=10 risk=2 — с кастомными параметрами\n"
        "/scan — ручной запуск скана топ-монет\n"
        "/digest — дайджест прямо сейчас\n"
        "/help — эта справка\n\n"
        f"⚙️ <b>Дефолты:</b> deposit={t['deposit']} | risk={t['risk_pct']}% | lev={t['lev']}x\n"
        f"min_conf={s['min_confidence']} | top_n={s['top_n_symbols']}\n\n"
        "📅 <b>Автосканирование:</b> через 5 мин после закрытия каждой 4h свечи\n"
        f"📊 <b>Дайджест:</b> ежедневно в {s['daily_digest_utc_hour']:02d}:00 UTC"
    )
    await update.message.reply_html(text)


async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Использование: /plan BTC_USDT [lev=20 risk=1 deposit=3000]"
        )
        return

    symbol = norm_sym(args[0])
    cfg = load_config()
    kv = _parse_kv(args[1:])
    t = cfg["trading"]

    deposit  = float(kv.get("deposit", t["deposit"]))
    risk_pct = float(kv.get("risk",    t["risk_pct"]))
    lev      = float(kv.get("lev",     t["lev"]))
    margin   =       kv.get("margin",  t["margin"])

    status = await update.message.reply_text(f"⏳ Загружаю {symbol}...")
    try:
        loop = asyncio.get_event_loop()
        snapshot = await loop.run_in_executor(None, snap.build_snapshot_with_fallback, symbol)
        plan = core.make_plan(snapshot, deposit=deposit, risk_pct=risk_pct, lev=lev, margin=margin)
        text = render_telegram_plan(plan, deposit=deposit, risk_pct=risk_pct)
        await status.edit_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await status.edit_text(f"❌ Ошибка: {e}")


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    s_cfg, t_cfg = cfg["scanner"], cfg["trading"]

    status = await update.message.reply_text(
        f"🔍 Сканирую топ-{s_cfg['top_n_symbols']} монет (~2–4 мин)..."
    )
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
            await status.edit_text("🧊 Нет сетапов выше порога уверенности")
            return

        await status.edit_text(f"✅ Найдено {len(actionable)} сетап(ов). Топ-5:")
        for plan in actionable[:5]:
            text = render_telegram_plan(plan, deposit=t_cfg["deposit"], risk_pct=t_cfg["risk_pct"])
            await update.message.reply_html(text)
            await asyncio.sleep(0.4)

        if len(actionable) > 5:
            await update.message.reply_text(
                f"...и ещё {len(actionable) - 5}. Используй /digest для полного обзора."
            )
    except Exception as e:
        await status.edit_text(f"❌ Ошибка сканирования: {e}")


async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    status = await update.message.reply_text("📊 Готовлю дайджест...")
    await _run_digest(context.bot, update.effective_chat.id, cfg, status_msg=status)


# ───────────────────────── дайджест ─────────────────────────

async def _run_digest(
    bot, chat_id: Any, cfg: Dict, *, status_msg=None
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

        high   = [r for r in results if _conf(r) >= 0.65 and r.get("side") != "skip"]
        medium = [r for r in results if 0.50 <= _conf(r) < 0.65 and r.get("side") != "skip"]
        skipped = len(results) - len(high) - len(medium)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        lines = [
            f"📊 <b>Дайджест {now_str} UTC</b>",
            f"Проверено: <b>{len(results)}</b> монет",
            "",
        ]

        if high:
            lines.append(f"🟢 <b>Высокая уверенность ≥0.65 — {len(high)} шт.</b>")
            for r in high[:15]:
                sym  = r.get("symbol", "?")
                side = str((r.get("primary") or {}).get("side", "?")).upper()
                c    = _conf(r)
                em   = "🟩" if side == "LONG" else "🟥"
                lines.append(f"  {em} <code>{sym}</code> {side} conf={c:.2f}")
            lines.append("")

        if medium:
            lines.append(f"🟡 <b>Средняя уверенность 0.50–0.65 — {len(medium)} шт.</b>")
            for r in medium[:10]:
                sym  = r.get("symbol", "?")
                side = str((r.get("primary") or {}).get("side", "?")).upper()
                c    = _conf(r)
                lines.append(f"  • <code>{sym}</code> {side} conf={c:.2f}")
            lines.append("")

        lines.append(f"🧊 Нет сетапа: <b>{skipped}</b> монет")
        summary = "\n".join(lines)

        if status_msg:
            await status_msg.edit_text(summary, parse_mode=ParseMode.HTML)
        else:
            await bot.send_message(chat_id=chat_id, text=summary, parse_mode=ParseMode.HTML)

        # Полные планы для топ-3 высококонфидентных
        for plan in high[:3]:
            full = render_telegram_plan(plan, deposit=t_cfg["deposit"], risk_pct=t_cfg["risk_pct"])
            await bot.send_message(chat_id=chat_id, text=full, parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.4)

    except Exception as e:
        err = f"❌ Ошибка дайджеста: {e}"
        if status_msg:
            await status_msg.edit_text(err)
        else:
            await bot.send_message(chat_id=chat_id, text=err)


# ───────────────────────── фоновые джобы ─────────────────────────

async def job_auto_scan(context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    s_cfg, t_cfg = cfg["scanner"], cfg["trading"]
    chat_id = cfg["telegram"]["chat_id"]
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

            text = render_telegram_plan(plan, deposit=t_cfg["deposit"], risk_pct=t_cfg["risk_pct"])
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
            st.mark_sent(symbol, side, conf)
            sent += 1
            await asyncio.sleep(0.5)

        logger.info("Auto-scan done: %d scanned, %d alerts sent", len(results), sent)

    except Exception as e:
        logger.error("Auto-scan error: %s", e)
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Ошибка автосканирования: {e}")


async def job_daily_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    await _run_digest(context.bot, cfg["telegram"]["chat_id"], cfg)


# ───────────────────────── main ─────────────────────────

def main() -> None:
    cfg = load_config()
    token = cfg["telegram"]["token"]
    s_cfg = cfg["scanner"]

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start",  cmd_help))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("plan",   cmd_plan))
    app.add_handler(CommandHandler("scan",   cmd_scan))
    app.add_handler(CommandHandler("digest", cmd_digest))

    jq = app.job_queue
    delay = s_cfg.get("scan_delay_after_4h_close_min", 5)

    # Автосканирование через N минут после закрытия 4h свечи (00, 04, 08, 12, 16, 20 UTC)
    for hour in (0, 4, 8, 12, 16, 20):
        jq.run_daily(job_auto_scan, time=dtime(hour, delay, 0, tzinfo=timezone.utc))

    # Ежедневный дайджест
    jq.run_daily(
        job_daily_digest,
        time=dtime(s_cfg.get("daily_digest_utc_hour", 8), 0, 0, tzinfo=timezone.utc),
    )

    logger.info("Bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
