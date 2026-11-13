from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

PDS_SEARCH_BASE_URL = "https://pds.nasa.gov/api/search/1"


class PdsApiError(RuntimeError):
    """Raised when the upstream NASA PDS Search API cannot be used."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class PdsClient:
    """Small read-only client for the official NASA PDS Search API."""

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._transport = transport
        self._timeout_seconds = timeout_seconds

    async def search_products(self, *, keywords: str, limit: int = 10) -> tuple[str, Any]:
        url = f"{PDS_SEARCH_BASE_URL}/products"
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
                follow_redirects=True,
            ) as client:
                response = await client.get(
                    url,
                    params={
                        "keywords": keywords,
                        "limit": limit,
                        "fields": ["lidvid", "title", "product_class", "start_date_time", "stop_date_time"],
                    },
                    headers={"Accept": "application/kvp+json"},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise PdsApiError("NASA PDS Search API request timed out", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            raise PdsApiError(
                f"NASA PDS Search API returned HTTP {exc.response.status_code}",
                status_code=404 if exc.response.status_code == 404 else 502,
            ) from exc
        except httpx.HTTPError as exc:
            raise PdsApiError("Could not connect to NASA PDS Search API") from exc
        except ValueError as exc:
            raise PdsApiError("NASA PDS Search API returned invalid JSON") from exc

        return str(response.url), payload

    async def resolve_product(self, *, identifier: str) -> tuple[str, Any]:
        encoded_identifier = quote(identifier, safe="")
        url = f"{PDS_SEARCH_BASE_URL}/products/{encoded_identifier}"
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, headers={"Accept": "application/json"})
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise PdsApiError("NASA PDS Search API request timed out", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            raise PdsApiError(
                f"NASA PDS Search API returned HTTP {exc.response.status_code}",
                status_code=404 if exc.response.status_code == 404 else 502,
            ) from exc
        except httpx.HTTPError as exc:
            raise PdsApiError("Could not connect to NASA PDS Search API") from exc
        except ValueError as exc:
            raise PdsApiError("NASA PDS Search API returned invalid JSON") from exc

        return str(response.url), payload
