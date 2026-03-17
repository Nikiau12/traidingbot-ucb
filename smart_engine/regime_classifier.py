import pandas as pd
from .models import Regime, MarketPhase

class RegimeClassifier:
    """
    Classifies the market regime using EMA context and ATR width.
    Determines if the market is trending, ranging, expanding, or compressing.
    """
    def classify(self, df: pd.DataFrame) -> Regime:
        if not all(col in df.columns for col in ['ema_20', 'ema_50', 'ema_200', 'atr']):
            return Regime.RANGE
            
        last = df.iloc[-1]
        
        # EMA Stacking
        uptrend = last['ema_20'] > last['ema_50'] > last['ema_200']
        downtrend = last['ema_20'] < last['ema_50'] < last['ema_200']
        
        # Price relation to fast EMA
        price_above = last['close'] > last['ema_20']
        price_below = last['close'] < last['ema_20']
        
        # Expansion/Compression check using recent ATR
        atr_sma = df['atr'].rolling(window=50).mean().iloc[-1]
        if last['atr'] < atr_sma * 0.6:
            return Regime.COMPRESSION
        if last['atr'] > atr_sma * 1.5:
            return Regime.EXPANSION
            
        if uptrend and price_above:
            return Regime.UPTREND
        elif downtrend and price_below:
            return Regime.DOWNTREND
            
        return Regime.RANGE
