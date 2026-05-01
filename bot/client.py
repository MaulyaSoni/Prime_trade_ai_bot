import hashlib
import hmac
import logging
import time
from typing import Any, Dict

import requests

logger = logging.getLogger("trading_bot.client")

BASE_URL = "https://testnet.binance.vision"
ORDER_ENDPOINT = "/api/v3/order"


class BinanceClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.
    Handles authentication (HMAC-SHA256 signing) and request lifecycle.
    """

    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, params: Dict[str, Any]) -> str:
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _safe_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return params without signature — safe to log."""
        if not params:
            return {}
        return {k: v for k, v in params.items() if k != "signature"}

    # ------------------------------------------------------------------ #
    #  Public interface                                                    #
    # ------------------------------------------------------------------ #

    def get_public(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        url = f"{BASE_URL}{endpoint}"
        logger.debug("GET %s | params: %s", url, params)
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("HTTP GET failed %s | exc: %s", url, exc)
            raise

    def get_signed(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        params = params or {}
        params["timestamp"] = self._timestamp()
        params["signature"] = self._sign(params)

        url = f"{BASE_URL}{endpoint}"
        logger.debug("GET %s | params: %s", url, self._safe_params(params))
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            if hasattr(exc, "response") and exc.response is not None:
                logger.error("HTTP %s from %s | body: %s", exc.response.status_code, url, exc.response.text)
            raise

    def post_signed(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign the params dict, POST to the given endpoint, and return the
        parsed JSON response. Raises on HTTP or network errors.
        """
        params["timestamp"] = self._timestamp()
        params["signature"] = self._sign(params)

        url = f"{BASE_URL}{endpoint}"
        logger.debug("POST %s | params: %s", url, self._safe_params(params))

        try:
            response = self.session.post(url, data=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            # Re-raise; callers handle the error detail
            logger.error(
                "HTTP %s from %s | body: %s",
                exc.response.status_code,
                url,
                exc.response.text,
            )
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error reaching %s: %s", url, exc)
            raise
        except requests.exceptions.Timeout as exc:
            logger.error("Request to %s timed out: %s", url, exc)
            raise

        data: Dict[str, Any] = response.json()
        logger.debug("Response: %s", data)
        return data
