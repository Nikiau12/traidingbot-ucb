import unittest
import pandas as pd
from unittest.mock import MagicMock
from smart_engine.models import (
    Regime, MarketPhase, MacroBias, ActiveBias, SetupType, 
    ConfirmationState, TriggerState, MTFVerdict
)
from smart_engine.mtf_fusion import MTFFusionEngine

class TestMTFFusionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = MTFFusionEngine()
        # Mock the classifiers so we don't need real DataFrames
        self.engine.regime_clf = MagicMock()
        self.engine.struct_eng = MagicMock()

    def test_bullish_continuation(self):
        # 1W Bullish, 1D Bullish, 4H Bullish + Impulse, 1H Bullish, 15m Bullish + Impulse
        self.engine.regime_clf.classify.side_effect = [
            Regime.UPTREND,  # 1w
            Regime.UPTREND,  # 1d
            Regime.UPTREND,  # 4h
            Regime.UPTREND,  # 1h
            Regime.UPTREND   # 15m
        ]
        self.engine.struct_eng.identify_phase.side_effect = [
            MarketPhase.CONTINUATION, # 1w
            MarketPhase.CONTINUATION, # 1d
            MarketPhase.IMPULSE,      # 4h
            MarketPhase.CONTINUATION, # 1h
            MarketPhase.IMPULSE       # 15m
        ]
        
        dfs = {tf: pd.DataFrame([1,2,3]) for tf in ['1w', '1d', '4h', '1h', '15m']}
        verdict = self.engine.analyze(dfs)
        
        self.assertEqual(verdict.macro_bias, MacroBias.BULLISH)
        self.assertEqual(verdict.active_bias, ActiveBias.BULLISH)
        self.assertEqual(verdict.setup_type, SetupType.BULLISH_CONTINUATION)
        self.assertEqual(verdict.confirmation_state, ConfirmationState.STRONG)
        self.assertEqual(verdict.trigger_state, TriggerState.VALID)
        self.assertTrue(verdict.confidence >= 70)
        self.assertEqual(len(verdict.risk_flags), 0)

    def test_countertrend_bounce(self):
        # 1W Bearish, 1D Bearish, 4H Bearish + Correction, 1H Range, 15m Range
        self.engine.regime_clf.classify.side_effect = [
            Regime.DOWNTREND,  # 1w
            Regime.DOWNTREND,  # 1d
            Regime.DOWNTREND,  # 4h
            Regime.RANGE,      # 1h
            Regime.RANGE       # 15m
        ]
        self.engine.struct_eng.identify_phase.side_effect = [
            MarketPhase.IMPULSE,
            MarketPhase.IMPULSE,
            MarketPhase.CORRECTION, # 4H correction inside downtrend (bounce)
            MarketPhase.UNKNOWN,
            MarketPhase.UNKNOWN
        ]
        
        dfs = {tf: pd.DataFrame([1,2,3]) for tf in ['1w', '1d', '4h', '1h', '15m']}
        verdict = self.engine.analyze(dfs)
        
        self.assertEqual(verdict.macro_bias, MacroBias.BEARISH)
        self.assertEqual(verdict.active_bias, ActiveBias.BEARISH)
        self.assertEqual(verdict.setup_type, SetupType.COUNTERTREND_BOUNCE)
        self.assertEqual(verdict.confirmation_state, ConfirmationState.WEAK)
        self.assertTrue(verdict.confidence < 50)
        self.assertIn("countertrend_context", verdict.risk_flags)

if __name__ == '__main__':
    unittest.main()
