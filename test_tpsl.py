import asyncio
import json
from bingx.exchange_client_bingx import ExchangeClientBingX

async def test_update_sl():
    exchange = ExchangeClientBingX()
    try:
        # Check if CCXT bingx has implicit methods for TP/SL on swap positions
        methods = [m for m in dir(exchange.exchange) if 'tpsl' in m.lower() or 'stoploss' in m.lower() or 'position' in m.lower() or 'trigger' in m.lower()]
        
        relevant_methods = [m for m in methods if 'swap' in m.lower() and ('tpsl' in m.lower() or 'stop' in m.lower() or 'position' in m.lower() or 'trade' in m.lower())]
        
        print("Relevant CCXT implicit methods:")
        for m in sorted(dict.fromkeys(relevant_methods)):
            print(" -", m)
            
    except Exception as e:
        print("Error:", e)
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_update_sl())
