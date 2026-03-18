from typing import Dict, Any
from .models import Regime, MarketPhase, SignalType, ContextScore

class ConfidenceScorer:
    """
    Synthesizes Market Regime, Structure Phase, and Momentum into a comprehensive 1-100 score.
    Makes the crucial decision to downgrade noisy ranges to NO_TRADE.
    """
    def score_setup(self, setup_type: str, regime: Regime, phase: MarketPhase, momentum: Dict[str, Any]) -> ContextScore:
        score = 50
        reasons = []
        signal_type = SignalType.NO_TRADE
        
        if setup_type.upper() == "LONG":
            signal_type = SignalType.LONG
            
            # Regime Context
            if regime in [Regime.UPTREND, Regime.EXPANSION]:
                score += 20
                reasons.append("HTF Контекст: Глобальный UPTREND. Отличная поддержка тренда.")
            elif regime == Regime.RANGE:
                score -= 10
                reasons.append("Рынок в боковике/консолидации. Направление не ясно.")
            else:
                score -= 30
                reasons.append("Опасно: Попытка взять ЛОНГ против медвежьего HTF-тренда.")
                
            # Structure Context
            if phase == MarketPhase.CORRECTION:
                score += 15
                reasons.append("Структура: Вход на локальном откате. Идеальное соотношение Risk/Reward.")
            elif phase == MarketPhase.IMPULSE:
                score -= 10
                reasons.append("Внимание: Рынок уже в фазе роста. Высокий риск поймать вершину (FOMO).")
                
            # Momentum Context
            if "hidden bullish" in momentum['status']:
                score += 15
                reasons.append("Моментум: RSI разгрузился, но тренд сохранен (Hidden Bullish Divergence).")
            elif "overbought" in momentum['status']:
                score -= 15
                reasons.append("Моментум: Инструмент перегрет. Возможна скорая коррекция.")
                
        elif setup_type.upper() == "SHORT":
            signal_type = SignalType.SHORT
            
            if regime == Regime.DOWNTREND:
                score += 20
                reasons.append("HTF Контекст: Глобальный DOWNTREND.")
            elif regime == Regime.UPTREND:
                score -= 30
                reasons.append("Опасно: Шортить бычий рынок — плохая идея.")
                
            if phase == MarketPhase.CORRECTION:
                score += 15
                reasons.append("Структура: Отличный вход на бычьем мини-отскоке (Lower High).")
            elif phase == MarketPhase.IMPULSE:
                score -= 10
                reasons.append("Внимание: Падение уже идет. Риск зайти на минимумах.")
                
        # Cap score
        score = max(0, min(100, score))
        
        # Override to NO TRADE if score is terrible
        if score < 40 or regime == Regime.COMPRESSION:
            signal_type = SignalType.NO_TRADE
            reasons.append("🔴 ИТОГ: Мусорный сетап. Низкое качество или сжатие ликвидности. Сделка отменяется.")
        else:
            reasons.append(f"🟢 ИТОГ: Сигнал подтвержден контекстом. Confidence Score: {score}/100.")
            
        return ContextScore(
            signal=signal_type,
            confidence=score,
            regime=regime,
            phase=phase,
            reasons=reasons
        )
