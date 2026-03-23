import asyncio
import ccxt.async_support as ccxt
import time

async def check_bingx_limits():
    exchange = ccxt.bingx({
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })
    
    await exchange.load_markets()
    
    # Check BTC, ETH, and a few top alts
    symbols_to_check = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'DOGE/USDT:USDT', 'XRP/USDT:USDT', 'PEPE/USDT:USDT', 'WIF/USDT:USDT', 'ADA/USDT:USDT']
    
    print("=== Минимальные лимиты BingX (Объем в USDT) ===")
    print("При марже 0.5$ и 15x плече, ваш объем = 7.5$")
    print("-" * 50)
    for symbol in symbols_to_check:
        if symbol in exchange.markets:
            market = exchange.markets[symbol]
            min_cost = market.get('limits', {}).get('cost', {}).get('min', 'Неизвестно')
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 'Неизвестно')
            price = market.get('info', {}).get('lastPrice', 1) 
            
            print(f"{symbol}:")
            print(f"  Мин. объем (Notional): {min_cost} USDT")
            print(f"  Мин. монеты (Amount): {min_amount}")
        else:
            print(f"{symbol} не найден!")
            
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(check_bingx_limits())
