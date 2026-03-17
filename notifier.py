from aiogram import Bot
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import asyncio

class Notifier:
    def __init__(self, bot: Bot = None, active_users: set = None):
        self.bot = bot
        self.active_users = active_users if active_users is not None else set()
        if TELEGRAM_CHAT_ID: # Fallback just in case
            self.active_users.add(str(TELEGRAM_CHAT_ID))

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
            f"Изменение цены: {spike_data['pct_change']:.2f}%\n"
            f"Тип всплеска: {spike_data['type']}\n"
            f"Объем: x{spike_data['volume_ratio']:.1f} от среднего"
        )
        return msg

    def format_smc_setup(self, symbol, timeframe, setup_data):
        direction_icon = "🟢 LONG" if setup_data['type'] == 'LONG' else "🔴 SHORT"
        msg = (
            f"🎯 <b>SMC СЕТАП: {symbol}</b>\n"
            f"📈 Направление: {direction_icon}\n"
            f"⏱ Таймфрейм: {timeframe}\n"
            f"🧠 Паттерн: {setup_data['reason']}\n\n"
            f"🎯 <b>Точка входа (Entry)</b>: {setup_data['entry']:.5f}\n"
            f"🛑 <b>Стоп-Лосс (SL)</b>: {setup_data['stop_loss']:.5f}\n"
            f"✅ <b>Тейк-Профит (TP)</b>: {setup_data['take_profit']:.5f}\n"
            f"⚖️ Risk:Reward: 1:{setup_data['rr']}"
        )
        return msg

    def format_full_analysis(self, symbol, analyses):
        msg_parts = [f"📊 <b>ПОЛНЫЙ ТЕХНИЧЕСКИЙ АНАЛИЗ SMC: {symbol}</b>\n"]
        
        # Determine all-time trend from 1w
        tf_1w = analyses.get("1w", {})
        alltime_trend = "Пока неизвестно (мало исторических данных)"
        if 'structure' in tf_1w and tf_1w['structure']:
            last_1w_struct = tf_1w['structure'][-1]
            if last_1w_struct['BOS'] == 1 or last_1w_struct['CHOCH'] == 1:
                alltime_trend = "🟢 Глобальный Бычий (Price Discovery / Рост)"
            elif last_1w_struct['BOS'] == -1 or last_1w_struct['CHOCH'] == -1:
                alltime_trend = "🔴 Глобальный Медвежий (Затяжное падение)"
        
        msg_parts.append(f"<b>Вся История (1W)</b>: {alltime_trend}")
        
        # Determine overall trend from 4h
        tf_4h = analyses.get("4h", {})
        macro_trend = "⚪️ Нейтральный (в боковике)"
        if 'structure' in tf_4h and tf_4h['structure']:
            last_4h_struct = tf_4h['structure'][-1]
            if last_4h_struct['BOS'] == 1 or last_4h_struct['CHOCH'] == 1:
                macro_trend = "🟢 Восходящий (Бычий)"
            elif last_4h_struct['BOS'] == -1 or last_4h_struct['CHOCH'] == -1:
                macro_trend = "🔴 Нисходящий (Медвежий)"
        
        msg_parts.append(f"<b>Макро Тренд (4h)</b>: {macro_trend}")
        
        # Look at local structure 15m
        tf_15m = analyses.get("15m", {})
        micro_trend = "⚪️ Нейтральный"
        if 'structure' in tf_15m and tf_15m['structure']:
            last_15m_struct = tf_15m['structure'][-1]
            if last_15m_struct['BOS'] == 1 or last_15m_struct['CHOCH'] == 1:
                micro_trend = "🟢 Памп / Локально растем"
            elif last_15m_struct['BOS'] == -1 or last_15m_struct['CHOCH'] == -1:
                micro_trend = "🔴 Дамп / Локально падаем"
                
        msg_parts.append(f"<b>Микро Тренд (15m)</b>: {micro_trend}\n")
        
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
        if 'liquidity' in tf_15m and tf_15m['liquidity']:
            msg_parts.append("\n💧 <b>Зоны ликвидности (15m):</b>")
            for liq in tf_15m['liquidity'][-2:]:
                liq_type = "Buy-side (Сверху)" if liq['Liquidity'] == 1 else "Sell-side (Снизу)"
                lvl = liq.get('Level', 0)
                msg_parts.append(f"• {liq_type} скопление стопов на уровне: {lvl:.4f}")
        
        # AI Verdict
        msg_parts.append("\n💡 <b>Мнение Бота:</b>")
        if macro_trend == "🟢 Восходящий (Бычий)" and micro_trend == "🟢 Памп / Локально растем":
            msg_parts.append("Тренды синхронизированы в лонг. Инструмент очень сильный. Рекомендуется искать точки входа в покупку (LONG) от ближайших бычьих ордерблоков или перекрытий FVG на младших таймфреймах.")
        elif macro_trend == "🔴 Нисходящий (Медвежий)" and micro_trend == "🔴 Дамп / Локально падаем":
            msg_parts.append("Рынок тотально падает. Безопаснее всего искать шорт-позиции (SHORT) после небольших откатов в медвежьи имбалансы (FVG).")
        elif macro_trend != micro_trend and (macro_trend != "⚪️ Нейтральный (в боковике)"):
            msg_parts.append("Локальный тренд прямо сейчас идет против глобального. Вероятно, происходит снятие ликвидности или глубокая коррекция. Рекомендуется воздержаться от сделок до тех пор, пока на 15m не произойдет слом (CHoCH) обратно по глобальному тренду.")
        else:
            msg_parts.append("На рынке смешанная картина (боковик или консолидация). Слишком мало данных для уверенного сетапа. Торговля не рекомендуется до выхода из торгового диапазона.")
            
        # Explicit Scenarios
        msg_parts.append("\n📝 <b>КОНКРЕТНЫЕ СЦЕНАРИИ ТОРГОВЛИ:</b>")
        
        # Long Scenario logic based on 1h POIs
        long_poi = "сильную зону поддержки"
        if 'fvg' in tf_1h and any(f['FVG'] == 1 for f in tf_1h['fvg']):
            f = [f for f in tf_1h['fvg'] if f['FVG'] == 1][-1]
            long_poi = f"перекрытие Бычьего имбаланса ({f.get('Bottom', 0):.4f} - {f.get('Top', 0):.4f})"
        elif 'order_blocks' in tf_1h and any(ob['OB'] == 1 for ob in tf_1h['order_blocks']):
            ob = [ob for ob in tf_1h['order_blocks'] if ob['OB'] == 1][-1]
            long_poi = f"тест Бычьего Ордерблока ({ob.get('Bottom', 0):.4f} - {ob.get('Top', 0):.4f})"
            
        msg_parts.append(f"📈 <b>Вариант ЛОНГа:</b> Дождаться спуска в {long_poi}. Если на 15-минутном графике там происходит локальный слом структуры вверх (CHoCH), открываем LONG со стопом за последний минимум. Тейк-профит — на обновлении ближайшего максимума.")

        # Short Scenario logic
        short_poi = "зону сильного сопротивления"
        if 'fvg' in tf_1h and any(f['FVG'] == -1 for f in tf_1h['fvg']):
            f = [f for f in tf_1h['fvg'] if f['FVG'] == -1][-1]
            short_poi = f"Медвежий имбаланс (FVG) между {f.get('Bottom', 0):.4f} и {f.get('Top', 0):.4f}"
        elif 'order_blocks' in tf_1h and any(ob['OB'] == -1 for ob in tf_1h['order_blocks']):
            ob = [ob for ob in tf_1h['order_blocks'] if ob['OB'] == -1][-1]
            short_poi = f"Медвежий Ордерблок (OB) на отметке {ob.get('Bottom', 0):.4f} - {ob.get('Top', 0):.4f}"
            
        msg_parts.append(f"📉 <b>Вариант ШОРТа:</b> Если цена подскакивает в {short_poi}, и мы видим резкий слом (CHoCH) медвежьего характера на 15m, тогда открываем SHORT со стопом за этот новый максимум. Иначе — риск пробития зоны.")

        return "\n".join(msg_parts)
