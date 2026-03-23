import asyncio
import ccxt.async_support as ccxt
from core.config import BINGX_API_KEY, BINGX_API_SECRET
from collections import defaultdict
import datetime

async def analyze_trades():
    exchange = ccxt.bingx({
        'apiKey': BINGX_API_KEY,
        'secret': BINGX_API_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })
    
    try:
        print("Получение истории всех сделок (Trade All Fill Orders)...")
        # Использование прямого BingX V2 API endpoint для получения всех закрытых сделок:
        response = await exchange.swapV2PrivateGetTradeAllFillOrders({'limit': 500})
        
        trades = response.get('data', [])
        if not trades:
            print("Не найдено закрытых сделок (Trades) за последнее время.")
            await exchange.close()
            return
            
        total_pnl = 0.0
        winners = 0
        losers = 0
        
        symbol_pnl = defaultdict(float)
        
        for t in trades:
            # BingX response:
            # { 'symbol': 'BTC-USDT', 'side': 'BUY', 'price': '60000', 'volume': '0.001', 'commission': '0.1', 'realizedPnl': '5.0' }
            pnl = float(t.get('realizedPnl', 0))
            if pnl > 0.0001:
                winners += 1
            elif pnl < -0.0001:
                losers += 1
                
            total_pnl += pnl
            sym = t.get('symbol', 'UNKNOWN')
            symbol_pnl[sym] += pnl
                
        print("\n=== 📊 ОТЧЕТ ПО ТОРГОВЛЕ BINGX ===")
        print(f"Всего исполнено ордеров (заявок): {len(trades)}")
        print(f"Кол-во ПРИБЫЛЬНЫХ трейдов: {winners}")
        print(f"Кол-во УБЫТОЧНЫХ трейдов: {losers}")
        win_rate = (winners / len(trades)) * 100 if len(trades) > 0 else 0
        print(f"Винрейт: {win_rate:.1f}%")
        print("-" * 30)
        print(f"💵 Общий чистый PnL (профит): {total_pnl:.4f} USDT")
        print("-" * 30)
        
        sorted_coins = sorted(symbol_pnl.items(), key=lambda x: x[1], reverse=True)
        print("Топ-3 самые прибыльные монеты:")
        for sym, pnl in sorted_coins[:3]:
            if pnl > 0:
                print(f"  {sym}: +{pnl:.4f} USDT")
            
        print("\nТоп-3 самые убыточные монеты:")
        for sym, pnl in sorted_coins[-3:]:
            if pnl < 0:
                print(f"  {sym}: {pnl:.4f} USDT")
                
    except Exception as e:
        print(f"Ошибка при анализе: {e}")
        
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(analyze_trades())
