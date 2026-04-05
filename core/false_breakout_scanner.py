import asyncio
import json
import traceback
import pandas as pd
from datetime import datetime, timezone
from bingx.exchange_client_bingx import ExchangeClientBingX
from core.notifier import Notifier
from core.config import AUTO_TRADING_ENABLED, BINGX_FALSE_BREAKOUT_MARGIN, BINGX_LEVERAGE, TARGET_COINS
from core.smart_engine import SmartContextEngine

notifier = Notifier()

class FalseBreakoutScanner:
    def __init__(self, exchange: ExchangeClientBingX):
        self.exchange = exchange
        # Торгуем только монетами из TARGET_COINS (BTC, ETH, SOL)
        self.symbols = [f"{coin}/USDT:USDT" for coin in TARGET_COINS]
        self.interval = 300  # Проверка каждые 5 минут
        self.smart_engine = SmartContextEngine()
        
        # Кеш для хранения уровней (чтобы не пересчитывать каждый цикл, только раз в пару часов)
        self.levels_cache = {}

    def _get_pivot_levels(self, df: pd.DataFrame, window=5):
        """
        Ищет локальные максимумы (сопротивления) и минимумы (поддержки) 
        в окне N свечей до и после.
        """
        # Считаем разметку Swing High / Swing Low
        df['pivot_high'] = df['high'] == df['high'].rolling(window=2*window+1, center=True).max()
        df['pivot_low'] = df['low'] == df['low'].rolling(window=2*window+1, center=True).min()
        
        # Исключаем последние `window` свечей, так как они еще не подтверждены будущим
        valid_df = df.iloc[:-window]
        
        resistances = valid_df[valid_df['pivot_high']]['high'].dropna().tolist()
        supports = valid_df[valid_df['pivot_low']]['low'].dropna().tolist()
        
        return resistances, supports

    async def update_htf_levels(self, symbol: str):
        """ Обновляет значимые уровни ликвидности с графиков 4H и 1D """
        try:
            # 1. Загружаем 4H
            df_4h = await self.exchange.fetch_ohlcv(symbol, "4h", limit=150)
            res_4h, sup_4h = self._get_pivot_levels(df_4h, window=8) # 8 свечей = 32 часа
            
            # 2. Загружаем 1D
            df_1d = await self.exchange.fetch_ohlcv(symbol, "1d", limit=100)
            res_1d, sup_1d = self._get_pivot_levels(df_1d, window=5) # 5 свечей = 5 дней
            
            # Объединяем
            all_resistances = res_4h + res_1d
            all_supports = sup_4h + sup_1d
            
            # Добавим ATR(14) с Дневки для оценки "ширины" погрешности уровня
            self.smart_engine.add_context_indicators(df_1d)
            atr_1d = df_1d['atr'].iloc[-1]
            macro_trend = self.smart_engine.regime_classifier.classify(df_1d).name # UPTREND, DOWNTREND, RANGE
            
            return {
                "resistances": sorted(list(set(all_resistances))),
                "supports": sorted(list(set(all_supports))),
                "atr_1d": atr_1d,
                "macro_trend": macro_trend,
                "last_update": datetime.now(timezone.utc).timestamp()
            }
        except Exception as e:
            print(f"Ошибка при обновлении HTF уровней {symbol}: {e}")
            return None

    def find_false_breakout(self, symbol: str, df_15m: pd.DataFrame, htf_data: dict):
        """
        Анализирует последние свечи 15m на пробитие и возврат от уровней поддержки/сопротивления.
        """
        price_close = df_15m['close'].iloc[-1]
        price_close_prev = df_15m['close'].iloc[-2]
        
        resistances = htf_data['resistances']
        supports = htf_data['supports']
        atr_1d = htf_data['atr_1d']
        trend = htf_data['macro_trend']
        
        # Допуск закола (глубина) — не более 0.15 ATR от дневного хода!
        max_deviation = atr_1d * 0.15
        
        setup = None
        
        # 1. Поиск ЛОЖНОГО ПРОБОЯ ВВЕРХ (Повод для шорта)
        # Суть: Предыдущая 15m свеча (или текущая тенью) проколола Сопротивление, 
        # но цена закрытия текущей свечи вернулась обратно ПОД сопротивление.
        for r in resistances:
            # Находим свечи, которые участвовали в тесте уровня
            recent_high = df_15m['high'].iloc[-3:].max()
            
            # Условие:
            # 1. Цена заколола уровень, но не улетела дальше max_deviation
            # 2. Текущее закрытие ниже уровня (возврат)
            # 3. Предыдущее закрытие (или хай) было выше уровня
            
            if r <= recent_high <= (r + max_deviation) and price_close < r:
                # Проверяем, была ли цена закрытием выше (2-bar pattern) или только тенью (pinbar)
                breakout_type = "pin-bar"
                if price_close_prev > r:
                    breakout_type = "2-bar"
                
                # Запрещаем входить слишком далеко от уровня (Risk:Reward будет плохим)
                if abs(r - price_close) > (atr_1d * 0.25):
                    continue
                    
                confidence = 8 if trend in ["DOWNTREND", "RANGE"] else 5
                
                setup = {
                    "symbol": symbol,
                    "setup": "SHORT",
                    "confidence": confidence,
                    "reasoning": f"Формация ложного пробоя сопротивления {r}. Зашли за уровень и вернулись.",
                    "entry": price_close,
                    "stop": recent_high + (atr_1d * 0.02),
                    "target": price_close - atr_1d * 0.5, # Тейк минимум пол-ATR
                    "context": {
                        "trend": trend,
                        "level": r,
                        "level_type": "Resistance (HTF)",
                        "breakout_type": breakout_type
                    }
                }
                return setup

        # 2. Поиск ЛОЖНОГО ПРОБОЯ ВНИЗ (Повод для лонга)
        for s in supports:
            recent_low = df_15m['low'].iloc[-3:].min()
            
            if (s - max_deviation) <= recent_low <= s and price_close > s:
                breakout_type = "pin-bar"
                if price_close_prev < s:
                    breakout_type = "2-bar"
                    
                if abs(price_close - s) > (atr_1d * 0.25):
                    continue
                    
                confidence = 8 if trend in ["UPTREND", "RANGE"] else 5
                
                setup = {
                    "symbol": symbol,
                    "setup": "LONG",
                    "confidence": confidence,
                    "reasoning": f"Формация ложного срыва поддержки {s}. Сняли стопы и вернулись.",
                    "entry": price_close,
                    "stop": recent_low - (atr_1d * 0.02),
                    "target": price_close + atr_1d * 0.5,
                    "context": {
                        "trend": trend,
                        "level": s,
                        "level_type": "Support (HTF)",
                        "breakout_type": breakout_type
                    }
                }
                return setup

        return None

    async def run_loop(self):
        print("🕵️  [Sweep Scanner] Модуль поиска Ложных Пробоев (Ликвидность) запущен.")
        await asyncio.sleep(10) # Задержка запуска
        
        while True:
            try:
                for symbol in self.symbols:
                    now = datetime.now(timezone.utc).timestamp()
                    
                    # Обновляем HTF уровни раз в 2 часа
                    if symbol not in self.levels_cache or (now - self.levels_cache[symbol]['last_update']) > 7200:
                        print(f"🕵️  [Sweep Scanner] Обновление HTF-уровней ликвидности для {symbol}...")
                        htf_data = await self.update_htf_levels(symbol)
                        if htf_data:
                            self.levels_cache[symbol] = htf_data
                            
                    if symbol not in self.levels_cache:
                        continue
                        
                    # Сканируем рабочий фрейм 15m (наблюдаем за поведением вокруг уровней)
                    df_15m = await self.exchange.fetch_ohlcv(symbol, "15m", limit=10)
                    if df_15m.empty: continue
                    
                    setup = self.find_false_breakout(symbol, df_15m, self.levels_cache[symbol])
                    
                    if setup:
                        print(f"🚨 НАЙДЕН СЕТАП ЛОЖНОГО ПРОБОЯ: {symbol} -> {setup['setup']}")
                        
                        entry_price = setup['entry']
                        position_coin_size = (BINGX_FALSE_BREAKOUT_MARGIN * BINGX_LEVERAGE) / entry_price
                        side = 'buy' if setup['setup'] == "LONG" else 'sell'
                        
                        # Исполнение ордера
                        order_status = "ОЖИДАЕМ (Сигнальный Режим)"
                        if AUTO_TRADING_ENABLED:
                            order = await self.exchange.create_market_order_with_sl_tp(
                                symbol=symbol,
                                side=side,
                                amount=position_coin_size,
                                stop_loss=setup['stop'],
                                take_profit=setup['target']
                            )
                            if order:
                                order_status = "✅ ОРДЕР УСПЕШНО ОТКРЫТ"
                            else:
                                order_status = "❌ ОШИБКА ИСПОЛНЕНИЯ БИРЖЕЙ"
                        else:
                            order_status = "⏸️ АВТОТОРГОВЛЯ ВЫКЛЮЧЕНА"

                        message = (
                            f"🦊 <b>[LIQUIDITY SWEEP EXECUTED]</b> 🦊\n\n"
                            f"Монета: <b>{symbol}</b>\n"
                            f"Сетап: <b>{setup['setup']}</b> (Уверенность: {setup['confidence']}/10)\n"
                            f"Статус: <b>{order_status}</b>\n\n"
                            f"Обоснование: {setup['reasoning']}\n\n"
                            f"Вход (Market): <b>{setup['entry']:.4f}</b>\n"
                            f"Стоп (за тень): <b>{setup['stop']:.4f}</b>\n"
                            f"Цель: <b>{setup['target']:.4f}</b>\n\n"
                            f"<b>Контекст:</b>\n"
                            f"- Глобальный Тренд: {setup['context']['trend']}\n"
                            f"- Заколотый уровень: {setup['context']['level']:.4f}\n"
                            f"- Тип пробоя: {setup['context']['breakout_type']}\n"
                        )
                        await notifier.send_message(message)
                        
                        # Колдаун на пару часов, чтобы не спамить один и тот же уровень
                        self.levels_cache[symbol]['last_update'] = now + 7200 
                        
            except Exception as e:
                print(f"Ошибка в цикле FalseBreakoutScanner: {e}")
                traceback.print_exc()
                
            # Пауза между итерациями сканирования (5 мин)
            await asyncio.sleep(self.interval)
