import pandas as pd
from .models import CoinProfile, Regime

class MomentumEngine:
    """
    Context-aware RSI Engine. Interprets RSI differently for Trending vs Ranging environments.
    It adapts to Top-50 high-beta altcoins dynamically via the CoinProfile thresholds.
    """
    def analyze_momentum(self, df: pd.DataFrame, profile: CoinProfile, regime: Regime) -> dict:
        if 'rsi' not in df.columns:
            return {"status": "unknown", "divergence": "none"}
            
        rsi = df['rsi'].iloc[-1]
        status = "neutral"
        
        # Adaptive Context Thresholding
        if regime in [Regime.UPTREND, Regime.EXPANSION]:
            if rsi < profile.rsi_os_trend:
                status = "oversold_in_uptrend (hidden bullish)"
            elif rsi > profile.rsi_ob_trend:
                status = "overbought"
        elif regime == Regime.DOWNTREND:
            if rsi > profile.rsi_ob_trend:
                status = "overbought_in_downtrend (hidden bearish)"
            elif rsi < profile.rsi_os_trend:
                status = "oversold"
        else: # RANGE/COMPRESSION
            if rsi < profile.rsi_os_range:
                status = "oversold_range"
            elif rsi > profile.rsi_ob_range:
                status = "overbought_range"
                
        # Basic Divergence Logic Placeholder 
        # Compares basic trailing slopes to find hidden vs regular divergences
        divergence = "none"
        if len(df) > 10:
            price_trend = df['close'].iloc[-1] - df['close'].iloc[-10]
            rsi_trend = df['rsi'].iloc[-1] - df['rsi'].iloc[-10]
            
            if price_trend < 0 and rsi_trend > 0 and rsi < 40:
                divergence = "bullish_divergence"
            elif price_trend > 0 and rsi_trend < 0 and rsi > 60:
                divergence = "bearish_divergence"

        return {
            "current_rsi": round(rsi, 2),
            "status": status,
            "divergence": divergence
        }
