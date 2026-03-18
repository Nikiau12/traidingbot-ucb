import pandas as pd
from .models import (
    CoinProfile, ContextScore, SignalType, Regime, MarketPhase,
    MacroBias, ActiveBias, SetupType, ConfirmationState, TriggerState, MTFVerdict
)
from .coin_config import get_coin_profile
from .regime_classifier import RegimeClassifier
from .structure_engine import StructureEngine
from .momentum_rsi import MomentumEngine
from .confidence_scorer import ConfidenceScorer
from .mtf_fusion import MTFFusionEngine

__all__ = [
    'SmartContextEngine',
    'MTFFusionEngine',
    'CoinProfile',
    'ContextScore',
    'SignalType',
    'Regime',
    'MarketPhase',
    'MacroBias',
    'ActiveBias',
    'SetupType',
    'ConfirmationState',
    'TriggerState',
    'MTFVerdict'
]

class SmartContextEngine:
    """
    The central orchestration tier for Advanced V9 Context Engine.
    Exposes a unified analytical facade to grading market phases and raw signals.
    """
    def __init__(self):
        self.regime_classifier = RegimeClassifier()
        self.structure_engine = StructureEngine()
        self.momentum_engine = MomentumEngine()
        self.scorer = ConfidenceScorer()

    def add_context_indicators(self, df: pd.DataFrame):
        """
        Natively calculates the required context indicators (EMA, RSI, ATR).
        Modifies the DataFrame in place.
        """
        if len(df) < 14:
            return
            
        # EMAs
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # ATR (14)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        
        # RSI (14) using Wilder's Smoothing
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

    def analyze_context(self, df: pd.DataFrame, symbol: str, raw_setup_type: str) -> ContextScore:
        # Load unique constraints for top-50 Altcoins vs Majors
        profile = get_coin_profile(symbol)
        
        # Ensure indicators exist
        if 'rsi' not in df.columns:
            self.add_context_indicators(df)
        
        # Determine Market Regime Architecture (Is it an Uptrend, Downtrend, or noisy range?)
        regime = self.regime_classifier.classify(df)
        
        # Wave/Swing Structure Component
        phase = self.structure_engine.identify_phase(df, regime)
        
        # Context-Aware RSI Engine
        momentum = self.momentum_engine.analyze_momentum(df, profile, regime)
        
        # Synthesize into an Explainable Decision / Quality Score
        score = self.scorer.score_setup(raw_setup_type, regime, phase, momentum)
        
        return score
