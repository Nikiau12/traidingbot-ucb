import asyncio
import json
import os
import time
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from exchange_client import ExchangeClient
from smc_analyzer import SMCAnalyzer
from spike_scanner import SpikeScanner
from notifier import Notifier
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TIMEFRAMES, TOP_COINS_LIMIT, CORE_PAIRS

bot_instance = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return set(json.load(f))
        except:
            pass
    # Если файла нет, инициализируем владельцем из .env
    default_users = set()
    if TELEGRAM_CHAT_ID:
        default_users.add(str(TELEGRAM_CHAT_ID))
    return default_users

def save_user(chat_id: str):
    users = load_users()
    if chat_id not in users:
        users.add(chat_id)
        with open(USERS_FILE, 'w') as f:
            json.dump(list(users), f)
        return True
    return False

active_users = load_users()

exchange = ExchangeClient()
smc_analyzer = SMCAnalyzer()
spike_scanner = SpikeScanner()
# Передаем set пользователей в Notifier
notifier = Notifier(bot_instance, active_users)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    chat_id = str(message.chat.id)
    is_new = save_user(chat_id)
    if is_new:
        notifier.active_users.add(chat_id)
        print(f"Новый пользователь зарегистрирован: {chat_id}")
    
    welcome_text = (
        "👋 <b>Привет! Я твой личный Smart Money Трейдинг Бот.</b>\n\n"
        "Я 24/7 сканирую крипторынок (250+ монет) и помогаю находить выгодные сделки.\n\n"
        "🤖 <b>Что я умею делать автоматически:</b>\n"
        "• Слежу за рынком и сам присылаю в этот чат сигналы, если где-то есть идеальный <i>SMC Сетап</i> (Точка входа, Стоп-лосс и Тейк-профит).\n"
        "• Присылаю алерты, если на каком-то щиткоине прямо сейчас происходит жесткий <i>Памп</i> или <i>Дамп</i> (всплеск объемов).\n\n"
        "💬 <b>Как со мной общаться (Прямо в чате):</b>\n"
        "• Напиши <code>Анализ монеты SOL</code> — и я выдам тебе глубокий независимый анализ трендов на 15m, 1h и 4h.\n"
        "• Напиши <code>Дай сетап по BTC</code> (или ETH, DOGE и т.д.) — и я мгновенно рассчитаю для тебя сделку.\n"
        "• Напиши <code>Сканер всплесков</code> — и я за пару секунд прочешу 250 монет в поисках аномалий на рынке.\n\n"
        "⌨️ <b>Быстрые команды:</b>\n"
        "🔸 /setup <code>[тикер]</code> — Быстрый поиск сетапа (например: /setup ETH)\n"
        "🔸 /spikes — Запустить ручной сканер пампов\n\n"
        "Удачной торговли! 📈"
    )
    await message.reply(welcome_text, parse_mode="HTML")
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
    await handle_setup_request(message, coin)

@router.message(Command("spikes"))
async def cmd_spikes(message: types.Message):
    await handle_spikes_request(message)

async def handle_full_analysis_request(message: types.Message, coin: str):
    symbol = await exchange.validate_symbol(coin)
    if not symbol:
        await message.reply(f"❌ Монета {coin} не найдена на бирже MEXC. Проверьте тикер.")
        return

    await message.reply(f"🤖 Собираю данные для глубокого анализа {symbol} (15m, 1h, 4h + Вся История 1W)...")
    try:
        analyses = {}
        # Get standard timeframes
        for tf in ["15m", "1h", "4h"]:
            df = await exchange.fetch_ohlcv(symbol, tf)
            if df.empty:
                continue
            analyses[tf] = smc_analyzer.analyze_tf(df)
            await asyncio.sleep(0.1)
            
        # Get historical All-Time timeframe (1W)
        df_1w = await exchange.fetch_historical_data(symbol)
        if not df_1w.empty:
            analyses["1w"] = smc_analyzer.analyze_tf(df_1w)
        
        if not analyses:
            await message.reply("🤷‍♂️ Не удалось получить графики для анализа с MEXC.")
            return
            
        msg = notifier.format_full_analysis(symbol, analyses)
        await message.reply(msg, parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Ошибка при глубоком анализе: {e}")

async def handle_setup_request(message: types.Message, coin: str):
    symbol = await exchange.validate_symbol(coin)
    if not symbol:
        await message.reply(f"❌ Сетап: Монета {coin} не найдена на MEXC.")
        return
        
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

async def handle_spikes_request(message: types.Message):
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
            
        for sym, spk in spikes_found[:15]:
            msg = notifier.format_spike_alert(sym, "15m", spk)
            await message.reply(msg, parse_mode="HTML")
            await asyncio.sleep(0.1)
            
    except Exception as e:
        await message.reply(f"❌ Ошибка при сканировании: {e}")

from aiogram import F

@router.message(F.text)
async def handle_natural_language(message: types.Message):
    text = message.text.lower()
    
    # NLP Триггеры для сетапов
    if "дай сетап по" in text:
        # Пытаемся вычленить монету, например "дай сетап по биткоину" -> "биткоин" -> "BTC"
        words = text.split("дай сетап по")
        if len(words) > 1:
            raw_coin = words[1].strip()
            # Простейший маппинг русских названий в тикеры
            coin_map = {
                "биткойн": "BTC", "биткоину": "BTC", "битку": "BTC", "btc": "BTC",
                "эфиру": "ETH", "эфириуму": "ETH", "eth": "ETH", 
                "солане": "SOL", "солану": "SOL", "solana": "SOL", "sol": "SOL",
                "доги": "DOGE", "doge": "DOGE",
                "тон": "TON", "тону": "TON"
            }
            coin_ticker = coin_map.get(raw_coin, raw_coin.upper()) # Если нет в словаре, пробуем как есть
            await handle_setup_request(message, coin_ticker)
            return

    # NLP Триггеры для полного анализа ("анализ монеты")
    if "анализ монеты" in text:
        words = text.split("анализ монеты")
        if len(words) > 1:
            raw_coin = words[1].strip()
            coin_map = {
                "биткойн": "BTC", "биткоину": "BTC", "битку": "BTC", "btc": "BTC", "биткоин": "BTC",
                "эфиру": "ETH", "эфириуму": "ETH", "eth": "ETH", "эфир": "ETH",
                "солане": "SOL", "солану": "SOL", "solana": "SOL", "sol": "SOL",
                "доги": "DOGE", "doge": "DOGE",
                "тон": "TON", "тону": "TON"
            }
            coin_ticker = coin_map.get(raw_coin, raw_coin.upper())
            await handle_full_analysis_request(message, coin_ticker)
            return

    # NLP Триггеры для сканера
    if "сканер всплесков" in text or "памп" in text or "щиткоин" in text:
        await handle_spikes_request(message)
        return


async def market_scanner_loop():
    # Анти-спам кэши: отслеживаем время (timestamp) последнего отправленного алерта
    last_spike_alert = {}  # format: {"BTC/USDT_15m": 1690000000.0}
    last_setup_alert = {}  # format: {"BTC/USDT_1h_LONG": 1690000000.0}
    
    # Кулдауны (в секундах)
    SPIKE_COOLDOWN = 60 * 60  # 1 час для одинакового спайка
    SETUP_COOLDOWN = 2 * 60 * 60  # 2 часа для одинакового направления сетапа

    while True:
        try:
            symbols = await exchange.get_top_pairs()
            print(f"Фоновый скан: {len(symbols)} пар...")
            
            current_time = time.time()

            for i, symbol in enumerate(symbols):
                is_smc_eligible = (i < TOP_COINS_LIMIT) or (symbol in CORE_PAIRS)

                for tf in ["15m", "1h", "4h"]:
                    df = await exchange.fetch_ohlcv(symbol, tf)
                    if df.empty:
                        continue
                    
                    # ----- Мониторинг всплесков -----
                    spike = spike_scanner.scan(df)
                    if spike:
                        spike_key = f"{symbol}_{tf}_{spike['direction']}"
                        last_time = last_spike_alert.get(spike_key, 0)
                        
                        if current_time - last_time > SPIKE_COOLDOWN:
                            msg = notifier.format_spike_alert(symbol, tf, spike)
                            await notifier.send_message(msg)
                            last_spike_alert[spike_key] = current_time # Обновляем кэш
                            await asyncio.sleep(0.1)

                    # ----- Мониторинг SMC паттернов -----
                    if is_smc_eligible:
                        smc_results = smc_analyzer.analyze_tf(df)
                        setup = smc_analyzer.find_setup(smc_results)
                        
                        if setup:
                            setup_key = f"{symbol}_{tf}_{setup['type']}"
                            last_time = last_setup_alert.get(setup_key, 0)
                            
                            if current_time - last_time > SETUP_COOLDOWN:
                                msg = notifier.format_smc_setup(symbol, tf, setup)
                                await notifier.send_message(msg)
                                last_setup_alert[setup_key] = current_time # Обновляем кэш
                                await asyncio.sleep(0.1)

                await asyncio.sleep(0.5)

            # Очистка старого кэша, чтобы не текло ОЗУ (удаляем то, что старше кулдауна)
            current_time = time.time()
            last_spike_alert = {k: v for k, v in last_spike_alert.items() if current_time - v <= SPIKE_COOLDOWN}
            last_setup_alert = {k: v for k, v in last_setup_alert.items() if current_time - v <= SETUP_COOLDOWN}

            print("Фоновый цикл завершен. Ожидание 60 секунд...")
            await asyncio.sleep(60)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Ошибка в главном цикле: {e}")
            await asyncio.sleep(10)

async def main():
    print("Инициализация SMC Трейдинг Бота с интерактивным меню...")
    
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
