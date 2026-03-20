import asyncio
from bingx.exchange_client_bingx import ExchangeClientBingX
from core.htf_limit_manager import HTFLimitManager
import core.config as config

async def test():
    # Force Auto Trading for test
    config.AUTO_TRADING_ENABLED = True
    
    exchange = ExchangeClientBingX()
    htf = HTFLimitManager(exchange)
    
    try:
        print("Testing single execution pass of HTF Manager...")
        # We will manually run the inner loop once
        for symbol in htf.symbols:
            print(f"\n--- Testing {symbol} ---")
            try:
                trend = await htf.get_macro_trend(symbol)
                print(f"Macro trend: {trend}")
                
                df_4h = await htf.exchange.fetch_ohlcv(symbol, "4h", limit=200)
                current_price = await htf.exchange.fetch_ticker_price(symbol)
                
                from smartmoneyconcepts import smc
                fvg_data = smc.fvg(df_4h)
                
                df_fvg = df_4h.copy()
                for col in ['FVG', 'Top', 'Bottom', 'MitigatedIndex']:
                    df_fvg[col] = fvg_data[col]
                    
                poi = None
                direction = ""

                if trend == "BULLISH":
                    active_fvgs = df_fvg[(df_fvg['FVG'] == 1) & (df_fvg['MitigatedIndex'] == 0)]
                    valid = active_fvgs[active_fvgs['Top'] < current_price]
                    if not valid.empty:
                        best = valid.loc[valid['Top'].idxmax()]
                        poi = {'entry': best['Top'], 'sl': best['Bottom'] - (best['Top'] - best['Bottom']) * 0.1}
                        direction = "LONG"
                elif trend == "BEARISH":
                    active_fvgs = df_fvg[(df_fvg['FVG'] == -1) & (df_fvg['MitigatedIndex'] == 0)]
                    valid = active_fvgs[active_fvgs['Bottom'] > current_price]
                    if not valid.empty:
                        best = valid.loc[valid['Bottom'].idxmin()]
                        poi = {'entry': best['Bottom'], 'sl': best['Top'] + (best['Top'] - best['Bottom']) * 0.1}
                        direction = "SHORT"
                        
                if not poi:
                    print("No active 4H POI found.")
                    continue
                    
                print(f"Candidate POI: Direction={direction}, Entry={poi['entry']:.4f}, SL={poi['sl']:.4f}")
                
            except Exception as e:
                print(f"Error testing {symbol}: {e}")
                
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test())
