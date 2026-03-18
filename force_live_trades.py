import asyncio
from bot_bingx import execute_smart_grid
from exchange_client_bingx import ExchangeClientBingX

async def force_trade():
    print("🚀 ПРИНУДИТЕЛЬНЫЙ ВХОД В РЕАЛЬНУЮ СДЕЛКУ 🚀")
    exchange = ExchangeClientBingX()
    
    # 1. Запуск сетки по ETH
    eth_price = await exchange.fetch_ticker_price("ETH/USDT:USDT")
    if eth_price > 0:
        print(f"\n--- Открываем сетку по ETH/USDT:USDT (Цена {eth_price}) ---")
        fake_setup_eth = {
            "type": "LONG",
            "entry": eth_price,
            "stop_loss": eth_price * 0.98 # 2% SL
        }
        await execute_smart_grid("ETH/USDT:USDT", "30m", fake_setup_eth, verdict=None, is_spike=False)
    
    # SOL temporarily disabled per user choice.
    
    await exchange.close()
    print("\n✅ Команда на вход отправлена! Проверьте Telegram и BingX.")

if __name__ == "__main__":
    asyncio.run(force_trade())
