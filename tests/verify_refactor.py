import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.config import BINGX_FALSE_BREAKOUT_MARGIN, BINGX_LEVERAGE, TARGET_COINS

def test_margin():
    print(f"Target Coins: {TARGET_COINS}")
    print(f"Margin: {BINGX_FALSE_BREAKOUT_MARGIN}")
    print(f"Leverage: {BINGX_LEVERAGE}")
    
    entry_price = 50000.0 # Example BTC price
    position_coin_size = (BINGX_FALSE_BREAKOUT_MARGIN * BINGX_LEVERAGE) / entry_price
    total_value = position_coin_size * entry_price
    
    print(f"For entry {entry_price}:")
    print(f"Position size (coin): {position_coin_size}")
    print(f"Total position value: {total_value} USDT")
    
    expected_value = 11.0 * 15.0 # Margin * Leverage
    assert abs(total_value - expected_value) < 0.0001
    print("✅ Margin calculation verified!")

if __name__ == "__main__":
    test_margin()
