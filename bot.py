import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from exchange_client import ExchangeClient
from smc_analyzer import SMCAnalyzer
from spike_scanner import SpikeScanner
from notifier import Notifier
from config import TELEGRAM_BOT_TOKEN, TIMEFRAMES, TOP_COINS_LIMIT, CORE_PAIRS

bot_instance = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

exchange = ExchangeClient()
smc_analyzer = SMCAnalyzer()
spike_scanner = SpikeScanner()
notifier = Notifier(bot_instance)

@router.message(Command("setup"))
async def cmd_setup(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("ℹ️ Использование: <code>/setup BTC</code> (или другой тикер)", parse_mode="HTML")
        return
    
    coin = parts[1].upper()
    symbol = f"{coin}/USDT" if "USDT" not in coin else coin
    
    await message.reply(f"🔍 Анализирую {symbol} по стратегии SMC...")
    
    try:
        found = False
        for tf in ["15m", "1h", "4h"]:
            df = await exchange.fetch_ohlcv(symbol, tf)
            if df.empty:
                continue
            smc_results = smc_analyzer.analyze_tf(df)
            setup = smc_analyzer.find_setup(smc_results)
            if setup:
                msg = notifier.format_smc_setup(symbol, tf, setup)
                await message.reply(msg, parse_mode="HTML")
                found = True
        
        if not found:
            await message.reply(f"🤷‍♂️ В данный момент нет свежих сетапов SMC по {symbol} на таймфреймах 15m, 1h, 4h.")
            
    except Exception as e:
        await message.reply(f"❌ Ошибка при анализе: {e}")

@router.message(Command("spikes"))
async def cmd_spikes(message: types.Message):
    await message.reply("🚀 Запускаю ручной сканер всплесков/пампов по Топ-250 монетам. Это займет пару минут...")
    
    try:
        symbols = await exchange.get_top_pairs()
        spikes_found = []
        
        for symbol in symbols:
            df = await exchange.fetch_ohlcv(symbol, "15m")
            if df.empty:
                continue
                
            spike = spike_scanner.scan(df)
            if spike:
                spikes_found.append((symbol, spike))
            await asyncio.sleep(0.05)
            
        if not spikes_found:
            await message.reply("🤷‍♂️ Аномальных всплесков объемов прямо сейчас не замечено.")
            return
            
        # Отправляем топ 15 всплесков
        for sym, spk in spikes_found[:15]:
            msg = notifier.format_spike_alert(sym, "15m", spk)
            await message.reply(msg, parse_mode="HTML")
            await asyncio.sleep(0.1)
            
    except Exception as e:
        await message.reply(f"❌ Ошибка при сканировании: {e}")

async def market_scanner_loop():
    while True:
        try:
            symbols = await exchange.get_top_pairs()
            print(f"Фоновый скан: {len(symbols)} пар...")

            for i, symbol in enumerate(symbols):
                is_smc_eligible = (i < TOP_COINS_LIMIT) or (symbol in CORE_PAIRS)

                for tf in ["15m", "1h", "4h"]:
                    df = await exchange.fetch_ohlcv(symbol, tf)
                    if df.empty:
                        continue
                    
                    # ----- Мониторинг всплесков -----
                    spike = spike_scanner.scan(df)
                    if spike:
                        msg = notifier.format_spike_alert(symbol, tf, spike)
                        await notifier.send_message(msg)
                        await asyncio.sleep(0.1)

                    # ----- Мониторинг SMC паттернов -----
                    if is_smc_eligible:
                        smc_results = smc_analyzer.analyze_tf(df)
                        setup = smc_analyzer.find_setup(smc_results)
                        
                        if setup:
                            msg = notifier.format_smc_setup(symbol, tf, setup)
                            await notifier.send_message(msg)
                            await asyncio.sleep(0.1)

                await asyncio.sleep(0.5)

            print("Фоновый цикл завершен. Ожидание 60 секунд...")
            await asyncio.sleep(60)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Ошибка в главном цикле: {e}")
            await asyncio.sleep(10)

async def main():
    print("Инициализация SMC Трейдинг Бота с интерактивным меню...")
    await notifier.send_message("✅ <b>Трейдинг Бот запущен (V4)</b>\nСлежу за рынком... \n\nДоступные команды:\n/setup <code>BTC</code> — анализ по SMC\n/spikes — сканер пампов")
    
    dp.include_router(router)
    
    # Запускаем фоновый сканнер рынка
    scanner_task = asyncio.create_task(market_scanner_loop())
    
    try:
        # Запускаем поллинг телеграм-бота (для команд)
        await dp.start_polling(bot_instance)
    finally:
        scanner_task.cancel()
        await exchange.close()
        await notifier.close()

if __name__ == "__main__":
    asyncio.run(main())
