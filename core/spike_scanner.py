import pandas as pd
from core.config import SPIKE_VOLUME_MULTIPLIER, SPIKE_PRICE_ATR_MULTIPLIER, SPIKE_MIN_PCT_CHANGE

class SpikeScanner:
    def __init__(self, atr_period=14, volume_period=20):
        self.atr_period = atr_period
        self.vol_period = volume_period

    def scan(self, df: pd.DataFrame) -> dict:
        """
        Scans a dataframe of a specific timeframe for volume and price spikes.
        Returns a dict {'is_spike': bool, 'type': 'price'/'volume'/'both', 'direction': 'up'/'down', 'info': str}
        """
        if len(df) < max(self.atr_period, self.vol_period) + 1:
            return None

        # Calculate True Range (TR)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # Calculate ATR (Simple Moving Average of TR for simplicity)
        atr = tr.rolling(window=self.atr_period).mean()

        # Calculate average volume
        avg_vol = df['volume'].rolling(window=self.vol_period).mean()

        # Get the latest completed candle (index -2 if the last one is still open, but usually fetch_ohlcv returning limited rows might have the last one active or closed depending on parameters)
        # Let's inspect the last row
        last_row = df.iloc[-1]
        prev_atr = atr.iloc[-2]
        prev_avg_vol = avg_vol.iloc[-2]

        is_price_spike = False
        is_vol_spike = False

        # Price spike condition: candle body > ATR * multiplier
        body_size = abs(last_row['close'] - last_row['open'])
        if body_size > (prev_atr * SPIKE_PRICE_ATR_MULTIPLIER):
            is_price_spike = True

        # Volume spike condition: volume > avg_vol * multiplier
        if last_row['volume'] > (prev_avg_vol * SPIKE_VOLUME_MULTIPLIER):
            is_vol_spike = True

        if is_price_spike or is_vol_spike:
            direction = 'up' if last_row['close'] > last_row['open'] else 'down'
            spike_type = 'both' if (is_price_spike and is_vol_spike) else ('price' if is_price_spike else 'volume')
            pct_change = abs((last_row['close'] - last_row['open']) / last_row['open'] * 100)
            
            if pct_change >= SPIKE_MIN_PCT_CHANGE:
                return {
                    'is_spike': True,
                    'type': spike_type,
                    'direction': direction,
                    'pct_change': pct_change,
                    'start_price': last_row['open'],
                    'current_price': last_row['close'],
                    'volume_ratio': last_row['volume'] / prev_avg_vol if prev_avg_vol > 0 else 0
                }
        
        return None
