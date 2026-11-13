from __future__ import annotations

import httpx

from app.services.lalt_pds3 import (
    LALT_GT_SP_IMAGE_BYTES,
    LALT_GT_SP_IMAGE_URL,
    LALT_GT_SP_LABEL_URL,
    LALT_GT_SP_LINES,
    LALT_GT_SP_SAMPLE_BYTES,
    LALT_GT_SP_SAMPLES,
)


LALT_LABEL_MAX_BYTES = 64_000


class LaltApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class LaltClient:
    """Read-only client for the fixed JAXA DARTS LALT south-polar product."""

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

    async def fetch_gt_sp_sample(
        self,
        *,
        line_index: int,
        sample_index: int,
    ) -> tuple[str, bytes, tuple[int, int]]:
        if not isinstance(line_index, int) or isinstance(line_index, bool):
            raise LaltApiError("LALT line index must be an integer", status_code=422)
        if not isinstance(sample_index, int) or isinstance(sample_index, bool):
            raise LaltApiError("LALT sample index must be an integer", status_code=422)
        if not 0 <= line_index < LALT_GT_SP_LINES:
            raise LaltApiError("LALT line index is outside the image bounds", status_code=422)
        if not 0 <= sample_index < LALT_GT_SP_SAMPLES:
            raise LaltApiError("LALT sample index is outside the image bounds", status_code=422)

        byte_start = (line_index * LALT_GT_SP_SAMPLES + sample_index) * LALT_GT_SP_SAMPLE_BYTES
        byte_end = byte_start + LALT_GT_SP_SAMPLE_BYTES - 1
        expected_range = f"bytes {byte_start}-{byte_end}/{LALT_GT_SP_IMAGE_BYTES}"
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
                follow_redirects=False,
            ) as client:
                async with client.stream(
                    "GET",
                    LALT_GT_SP_IMAGE_URL,
                    headers={
                        "Accept": "application/octet-stream",
                        "Accept-Encoding": "identity",
                        "Range": f"bytes={byte_start}-{byte_end}",
                    },
                ) as response:
                    self._validate_response_origin(response)
                    if response.status_code != 206:
                        if response.status_code >= 400:
                            response.raise_for_status()
                        raise LaltApiError(
                            "JAXA LALT archive did not honor the four-byte Range request; full image download refused"
                        )
                    if response.headers.get("content-range", "") != expected_range:
                        raise LaltApiError("JAXA LALT archive returned an unexpected Content-Range")
                    content_length = response.headers.get("content-length")
                    if content_length is not None and content_length != str(LALT_GT_SP_SAMPLE_BYTES):
                        raise LaltApiError("JAXA LALT archive returned an unexpected sample Content-Length")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > LALT_GT_SP_SAMPLE_BYTES:
                            raise LaltApiError("JAXA LALT archive returned more than four sample bytes")
                    if len(body) != LALT_GT_SP_SAMPLE_BYTES:
                        raise LaltApiError("JAXA LALT archive returned an incomplete four-byte sample")
                    source_url = str(response.url)
        except LaltApiError:
            raise
        except httpx.TimeoutException as exc:
            raise LaltApiError("JAXA LALT pixel request timed out", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            raise LaltApiError(
                f"JAXA LALT image archive returned HTTP {exc.response.status_code}",
                status_code=404 if exc.response.status_code == 404 else 502,
            ) from exc
        except httpx.HTTPError as exc:
            raise LaltApiError("Could not connect to the fixed JAXA DARTS LALT image source") from exc
        return source_url, bytes(body), (byte_start, byte_end)
