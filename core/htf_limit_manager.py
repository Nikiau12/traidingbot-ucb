import asyncio
import time
from bingx.exchange_client_bingx import ExchangeClientBingX
from core.notifier import Notifier
from smartmoneyconcepts import smc
from core.config import AUTO_TRADING_ENABLED, BINGX_MARGIN_PER_ORDER, BINGX_LEVERAGE

notifier = Notifier()

class HTFLimitManager:
    def __init__(self, exchange: ExchangeClientBingX):
        self.exchange = exchange
        self.symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
        self.interval = 1800 # 30 минут
        self.risk_amount = BINGX_MARGIN_PER_ORDER
        self.tp_ratio = 3.0 # Risk:Reward 1:3

    async def get_macro_trend(self, symbol):
        df_1d = await self.exchange.fetch_ohlcv(symbol, "1d", limit=100)
        close = df_1d['close'].iloc[-1]
        sma20 = df_1d['close'].rolling(20).mean().iloc[-1]
        sma50 = df_1d['close'].rolling(50).mean().iloc[-1]
        if close > sma20 and sma20 > sma50:
            return "BULLISH"
        elif close < sma20 and sma20 < sma50:
            return "BEARISH"
        return "CHOPPY"

    async def run_loop(self):
        print("🚀 [HTF Sniper] Запущен фоновый сканер старших таймфреймов для BTC/ETH (Лимитные Свинг-ордера)")
        await asyncio.sleep(5) # Delay startup
        
        while True:
            try:
                if not AUTO_TRADING_ENABLED:
                    await asyncio.sleep(3600)
                    continue

                for symbol in self.symbols:
                    try:
                        print(f"[HTF Sniper] Анализ {symbol}...")
                        trend = await self.get_macro_trend(symbol)
                        if trend == "CHOPPY":
                            print(f"[HTF Sniper] {symbol} в распиле на 1D. Пропуск.")
                            continue

                        df_4h = await self.exchange.fetch_ohlcv(symbol, "4h", limit=200)
                        current_price = await self.exchange.fetch_ticker_price(symbol)
                        
                        fvg_data = smc.fvg(df_4h)
                        df_fvg = df_4h.copy()
                        for col in ['FVG', 'Top', 'Bottom', 'MitigatedIndex']:
                            df_fvg[col] = fvg_data[col]

                        poi = None
                        direction = ""

                        if trend == "BULLISH":
                            # Поиск Бычьих FVG
                            active_fvgs = df_fvg[(df_fvg['FVG'] == 1) & (df_fvg['MitigatedIndex'] == 0)]
                            valid = active_fvgs[active_fvgs['Top'] < current_price]
                            if not valid.empty:
                                best = valid.loc[valid['Top'].idxmax()]
                                poi = {
                                    'entry': best['Top'],
                                    'sl': best['Bottom'] - (best['Top'] - best['Bottom']) * 0.1 # Чуть ниже FVG
                                }
                            direction = "LONG"
                        elif trend == "BEARISH":
                            # Поиск Медвежьих FVG
                            active_fvgs = df_fvg[(df_fvg['FVG'] == -1) & (df_fvg['MitigatedIndex'] == 0)]
                            valid = active_fvgs[active_fvgs['Bottom'] > current_price]
                            if not valid.empty:
                                best = valid.loc[valid['Bottom'].idxmin()] # Ближайшее сопротивление
                                poi = {
                                    'entry': best['Bottom'],
                                    'sl': best['Top'] + (best['Top'] - best['Bottom']) * 0.1 # Чуть выше FVG
                                }
                            direction = "SHORT"

                        if not poi:
                            print(f"[HTF Sniper] Не найдено активных 4H POI для {symbol} по тренду {trend}.")
                            continue

                        entry_price = poi['entry']
                        stop_loss = float(poi['sl'])
                        
                        if entry_price == stop_loss:
                            continue
                            
                        distance_to_sl = abs(entry_price - stop_loss)
                        if distance_to_sl / entry_price < 0.005: # Слишком узкий стоп (менее 0.5% движения)
                            if direction == "LONG": stop_loss = entry_price * 0.99
                            else: stop_loss = entry_price * 1.01
                            distance_to_sl = abs(entry_price - stop_loss)
                            
                        tp_price = entry_price + (distance_to_sl * self.tp_ratio) if direction == "LONG" else entry_price - (distance_to_sl * self.tp_ratio)

                        # Обновление Ордеров!
                        # Отменяем старые LIMIT ордера по этой монете
                        open_orders = await self.exchange.exchange.fetch_open_orders(symbol)
                        limits = [o for o in open_orders if o['type'] == 'limit']
                        for o in limits:
                            await self.exchange.exchange.cancel_order(o['id'], symbol)

                        # Ставим новый ордер
                        position_coin_size = (self.risk_amount * BINGX_LEVERAGE) / entry_price
                        side = 'buy' if direction == "LONG" else 'sell'
                        
                        order = await self.exchange.create_limit_order_with_sl_tp(
                            symbol=symbol,
                            side=side,
                            amount=position_coin_size,
                            price=entry_price,
                            stop_loss=stop_loss,
                            take_profit=tp_price
                        )
                        
                        if order:
                            msg = (f"🎯 <b>[HTF Снайпер - Установка Капкана]</b> 🎯\n\n"
                                   f"Монета: <b>{symbol}</b> (4H Таймфрейм)\n"
                                   f"Макро Тренд (1D): {trend}\n"
                                   f"Направление: {'🟢 LONG' if direction == 'LONG' else '🔴 SHORT'}\n\n"
                                   f"⏳ <b>Отложенный Limit-Ордер:</b> {entry_price:.4f}\n"
                                   f"🛡 Stop-Loss (Ниже FVG): {stop_loss:.4f}\n"
                                   f"💰 Take-Profit (1:3): {tp_price:.4f}\n\n"
                                   f"Бот будет автоматически обновлять уровень ордера при смещении 4H структуры.")
                            await notifier.send_message(msg)

                    except Exception as e:
                        print(f"Ошибка в сканере HTF {symbol}: {e}")
                        
            except Exception as e:
                print(f"Критическая ошибка HTF цикла: {e}")
                
            print(f"[HTF Sniper] Цикл завершен. Ожидание {self.interval // 60} минут...")
            await asyncio.sleep(self.interval)
