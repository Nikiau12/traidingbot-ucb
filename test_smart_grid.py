import asyncio
from exchange_client_bingx import ExchangeClientBingX
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

async def run_smart_grid_test():
    print("====== ТЕСТОВОЕ РАССТАВЛЕНИЕ УМНОЙ СЕТКИ BINGX ======\n")
    exchange = ExchangeClientBingX()
    
    symbol = "BTC/USDT:USDT"
    
    print("1. Опрашиваем цены...")
    current_price = await exchange.fetch_ticker_price(symbol)
    if current_price <= 0:
        print("Ошибка получения цены.")
        return
        
    print(f"✅ Текущая цена BTC: {current_price:.2f} USDT")
    
    # Симулируем искусственный SMC сигнал в LONG
    # Входим по текущей цене, стоп лосс ставим на 2% ниже, чтоб нас случайно не выбило
    entry_price = current_price
    stop_loss = current_price * 0.98  # 2% Stop Loss
    distance_to_sl = entry_price - stop_loss
    
    # Фиксированный объем для прохождения минимального лимита BingX
    # 0.0001 BTC ~ 7 USDT (это минимальный шаг для Биткоина на BingX Futs)
    amount_btc = 0.0001
    
    print("\n2. Отправляем Ордер 1 (Market Вход)...")
    tp1 = entry_price + distance_to_sl * 1.0
    order1 = await exchange.create_market_order_with_sl_tp(
        symbol=symbol, side='buy', amount=amount_btc, stop_loss=stop_loss, take_profit=tp1
    )
    if order1:
        print(f"✅ Ордер 1 Успешен! Market Вход. TP: {tp1:.2f}")
    
    print("\n3. Отправляем Ордер 2 (Limit - Первая просадка)...")
    entry2 = entry_price - distance_to_sl * 0.4 # Вход на 40% ниже 
    tp2 = entry2 + (entry2 - stop_loss) * 2.0
    order2 = await exchange.create_limit_order_with_sl_tp(
        symbol=symbol, side='buy', amount=amount_btc, price=entry2, stop_loss=stop_loss, take_profit=tp2
    )
    if order2:
        print(f"✅ Ордер 2 Успешен! Отложка на {entry2:.2f}. TP: {tp2:.2f}")

    print("\n4. Отправляем Ордер 3 (Limit - Снайпер)...")
    entry3 = entry_price - distance_to_sl * 0.7 # Вход на 70% ниже
    tp3 = entry3 + (entry3 - stop_loss) * 3.0
    order3 = await exchange.create_limit_order_with_sl_tp(
        symbol=symbol, side='buy', amount=amount_btc, price=entry3, stop_loss=stop_loss, take_profit=tp3
    )
    if order3:
        print(f"✅ Ордер 3 Успешен! Отложка на {entry3:.2f}. TP: {tp3:.2f}")
        
    print("\n==================================================")
    print("🚀 СЕТКА ИЗ 3-Х ОРДЕРОВ УСПЕШНО РАЗМЕЩЕНА!")
    print("👉 Откройте приложение BingX -> Фьючерсы -> Позиции/Открытые ордера")
    print("Вы увидите 1 активную позицию и 2 отложенные лимитки (плюс TP/SL на каждой).")
    print("Закройте/отмените их вручную после визуальной проверки.")
    print("==================================================")
    
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(run_smart_grid_test())
