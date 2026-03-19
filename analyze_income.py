import asyncio
import ccxt.async_support as ccxt
from core.config import BINGX_API_KEY, BINGX_API_SECRET
from collections import defaultdict

async def analyze_ledger():
    exchange = ccxt.bingx({
        'apiKey': BINGX_API_KEY,
        'secret': BINGX_API_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })
    
    try:
        print("Получение истории доходов (Income) с BingX...")
        
        # Получаем данные о балансе и доходах
        # В CCXT можно попробовать fetch_ledger или внутренний endpoint
        try:
            res = await exchange.swapV2PrivateGetUserIncome({"limit": 500})
            if isinstance(res, dict) and 'data' in res:
                incomes = res['data']
                print(f"Успешно получено {len(incomes)} записей!")
                
                total_pnl = 0.0
                symbol_pnl = defaultdict(float)
                
                win_count = 0
                loss_count = 0
                fee_total = 0.0
                
                for item in incomes:
                    # BingX Income types: 
                    # REALIZED_PNL, FUNDING_FEE, TRADING_FEE, etc.
                    inc_type = item.get('incomeType', '')
                    asset = item.get('asset', 'USDT')
                    amount = float(item.get('income', 0))
                    sym = item.get('symbol', 'UNKNOWN')
                    
                    if inc_type == 'REALIZED_PNL':
                        total_pnl += amount
                        symbol_pnl[sym] += amount
                        if amount > 0: win_count += 1
                        elif amount < 0: loss_count += 1
                    elif inc_type == 'TRADING_FEE':
                        fee_total += amount
                        total_pnl += amount # Комиссии обычно отрицательные
                        symbol_pnl[sym] += amount
                        
                print("\n=== 📊 ОТЧЕТ ПО ТОРГОВЛЕ BINGX (По данным баланса) ===")
                print(f"Прибыльных сделок (Realized PnL > 0): {win_count}")
                print(f"Убыточных сделок (Realized PnL < 0): {loss_count}")
                print(f"Уплачено комиссий (Trading Fees): {fee_total:.4f} USDT")
                print("-" * 40)
                print(f"💵 Общий чистый PnL (с учетом комиссий): {total_pnl:.4f} USDT")
                print("-" * 40)
                
                sorted_coins = sorted(symbol_pnl.items(), key=lambda x: x[1], reverse=True)
                print("Топ монеты по плюсу:")
                for sym, pnl in sorted_coins[:3]:
                    if pnl > 0: print(f"  {sym}: +{pnl:.4f} USDT")
                
                print("\nТоп монеты по минусу:")
                for sym, pnl in sorted_coins[-3:]:
                    if pnl < 0: print(f"  {sym}: {pnl:.4f} USDT")
                
            else:
                print("Ответ API имеет неожиданный формат:", res)

        except Exception as api_e:
            print("Не удалось вызвать PrivateGetUserIncome:", api_e)
            
    except Exception as e:
        print(f"Общая ошибка: {e}")
        
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(analyze_ledger())
