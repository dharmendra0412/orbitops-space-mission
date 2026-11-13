from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

PDS_SEARCH_BASE_URL = "https://pds.nasa.gov/api/search/1"
PDS_LOLA_GDR_SAMPLE_LABEL_URL = (
    "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/"
    "lrolol_1xxx/data/lola_gdr/polar/img/ldem_85s_40m.lbl"
)


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
                        "fields": ["lidvid", "title"],
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

    async def list_members(self, *, identifier: str, depth: int = 1, limit: int = 100, search_after: str | None = None) -> tuple[str, Any]:
        if depth not in (1, 2):
            raise ValueError("PDS hierarchy depth must be 1 or 2")

        if not 1 <= limit <= 100:
            raise ValueError("PDS hierarchy page size must be between 1 and 100")

        encoded_identifier = quote(identifier, safe="")
        suffix = "/members" * depth
        url = f"{PDS_SEARCH_BASE_URL}/products/{encoded_identifier}{suffix}"
        params: dict[str, str | int] = {
            "limit": limit,
            "sort": "ops:Harvest_Info.ops:harvest_date_time",
        }
        if search_after:
            params["search-after"] = search_after
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, params=params, headers={"Accept": "application/json"})
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


    async def fetch_lola_gdr_sample_label(self) -> tuple[str, str]:
        """Fetch one fixed, public LOLA PDS3 label; never accepts a caller URL."""
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
                follow_redirects=False,
            ) as client:
                response = await client.get(
                    PDS_LOLA_GDR_SAMPLE_LABEL_URL,
                    headers={"Accept": "text/plain"},
                )
                response.raise_for_status()
                if len(response.content) > 1_000_000:
                    raise PdsApiError("NASA PDS label exceeds the configured size limit")
                label_text = response.content.decode("ascii")
        except PdsApiError:
            raise
        except UnicodeDecodeError as exc:
            raise PdsApiError("NASA PDS label is not valid ASCII text") from exc
        except httpx.TimeoutException as exc:
            raise PdsApiError("NASA PDS label request timed out", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            raise PdsApiError(
                f"NASA PDS archive returned HTTP {exc.response.status_code}",
                status_code=404 if exc.response.status_code == 404 else 502,
            ) from exc
        except httpx.HTTPError as exc:
            raise PdsApiError("Could not connect to the NASA PDS archive") from exc

        return str(response.url), label_text

    async def resolve_product(self, *, identifier: str) -> tuple[str, Any]:
        encoded_identifier = quote(identifier, safe="")
        url = f"{PDS_SEARCH_BASE_URL}/products/{encoded_identifier}"
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, headers={"Accept": "application/vnd.nasa.pds.pds4+json"})
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

def extract_next_search_after(payload: Any) -> str | None:
    """Read the final record's documented harvest-time sort value, if supplied.

    PDS responses may expose the registry field as a flattened dotted key or
    as a nested Harvest_Info object. Only a source-provided string is returned;
    a missing or malformed value deliberately disables further-page navigation.
    """
    rows = payload if isinstance(payload, list) else (
        payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), list) else None
    )
    if not rows:
        return None

    last = rows[-1]
    if not isinstance(last, dict):
        return None

    value = last.get("ops:Harvest_Info.ops:harvest_date_time")
    if value is None:
        harvest_info = last.get("ops:Harvest_Info")
        if isinstance(harvest_info, dict):
            value = harvest_info.get("ops:harvest_date_time")

    if isinstance(value, list):
        value = value[-1] if value else None
    if not isinstance(value, str):
        return None

    cursor = value.strip()
    return cursor or None

