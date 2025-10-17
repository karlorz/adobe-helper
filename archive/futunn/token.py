"""
Token Manager for Futunn API

Handles acquisition and management of authentication tokens required for API requests.
Inspired by TokenAcquirer from py-googletrans.
"""

import hashlib
import hmac
import json
import logging
import re
from typing import Any

import httpx

from futunn import constants, urls
from futunn.exceptions import TokenExpiredError

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages authentication tokens for Futunn API.

    Fetches and caches tokens from cookies and headers when visiting the main page.
    """

    def __init__(self, client: httpx.AsyncClient):
        """
        Initialize TokenManager

        Args:
            client: httpx.AsyncClient instance to use for requests
        """
        self.client = client
        self.csrf_token: str | None = None

    async def get_headers(
        self,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """
        Get authentication tokens, fetching new ones if necessary.

        Returns:
            Dict containing required headers with tokens

        Raises:
            TokenExpiredError: If unable to fetch tokens
        """
        if self.csrf_token is None:
            await self._fetch_tokens()

        csrf_token = self._read_csrf_cookie()
        if not csrf_token:
            raise TokenExpiredError("Missing csrfToken cookie")

        payload = self._select_payload(params=params, data=data)
        quote_token = self._build_quote_token(payload)

        return self._build_headers(csrf_token=csrf_token, quote_token=quote_token)

    async def _fetch_tokens(self) -> None:
        """
        Fetch tokens by visiting the main Futunn page.

        This mimics a browser visit to extract cookies and tokens.
        """
        try:
            logger.info("Fetching authentication tokens from Futunn")

            # Visit the main stock list page to get cookies
            response = await self.client.get(
                urls.STOCK_LIST_PAGE,
                headers={
                    "User-Agent": constants.DEFAULT_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                follow_redirects=True,
            )

            if response.status_code != 200:
                raise TokenExpiredError(
                    f"Failed to fetch tokens: HTTP {response.status_code}"
                )

            self.csrf_token = self._extract_csrf_token(response, response.cookies)

            logger.info("Successfully fetched csrf token")

        except httpx.RequestError as e:
            logger.error(f"Network error while fetching tokens: {e}")
            raise TokenExpiredError(f"Network error: {e}")

    def _extract_csrf_token(self, response: httpx.Response, cookies: httpx.Cookies) -> str:
        """
        Extract CSRF token from response.

        Args:
            response: HTTP response object
            cookies: Cookies from response

        Returns:
            CSRF token string
        """
        csrf_cookie = cookies.get("csrfToken")
        if csrf_cookie:
            return csrf_cookie

        # Try to find token in response headers
        csrf_token = response.headers.get("x-csrf-token")
        if csrf_token:
            return csrf_token

        # Try to find in page content
        content = response.text
        match = re.search(r'csrf[_-]?token["\']\s*[:=]\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)

        raise TokenExpiredError("Unable to extract CSRF token from Futunn page")

    def _build_headers(self, *, csrf_token: str, quote_token: str) -> dict[str, str]:
        """
        Build request headers with authentication tokens.

        Returns:
            Dictionary of headers
        """
        return {
            "futu-x-csrf-token": csrf_token,
            "quote-token": quote_token,
            "referer": urls.STOCK_LIST_PAGE,
            "user-agent": constants.DEFAULT_USER_AGENT,
            "accept": "application/json, text/plain, */*",
        }

    async def refresh_tokens(self) -> dict[str, str]:
        """
        Force refresh of authentication tokens.

        Returns:
            Dict containing refreshed headers with tokens
        """
        logger.info("Refreshing authentication tokens")
        self.csrf_token = None
        return await self.get_headers()

    def invalidate(self) -> None:
        """Invalidate cached tokens, forcing refresh on next request"""
        logger.info("Invalidating cached tokens")
        self.csrf_token = None
        self.client.cookies.clear()

    def _read_csrf_cookie(self) -> str | None:
        cookie = self.client.cookies.get("csrfToken", domain="www.futunn.com")
        if cookie is None:
            cookie = self.client.cookies.get("csrfToken")
        return cookie or self.csrf_token

    @staticmethod
    def _select_payload(
        *, params: dict[str, Any] | None, data: dict[str, Any] | None
    ) -> str:
        if data:
            payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        elif params:
            payload = TokenManager._stringify_params(params)
        else:
            payload = "{}"

        payload = payload or "quote"
        return payload

    @staticmethod
    def _stringify_params(params: dict[str, Any]) -> str:
        serialized: dict[str, str] = {}
        for key, value in params.items():
            if value is None:
                continue
            serialized[key] = TokenManager._js_string(value)
        return json.dumps(serialized, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _js_string(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return "null"
        return str(value)

    @staticmethod
    def _build_quote_token(payload: str) -> str:
        if not payload:
            payload = "quote"

        hmac_hex = hmac.new(
            key=b"quote_web",
            msg=payload.encode("utf-8"),
            digestmod=hashlib.sha512,
        ).hexdigest()

        intermediate = hmac_hex[:10]
        sha_digest = hashlib.sha256(intermediate.encode("utf-8")).hexdigest()
        return sha_digest[:10]
