from aiogram import Bot
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import asyncio

class Notifier:
    def __init__(self):
        self.bot = None
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            self.bot = Bot(token=TELEGRAM_BOT_TOKEN)

    async def send_message(self, text: str):
        if not self.bot:
            print(f"[Notifier - console only] {text}")
            return

        try:
            await self.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="HTML")
        except Exception as e:
            print(f"Failed to send telegram message: {e}")

    async def close(self):
        if self.bot:
            await self.bot.session.close()

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
