import asyncio
import pandas as pd
from smartmoneyconcepts import smc
from bingx.exchange_client_bingx import ExchangeClientBingX

async def test_smc():
    exchange = ExchangeClientBingX()
    try:
        df = await exchange.fetch_ohlcv("BTC/USDT:USDT", "4h")
        
        fvg = smc.fvg(df)
        print("FVG Columns:", fvg.columns.tolist())
        # Print a sample bullish FVG
        bull_fvg = fvg[(fvg['FVG'] == 1) & (fvg['MitigatedIndex'] == 0)]
        print("Unmitigated Bullish FVGs:")
        print(bull_fvg.tail(2))
        
        ob = smc.ob(df)
        print("\nOB Columns:", ob.columns.tolist())
        bull_ob = ob[(ob['OB'] == 1) & (ob['MitigatedIndex'] == 0)]
        print("Unmitigated Bullish OBs:")
        print(bull_ob.tail(2))
        
    except Exception as e:
        print("Error:", e)
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_smc())
