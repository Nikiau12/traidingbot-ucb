import asyncio
import os
from dotenv import load_dotenv

# Force reload dotenv
load_dotenv(override=True)

from exchange_client_bingx import ExchangeClientBingX

async def test_order():
    print("====== ТЕСТОВОЕ ПОДКЛЮЧЕНИЕ К BINGX ======")
    
    bingx_key = os.getenv("BINGX_API_KEY", "")
    if not bingx_key:
        print("❌ ОШИБКА: BINGX_API_KEY не найден в файле .env!")
        return
        
    client = ExchangeClientBingX()
    
    try:
        print("\n1. Проверка баланса...")
        balance = await client.fetch_balance_usdt()
        print(f"✅ Доступный баланс USDT (Futures): {balance:.2f} USDT")
        if balance < 2.0:
            print("❌ ОШИБКА: Баланс меньше 2 USDT. Пополните фьючерсный счет BingX.")
            return

        print("\n2. Проверка цены BTC/USDT...")
        symbol = "BTC/USDT:USDT"
        price = await client.fetch_ticker_price(symbol)
        print(f"✅ Текущая цена {symbol}: {price:.2f} USDT")
        
        # Test Trade: ~12 USDT position size (which is > 0.0001 BTC minimum on BingX)
        amount = 12.0 / price
        
        # Stop loss 2% below, Take profit 4% above
        stop_loss = price * 0.98
        take_profit = price * 1.04
        
        print(f"\n3. Отправка тестового LONG ордера на {amount:.5f} BTC (~12 USDT позиции = ~2.4$ вашей маржи)")
        print(f"   SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
        
        # Uncomment below to actually fire the order!
        print("\n[СИМУЛЯЦИЯ ПРАВИЛЬНОЙ ОТПРАВКИ ВО ВРЕМЯ ТЕСТОВ]")
        print("Если вы видите этот текст, значит соединение с API установлено!")
        
        order = await client.create_market_order_with_sl_tp(
            symbol=symbol,
            side="buy", # LONG
            amount=amount,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        if order:
            print("✅ ТЕСТОВЫЙ ОРДЕР УСПЕШНО ИСПОЛНЕН БИРЖЕЙ! Проверьте приложение BingX!")
            print(order)
        else:
            print("❌ Биржа отклонила ордер (возможно, слишком маленький объем для этой монеты или неверные настройки плеча).")

    except Exception as e:
        print(f"❌ Критическая ошибка при тесте: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_order())
