import asyncio
import ccxt.async_support as ccxt
import pandas as pd
from config import BINGX_API_KEY, BINGX_API_SECRET, CORE_PAIRS, MEMECOIN_V2_LIMIT

class ExchangeClientBingX:
    def __init__(self):
        self.exchange = ccxt.bingx({
            'apiKey': BINGX_API_KEY,
            'secret': BINGX_API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap', # We want to trade Futures (Perpetual Swaps)
            }
        })
        self._markets_loaded = False
        
    async def load_markets_if_needed(self):
        if not self._markets_loaded:
            await self.exchange.load_markets()
            self._markets_loaded = True

    async def validate_symbol(self, raw_coin: str) -> str:
        """
        Takes a raw coin string (like 'PEPE' or 'PEPEUSDT') and tries to find a valid Perpetual Swap trading pair on BingX.
        Returns the formatted symbol (e.g. 'PEPE/USDT:USDT') or None if not found.
        """
        await self.load_markets_if_needed()
        
        # Normalize input
        coin = raw_coin.upper().replace("USDT", "")
        # BingX futures symbols format ccxt uses: 'BTC/USDT:USDT'
        target_symbol = f"{coin}/USDT:USDT"
        
        if target_symbol in self.exchange.markets:
            return target_symbol
            
        return None

    async def fetch_balance_usdt(self) -> float:
        """Fetch free/available USDT balance for futures trading."""
        try:
            # Type 'swap' specifies the perpetual futures account
            balance = await self.exchange.fetch_balance({'type': 'swap'})
            if 'USDT' in balance and 'free' in balance['USDT']:
                return float(balance['USDT']['free'])
            return 0.0
        except Exception as e:
            print(f"Error fetching BingX balance: {e}")
            return 0.0

    async def fetch_ticker_price(self, symbol: str) -> float:
        """Fetch the current market price (last price) of a symbol."""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            return 0.0

    async def close(self):
        await self.exchange.close()

    async def get_top_pairs(self):
        """Fetches the top N USDT perpetual pairs by 24h quote volume."""
        try:
            tickers = await self.exchange.fetch_tickers()
            usdt_pairs = []
            for symbol, ticker in tickers.items():
                if symbol.endswith('USDT') or symbol.endswith('USDT:USDT'):
                    quote_volume = ticker.get('quoteVolume', 0)
                    if quote_volume is not None:
                        usdt_pairs.append((symbol, quote_volume))
            
            # Sort by volume descending
            usdt_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # Extract top N symbols
            top_symbols = [pair[0] for pair in usdt_pairs[:MEMECOIN_V2_LIMIT]]
            
            # Ensure our CORE_PAIRS are included
            # BingX might not have all CORE_PAIRS, so we filter them through validate_symbol later if needed
            final_symbols = list(set(CORE_PAIRS + top_symbols))
            return final_symbols
            
        except Exception as e:
            print(f"Error fetching top pairs: {e}")
            return CORE_PAIRS

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """Fetch OHLCV historical data and return as a Pandas DataFrame."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Convert types to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            return df
            
        except Exception as e:
            print(f"[BingX] Error fetching OHLCV for {symbol} on {timeframe}: {e}")
            return pd.DataFrame() # Return empty df on error

    async def fetch_historical_data(self, symbol: str, timeframe: str = '1w') -> pd.DataFrame:
        """
        Fetches the maximum available historical data for '1w' (weekly) timeframe
        """
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, since=0, limit=1000)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            return df
        except Exception as e:
            return pd.DataFrame()

    async def create_market_order_with_sl_tp(self, symbol: str, side: str, amount: float, stop_loss: float, take_profit: float):
        """
        Create a market order (LONG/SHORT) on BingX futures with explicit sl and tp.
        `side` should be 'buy' or 'sell'.
        Handles Hedge mode by passing 'positionSide'.
        """
        try:
            position_side = 'LONG' if side.lower() == 'buy' else 'SHORT'
            
            # BingX CCXT expects stopLoss and takeProfit in the params dictionary
            params = {
                'positionSide': position_side,
                'stopLoss': {
                    'triggerPrice': stop_loss,
                    'type': 'STOP_MARKET'
                },
                'takeProfit': {
                    'triggerPrice': take_profit,
                    'type': 'TAKE_PROFIT_MARKET'
                }
            }
            # BingX can require positionMode = 'one-way' or 'hedge', standard parameter handling:
            order = await self.exchange.create_market_order(symbol, side, amount, None, params)
            print(f"[BingX] Order executed securely: {order}")
            return order
        except Exception as e:
            print(f"[BingX] Error creating order for {symbol}: {e}")
            return None
