from __future__ import annotations

import math
from typing import Any, Dict, Optional

def _fmt(x: Any) -> str:
    try:
        x = float(x)
        if not math.isfinite(x):
            return "n/a"
        if abs(x) >= 1000:
            return f"{x:,.0f}".replace(",", " ")
        if abs(x) >= 10:
            return f"{x:.2f}"
        return f"{x:.4f}"
    except Exception:
        return "n/a"

def _tp(scn: Dict[str, Any], i: int) -> Optional[float]:
    tps = scn.get("tps") or []
    if len(tps) > i and isinstance(tps[i], dict):
        return tps[i].get("price")
    return None

def render_telegram_plan(plan: Dict[str, Any], *, deposit: float, risk_pct: float) -> str:
    # SKIP
    if plan.get("side") == "skip":
        sym = plan.get("symbol", "?")
        conf = float(plan.get("confidence", 0.0) or 0.0)
        rs = plan.get("reasons") or []
        why = " · ".join(rs[:10]) if rs else "no_setup"
        cache = " ⚠️<i>cache</i>" if plan.get("used_cache") else ""
        return (
            f"🧠 <b>Контекст</b>\n"
            f"📌 <b><code>{sym}</code> — SKIP</b>{cache}\n"
            f"🧊 Уверенность: <b>{conf:.2f}</b>\n"
            f"🔍 Причины: {why}\n\n"
            f"🚨 <b>Риск-правило</b>\n"
            f"<b>CROSS + плечо — без стопа нельзя.</b> Стоп обязателен."
        )

    sym = plan.get("symbol", "?")
    price = plan.get("price")
    used_cache = bool(plan.get("used_cache"))
    lev = plan.get("lev")
    margin = plan.get("margin")

    tr = plan.get("trend") or {}
    lvl = plan.get("levels") or {}
    sup = lvl.get("support")
    res = lvl.get("resistance")
    mid = lvl.get("mid")

    primary = plan.get("primary") or {}
    side = str(primary.get("side", "skip")).upper()
    conf = float(primary.get("confidence", 0.0) or 0.0)

    entry = primary.get("entry")
    stop = primary.get("stop")
    tp1 = _tp(primary, 0)
    tp2 = _tp(primary, 1)

    qty = primary.get("qty")
    risk_usdt = primary.get("risk_usdt")
    margin_need = primary.get("margin_need")

    reasons = primary.get("reasons") or []
    short_reasons = reasons[-10:] if len(reasons) > 10 else reasons
    why = " · ".join(short_reasons)

    cache_tag = "  ⚠️<i>cache</i>" if used_cache else ""

    side_tag = "🟥" if side == "SHORT" else "🟩" if side == "LONG" else "🧊"

    # “стикеры”-ярлыки в начале ключевых строк
    return (
        f"🧠 <b>Контекст</b>\n"
        f"📌 <b><code>{sym}</code> — план</b>{cache_tag}\n"
        f"💵 Цена: <code>{_fmt(price)}</code>\n\n"

        f"🧷 <b>Профиль</b>\n"
        f"💰 депозит: <b>{_fmt(deposit)}</b>\n"
        f"🎯 риск: <b>{_fmt(deposit*(risk_pct/100.0))}</b> USDT (<b>{risk_pct}%</b>)\n"
        f"🧰 плечо: <b>{_fmt(lev)}x</b> ({margin})\n\n"

        f"🧭 <b>Режим рынка</b>\n"
        f"• trend 1D: <b>{tr.get('1d','—')}</b> | 4H: <b>{tr.get('4h','—')}</b>\n"
        f"• структура 4H: <b>{tr.get('struct4h','—')}</b> | BOS/CHOCH: <b>{tr.get('bos','—')}</b>\n"
        f"• regime: <b>{tr.get('regime','—')}</b> | midrange: <b>{_fmt(mid) if mid is not None else '—'}</b>\n\n"

        f"{side_tag} <b>Сценарий</b>\n"
        f"✅ <b>{side}</b> (conf <b>{conf:.2f}</b>)\n"
        f"🎯 entry: <code>{_fmt(entry)}</code>\n"
        f"🛑 stop: <code>{_fmt(stop)}</code>\n"
        f"🥅 tp1: <code>{_fmt(tp1)}</code>\n"
        f"🥅 tp2: <code>{_fmt(tp2)}</code>\n\n"

        f"📦 <b>Размер</b>\n"
        f"• qty: <code>{_fmt(qty)}</code>\n"
        f"• risk: <b>{_fmt(risk_usdt)}</b> USDT | margin_need: <code>{_fmt(margin_need)}</code>\n\n"

        f"🧱 <b>Уровни</b>\n"
        f"🟩 support: <code>{_fmt(sup)}</code>\n"
        f"🟥 resistance: <code>{_fmt(res)}</code>\n\n"

        f"🔍 <b>Почему</b>\n"
        f"{why}\n\n"

        f"🚨 <b>Риск-правило</b>\n"
        f"<b>CROSS + плечо — без стопа нельзя.</b> Стоп обязателен."
    )
