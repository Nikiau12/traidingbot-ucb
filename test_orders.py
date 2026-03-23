import asyncio
import json
from bingx.exchange_client_bingx import ExchangeClientBingX

async def test_orders():
    exchange = ExchangeClientBingX()
    try:
        orders = await exchange.exchange.fetch_open_orders(symbol=None)
        print("All Open Orders:")
        for o in orders:
            if 'BB' in o['symbol'] or 'tp' in o.get('type', '').lower() or 'stop' in o.get('type', '').lower():
                print(json.dumps(o['info'], indent=2))
                
        # Also let's check triggers endpoint if it exists
        # swapV2PrivateGetTradeOpenOrders vs swapV2PrivateGetTradeAllOpenOrders
    except Exception as e:
        print("Error:", e)
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_orders())
