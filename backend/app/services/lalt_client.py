from __future__ import annotations

import httpx

from app.services.lalt_pds3 import LALT_GT_SP_LABEL_URL


LALT_LABEL_MAX_BYTES = 64_000


class LaltApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class LaltClient:
    """Read-only label client for the fixed JAXA DARTS LALT south-polar product."""

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._transport = transport
        self._timeout_seconds = timeout_seconds

    @staticmethod
    def _validate_response_origin(response: httpx.Response) -> None:
        if response.is_redirect:
            raise LaltApiError("JAXA LALT source redirected; refusing an unverified destination")
        if response.url.scheme != "https" or response.url.host != "data.darts.isas.jaxa.jp":
            raise LaltApiError("JAXA LALT response came from an unexpected source host")

    async def fetch_gt_sp_label(self) -> tuple[str, str]:
        """Fetch only the small fixed PDS3 label; no caller-supplied URLs are accepted."""
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
                follow_redirects=False,
            ) as client:
                async with client.stream(
                    "GET",
                    LALT_GT_SP_LABEL_URL,
                    headers={"Accept": "text/plain", "Accept-Encoding": "identity"},
                ) as response:
                    self._validate_response_origin(response)
                    response.raise_for_status()
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > LALT_LABEL_MAX_BYTES:
                            raise LaltApiError("JAXA LALT label exceeds the configured size limit")
                    source_url = str(response.url)
            label_text = bytes(body).decode("ascii")
        except LaltApiError:
            raise
        except UnicodeDecodeError as exc:
            raise LaltApiError("JAXA LALT label is not valid ASCII text") from exc
        except httpx.TimeoutException as exc:
            raise LaltApiError("JAXA LALT label request timed out", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            raise LaltApiError(
                f"JAXA LALT archive returned HTTP {exc.response.status_code}",
                status_code=404 if exc.response.status_code == 404 else 502,
            ) from exc
        except httpx.HTTPError as exc:
            raise LaltApiError("Could not connect to the fixed JAXA DARTS LALT source") from exc
        return source_url, label_text
