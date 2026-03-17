import pandas as pd
from typing import Dict, Optional, List
from .models import (
    Regime, MarketPhase, MacroBias, ActiveBias, SetupType, 
    ConfirmationState, TriggerState, MTFVerdict
)
from .regime_classifier import RegimeClassifier
from .structure_engine import StructureEngine

class MTFFusionEngine:
    """
    Implements a strict hierarchical Multi-Timeframe decision pipeline.
    Hierarchy weight: 1W > 1D > 4H > 1H > 15m
    """
    def __init__(self):
        self.regime_clf = RegimeClassifier()
        self.struct_eng = StructureEngine()

    def _get_macro_bias(self, regime: Regime) -> MacroBias:
        if regime in [Regime.UPTREND, Regime.EXPANSION]:
            return MacroBias.BULLISH
        elif regime == Regime.DOWNTREND:
            return MacroBias.BEARISH
        elif regime == Regime.RANGE:
            return MacroBias.NEUTRAL
        else:
            return MacroBias.MIXED

    def _get_active_bias(self, regime: Regime) -> ActiveBias:
        if regime in [Regime.UPTREND, Regime.EXPANSION]:
            return ActiveBias.BULLISH
        elif regime == Regime.DOWNTREND:
            return ActiveBias.BEARISH
        elif regime == Regime.RANGE:
            return ActiveBias.NEUTRAL
        else:
            return ActiveBias.MIXED

    def _get_setup_type(self, regime: Regime, phase: MarketPhase, macro: MacroBias) -> SetupType:
        if regime == Regime.UPTREND:
            if phase == MarketPhase.CORRECTION:
                return SetupType.CONSTRUCTIVE_PULLBACK
            return SetupType.BULLISH_CONTINUATION
            
        elif regime == Regime.DOWNTREND:
            if phase == MarketPhase.CORRECTION:
                # If macro is bullish and we have a downtrend correction, it's a bounce.
                return SetupType.COUNTERTREND_BOUNCE
            return SetupType.BEARISH_CONTINUATION
            
        elif regime == Regime.COMPRESSION:
            return SetupType.BREAKOUT_CONTINUATION
            
        elif regime == Regime.RANGE:
            return SetupType.RANGE_MEAN_REVERSION
            
        return SetupType.MIXED_CONTEXT

    def _get_confirmation_state(self, h1_regime: Regime, h4_regime: Regime) -> ConfirmationState:
        if h1_regime == h4_regime and h1_regime not in [Regime.RANGE, Regime.COMPRESSION]:
            return ConfirmationState.STRONG
        elif h1_regime == h4_regime:
            return ConfirmationState.MEDIUM
        elif h1_regime in [Regime.RANGE, Regime.COMPRESSION]:
            return ConfirmationState.WEAK
        else:
            return ConfirmationState.CONFLICTING

    def _get_trigger_state(self, m15_regime: Regime, m15_phase: MarketPhase, h1_regime: Regime) -> TriggerState:
        if m15_regime == Regime.COMPRESSION:
            return TriggerState.READY
        elif m15_regime == h1_regime and m15_phase == MarketPhase.IMPULSE:
            return TriggerState.VALID
        elif m15_phase == MarketPhase.CORRECTION:
            return TriggerState.EARLY
        elif m15_regime == Regime.EXPANSION:
            return TriggerState.OVEREXTENDED
        elif m15_regime == Regime.RANGE:
            return TriggerState.NOISY
        return TriggerState.WEAK

    def _calculate_confidence_and_risks(
        self, 
        macro: MacroBias, 
        active: ActiveBias, 
        setup: SetupType,
        conf: ConfirmationState, 
        trigger: TriggerState
    ) -> tuple[int, List[str]]:
        score = 50
        risk_flags = []
        
        # 1. Evaluate 1D alignment with 1W
        if macro.name == active.name and macro != MacroBias.NEUTRAL:
            score += 20
        elif (macro == MacroBias.BULLISH and active == MacroBias.BEARISH) or (macro == MacroBias.BEARISH and active == MacroBias.BULLISH):
            score -= 20
            risk_flags.append("countertrend_to_macro")
        elif macro == MacroBias.NEUTRAL or active == ActiveBias.NEUTRAL:
            score -= 5
            risk_flags.append("neutral_or_mixed_macro_context")
            
        # 2. Evaluate 4H setup alignment
        if "CONTINUATION" in setup.name:
            # check if aligned with active bias
            if ("BULLISH" in setup.name and active == ActiveBias.BULLISH) or ("BEARISH" in setup.name and active == ActiveBias.BEARISH):
                score += 15
            else:
                score -= 10
                risk_flags.append("setup_conflicts_with_active_bias")
        elif setup == SetupType.CONSTRUCTIVE_PULLBACK:
            if active == ActiveBias.BULLISH:
                score += 15
            else:
                score -= 10
                risk_flags.append("pullback_in_bearish_context")
        elif setup == SetupType.COUNTERTREND_BOUNCE:
            score -= 15
            risk_flags.append("countertrend_context")
        elif setup == SetupType.RANGE_MEAN_REVERSION:
            score -= 5
            risk_flags.append("choppy_range_environment")
            
        # 3. Evaluate 1H Confirmation
        if conf == ConfirmationState.STRONG:
            score += 10
        elif conf == ConfirmationState.CONFLICTING:
            score -= 15
            risk_flags.append("conflicting_timeframes")
        elif conf in [ConfirmationState.WEAK, ConfirmationState.ABSENT]:
            score -= 10
            risk_flags.append("weak_confirmation")
            
        # 4. Evaluate 15m Trigger
        if trigger == TriggerState.OVEREXTENDED:
            score -= 10
            risk_flags.append("stretched_entry")
        elif trigger == TriggerState.EARLY:
            risk_flags.append("early_trigger_wait_for_confirmation")
            # Don't penalize too much for early
        elif trigger == TriggerState.NOISY:
            score -= 10
            risk_flags.append("noisy_structure")
        elif trigger in [TriggerState.READY, TriggerState.VALID]:
            score += 5
            
        # Cap score
        score = max(0, min(100, score))
        
        return score, risk_flags

    def analyze(self, dfs: Dict[str, pd.DataFrame]) -> MTFVerdict:
        """
        Receives dict of DataFrames: '1w', '1d', '4h', '1h', '15m'
        Outputs fused MTFVerdict.
        """
        # Calculate regimes and phases individually
        regimes = {}
        phases = {}
        
        for tf, df in dfs.items():
            if df is not None and not df.empty:
                regimes[tf] = self.regime_clf.classify(df)
                phases[tf] = self.struct_eng.identify_phase(df, regimes[tf])
            else:
                regimes[tf] = None
                phases[tf] = None
                
        # 1W - Macro
        macro_bias = self._get_macro_bias(regimes.get('1w')) if regimes.get('1w') else MacroBias.NEUTRAL
        
        # 1D - Active
        active_bias = self._get_active_bias(regimes.get('1d')) if regimes.get('1d') else ActiveBias.NEUTRAL
        
        # 4H - Setup
        setup_type = self._get_setup_type(regimes.get('4h'), phases.get('4h'), macro_bias) if regimes.get('4h') else SetupType.NO_TRADE
        
        # 1H - Confirmation
        h1_regime = regimes.get('1h')
        h4_regime = regimes.get('4h')
        conf_state = self._get_confirmation_state(h1_regime, h4_regime) if h1_regime and h4_regime else ConfirmationState.ABSENT
        
        # 15m - Trigger
        m15_regime = regimes.get('15m')
        m15_phase = phases.get('15m')
        trigger_state = self._get_trigger_state(m15_regime, m15_phase, h1_regime) if m15_regime and h1_regime else TriggerState.ABSENT
        
        confidence, risk_flags = self._calculate_confidence_and_risks(
            macro_bias, active_bias, setup_type, conf_state, trigger_state
        )
        
        # Final safety net
        if confidence < 35:
            setup_type = SetupType.NO_TRADE
            
        return MTFVerdict(
            macro_bias=macro_bias,
            active_bias=active_bias,
            setup_type=setup_type,
            confirmation_state=conf_state,
            trigger_state=trigger_state,
            confidence=confidence,
            risk_flags=risk_flags
        )
