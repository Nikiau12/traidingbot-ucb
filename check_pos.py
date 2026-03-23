import asyncio
import json
from bingx.exchange_client_bingx import ExchangeClientBingX

async def test_fetch():
    exchange = ExchangeClientBingX()
    try:
        positions = await exchange.exchange.fetch_positions()
        active = [p for p in positions if float(p.get('contracts', 0)) > 0]
        if active:
            print("Active Position Sample:")
            print(json.dumps(active[0]['info'], indent=2))
        else:
            print("No active positions.")
            if positions:
                print("First empty position:")
                print(json.dumps(positions[0]['info'], indent=2))
    except Exception as e:
        print("Error:", e)
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_fetch())
