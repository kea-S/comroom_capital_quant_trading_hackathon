import pandas as pd
import numpy as np
import statsmodels.api as sm

from pair import Pair
from api import APIClient
from strategy.strategy import Strategy

class StrategyRunner:
    def __init__(self, pairs, entry_z_score, exit_z_score, stop_loss_pct, cooldown_hrs):
        self.pairs = pairs
        self.entry_z_score = entry_z_score
        self.exit_z_score = exit_z_score
        self.stop_loss_pct = stop_loss_pct
        self.cooldown_hrs = cooldown_hrs
        self.api = APIClient()
        self.strategy = Strategy()

    def buy(self, pair: Pair, coin, quantity):
        """Place a buy order for a coin within a pair."""
        print(f"[{pair}] Executing BUY for {coin}, quantity={quantity}")
        res = self.api.place_order(coin, "BUY", quantity)
        if res and res.get("Success"):
            entry_price = res["OrderDetail"].get("Price")
            pair.set_position(coin, entry_price)
            return True
        return False

    def sell(self, pair: Pair, coin, quantity):
        """Place a sell order for a coin within a pair."""
        print(f"[{pair}] Executing SELL for {coin}, quantity={quantity}")
        res = self.api.place_order(coin, "SELL", quantity)
        if res and res.get("Success"):
            pair.reset_position()
            return True
        return False

    def handle_data(self, pair: Pair, a_data, b_data):
        """
        For a given pair, execute strategy logic to either buy or sell.
        Executed every hour.
        """
        if pair.is_cooldown():
            print(f"{pair} is on cooldown: {pair.cooldown}")
            pair.update_cooldown()
            return
        
        coin_a = pair.coin_a
        coin_b = pair.coin_b
        window_size = pair.window_size
        
        # Data doesn't have enough values
        if len(a_data) < window_size or len(b_data) < window_size:
            print(f"Data for {pair} doesn't have enough candles! (required: {window_size})")
            return
        
        # Turn data into dataframe and calculate log prices
        close_a = pd.Series([d['close'] for d in a_data]).astype(float)
        close_b = pd.Series([d['close'] for d in b_data]).astype(float)
        
        log_a = np.log(close_a).tail(window_size)
        log_b = np.log(close_b).tail(window_size)

        z_score = self.strategy.get_z_score(log_a, log_b)
        
        current_price_a = float(close_a.iloc[-1])
        current_price_b = float(close_b.iloc[-1])

        # Entry / exit logic based on z_score
        position_ticker = pair.get_position_ticker()
        position_entry_price = pair.get_position_entry_price()
        
        if position_ticker is None:
            if z_score < -self.entry_z_score:
                qty = pair.allocated_capital / current_price_a
                self.buy(pair, coin_a, qty)
            elif z_score > self.entry_z_score:
                qty = pair.allocated_capital / current_price_b
                self.buy(pair, coin_b, qty)
        
        elif position_ticker == coin_a:
            # Stop loss logic
            unrealized_return = (current_price_a - position_entry_price) / position_entry_price
            if unrealized_return <= -self.stop_loss_pct:
                print(f"[{pair}] STOP LOSS triggered for {coin_a}")
                # Use current price for sell qty approximation or fixed capital
                if self.sell(pair, coin_a, pair.allocated_capital / position_entry_price):
                    pair.set_cooldown(self.cooldown_hrs)
            elif z_score >= -self.exit_z_score:
                self.sell(pair, coin_a, pair.allocated_capital / position_entry_price)

        elif position_ticker == coin_b:
            # Stop loss logic
            unrealized_return = (current_price_b - position_entry_price) / position_entry_price
            if unrealized_return <= -self.stop_loss_pct:
                print(f"[{pair}] STOP LOSS triggered for {coin_b}")
                if self.sell(pair, coin_b, pair.allocated_capital / position_entry_price):
                    pair.set_cooldown(self.cooldown_hrs)
            elif z_score <= self.exit_z_score:
                self.sell(pair, coin_b, pair.allocated_capital / position_entry_price)

    def run(self, data_provider):
        """
        Iterate over all pairs and run handle_data.
        data_provider should be a function or object that returns hourly data for a coin.
        """
        for pair in self.pairs:
            a_data = data_provider(pair.coin_a)
            b_data = data_provider(pair.coin_b)
            if a_data and b_data:
                self.handle_data(pair, a_data, b_data)