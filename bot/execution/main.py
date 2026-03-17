import pandas as pd
import numpy as np
import statsmodels.api as sm
import json
import os

from pair import Pair
from api import APIClient
from strategy import Strategy
from data_handler import DataHandler

class StrategyRunner:
    def __init__(self, config_path=None):
        self.api = APIClient()
        self.strategy = Strategy()
        self.data_handler = DataHandler()
        self.precisions = {}
        self._init_precisions()
        
        if config_path:
            self.load_config(config_path)
        else:
            self.pairs = []
            self.entry_z_score = 1.5
            self.exit_z_score = 0.5
            self.stop_loss_pct = 0.15
            self.cooldown_hrs = 120

    def load_config(self, path):
        """Load strategy parameters and pairs from a JSON config file."""
        if not os.path.exists(path):
            print(f"Config file {path} not found!")
            return

        with open(path, 'r') as f:
            config = json.load(f)

        params = config.get("strategy_parameters", {})
        self.entry_z_score = params.get("z_entry_threshold", 1.5)
        self.exit_z_score = params.get("z_exit_threshold", 0.5)
        self.stop_loss_pct = params.get("stop_loss_pct", 0.15)
        self.cooldown_hrs = params.get("cooldown_hours", 120)

        self.pairs = []
        for p in config.get("trading_pairs", []):
            pair_obj = Pair(
                coin_a=p["coin_a"], 
                coin_b=p["coin_b"], 
                allocated_capital=p.get("allocated_capital", 0),
                window_size=p["window_size"]
            )
            self.pairs.append(pair_obj)
        
        print(f"Loaded config from {path}: {len(self.pairs)} pairs found.")

    def _init_precisions(self):
        """Fetch and store Price/Amount precision for all pairs from Roostoo."""
        info = self.api.get_exchange_info()
        if info and info.get("IsRunning"):
            trade_pairs = info.get("TradePairs", {})
            for pair_name, details in trade_pairs.items():
                self.precisions[pair_name] = {
                    "price": details.get("PricePrecision", 8),
                    "amount": details.get("AmountPrecision", 8)
                }
            print(f"Initialized precisions for {len(self.precisions)} coins.")
        else:
            print("Warning: Failed to initialize precisions from Roostoo API.")

    def round_to_precision(self, value, precision):
        """Round a value to a specified number of decimal places."""
        if value is None:
            return None
        return round(float(value), precision)

    def get_current_ask(self, coin):
        """Fetch the current minimum ask price for a coin from Roostoo."""
        ticker = self.api.get_ticker(coin)
        if ticker and ticker.get("Success"):
            pair_name = f"{coin}/USD"
            data = ticker.get("Data", {}).get(pair_name, {})
            return data.get("MinAsk")
        return None

    def buy(self, pair: Pair, coin, quantity):
        """Place a limit buy order for a coin within a pair at the current ask price."""
        price = self.get_current_ask(coin)
        if price is None:
            print(f"[{pair}] Failed to fetch ask price for {coin}, skipping BUY.")
            return False

        pair_name = f"{coin}/USD"
        precision = self.precisions.get(pair_name, {"amount": 8, "price": 8})
        
        rounded_qty = self.round_to_precision(quantity, precision["amount"])
        rounded_price = self.round_to_precision(price, precision["price"])
        
        print(f"[{pair}] Executing LIMIT BUY for {coin}, quantity={rounded_qty}, price={rounded_price}")
        res = self.api.place_order(coin, "BUY", rounded_qty, price=rounded_price, order_type="LIMIT")
        if res and res.get("Success"):
            entry_price = res["OrderDetail"].get("Price")
            pair.set_position(coin, entry_price)
            return True
        return False

    def sell(self, pair: Pair, coin, quantity):
        """Place a limit sell order for a coin within a pair at the current ask price."""
        price = self.get_current_ask(coin)
        if price is None:
            print(f"[{pair}] Failed to fetch ask price for {coin}, skipping SELL.")
            return False

        pair_name = f"{coin}/USD"
        precision = self.precisions.get(pair_name, {"amount": 8, "price": 8})
        
        rounded_qty = self.round_to_precision(quantity, precision["amount"])
        rounded_price = self.round_to_precision(price, precision["price"])
        
        print(f"[{pair}] Executing LIMIT SELL for {coin}, quantity={rounded_qty}, price={rounded_price}")
        res = self.api.place_order(coin, "SELL", rounded_qty, price=rounded_price, order_type="LIMIT")
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
        
        # Turn data into series and calculate log prices
        close_a = a_data["close"]
        close_b = b_data["close"]
        
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

    def run(self):
        """
        Iterate over all pairs and run handle_data.
        """
        for pair in self.pairs:
            # Update latest data for both coins in the pair
            self.data_handler.update_latest_data(pair.coin_a)
            self.data_handler.update_latest_data(pair.coin_b)
            
            a_data = self.data_handler.get_data(pair.coin_a)
            b_data = self.data_handler.get_data(pair.coin_b)
            
            if not a_data.empty and not b_data.empty:
                self.handle_data(pair, a_data, b_data)

if __name__ == "__main__":
    config_file = os.path.join(os.path.dirname(__file__), "../config/config.json")
    runner = StrategyRunner(config_path=config_file)
    runner.run()