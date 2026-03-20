import pandas as pd
import os
from datetime import datetime
from logger import logger

class PerformanceTracker:
    def __init__(self, data_dir="bot/logs"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        self.equity_file = os.path.join(self.data_dir, "equity_history.csv")
        self.trade_file = os.path.join(self.data_dir, "trade_history.csv")
        self.positions_file = os.path.join(self.data_dir, "current_positions.csv")

    def log_equity(self, total_value):
        """Append current total portfolio value to equity history."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df = pd.DataFrame([[timestamp, total_value]], columns=["timestamp", "total_value"])
        
        file_exists = os.path.isfile(self.equity_file)
        df.to_csv(self.equity_file, mode='a', index=False, header=not file_exists)
        logger.info(f"Logged equity: {total_value} at {timestamp}")

    def log_trade(self, pair, coin, side, price, quantity, z_score):
        """Append trade details to trade history."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df = pd.DataFrame([[timestamp, str(pair), coin, side, price, quantity, z_score]], 
                          columns=["timestamp", "pair", "coin", "side", "price", "quantity", "z_score"])
        
        file_exists = os.path.isfile(self.trade_file)
        df.to_csv(self.trade_file, mode='a', index=False, header=not file_exists)
        logger.info(f"Logged trade: {side} {quantity} {coin} for {pair} at {price} (z={z_score})")

    def update_current_positions(self, pairs):
        """Overwrite current positions file with latest state."""
        positions = []
        for pair in pairs:
            if pair.position:
                coin, entry_price = pair.position
                positions.append({
                    "pair": str(pair),
                    "coin": coin,
                    "entry_price": entry_price,
                    "allocated_capital": pair.allocated_capital
                })
        
        df = pd.DataFrame(positions)
        df.to_csv(self.positions_file, index=False)
        logger.info(f"Updated current positions: {len(positions)} active.")

