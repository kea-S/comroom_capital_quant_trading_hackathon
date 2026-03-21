import time
import hmac
import hashlib
import requests
import os
from dotenv import load_dotenv
from logger import logger

load_dotenv()

class APIClient:
    def __init__(self):
        self.base_url = "https://mock-api.roostoo.com"
        self.api_key = os.getenv("TESTING_API_KEY")
        self.secret_key = os.getenv("TESTING_API_SECRET")

    def _get_timestamp(self):
        """Return a 13-digit millisecond timestamp as string."""
        return str(int(time.time() * 1000))

    def get_exchange_info(self):
        """Get exchange information including precision for all pairs."""
        url = f"{self.base_url}/v3/exchangeInfo"
        params = {'timestamp': self._get_timestamp()}
        try:
            res = requests.get(url, params=params)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting exchange info: {e}")
            return None

    def _get_signed_headers(self, payload: dict = {}):
        """
        Generate signed headers and totalParams for endpoints.
        """
        payload['timestamp'] = self._get_timestamp()
        sorted_keys = sorted(payload.keys())
        total_params = "&".join(f"{k}={payload[k]}" for k in sorted_keys)

        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            total_params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {
            'RST-API-KEY': self.api_key,
            'MSG-SIGNATURE': signature
        }

        return headers, payload, total_params

    def get_ticker(self, pair=None):
        """Get ticker for one or all pairs."""
        url = f"{self.base_url}/v3/ticker"
        params = {'timestamp': self._get_timestamp()}
        if pair:
            # Standardize: coin -> coin/USD
            pair_roostoo = f"{pair}/USD" if "/" not in pair else pair
            params['pair'] = pair_roostoo
        try:
            res = requests.get(url, params=params)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting ticker: {e}")
            return None

    def get_balance(self):
        """Get wallet balances."""
        url = f"{self.base_url}/v3/balance"
        headers, payload, _ = self._get_signed_headers({})
        try:
            res = requests.get(url, headers=headers, params=payload)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting balance: {e}")
            return None

    def place_order(self, coin, side, quantity, price=None, order_type=None):
        """
        Place a LIMIT or MARKET order.
        """
        url = f"{self.base_url}/v3/place_order"
        pair = f"{coin}/USD"

        if order_type is None:
            order_type = "LIMIT" if price is not None else "MARKET"

        payload = {
            'pair': pair,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': str(quantity)
        }
        if order_type == 'LIMIT':
            payload['price'] = str(price)

        headers, _, total_params = self._get_signed_headers(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

        try:
            logger.info(f"Sending request to url={url}")
            res = requests.post(url, headers=headers, data=total_params)
            res.raise_for_status()
            logger.info(res.json())
            return res.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error placing order: {e}")
            return None

    def get_total_portfolio_value(self):
        """
        Calculate total wallet value in USD by fetching balances and current market prices.
        Returns a tuple: (total_value_usd, held_coins_list)
        held_coins_list is a list of tuples: (coin, quantity)
        """
        balances = self.get_balance()
        if not balances or not balances.get('Success'):
            logger.error("Error: Could not fetch balances for portfolio valuation.")
            return None, []

        tickers = self.get_ticker()
        if not tickers or not tickers.get('Success'):
            logger.error("Error: Could not fetch tickers for portfolio valuation.")
            return None, []

        spot_wallet = balances.get('SpotWallet', {})
        ticker_data = tickers.get('Data', {})
        
        total_value = 0.0
        held_coins = []

        for coin, qty_info in spot_wallet.items():
            total_qty = float(qty_info.get('Free', 0)) + float(qty_info.get('Lock', 0))
            if total_qty <= 0:
                continue

            held_coins.append((coin, total_qty))

            if coin == 'USD':
                total_value += total_qty
            else:
                pair_name = f"{coin}/USD"
                # Handle cases where the ticker might be missing or under a different name
                price_info = ticker_data.get(pair_name)
                if price_info:
                    last_price = float(price_info.get('LastPrice', 0))
                    total_value += total_qty * last_price
                else:
                    logger.warning(f"Warning: Price for {coin} ({pair_name}) not found in tickers.")

        return total_value, held_coins
