import asyncio
import time
from aiogram import Bot
from bingx.exchange_client_bingx import ExchangeClientBingX
from core.smc_analyzer import SMCAnalyzer
from core.spike_scanner import SpikeScanner
from core.smart_engine import SmartContextEngine, SignalType, MTFFusionEngine
from core.notifier import Notifier
from core.position_tracker import PositionTracker
from core.htf_limit_manager import HTFLimitManager
from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, AUTO_TRADING_ENABLED, BINGX_MARGIN_PER_ORDER, BINGX_LEVERAGE, BINGX_ALTCOIN_MARGIN, BINGX_MAX_OPEN_POSITIONS, BINGX_ALTCOIN_V9_MIN_SCORE, BINGX_BTC_TREND_FILTER, TARGET_COINS

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
        order_risk_usdt = setup.get('risk', BINGX_MARGIN_PER_ORDER)
        
        if balance_usdt < 10.0:
            msg = f"⚠️ [BingX] Недостаточно баланса для сделки по {symbol}. Текущий баланс: {balance_usdt:.2f} USDT"
            await notifier.send_message(msg)
            return False
            
        total_risk_amount_usdt = BINGX_MARGIN_PER_ORDER * 3.0
        
        total_risk_amount_usdt = order_risk_usdt * 3.0
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
        is_major = any(coin in symbol for coin in ['BTC', 'ETH', 'SOL'])
        
        if not is_major:
            # АЛЬТКОИН СНАЙПЕР (1 Market ордер с увеличенным TP 1:3)
            # Прибыль покрывает стоп в 3 раза
            tp = entry_price + (distance_to_sl * 3.0) if side == 'buy' else entry_price - (distance_to_sl * 3.0)
            amount_coin = position_size_usdt_per_order / current_price
            
            order = await exchange.create_market_order_with_sl_tp(
                symbol=symbol, side=side, amount=amount_coin, stop_loss=stop_loss, take_profit=tp
            )
            if order:
                orders_placed += 1
                grid_messages.append(f"└ 🎯 Снайпер (Market): {position_size_usdt_per_order:.1f}$, TP={tp:.4f} (1:3)")
                total_risk_amount_usdt = order_risk_usdt # На альты тратится только 1 пуля
                
        elif is_spike:
            # Для Спайков: 3 Market ордера с одинаковым TP (RR 1:2)
            tp = entry_price + (distance_to_sl * 2.0) if side == 'buy' else entry_price - (distance_to_sl * 2.0)
            
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
            
            strategy_name = ""
            if not is_major: strategy_name = "Снайпер (1 Market x 1:3)"
            elif is_spike: strategy_name = "Импульс (Market x3)"
            else: strategy_name = "SMC (Market + 2 Limits)"
            
            msg = (
                f"🤖 <b>[БИНГКС ИСПОЛНЕНИЕ]</b> 🤖\n\n"
                f"Монета: <b>{symbol}</b> | Направление: {'🟢 LONG' if side == 'buy' else '🔴 SHORT'}\n"
                f"Стратегия: {strategy_name}\n"
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
        error_str = str(e).lower()
        if 'amount' in error_str or 'volume' in error_str or 'min' in error_str or 'precision' in error_str:
            print(f"[BingX AutoTrader] ⏩ Пропуск {symbol}: Выделенной маржи в ~{order_risk_usdt}$ недостаточно по лимитам биржи.")
        else:
            print(f"Ошибка выставления Smart Grid: {e}")
        return False

async def autotrade_scanner_loop():
    last_setup_alert = {}
    SETUP_COOLDOWN = 2 * 60 * 60

    while True:
        try:
            # Проверка дневного лимита убытка
            from core.config import BINGX_DAILY_LOSS_LIMIT
            if BINGX_DAILY_LOSS_LIMIT > 0:
                daily_pnl = await exchange.fetch_daily_pnl()
                if daily_pnl <= -BINGX_DAILY_LOSS_LIMIT:
                    print(f"[BingX AutoTrader] 🛑 ДНЕВНОЙ ЛИМИТ УБЫТКА ДОСТИГНУТ! Потери за сегодня: {daily_pnl:.2f} USDT. Отдыхаем 1 час...")
                    await asyncio.sleep(3600)
                    continue

            current_positions_count = await exchange.fetch_active_positions_count()
            if current_positions_count >= BINGX_MAX_OPEN_POSITIONS:
                print(f"[BingX AutoTrader] Достигнут максиум открытых сделок ({current_positions_count}/{BINGX_MAX_OPEN_POSITIONS})! Сканирование приостановлено.")
                await asyncio.sleep(60)
                continue
                
            final_symbols = await exchange.get_validated_targets()
            print(f"[BingX AutoTrader] 🔍 Начинаем сканирование {len(final_symbols)} рабочих пар: {final_symbols}")
            
            # Получаем тренд BTC для синхронизации альткоинов
            btc_bullish = True
            if BINGX_BTC_TREND_FILTER:
                try:
                    df_btc = await exchange.fetch_ohlcv('BTC/USDT:USDT', '1h', limit=5)
                    if not df_btc.empty and len(df_btc) > 2:
                        btc_bullish = df_btc['close'].iloc[-1] > df_btc['close'].iloc[0]
                except Exception as e:
                    print(f"Ошибка проверки тренда BTC: {e}")
                    
            current_time = time.time()

            for symbol in final_symbols:
                is_major = any(coin in symbol for coin in ['BTC', 'ETH', 'SOL'])
                order_risk = BINGX_MARGIN_PER_ORDER if is_major else BINGX_ALTCOIN_MARGIN
                
                import pandas as pd
                for tf in ["1h"]: # Торгуем только на 1h по просьбе пользователя
                    df = await exchange.fetch_ohlcv(symbol, tf)
                    if df.empty:
                        continue
                        
                    # --- Торговля Импульсов (Пампы/Дампы) на 30m ---
                    if tf == "30m":
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
                                    'take_profit': take_profit,
                                    'risk': order_risk
                                }
                                
                                print(f"[BingX AutoTrader] 🔥 ОБНАРУЖЕН {'ПАМП' if side == 'LONG' else 'ДАМП'} ПО {symbol} (30m)! Вход {side} по тренду импульса.")
                                
                                executed = await execute_smart_grid(symbol, "30m_SPIKE", setup_spike, None, is_spike=True)
                                if executed:
                                    last_setup_alert[spike_key] = current_time
                                    await asyncio.sleep(2)
                                    continue # Если вошли по спайку, пропускаем SMC анализ для этого таймфрейма, чтобы избежать дублей
                    
                    # --- Медленная торговля SMC Сетапов ---
                    allow_smc = False
                    if is_major and tf in ["15m", "30m", "1h", "4h"]:
                        # Разрешаем мажорам искать сетапы на всех рабочих таймфреймах (в т.ч. быстрых 15m/30m)
                        allow_smc = True
                    elif not is_major and tf == "1h":
                        # Разрешаем альткоинам искать сетапы на стабильном 1h таймфрейме
                        allow_smc = True
                        
                    if allow_smc:
                        smc_results = smc_analyzer.analyze_tf(df)
                        setup = smc_analyzer.find_setup(smc_results)
                        
                        if setup:
                            setup['risk'] = order_risk
                            score = smart_engine.analyze_context(df, symbol, setup['type'])
                            if score.signal == SignalType.NO_TRADE:
                                continue
                                
                            # Жесткий фильтр V9
                            if is_major:
                                if score.confidence < 60: continue # Золотая середина: снизили с 70 до 60 для BTC/ETH
                            else:
                                if score.confidence < BINGX_ALTCOIN_V9_MIN_SCORE: continue
                                
                                # Фильтр BTC Корреляции для альткоинов
                                if BINGX_BTC_TREND_FILTER:
                                    if setup['type'] == 'LONG' and not btc_bullish:
                                        print(f"[BingX AutoTrader] 🚫 Пропуск LONG {symbol}: Биткоин в локальном падении.")
                                        continue
                                    if setup['type'] == 'SHORT' and btc_bullish:
                                        print(f"[BingX AutoTrader] 🚫 Пропуск SHORT {symbol}: Биткоин в локальном росте.")
                                        continue
                            # MTF V11 Verification
                            dfs_dict = await fetch_mtf_context(symbol)
                            verdict = mtf_engine.analyze(dfs_dict)
                            
                            # Строгий риск менеджмент: НЕТ торговли при низкой уверенности
                            required_mtf = 50 if is_major else 60
                            if verdict.setup_type.name == "NO_TRADE" or verdict.confidence < required_mtf:
                                continue
                                
                            # Если анализ выявил сильные конфликты с дневкой
                            if is_major:
                                # Ослабляем фильтр: убрана блокировка countertrend для мажоров, чтобы сетка ставилась чаще
                                serious_risks = []
                            else:
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
            
        print("[BingX] Принудительная установка плеча для рабочих торговых пар...")
        target_symbols = [f"{coin}/USDT:USDT" for coin in TARGET_COINS]
        for symbol in target_symbols:
            await exchange.set_leverage(symbol, BINGX_LEVERAGE)
            
        tracker = PositionTracker(exchange)
        asyncio.create_task(tracker.track_loop())
        
        htf_sniper = HTFLimitManager(exchange)
        asyncio.create_task(htf_sniper.run_loop())
        
        await autotrade_scanner_loop()
    finally:
        await exchange.close()
        await notifier.close()

if __name__ == "__main__":
    asyncio.run(main())
