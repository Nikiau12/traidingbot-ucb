import pandas as pd
from smartmoneyconcepts.smc import smc

class SMCAnalyzer:
    def __init__(self, lookback_period=200):
        self.lookback = lookback_period

    def analyze_tf(self, df: pd.DataFrame) -> dict:
        """
        Runs SMC calculations on a single timeframe DataFrame.
        Returns a dictionary with important levels and structures.
        """
        if len(df) < 50:
            return {}

        results = {}
        
        # We need Series of format exactly as expected by SMC library (OHLCV)
        # Note: smartmoneyconcepts natively expects pandas DataFrame with ohlcv columns named strictly.
        # But we need to ensure the index is datetime or strings.
        # It's better to pass the df directly if we formatted the columns right.
        df_smc = df.copy()
        df_smc.set_index('timestamp', inplace=True)
        
        try:
            # Swing Highs / Lows must be computed first
            swing_highs = smc.swing_highs_lows(df_smc)

            # Fair Value Gaps (FVG)
            fvg = smc.fvg(df_smc)
            # Find the most recent active FVG
            recent_fvgs = fvg[fvg['FVG'] != 0].tail(3)
            results['fvg'] = recent_fvgs.to_dict('records')
            
            # Market Structure (BOS, CHoCH)
            # bos_choch requires swing_highs_lows as the second argument
            bos_choch = smc.bos_choch(df_smc, swing_highs)
            recent_structure = bos_choch[(bos_choch['BOS'] != 0) | (bos_choch['CHOCH'] != 0)].tail(3)
            results['structure'] = recent_structure.to_dict('records')
            
            # Order Blocks
            # ob also typically requires swing_highs_lows
            ob = smc.ob(df_smc, swing_highs)
            recent_obs = ob[ob['OB'] != 0].tail(3)
            results['order_blocks'] = recent_obs.to_dict('records')
            
            # Liquidity
            liquidity = smc.liquidity(df_smc, swing_highs)
            recent_liq = liquidity[liquidity['Liquidity'] != 0].tail(3)
            results['liquidity'] = recent_liq.to_dict('records')
            
        except Exception as e:
            print(f"SMC analysis error: {e}")
            
        return results

    def find_setup(self, smc_results) -> dict:
        """
        Determines Entry, Stop Loss, and Take Profit based on the SMC results.
        Looks for a recent Market Structure break (CHoCH or BOS) aligned with an FVG or Order Block.
        Returns a setup dict or None.
        """
        if not smc_results or 'structure' not in smc_results or 'fvg' not in smc_results:
            return None

        recent_structure = smc_results['structure']
        recent_fvgs = smc_results['fvg']

        if not recent_structure or not recent_fvgs:
            return None

        # Sort structures by index (timestamp) descending to get the latest
        recent_structure.sort(key=lambda x: x['Level'], reverse=True)
        latest_structure = recent_structure[-1] # This gets the last record in time if sorted correctly, actually let's just take the last element built

        # Check for Bullish CHoCH or BOS
        if latest_structure['CHOCH'] == 1 or latest_structure['BOS'] == 1:
            # We are looking for a LONG setup
            # Find a bullish FVG (FVG == 1) below the current price or near the break
            bullish_fvgs = [fvg for fvg in recent_fvgs if fvg['FVG'] == 1]
            if bullish_fvgs:
                target_fvg = bullish_fvgs[-1]
                entry_price = target_fvg['Top'] # Enter at the top of the FVG
                
                # Stop loss below the bottom of the FVG or recent Swing Low
                # For safety, let's put SL below the FVG bottom with a small buffer (0.5%)
                stop_loss = target_fvg['Bottom'] * 0.995
                
                # Take profit at 1:2 Risk-Reward
                risk = entry_price - stop_loss
                take_profit = entry_price + (risk * 2.0)

                if risk > 0:
                    return {
                        'type': 'LONG',
                        'entry': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'rr': 2.0,
                        'reason': 'Bullish CHoCH/BOS + FVG'
                    }

        # Check for Bearish CHoCH or BOS
        elif latest_structure['CHOCH'] == -1 or latest_structure['BOS'] == -1:
            # We are looking for a SHORT setup
            bearish_fvgs = [fvg for fvg in recent_fvgs if fvg['FVG'] == -1]
            if bearish_fvgs:
                target_fvg = bearish_fvgs[-1]
                entry_price = target_fvg['Bottom'] # Enter at the bottom of the bearish FVG
                
                # Stop loss above the top of the FVG
                stop_loss = target_fvg['Top'] * 1.005
                
                # Take profit at 1:2 Risk-Reward
                risk = stop_loss - entry_price
                take_profit = entry_price - (risk * 2.0)

                if risk > 0:
                    return {
                        'type': 'SHORT',
                        'entry': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'rr': 2.0,
                        'reason': 'Bearish CHoCH/BOS + FVG'
                    }

        return None
