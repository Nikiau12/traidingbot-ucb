import asyncio
import json
from bingx.exchange_client_bingx import ExchangeClientBingX

async def test_update_sl():
    exchange = ExchangeClientBingX()
    try:
        symbol = 'BB-USDT'
        position_id = "2034540534534713345"
        old_sl_id = "2034642192375050241"
        
        # 1. Cancel existing Stop Loss order
        print("Canceling old SL...")
        await exchange.exchange.cancel_order(old_sl_id, symbol)
        print("Canceled SL successfully.")
        
        # 2. Create new SL
        new_sl = 0.02600
        qty = 291.48 # Same qty
        
        # Side is BUY because position is SHORT. Type is STOP_MARKET
        params = {
            'stopPrice': new_sl,
            'workingType': 'MARK_PRICE',
            'positionID': position_id,
            'positionSide': 'SHORT'
        }
        
        print("Creating new SL...")
        order = await exchange.exchange.create_order(
            symbol=symbol,
            type='STOP_MARKET',
            side='BUY',
            amount=qty,
            price=None,
            params=params
        )
        print("Success! New SL Order:")
        print(order)
        
    except Exception as e:
        print("Error:", e)
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_update_sl())
