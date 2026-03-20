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

    def get_pois(self, df, current_price):
        from smartmoneyconcepts import smc
        fvg_data = smc.fvg(df)
        df_fvg = df.copy()
        for col in ['FVG', 'Top', 'Bottom', 'MitigatedIndex']:
            df_fvg[col] = fvg_data[col]

        pois = []
        active_bulls = df_fvg[(df_fvg['FVG'] == 1) & (df_fvg['MitigatedIndex'] == 0)]
        valid_bulls = active_bulls[active_bulls['Top'] < current_price]
        if not valid_bulls.empty:
            best = valid_bulls.loc[valid_bulls['Top'].idxmax()]
            pois.append({
                'direction': 'LONG',
                'entry': best['Top'],
                'sl': best['Bottom'] - (best['Top'] - best['Bottom']) * 0.1
            })

        active_bears = df_fvg[(df_fvg['FVG'] == -1) & (df_fvg['MitigatedIndex'] == 0)]
        valid_bears = active_bears[active_bears['Bottom'] > current_price]
        if not valid_bears.empty:
            best = valid_bears.loc[valid_bears['Bottom'].idxmin()]
            pois.append({
                'direction': 'SHORT',
                'entry': best['Bottom'],
                'sl': best['Top'] + (best['Top'] - best['Bottom']) * 0.1
            })
            
        return pois

    async def run_loop(self):
        print("🚀 [HTF Sniper] Запущен агрессивный двусторонний сканер (Лимитные Капканы)")
        await asyncio.sleep(5)
        
        while True:
            try:
                if not AUTO_TRADING_ENABLED:
                    await asyncio.sleep(self.interval)
                    continue

                for symbol in self.symbols:
                    try:
                        print(f"[HTF Sniper] Анализ {symbol}...")
                        current_price = await self.exchange.fetch_ticker_price(symbol)
                        
                        all_pois = []
                        
                        # 4H Analysis
                        df_4h = await self.exchange.fetch_ohlcv(symbol, "4h", limit=200)
                        pois_4h = self.get_pois(df_4h, current_price)
                        for p in pois_4h: p['tf'] = "4h"
                        all_pois.extend(pois_4h)
                        
                        # ETH 30m Analysis
                        if symbol == "ETH/USDT:USDT":
                            df_30m = await self.exchange.fetch_ohlcv(symbol, "30m", limit=200)
                            pois_30m = self.get_pois(df_30m, current_price)
                            for p in pois_30m: p['tf'] = "30m"
                            all_pois.extend(pois_30m)

                        # Отменяем старые LIMIT ордера по этой монете
                        open_orders = await self.exchange.exchange.fetch_open_orders(symbol)
                        limits = [o for o in open_orders if o['type'] == 'limit']
                        for o in limits:
                            await self.exchange.exchange.cancel_order(o['id'], symbol)

                        if not all_pois:
                            print(f"[HTF Sniper] Не найдено активных POI для {symbol}.")
                            continue

                        # Расставляем новые капканы
                        alert_messages = []
                        for poi in all_pois:
                            direction = poi['direction']
                            tf = poi['tf']
                            entry_price = poi['entry']
                            stop_loss = float(poi['sl'])
                            
                            if entry_price == stop_loss: continue
                                
                            distance_to_sl = abs(entry_price - stop_loss)
                            if distance_to_sl / entry_price < 0.005: # Слишком узкий стоп (менее 0.5% движения)
                                if direction == "LONG": stop_loss = entry_price * 0.99
                                else: stop_loss = entry_price * 1.01
                                distance_to_sl = abs(entry_price - stop_loss)
                                
                            tp_price = entry_price + (distance_to_sl * self.tp_ratio) if direction == "LONG" else entry_price - (distance_to_sl * self.tp_ratio)

                            position_coin_size = (self.risk_amount * BINGX_LEVERAGE) / entry_price
                            side = 'buy' if direction == "LONG" else 'sell'
                            
                            order = await self.exchange.create_limit_order_with_sl_tp(
                                symbol=symbol, side=side, amount=position_coin_size, 
                                price=entry_price, stop_loss=stop_loss, take_profit=tp_price
                            )
                            
                            if order:
                                alert_messages.append(
                                    f"• <b>{tf}</b> {'🟢 LONG' if direction == 'LONG' else '🔴 SHORT'}: Вход <b>{entry_price:.4f}</b> (SL: {stop_loss:.4f}, TP: {tp_price:.4f})"
                                )

                        if alert_messages:
                            msg = (f"🎯 <b>[HTF Снайпер - Капканы Расставлены]</b> 🎯\n\n"
                                   f"Монета: <b>{symbol}</b>\n"
                                   f"Контртренд разрешен (Обе стороны).\n\n" + 
                                   "\n".join(alert_messages))
                            await notifier.send_message(msg)

                    except Exception as e:
                        print(f"Ошибка в сканере HTF {symbol}: {e}")
                        
            except Exception as e:
                print(f"Критическая ошибка HTF цикла: {e}")
                
            print(f"[HTF Sniper] Цикл завершен. Ожидание {self.interval // 60} минут...")
            await asyncio.sleep(self.interval)
