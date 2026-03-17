import asyncio
from exchange_client import ExchangeClient
from smc_analyzer import SMCAnalyzer
from spike_scanner import SpikeScanner
from notifier import Notifier
from config import TIMEFRAMES, TOP_COINS_LIMIT, CORE_PAIRS

async def main():
    print("Инициализация SMC Трейдинг Бота...")
    exchange = ExchangeClient()
    smc_analyzer = SMCAnalyzer()
    spike_scanner = SpikeScanner()
    notifier = Notifier()

    await notifier.send_message("✅ <b>Трейдинг Бот запущен</b>\nСлежу за рынком...")

    try:
        while True:
            try:
                # 1. Получаем список актуальных монет для торговли
                symbols = await exchange.get_top_pairs()
                print(f"Сканируем {len(symbols)} пар...")

                # 2. Перебираем монеты
                for i, symbol in enumerate(symbols):
                    # Проверяем, подходит ли монета для тяжелого SMC анализа (только топ-50 + базовые)
                    is_smc_eligible = (i < TOP_COINS_LIMIT) or (symbol in CORE_PAIRS)

                    # Сканируем ТФ
                    for tf in ["15m", "1h", "4h"]:
                        df = await exchange.fetch_ohlcv(symbol, tf)
                        if df.empty:
                            continue
                        
                        # ----- Мониторинг всплесков (Работает на всех 250 монетах) -----
                        spike = spike_scanner.scan(df)
                        if spike:
                            msg = notifier.format_spike_alert(symbol, tf, spike)
                            await notifier.send_message(msg)
                            await asyncio.sleep(0.1) # Antispam

                        # ----- Мониторинг SMC паттернов (Только для надежных Топ-50) -----
                        if is_smc_eligible:
                            smc_results = smc_analyzer.analyze_tf(df)
                            setup = smc_analyzer.find_setup(smc_results)
                            
                            if setup:
                                msg = notifier.format_smc_setup(symbol, tf, setup)
                                await notifier.send_message(msg)
                                await asyncio.sleep(0.1)

                    # Small delay between coins to respect rate limits
                    await asyncio.sleep(0.5)

                # Wait before next full cycle (e.g. 1 minute)
                print("Цикл завершен. Ожидание 60 секунд...")
                await asyncio.sleep(60)

            except Exception as e:
                print(f"Ошибка в главном цикле: {e}")
                await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("Бот остановлен пользователем.")
    finally:
        await exchange.close()
        await notifier.close()

if __name__ == "__main__":
    asyncio.run(main())
