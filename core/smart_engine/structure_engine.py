import pandas as pd
from .models import Regime, MarketPhase

class StructureEngine:
    """
    Analyzes price structure for trend continuation or exhaustion heuristics.
    Detects if the asset is in an impulsive, corrective, or exhaustion phase.
    """
    def __init__(self, swing_length: int = 5):
        self.swing_length = swing_length

    def identify_phase(self, df: pd.DataFrame, regime: Regime) -> MarketPhase:
        if len(df) < self.swing_length * 2:
            return MarketPhase.UNKNOWN
            
        last_close = df['close'].iloc[-1]
        rolling_max = df['high'].rolling(self.swing_length).max().iloc[-1]
        rolling_min = df['low'].rolling(self.swing_length).min().iloc[-1]
        
        # Distance from recent extremes
        dist_from_max = (rolling_max - last_close) / last_close
        dist_from_min = (last_close - rolling_min) / last_close
        
        if regime == Regime.UPTREND or regime == Regime.EXPANSION:
            if dist_from_max < 0.01:
                return MarketPhase.IMPULSE
            elif dist_from_max > 0.04:
                return MarketPhase.CORRECTION
            else:
                return MarketPhase.CONTINUATION
                
        elif regime == Regime.DOWNTREND:
            if dist_from_min < 0.01:
                return MarketPhase.IMPULSE
            elif dist_from_min > 0.04:
                return MarketPhase.CORRECTION
            else:
                return MarketPhase.CONTINUATION
                
        return MarketPhase.UNKNOWN
