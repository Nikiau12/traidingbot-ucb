import asyncio
import pandas as pd
from bingx.exchange_client_bingx import ExchangeClientBingX
from core.flag_pattern_scanner import FlagPatternScanner
from core.config import TARGET_COINS

async def main():
    exchange = ExchangeClientBingX()
    scanner = FlagPatternScanner(exchange)
    
    print("Testing FlagPatternScanner on TARGET_COINS (1d)...")
    for symbol in scanner.symbols:
        df = await exchange.fetch_ohlcv(symbol, "1d", limit=300)
        if df.empty:
            continue
            
        print(f"\nAnalyzing {symbol}...")
        
        # We will loop through the dataframe to see if a flag was triggered in the past 30 days
        triggers = []
        for i in range(100, len(df)):
            window_df = df.iloc[:i]
            setup = scanner.analyze_flag(symbol, window_df)
            if setup:
                date_str = window_df['timestamp'].iloc[-1]
                triggers.append({'date': date_str, 'setup': setup})
                
        if triggers:
            print(f"✅ Found {len(triggers)} triggers over the past 100 candles!")
            # Print the last 2 triggers
            for t in triggers[-2:]:
                print(f"Trigger Date: {t['date']}")
                print(f"Setup: {t['setup']['setup']}")
                print(f"Reasoning: {t['setup']['reasoning']}")
                print("-" * 30)
        else:
            print("No flag patterns detected for this coin in test window.")
            
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
