import asyncio
import json
import os
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from mexc.exchange_client_mexc import ExchangeClient
from core.smc_analyzer import SMCAnalyzer
from core.spike_scanner import SpikeScanner
from core.notifier import Notifier
from core.smart_engine import SmartContextEngine, SignalType, MTFFusionEngine
from core.coin_info_service import CoinInfoService
from core.listing_watcher import MexcListingWatcher
from core.access_manager import AccessManager
from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ADMIN_CHAT_IDS, TIMEFRAMES, TOP_COINS_LIMIT, TARGET_COINS, SMART_SPIKE_MIN_SCORE, SMART_SPIKE_MIN_QUOTE_VOLUME, MEXC_LISTING_SNAPSHOT_FILE, MEXC_ANNOUNCEMENTS_SNAPSHOT_FILE, MEXC_LISTING_CHECK_INTERVAL, MEXC_NEW_LISTINGS_URL, FREE_TRIAL_SIGNALS, PAID_ACCESS_HOURS, USDT_PAYMENT_ADDRESS, USDT_PAYMENT_AMOUNT, USDT_PAYMENT_NETWORK, ACCESS_STATE_FILE, USER_REGISTRY_FILE

bot_instance = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

USERS_FILE = USER_REGISTRY_FILE

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
smart_engine = SmartContextEngine()
mtf_engine = MTFFusionEngine()
coin_info_service = CoinInfoService()
access_manager = AccessManager(
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
# Передаем set пользователей в Notifier
notifier = Notifier(bot_instance, active_users, access_manager=access_manager)

def is_admin(chat_id: str) -> bool:
    return str(chat_id) in ADMIN_CHAT_IDS

def format_ts(timestamp: int) -> str:
    if not timestamp:
        return "нет"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

async def require_access(message: types.Message) -> bool:
    chat_id = str(message.chat.id)
    if is_admin(chat_id):
        return True
    allowed, _ = access_manager.consume_signal(chat_id)
    if allowed:
        return True
    await message.reply(access_manager.format_paywall(), parse_mode="HTML")
    return False

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    chat_id = str(message.chat.id)
    is_new = save_user(chat_id)
    access_manager.ensure_user(chat_id)
    notifier.active_users.add(chat_id)
    if is_new:
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
        "🔸 /spikes — Запустить ручной сканер пампов\n"
        "🔸 /status — Проверить доступ и пробные сигналы\n"
        "🔸 /subscribe — Инструкция по оплате USDT\n\n"
        "Удачной торговли! 📈"
    )
    await message.reply(welcome_text, parse_mode="HTML")

@router.message(Command("subscribe"))
async def cmd_subscribe(message: types.Message):
    await message.reply(access_manager.format_paywall(), parse_mode="HTML")

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    status = access_manager.status(str(message.chat.id))
    if status["has_paid_access"]:
        access_text = f"✅ Оплачен до: <b>{format_ts(status['paid_until'])}</b>"
    else:
        access_text = "⏳ Активной оплаты нет"

    claim = status.get("payment_claim") or {}
    claim_text = ""
    if claim:
        claim_text = (
            "\n\nПоследняя заявка на оплату:\n"
            f"TX: <code>{claim.get('tx_hash', 'н/д')}</code>\n"
            f"Статус: <b>{claim.get('status', 'pending')}</b>"
        )

    await message.reply(
        (
            "👤 <b>Статус доступа</b>\n\n"
            f"{access_text}\n"
            f"Бесплатных сигналов осталось: <b>{status['trial_left']}</b> из {FREE_TRIAL_SIGNALS}"
            f"{claim_text}"
        ),
        parse_mode="HTML",
    )

@router.message(Command("paid"))
async def cmd_paid(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            "Пришли хеш транзакции так:\n<code>/paid TX_HASH</code>",
            parse_mode="HTML",
        )
        return

    chat_id = str(message.chat.id)
    tx_hash = parts[1].strip()
    access_manager.record_payment_claim(chat_id, tx_hash)
    await message.reply(
        "✅ Заявка на оплату принята. Админ проверит транзакцию и включит доступ.",
        parse_mode="HTML",
    )

    admin_msg = (
        "💸 <b>Новая заявка на оплату</b>\n\n"
        f"User: <code>{chat_id}</code>\n"
        f"TX: <code>{tx_hash}</code>\n\n"
        f"Выдать доступ на {PAID_ACCESS_HOURS}ч:\n"
        f"<code>/grant {chat_id}</code>"
    )
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await bot_instance.send_message(chat_id=admin_id, text=admin_msg, parse_mode="HTML")
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")

@router.message(Command("grant"))
async def cmd_grant(message: types.Message):
    if not is_admin(str(message.chat.id)):
        await message.reply("⛔️ Команда доступна только админу.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Использование: <code>/grant CHAT_ID [hours]</code>", parse_mode="HTML")
        return
    target_chat_id = parts[1]
    hours = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else PAID_ACCESS_HOURS
    paid_until = access_manager.grant_access(target_chat_id, hours=hours)
    await message.reply(
        f"✅ Доступ выдан пользователю <code>{target_chat_id}</code> до <b>{format_ts(paid_until)}</b>",
        parse_mode="HTML",
    )
    try:
        await bot_instance.send_message(
            chat_id=target_chat_id,
            text=f"✅ Оплата подтверждена. Доступ открыт до <b>{format_ts(paid_until)}</b>.",
            parse_mode="HTML",
        )
    except Exception as e:
        print(f"Failed to notify granted user {target_chat_id}: {e}")

@router.message(Command("revoke"))
async def cmd_revoke(message: types.Message):
    if not is_admin(str(message.chat.id)):
        await message.reply("⛔️ Команда доступна только админу.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Использование: <code>/revoke CHAT_ID</code>", parse_mode="HTML")
        return
    access_manager.revoke_access(parts[1])
    await message.reply(f"✅ Доступ пользователя <code>{parts[1]}</code> отключен.", parse_mode="HTML")

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

async def fetch_mtf_context(symbol: str) -> dict:
    """Helper to fetch 5 timeframes for MTF analysis"""
    dfs_dict = {"1w": None, "1d": None, "4h": None, "1h": None, "15m": None}
    for tf in ["1w", "1d", "4h", "1h", "15m"]:
        if tf == "1w":
            df = await exchange.fetch_historical_data(symbol, "1w")
        else:
            df = await exchange.fetch_ohlcv(symbol, tf)
        if not df.empty:
            smart_engine.add_context_indicators(df)
            dfs_dict[tf] = df
        await asyncio.sleep(0.05)
    return dfs_dict

async def handle_full_analysis_request(message: types.Message, coin: str):
    if not await require_access(message):
        return
    symbol = await exchange.validate_symbol(coin)
    if not symbol:
        await message.reply(f"❌ Монета {coin} не найдена на бирже MEXC. Проверьте тикер.")
        return
    
    await message.reply(f"🤖 Собираю данные для глубокого анализа {symbol}\n(15m, 1h, 4h, 1d + Вся История 1w)...")
    try:
        analyses = {"1w": {}, "1d": {}, "4h": {}, "1h": {}, "15m": {}}
        # Parallelism or Sequential fetching using the new helper
        dfs_dict = await fetch_mtf_context(symbol)
        
        for tf, df in dfs_dict.items():
            if df is not None:
                analyses[tf] = smc_analyzer.analyze_tf(df)

        if not any(analyses.values()):
            await message.reply("🤷‍♂️ Не удалось получить графики для анализа с MEXC.")
            return
            
        # Get the strict hierarchical MTF verdict
        verdict = mtf_engine.analyze(dfs_dict)
        
        msg = notifier.format_full_analysis(symbol, analyses, verdict)
        await message.reply(msg, parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Ошибка при глубоком анализе: {e}")

async def handle_setup_request(message: types.Message, coin: str):
    if not await require_access(message):
        return
    symbol = await exchange.validate_symbol(coin)
    if not symbol:
        await message.reply(f"❌ Сетап: Монета {coin} не найдена на MEXC.")
        return
        
    await message.reply(f"🔍 Анализирую {symbol} по стратегии SMC...")
    try:
        found = False
        for tf in ["4h", "1d"]:
            df = await exchange.fetch_ohlcv(symbol, tf)
            if df.empty:
                continue
            smc_results = smc_analyzer.analyze_tf(df)
            setup = smc_analyzer.find_setup(smc_results)
            if setup:
                # Фильтруем сетап через Smart Context Engine
                score = smart_engine.analyze_context(df, symbol, setup['type'])
                if score.signal != SignalType.NO_TRADE:
                    # MTF V11 Verification
                    dfs_dict = await fetch_mtf_context(symbol)
                    verdict = mtf_engine.analyze(dfs_dict)
                    
                    if verdict.setup_type.name != "NO_TRADE":
                        msg = notifier.format_smc_setup(symbol, tf, setup, score, verdict)
                        await message.reply(msg, parse_mode="HTML")
                        found = True
        
        if not found:
            await message.reply(f"🤷‍♂️ В данный момент нет свежих сетапов SMC по {symbol} на старших таймфреймах (4h, 1d).")
            
    except Exception as e:
        await message.reply(f"❌ Ошибка при анализе: {e}")

async def handle_spikes_request(message: types.Message):
    if not await require_access(message):
        return
    await message.reply("🚀 Запускаю ручной сканер всплесков/пампов по Топ-250 монетам. Это займет пару минут...")
    try:
        symbols = await exchange.get_top_pairs()
        spikes_found = []
        for symbol in symbols:
            df = await exchange.fetch_ohlcv(symbol, "15m")
            if df.empty:
                continue
            ticker = await exchange.fetch_ticker_cached(symbol)
            spike = spike_scanner.scan(df, ticker=ticker)
            if spike:
                spikes_found.append((symbol, spike))
            await asyncio.sleep(0.05)
            
        if not spikes_found:
            await message.reply("🤷‍♂️ Аномальных всплесков объемов прямо сейчас не замечено.")
            return
            
        for sym, spk in spikes_found[:15]:
            coin_info = await coin_info_service.get_coin_info(sym)
            msg = notifier.format_spike_alert(sym, "15m", spk, coin_info=coin_info)
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
                target_symbols = [f"{coin}/USDT" for coin in TARGET_COINS]
                is_smc_eligible = (i < TOP_COINS_LIMIT) or (symbol in target_symbols)

                for tf in ["15m", "4h", "1d"]:
                    df = await exchange.fetch_ohlcv(symbol, tf)
                    if df.empty:
                        continue
                    
                    # ----- Мониторинг всплесков (только на 15m) -----
                    if tf == "15m":
                        ticker = await exchange.fetch_ticker_cached(symbol)
                        spike = spike_scanner.scan(df, ticker=ticker)
                        if spike:
                            if spike.get("score", 0) < SMART_SPIKE_MIN_SCORE:
                                continue
                            if spike.get("quote_volume", 0) and spike["quote_volume"] < SMART_SPIKE_MIN_QUOTE_VOLUME:
                                continue

                            spike_key = f"{symbol}_{tf}_{spike['direction']}"
                            last_time = last_spike_alert.get(spike_key, 0)
                            
                            if current_time - last_time > SPIKE_COOLDOWN:
                                coin_info = await coin_info_service.get_coin_info(symbol)
                                msg = notifier.format_spike_alert(symbol, tf, spike, coin_info=coin_info)
                                await notifier.send_message(msg)
                                last_spike_alert[spike_key] = current_time # Обновляем кэш
                                await asyncio.sleep(0.1)

                    # ----- Мониторинг SMC паттернов (только на 4h и 1d) -----
                    if tf in ["4h", "1d"] and is_smc_eligible:
                        smc_results = smc_analyzer.analyze_tf(df)
                        setup = smc_analyzer.find_setup(smc_results)
                        
                        if setup:
                            # Прогоняем сетап через Умный Движок (V9)
                            score = smart_engine.analyze_context(df, symbol, setup['type'])
                            
                            # Блокируем мусорные сигналы (NO_TRADE)
                            if score.signal == SignalType.NO_TRADE:
                                continue
                                
                            # MTF V11 Verification
                            dfs_dict = await fetch_mtf_context(symbol)
                            verdict = mtf_engine.analyze(dfs_dict)
                            
                            # Reject weak setups using MTF Logic
                            if verdict.setup_type.name == "NO_TRADE":
                                continue
                                
                            setup_key = f"{symbol}_{tf}_{setup['type']}"
                            last_time = last_setup_alert.get(setup_key, 0)
                            
                            if current_time - last_time > SETUP_COOLDOWN:
                                msg = notifier.format_smc_setup(symbol, tf, setup, score, verdict)
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

async def listing_watcher_loop():
    while True:
        try:
            announcements = await listing_watcher.check_new_announcements()
            for item in announcements[:10]:
                symbol = item["symbols"][0] if item.get("symbols") else ""
                coin_info = await coin_info_service.get_coin_info(symbol) if symbol else {}
                msg = notifier.format_listing_news_alert(item, coin_info=coin_info)
                await notifier.send_message(msg)
                await asyncio.sleep(0.2)

            new_symbols = await listing_watcher.check_new_markets(exchange)
            for symbol in new_symbols[:20]:
                coin_info = await coin_info_service.get_coin_info(symbol)
                msg = notifier.format_listing_alert(symbol, coin_info=coin_info)
                await notifier.send_message(msg)
                await asyncio.sleep(0.2)
            if new_symbols:
                print(f"Новые MEXC пары: {', '.join(new_symbols[:20])}")
            await asyncio.sleep(MEXC_LISTING_CHECK_INTERVAL)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Ошибка watcher листингов: {e}")
            await asyncio.sleep(60)

async def main():
    print("Инициализация SMC Трейдинг Бота с интерактивным меню...")
    
    dp.include_router(router)
    
    # Запускаем фоновый сканнер рынка
    scanner_task = asyncio.create_task(market_scanner_loop())
    listing_task = asyncio.create_task(listing_watcher_loop())
    
    try:
        # Запускаем поллинг телеграм-бота (для команд)
        await dp.start_polling(bot_instance)
    finally:
        scanner_task.cancel()
        listing_task.cancel()
        await exchange.close()
        await notifier.close()

if __name__ == "__main__":
    asyncio.run(main())
