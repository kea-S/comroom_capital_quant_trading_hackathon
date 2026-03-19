import time
import requests
import pandas as pd
import numpy as np
import os
import pickle

CACHE_DIR = "bot/data/klines_cache"

class DataHandler:
    """
    Handles fetching and caching candlestick data from Binance public API.
    """
    BASE_URL = "https://api.binance.com/api/v3/klines"

    def __init__(self, interval="1h", days_back=90):
        self.interval = interval
        self.days_back = days_back
        self.cache_dir = CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

        self.cache = self._load_cache() # {coin_ticker: pd.DataFrame} 
        
    def _load_cache(self):
        cache = {}

        print("Loading cache from disk...")

        for file in os.listdir(self.cache_dir):
            if file.endswith(".pkl"):
                coin = file[:-4]
                path = os.path.join(self.cache_dir, file)

                try:
                    with open(path, "rb") as f:
                        df = pickle.load(f)
                        cache[coin] = df
                        print(f"Got {coin} cache. Count: {len(df)} candles.")
                except Exception as e:
                    print(f"Failed to load {coin}: {e}")

        return cache
            
    def _save_cache(self, coin):
        try:
            path = os.path.join(self.cache_dir, f"{coin}.pkl")
            tmp_path = path + ".tmp"

            with open(tmp_path, "wb") as f:
                pickle.dump(self.cache[coin], f)

            os.replace(tmp_path, path)  # atomic write

        except Exception as e:
            print(f"Failed to save {coin} cache: {e}")

    def fetch_binance_klines(self, symbol: str, interval: str, start_ms: int, end_ms: int) -> pd.DataFrame:
        """
        Fetch historical kline data from Binance public API for a specific range.
        """
        limit = 1000
        all_rows = []
        cursor = start_ms

        while cursor < end_ms:
            params = {
                "symbol": symbol,
                "interval": interval,
                "startTime": cursor,
                "endTime": end_ms,
                "limit": limit,
            }
            try:
                resp = requests.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                batch = resp.json()
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                break

            if not batch:
                break

            all_rows.extend(batch)
            # advance cursor past the last candle's open_time
            cursor = batch[-1][0] + 1
            time.sleep(0.1)  # rate-limit courtesy

        if not all_rows:
            return pd.DataFrame()

        cols = [
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ]
        df = pd.DataFrame(all_rows, columns=cols)
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        return df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]

    def get_data(self, coin: str) -> pd.DataFrame:
        """
        Get cached data for a coin. If not cached, fetch initial historical data.
        """
        # Convert coin (e.g. BTC) to Binance symbol (e.g. BTCUSDT)
        symbol = f"{coin}USDT"
        
        if coin not in self.cache:
            print(f"Fetching initial historical data for {coin}...")
            end_ms = int(time.time() * 1000)
            start_ms = int((time.time() - self.days_back * 86400) * 1000)
            df = self.fetch_binance_klines(symbol, self.interval, start_ms, end_ms)
            if not df.empty:
                self.cache[coin] = df
            self._save_cache(coin)
            print(f"Got {coin} cache. Count: {len(df)} candles.")
        
        return self.cache.get(coin, pd.DataFrame())

    def update_latest_data(self, coin: str):
        """
        Update the cache for a coin with the latest candles.
        """
        if coin not in self.cache or self.cache[coin].empty:
            self.get_data(coin)
            return

        symbol = f"{coin}USDT"
        last_time = self.cache[coin]["open_time"].max()
        start_ms = int(last_time.timestamp() * 1000) + 1
        end_ms = int(time.time() * 1000)

        # Only update if at least one hour has passed (roughly) to avoid redundant calls
        # but Binance API will return what's available anyway.
        new_df = self.fetch_binance_klines(symbol, self.interval, start_ms, end_ms)
        
        if not new_df.empty:
            # Drop the last candle of old data if it overlaps (though start_ms+1 should prevent this)
            updated_df = pd.concat([self.cache[coin], new_df]).drop_duplicates(subset=["open_time"])
            self.cache[coin] = updated_df.sort_values("open_time").reset_index(drop=True)
            self._save_cache(coin)
            print(f"Updated {coin} cache. New count: {len(self.cache[coin])} candles.")
