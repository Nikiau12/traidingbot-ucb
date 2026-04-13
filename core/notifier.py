from aiogram import Bot
from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from core.smart_engine import Regime, MTFVerdict
import asyncio

class Notifier:
    TRANSLATIONS = {
        "bullish": "🟢 Бычий (Восходящий)",
        "bearish": "🔴 Медвежий (Нисходящий)",
        "neutral": "⚪️ Нейтральный (Флэт / Боковик)",
        
        "bullish_continuation": "📈 Продолжение роста",
        "bearish_continuation": "📉 Продолжение падения",
        "bullish_reversal": "🚀 Бычий разворот (Ловля дна)",
        "bearish_reversal": "🩸 Медвежий разворот (Тест хая)",
        "counter_trend_bounce": "⚠️ Опасный контр-трендовый отскок",
        "no_trade": "🚫 Вне рынка",
        
        "strong": "🟢 Сильное",
        "moderate": "🟡 Умеренное",
        "weak": "🔴 Слабое",
        "conflicting": "⚠️ Противоречивое",
        "aligned": "✅ Сформирован",
        "pending": "⏳ В процессе формирования",
        "noisy": "🌪 Рыночный шум",
        
        "countertrend_to_macro": "Сделка против макро-тренда (Высокий Риск)",
        "countertrend_context": "Локальное движение цены не поддерживает сетап",
        "neutral or mixed macro context": "Старшие ТФ смешанные или в боковике (вероятен распил)",
        "setup conflicts with active bias": "Сетап заходит против сильного дневного тренда",
        "weak_confirmation": "Слабое структурное подтверждение",
        "noisy structure": "Рваная/шумная локальная структура цены",
        "choppy range environment": "Опасная торговля внутри узкого диапазона"
    }

    def __init__(self, bot: Bot = None, active_users: set = None):
        self.bot = bot
        self.active_users = active_users if active_users is not None else set()
        if TELEGRAM_CHAT_ID: # Fallback just in case
            self.active_users.add(str(TELEGRAM_CHAT_ID))
            
    def _t(self, key: str) -> str:
        if not key:
            return ""
        k = str(key).lower()
        return self.TRANSLATIONS.get(k, key.replace('_', ' ').capitalize())

    async def send_message(self, text: str):
        if not self.bot:
            print(f"[Notifier - console only] {text}")
            return

        if not self.active_users:
            print(f"[Notifier - no active users] {text}")
            return

        for chat_id in self.active_users:
            try:
                await self.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
            except Exception as e:
                print(f"Failed to send telegram message to {chat_id}: {e}")

    async def close(self):
        pass # The bot session will be closed by the main aiogram loop

    def format_spike_alert(self, symbol, timeframe, spike_data):
        direction = "🟢 LONG (Памп)" if spike_data['direction'] == 'up' else "🔴 SHORT (Дамп)"
        msg = (
            f"🚀 <b>ВСПЛЕСК АКТИВНОСТИ: {symbol}</b>\n"
            f"Таймфрейм: {timeframe}\n"
            f"Направление: {direction}\n"
            f"Цена ДО: {spike_data['start_price']:.5f}\n"
            f"Цена СЕЙЧАС: {spike_data['current_price']:.5f}\n"
            f"Изменение цены: {spike_data['pct_change']:.2f}%\n"
            f"Тип всплеска: {spike_data['type']}\n"
            f"Объем: x{spike_data['volume_ratio']:.1f} от среднего"
        )
        return msg

    def format_smc_setup(self, symbol, timeframe, setup_data, context_score=None, verdict: MTFVerdict=None):
        direction_icon = "🟢 LONG" if setup_data['type'] == 'LONG' else "🔴 SHORT"
        msg = (
            f"🎯 <b>SMC СЕТАП: {symbol}</b>\n"
            f"📈 Направление: {direction_icon}\n"
            f"⏱ Таймфрейм: {timeframe}\n"
            f"🧠 Паттерн: {setup_data['reason']}\n\n"
        )
        
        if context_score:
            msg += (
                f"🧠 <b>Умный Анализ (V9): {context_score.confidence}/100</b>\n"
                f"📊 Режим: {context_score.regime.value.upper()} | Фаза: {context_score.phase.value.upper()}\n"
            )
            for reason in context_score.reasons:
                msg += f"  • {reason}\n"
            msg += "\n"

        if verdict:
            msg += (
                f"🌐 <b>MTF Fusion (V11): {verdict.confidence}/100</b>\n"
                f"🧭 Тип Сетапа: {self._t(verdict.setup_type.name)}\n"
            )
            if verdict.risk_flags:
                msg += "⚠️ <b>Факторы Риска:</b>\n"
                for risk in verdict.risk_flags:
                    msg += f"  • {self._t(risk)}\n"
            else:
                msg += "✅ <b>Факторы Риска: Отсутствуют (Рынок чист)</b>\n"
            msg += "\n"

        msg += (
            f"🎯 <b>Точка входа (Entry)</b>: {setup_data['entry']:.5f}\n"
            f"🛑 <b>Стоп-Лосс (SL)</b>: {setup_data['stop_loss']:.5f}\n"
            f"✅ <b>Тейк-Профит (TP)</b>: {setup_data['take_profit']:.5f}\n"
            f"⚖️ Risk:Reward: 1:{setup_data['rr']}"
        )
        return msg

    def format_full_analysis(self, symbol, analyses, verdict: MTFVerdict):
        msg_parts = [f"📊 <b>ПОЛНЫЙ ТЕХНИЧЕСКИЙ АНАЛИЗ (MTF Fusion V11): {symbol}</b>\n"]
        
        # 1. MTF Verdict Section
        msg_parts.append(f"🌐 <b>Макро Тренд (1W)</b>: {self._t(verdict.macro_bias.name)}")
        msg_parts.append(f"📅 <b>Активный Тренд (1D)</b>: {self._t(verdict.active_bias.name)}")
        msg_parts.append(f"🧭 <b>Тип Сетапа (4H)</b>: {self._t(verdict.setup_type.name)}")
        msg_parts.append(f"⚖️ <b>Подтверждение (1H)</b>: {self._t(verdict.confirmation_state.name)}")
        msg_parts.append(f"⚡️ <b>Триггер (15m)</b>: {self._t(verdict.trigger_state.name)}")
        msg_parts.append(f"🧠 <b>Уверенность MTF</b>: {verdict.confidence}/100\n")
        
        if verdict.risk_flags:
            msg_parts.append("⚠️ <b>Факторы Риска:</b>")
            for risk in verdict.risk_flags:
                msg_parts.append(f"  • {self._t(risk)}")
            msg_parts.append("")
        else:
            msg_parts.append("✅ <b>Риски минимальны (Синхронизация ТФ)</b>\n")
            
        # Nearest POI (FVG / OB) on 1h
        tf_1h = analyses.get("1h", {})
        msg_parts.append("🔎 <b>Ближайшие зоны интереса (1h):</b>")
        if 'fvg' in tf_1h and tf_1h['fvg']:
            last_fvg = tf_1h['fvg'][-1]
            fvg_type = "Бычий" if last_fvg['FVG'] == 1 else "Медвежий"
            top = last_fvg.get('Top', 0)
            bottom = last_fvg.get('Bottom', 0)
            msg_parts.append(f"• Свежий {fvg_type} имбаланс (FVG): {bottom:.4f} - {top:.4f}")
        else:
            msg_parts.append("• Явных имбалансов поблизости нет.")
            
        if 'order_blocks' in tf_1h and tf_1h['order_blocks']:
            last_ob = tf_1h['order_blocks'][-1]
            ob_type = "Бычий" if last_ob['OB'] == 1 else "Медвежий"
            top = last_ob.get('Top', 0)
            bottom = last_ob.get('Bottom', 0)
            msg_parts.append(f"• Актуальный {ob_type} Ордерблок (OB): {bottom:.4f} - {top:.4f}")
            
        # Liquidity on 15m
        tf_15m = analyses.get("15m", {})
        if 'liquidity' in tf_15m and tf_15m['liquidity']:
            msg_parts.append("\n💧 <b>Зоны ликвидности (15m):</b>")
            for liq in tf_15m['liquidity'][-2:]:
                liq_type = "Buy-side (Сверху)" if liq['Liquidity'] == 1 else "Sell-side (Снизу)"
                lvl = liq.get('Level', 0)
                msg_parts.append(f"• {liq_type} скопление стопов на уровне: {lvl:.4f}")
        
        # AI Verdict Context Engine Logic
        msg_parts.append("\n💡 <b>Мнение Бота:</b>")
        
        if verdict.confidence >= 70:
            msg_parts.append("Тренды синхронизированы. Рынок имеет четкое направленное движение. Идеальное время для торговли в направлении макро-тренда от ближайших зон.")
        elif verdict.confidence >= 50:
            msg_parts.append("Есть незначительные рассинхроны между таймфреймами, но общая картина понятна. Можно торговать со сниженным риском.")
        elif verdict.confidence >= 35:
            msg_parts.append("Смешанная картина. Присутствуют контр-трендовые отскоки или слабая структура. Будьте осторожны.")
        else:
            msg_parts.append("На рынке полный хаос и конфликты таймфреймов. Настоятельно рекомендуется воздержаться от сделок до прояснения ситуации.")

        return "\n".join(msg_parts)
