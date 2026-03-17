import pandas as pd
import numpy as np
import statsmodels.api as sm

from pair import Pair
from strategy import Strategy

class StrategyRunner(self):
    def __init__(self, pairs, entry_z_score, exit_z_score, stop_loss_pct, cooldown_hrs):
        self.pairs = pairs
        self.entry_z_score = entry_z_score,
        self.exit_z_score = exit_z_score,
        self.stop_loss_pct = stop_loss_pct,
        self.cooldown_hrs = cooldown_hrs
        
    """
    For a given pair, execute strategy logic to either buy or sell
    Executed every hour

    a_data: raw binance data for coin A
    b_data: raw binance data for coin B
    """
    def handle_data(self, pair: Pair, a_data, b_data):
        if pair.is_cooldown():
            print(f"{pair} is on cooldown: {pair.cooldown}")
            return
        
        coin_a = pair.coin_a
        coin_b = pair.coin_b
        window_size = pair.window_size
        
        # Data doesn't have enough values
        if len(a_data) < window_size or len(b_data) < window_size:
            print(f"Data for {pair} doesn't have enough candles! (required: {window_size})")
            return
        
        # Turn data into dataframe
        raw_data = {}
        raw_data[coin_a] = a_data
        raw_data[coin_b] = b_data

        close_prices = pd.DataFrame({
            name: df.set_index("open_time")["close"]
            for name, df in raw_data.items() 
        })
        log_prices  = np.log(close_prices).dropna()

        # Get z-score based on strategy logic
        z_score = self.strategy.get_z_score(log_prices[coin_a], log_prices[coin_b])

        # Entry / exit logic based on z_score
        if pair.get_position() is None:
            if z_score < -self.entry_z_score:
                print(f"[{pair}] Z-Score is {z_score:.2f}. Signal: BUY {coin_a}")
                # TODO buy logic
                pair.set_position(coin_a)
            elif z_score > self.entry_z_score:
                print(f"[{pair}] Z-Score is {z_score:.2f}. Signal: BUY {coin_b}")
                # TODO buy logic
                pair.set_position(coin_b)
        
        # Exit logic
        else:
            if pair.get_position() == coin_a:
                # TODO: stop loss logic
                
                if z_score >= -self.exit_z_score:
                    print(f"[{pair}] Z-Score is {z_score:.2f}. Signal: SELL {coin_a}")
                    # TODO sell logic
                    pair.set_position(None)
            
            elif pair.get_position() == coin_b:
                # TODO: stop loss logic
                
                if z_score <= self.exit_z_score:
                    print(f"[{pair}] Z-Score is {z_score:.2f}. Signal: SELL {coin_b}")
                    # TODO sell logic
                    pair.set_position(None)
                
