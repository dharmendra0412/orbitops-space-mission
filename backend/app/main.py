from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Annotated

from fastapi import FastAPI, HTTPException, Path, Query

from app.services.pds_client import PdsApiError, PdsClient, extract_next_search_after
from app.services.pds3_label import PdsLabelError, parse_pds3_label

app = FastAPI(
    title="ORBITOPS Data API",
    version="0.1.0",
    description="Read-only discovery proxy for authoritative planetary-science archives.",
)

pds_client = PdsClient()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "orbitops-data-api"}


@app.get("/api/v1/pds/search")
async def search_pds_products(
    keywords: Annotated[str, Query(min_length=2, max_length=120)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> dict[str, Any]:
    """Return the unmodified JSON payload returned by NASA's PDS Search API."""
    if len(keywords.strip()) < 2:
        raise HTTPException(status_code=422, detail="Enter at least two non-whitespace characters.")

    try:
        request_url, upstream_payload = await pds_client.search_products(
            keywords=keywords.strip(),
            limit=limit,
        )
    except PdsApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return {
        "source": "NASA Planetary Data System Search API",
        "source_url": request_url,
        "api_documentation": "https://nasa-pds.github.io/pds-api/",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "query": {"keywords": keywords.strip(), "limit": limit},
        "response": upstream_payload,
    }


@app.get("/api/v1/pds/products/{identifier}/members")
async def list_pds_product_members(
    identifier: Annotated[str, Path(min_length=5, max_length=512)],
    depth: Annotated[int, Query(ge=1, le=2)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    search_after: Annotated[str | None, Query(max_length=128)] = None,
) -> dict[str, Any]:
    """Browse one or two levels down the official PDS product hierarchy."""
    try:
        request_url, upstream_payload = await pds_client.list_members(
            identifier=identifier,
            depth=depth,
            limit=limit,
            search_after=search_after,
        )
    except PdsApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    next_search_after = extract_next_search_after(upstream_payload)
    # Do not offer a "next page" action when the upstream cursor does not
    # advance; doing so could make the UI request the same page indefinitely.
    if search_after is not None and next_search_after == search_after:
        next_search_after = None

    return {
        "source": "NASA Planetary Data System Search API",
        "source_url": request_url,
        "api_documentation": "https://nasa-pds.github.io/pds-api/",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "identifier": identifier,
        "depth": depth,
        "page": {"limit": limit, "sort": "ops:Harvest_Info.ops:harvest_date_time", "search_after": search_after},
        "next_search_after": next_search_after,
        "response": upstream_payload,
    }


@app.get("/api/v1/pds/products/{identifier}")
async def resolve_pds_product(
    identifier: Annotated[str, Path(min_length=5, max_length=512)],
) -> dict[str, Any]:
    """Resolve a PDS product LID/LIDVID and preserve the source response."""
    try:
        request_url, upstream_payload = await pds_client.resolve_product(
            identifier=identifier,
        )
    except PdsApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return {
        "source": "NASA Planetary Data System Search API",
        "source_url": request_url,
        "api_documentation": "https://nasa-pds.github.io/pds-api/",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "identifier": identifier,
        "response": upstream_payload,
    }



@app.get("/api/v1/pds3/lola/gdr/ldem-85s-40m/label")
async def get_lola_gdr_sample_label() -> dict[str, Any]:
    """Retrieve and parse the fixed, source-verified LOLA PDS3 sample label."""
    try:
        source_url, label_text = await pds_client.fetch_lola_gdr_sample_label()
    except PdsApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    try:
        metadata = parse_pds3_label(label_text)
    except PdsLabelError as exc:
        raise HTTPException(status_code=502, detail=f"NASA PDS returned an unsupported label: {exc}") from exc

    return {
        "source": "NASA PDS Geosciences Node",
        "source_url": source_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "label_format": metadata.get("PDS_VERSION_ID"),
        "product_file": metadata.get("FILE_NAME"),
        "metadata": metadata,
        "note": "Source label metadata only; the IMG data file has not been downloaded or decoded. Height conversion is on hold because official LOLA references disagree on whether OFFSET is included in HEIGHT; no elevation or radius is calculated.",
    }
