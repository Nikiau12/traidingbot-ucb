import asyncio
import time
from aiogram import Bot
from exchange_client_bingx import ExchangeClientBingX
from smc_analyzer import SMCAnalyzer
from spike_scanner import SpikeScanner
from smart_engine import SmartContextEngine, SignalType, MTFFusionEngine
from notifier import Notifier
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, AUTO_TRADING_ENABLED, BINGX_WHITELIST, BINGX_MARGIN_PER_ORDER, BINGX_LEVERAGE

bot_instance = Bot(token=TELEGRAM_BOT_TOKEN)

exchange = ExchangeClientBingX()
smc_analyzer = SMCAnalyzer()
spike_scanner = SpikeScanner()
smart_engine = SmartContextEngine()
mtf_engine = MTFFusionEngine()

# Initialize notifier to send alerts to the original chat owner
notifier = Notifier(bot_instance, {str(TELEGRAM_CHAT_ID)} if TELEGRAM_CHAT_ID else set())

async def fetch_mtf_context(symbol: str) -> dict:
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

async def execute_smart_grid(symbol, tf, setup, verdict, is_spike=False):
    if not AUTO_TRADING_ENABLED:
        print(f"[BingX AutoTrader] Пропуск автоматической сделки по {symbol}. AUTO_TRADING_ENABLED=False.")
        return False
        
    try:
        balance_usdt = await exchange.fetch_balance_usdt()
        if balance_usdt < 10.0:
            msg = f"⚠️ [BingX] Недостаточно баланса для сделки по {symbol}. Текущий баланс: {balance_usdt:.2f} USDT"
            await notifier.send_message(msg)
            return False
            
        total_risk_amount_usdt = BINGX_MARGIN_PER_ORDER * 3.0
        
        # Разделяем риск на 3 ордера (сетку)
        order_risk_usdt = BINGX_MARGIN_PER_ORDER
        position_size_usdt_per_order = order_risk_usdt * BINGX_LEVERAGE
        
        current_price = await exchange.fetch_ticker_price(symbol)
        if current_price <= 0:
            return False
            
        entry_price = setup['entry']
        stop_loss = setup['stop_loss']
        side = 'buy' if setup['type'] == 'LONG' else 'sell'
        
        if entry_price == stop_loss:
            return False
            
        distance_to_sl = abs(entry_price - stop_loss)
        
        orders_placed = 0
        grid_messages = []
        
        if is_spike:
            # Для Спайков: 3 Market ордера с одинаковым TP (RR 1:2)
            tp = entry_price + (entry_price - stop_loss) * 2.0 if side == 'buy' else entry_price - (stop_loss - entry_price) * 2.0
            
            for i in range(3):
                amount_coin = position_size_usdt_per_order / current_price
                order = await exchange.create_market_order_with_sl_tp(
                    symbol=symbol, side=side, amount=amount_coin, stop_loss=stop_loss, take_profit=tp
                )
                if order:
                    orders_placed += 1
                    grid_messages.append(f"└ Орд {i+1} (Market): {position_size_usdt_per_order:.1f}$, TP={tp:.4f} (1:2)")
        else:
            # Для SMC: 1 Market + 2 Консервативных Limit
            # Все ордера имеют Риск/Прибыль 1:2 относительно своей точки входа!
            
            # Ордер 1 (Market)
            tp1 = entry_price + distance_to_sl * 2.0 if side == 'buy' else entry_price - distance_to_sl * 2.0
            amount1 = position_size_usdt_per_order / current_price
            order1 = await exchange.create_market_order_with_sl_tp(
                symbol=symbol, side=side, amount=amount1, stop_loss=stop_loss, take_profit=tp1
            )
            if order1:
                orders_placed += 1
                grid_messages.append(f"└ Орд 1 (Market): Вход {current_price:.4f}, TP={tp1:.4f} (1:2)")
                
            # Ордер 2 (Limit - 40% просадки)
            entry2 = entry_price - distance_to_sl * 0.4 if side == 'buy' else entry_price + distance_to_sl * 0.4
            tp2 = entry2 + (entry2 - stop_loss) * 2.0 if side == 'buy' else entry2 - (stop_loss - entry2) * 2.0
            amount2 = position_size_usdt_per_order / entry2
            order2 = await exchange.create_limit_order_with_sl_tp(
                symbol=symbol, side=side, amount=amount2, price=entry2, stop_loss=stop_loss, take_profit=tp2
            )
            if order2:
                orders_placed += 1
                grid_messages.append(f"└ Орд 2 (Limit): Вход {entry2:.4f}, TP={tp2:.4f} (1:2)")
                
            # Ордер 3 (Limit - 70% просадки)
            entry3 = entry_price - distance_to_sl * 0.7 if side == 'buy' else entry_price + distance_to_sl * 0.7
            tp3 = entry3 + (entry3 - stop_loss) * 2.0 if side == 'buy' else entry3 - (stop_loss - entry3) * 2.0
            amount3 = position_size_usdt_per_order / entry3
            order3 = await exchange.create_limit_order_with_sl_tp(
                symbol=symbol, side=side, amount=amount3, price=entry3, stop_loss=stop_loss, take_profit=tp3
            )
            if order3:
                orders_placed += 1
                grid_messages.append(f"└ Орд 3 (Limit): Вход {entry3:.4f}, TP={tp3:.4f} (1:2)")
                
        if orders_placed > 0:
            grid_text = "\n".join(grid_messages)
            msg = (
                f"🤖 <b>[SMART GRID ВЫСТАВЛЕН - BINGX]</b> 🤖\n\n"
                f"Монета: <b>{symbol}</b> | Направление: {'🟢 LONG' if side == 'buy' else '🔴 SHORT'}\n"
                f"Стратегия: {'Импульс (Market x3)' if is_spike else 'SMC (Market + 2 Limits)'}\n"
                f"Общий риск: {total_risk_amount_usdt:.2f} USDT (Плечо: x{BINGX_LEVERAGE})\n"
                f"Единый Stop-Loss: {stop_loss:.5f}\n\n"
                f"<b>Структура сетки:</b>\n"
                f"{grid_text}\n\n"
                f"Баланс: {balance_usdt:.2f} USDT"
            )
            await notifier.send_message(msg)
            return True
        else:
            await notifier.send_message(f"❌ [BingX] Ошибка выставления сетки ордеров по {symbol}. Биржа отклонила все запросы.")
            return False
            
    except Exception as e:
        print(f"Ошибка выставления Smart Grid: {e}")
        return False

async def autotrade_scanner_loop():
    last_setup_alert = {}
    SETUP_COOLDOWN = 2 * 60 * 60

    while True:
        try:
            symbols = BINGX_WHITELIST
            print(f"[BingX AutoTrader] Фоновый скан белого списка: {symbols}...")
            current_time = time.time()

            for i, symbol in enumerate(symbols):
                for tf in ["15m", "30m", "1h", "4h", "1d"]:
                    df = await exchange.fetch_ohlcv(symbol, tf)
                    if df.empty:
                        continue
                        
                    # --- Торговля Импульсов (Пампы/Дампы) на 15m ---
                    if tf == "15m":
                        spike = spike_scanner.scan(df)
                        if spike:
                            spike_key = f"{symbol}_{tf}_{spike['direction']}_SPIKE"
                            last_time = last_setup_alert.get(spike_key, 0)
                            
                            if current_time - last_time > SETUP_COOLDOWN:
                                entry_price = float(df.iloc[-1]['close'])
                                open_price = float(df.iloc[-1]['open'])
                                
                                if spike['direction'] == 'up':
                                    side = 'LONG'
                                    stop_loss = open_price * 0.999 # Стоп за началом импульса
                                    take_profit = entry_price + (entry_price - stop_loss) * 2.0
                                else:
                                    side = 'SHORT'
                                    stop_loss = open_price * 1.001
                                    take_profit = entry_price - (stop_loss - entry_price) * 2.0
                                    
                                setup_spike = {
                                    'type': side,
                                    'entry': entry_price,
                                    'stop_loss': stop_loss,
                                    'take_profit': take_profit
                                }
                                
                                print(f"[BingX AutoTrader] 🔥 ОБНАРУЖЕН {'ПАМП' if side == 'LONG' else 'ДАМП'} ПО {symbol}! Вход {side} по тренду импульса.")
                                
                                executed = await execute_smart_grid(symbol, "15m_SPIKE", setup_spike, None, is_spike=True)
                                if executed:
                                    last_setup_alert[spike_key] = current_time
                                    await asyncio.sleep(2)
                                    continue # Если вошли по спайку, пропускаем SMC анализ для этого таймфрейма, чтобы избежать дублей
                    
                    # --- Медленная торговля SMC Сетапов ---
                    allow_smc = False
                    if symbol == "BTC/USDT" and tf in ["4h", "1d"]:
                        allow_smc = True
                    elif symbol == "ETH/USDT" and tf == "30m":
                        allow_smc = True
                    elif symbol == "SOL/USDT" and tf == "15m":
                        allow_smc = True
                        
                    if allow_smc:
                        smc_results = smc_analyzer.analyze_tf(df)
                        setup = smc_analyzer.find_setup(smc_results)
                        
                        if setup:
                            score = smart_engine.analyze_context(df, symbol, setup['type'])
                            if score.signal == SignalType.NO_TRADE:
                                continue
                                
                            # MTF V11 Verification
                            dfs_dict = await fetch_mtf_context(symbol)
                            verdict = mtf_engine.analyze(dfs_dict)
                            
                            # Строгий риск менеджмент: НЕТ торговли при низкой уверенности
                            if verdict.setup_type.name == "NO_TRADE" or verdict.confidence < 60:
                                continue
                                
                            # Если анализ выявил сильные конфликты с дневкой
                            serious_risks = [f for f in verdict.risk_flags if 'countertrend' in f or 'choppy' in f]
                            if serious_risks:
                                print(f"[BingX AutoTrader] Скип {symbol}. Слишком опасно: {serious_risks}")
                                continue
                                
                            setup_key = f"{symbol}_{tf}_{setup['type']}"
                            last_time = last_setup_alert.get(setup_key, 0)
                            
                            if current_time - last_time > SETUP_COOLDOWN:
                                executed = await execute_smart_grid(symbol, tf, setup, verdict, is_spike=False)
                                if executed:
                                    last_setup_alert[setup_key] = current_time
                                    await asyncio.sleep(2)

                await asyncio.sleep(0.5)

            current_time = time.time()
            last_setup_alert = {k: v for k, v in last_setup_alert.items() if current_time - v <= SETUP_COOLDOWN}

            print("[BingX AutoTrader] Цикл завершен. Ожидание 60 секунд...")
            await asyncio.sleep(60)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Ошибка в цикле автоторговли: {e}")
            await asyncio.sleep(10)

async def main():
    print("🚀 Инициализация BingX AutoTrader Бота (Невидимка)...")
    try:
        if not AUTO_TRADING_ENABLED:
            print("[ВНИМАНИЕ] Автоматическая торговля отключена (AUTO_TRADING_ENABLED=False). Сделки не будут открываться.")
        await autotrade_scanner_loop()
    finally:
        await exchange.close()
        await notifier.close()

if __name__ == "__main__":
    asyncio.run(main())
