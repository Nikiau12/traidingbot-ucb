import asyncio
from bingx.exchange_client_bingx import ExchangeClientBingX

async def test_btc():
    exchange = ExchangeClientBingX()
    try:
        # Try fetching candles for BTC/USDT:USDT
        try:
            df = await exchange.fetch_ohlcv("BTC/USDT:USDT", "15m")
            print("Successfully fetched BTC/USDT:USDT 15m candles! Length:", len(df))
        except Exception as e:
            print("Failed to fetch BTC/USDT:USDT:", e)
            
        # Try fetching orderbook or ticker
        try:
            ticker = await exchange.exchange.fetch_ticker("BTC/USDT:USDT")
            print("BTC Ticker:", ticker['last'])
        except Exception as e:
            print("Failed to fetch ticker:", e)
            
        # Try to check if BTC/USDT:USDT is in get_top_pairs
        top = await exchange.get_top_pairs(10)
        print("Top 10 pairs from GET:", list(top))
        if "BTC/USDT:USDT" in top:
            print("BTC/USDT:USDT is correctly in TOP PAIRS.")
        else:
            print("WARNING: BTC IS MISSING FROM TOP PAIRS!")
            
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_btc())
