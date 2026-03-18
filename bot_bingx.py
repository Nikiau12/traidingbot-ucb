import asyncio
import time
from aiogram import Bot
from exchange_client_bingx import ExchangeClientBingX
from smc_analyzer import SMCAnalyzer
from smart_engine import SmartContextEngine, SignalType, MTFFusionEngine
from notifier import Notifier
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TOP_COINS_LIMIT, CORE_PAIRS, AUTO_TRADING_ENABLED, RISK_PER_TRADE_PERCENT, LEVERAGE

bot_instance = Bot(token=TELEGRAM_BOT_TOKEN)

exchange = ExchangeClientBingX()
smc_analyzer = SMCAnalyzer()
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

async def execute_trade(symbol, tf, setup, verdict):
    if not AUTO_TRADING_ENABLED:
        print(f"[BingX AutoTrader] Пропуск автоматической сделки (Симуляция) по {symbol}. AUTO_TRADING_ENABLED = False.")
        return False
        
    try:
        balance_usdt = await exchange.fetch_balance_usdt()
        if balance_usdt < 10.0:
            msg = f"⚠️ [BingX] Недостаточно баланса для сделки по {symbol}. Текущий баланс: {balance_usdt:.2f} USDT"
            await notifier.send_message(msg)
            return False
            
        # Position sizing logic base
        risk_amount_usdt = balance_usdt * (RISK_PER_TRADE_PERCENT / 100.0)
        
        entry_price = setup['entry']
        stop_loss = setup['stop_loss']
        take_profit = setup['take_profit']
        
        if entry_price == stop_loss:
            return False
            
        sl_percent = abs(entry_price - stop_loss) / entry_price
        
        position_size_usdt = risk_amount_usdt * LEVERAGE
        
        # Convert to base asset (Coin amount)
        price = await exchange.fetch_ticker_price(symbol)
        if price <= 0:
            return False
            
        amount_coin = position_size_usdt / price
        side = 'buy' if setup['type'] == 'LONG' else 'sell'
        
        print(f"[BingX AutoTrader] Размещаю ордер {side} на {amount_coin:.4f} {symbol}. SL={stop_loss}, TP={take_profit}")
        
        order = await exchange.create_market_order_with_sl_tp(
            symbol=symbol,
            side=side,
            amount=amount_coin,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        if order:
            msg = (
                f"🤖 <b>[БИНГО! АВТОТРЕЙДЕР В РАБОТЕ - BINGX]</b> 🤖\n\n"
                f"Успешно открыта позиция по <b>{symbol}</b>!\n"
                f"Направление: {'🟢 LONG' if side == 'buy' else '🔴 SHORT'}\n"
                f"Размер маржи: {risk_amount_usdt:.2f} USDT (Плечо: x{LEVERAGE})\n"
                f"Объем позиции: {position_size_usdt:.2f} USDT\n"
                f"Баланс: {balance_usdt:.2f} USDT\n"
                f"Stop-Loss: {stop_loss:.5f}\n"
                f"Take-Profit: {take_profit:.5f}"
            )
            await notifier.send_message(msg)
            return True
        else:
            await notifier.send_message(f"❌ [BingX] Ошибка исполнения сделки по {symbol}. API биржи не приняло ордер.")
            return False
            
    except Exception as e:
        print(f"Ошибка исполнения ордера: {e}")
        return False

async def autotrade_scanner_loop():
    last_setup_alert = {}
    SETUP_COOLDOWN = 2 * 60 * 60

    while True:
        try:
            symbols = await exchange.get_top_pairs()
            print(f"[BingX AutoTrader] Фоновый скан: {len(symbols)} пар...")
            current_time = time.time()

            for i, symbol in enumerate(symbols):
                is_smc_eligible = (i < TOP_COINS_LIMIT) or (symbol in CORE_PAIRS)
                if not is_smc_eligible:
                    continue

                for tf in ["15m", "1h", "4h"]:
                    df = await exchange.fetch_ohlcv(symbol, tf)
                    if df.empty:
                        continue
                        
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
                            executed = await execute_trade(symbol, tf, setup, verdict)
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
