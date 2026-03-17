import time
import hmac
import hashlib
import requests
import os
from dotenv import load_dotenv

load_dotenv()

class APIClient:
    def __init__(self):
        self.base_url = "https://mock-api.roostoo.com"
        self.api_key = os.getenv("TESTING_API_KEY")
        self.secret_key = os.getenv("TESTING_API_SECRET")

    def _get_timestamp(self):
        """Return a 13-digit millisecond timestamp as string."""
        return str(int(time.time() * 1000))

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
            params['pair'] = pair
        try:
            res = requests.get(url, params=params)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting ticker: {e}")
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
            print(f"Error getting balance: {e}")
            return None

    def place_order(self, pair_or_coin, side, quantity, price=None, order_type=None):
        """
        Place a LIMIT or MARKET order.
        """
        url = f"{self.base_url}/v3/place_order"
        pair = f"{pair_or_coin}/USD" if "/" not in pair_or_coin else pair_or_coin

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
            res = requests.post(url, headers=headers, data=total_params)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException as e:
            print(f"Error placing order: {e}")
            return None
