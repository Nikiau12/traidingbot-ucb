import unittest
import pandas as pd
import numpy as np
from smart_engine import SmartContextEngine, Regime, SignalType, MarketPhase

class TestSmartEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SmartContextEngine()

    def test_uptrend_long_confidence(self):
        # Mocking an obvious uptrend
        data = []
        for i in range(250):
            data.append({
                'close': i + 200, 'high': i + 205, 'low': i + 195,
                'ema_20': i + 150, 'ema_50': i + 100, 'ema_200': i + 50,
                'atr': 10, 'rsi': 55
            })
        df = pd.DataFrame(data)
        
        score = self.engine.analyze_context(df, "BTC/USDT", "LONG")
        self.assertEqual(score.regime, Regime.UPTREND)
        self.assertTrue(score.confidence > 50)  # Boosted by trend
        self.assertEqual(score.signal, SignalType.LONG)
        self.assertTrue(any("UPTREND" in msg for msg in score.reasons))

    def test_downtrend_long_discarded(self):
        # Mocking a severe downtrend
        data = []
        for i in range(250):
            data.append({
                'close': 500 - i, 'high': 505 - i, 'low': 495 - i,
                'ema_20': 550 - i, 'ema_50': 600 - i, 'ema_200': 650 - i,
                'atr': 10, 'rsi': 45
            })
        df = pd.DataFrame(data)
        
        score = self.engine.analyze_context(df, "ETH/USDT", "LONG")
        self.assertEqual(score.regime, Regime.DOWNTREND)
        
        # A LONG in a DOWNTREND should be severely punished by the scoring system.
        # Should drop below the 40 threshold and trigger NO_TRADE.
        self.assertTrue(score.confidence < 40)
        self.assertEqual(score.signal, SignalType.NO_TRADE)
        self.assertTrue(any("ИТОГ: Мусорный сетап" in msg for msg in score.reasons))

    def test_compression_no_trade(self):
        # Mocking a dead, ranging market with compressed volatility
        data = []
        for i in range(250):
            # Start with normal volatility (1.0). Only drop it for the very last 5 periods 
            # so the 50-period moving average stays high.
            current_atr = 1.0 if i < 245 else 0.4 
            data.append({
                'close': 100, 'high': 101, 'low': 99,
                'ema_20': 100, 'ema_50': 100, 'ema_200': 100,
                'atr': current_atr, 'rsi': 50
            })
        df = pd.DataFrame(data)
        
        score = self.engine.analyze_context(df, "DOGE/USDT", "LONG")
        self.assertEqual(score.regime, Regime.COMPRESSION)
        self.assertEqual(score.signal, SignalType.NO_TRADE)

if __name__ == '__main__':
    unittest.main()
