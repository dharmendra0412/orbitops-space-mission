from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Annotated

from fastapi import FastAPI, HTTPException, Path, Query

from app.services.pds_client import PdsApiError, PdsClient, extract_next_search_after
from app.services.pds3_label import PdsLabelError, parse_pds3_label
from app.services.lalt_client import LaltApiError, LaltClient
from app.services.lalt_pds3 import (
    LaltPdsError,
    decode_lalt_pc_real_sample,
    lalt_grid_node_to_lat_lon,
    parse_and_validate_lalt_gt_sp_label,
)
from app.services.lola_gdr import (
    LolaRasterError,
    lola_dn_to_height_m,
    lola_dn_to_planetary_radius_m,
    lola_map_scale_m_per_pixel,
    lola_polar_pixel_to_latlon,
    validate_lola_gdr_label,
)

app = FastAPI(
    title="ORBITOPS Data API",
    version="0.1.0",
    description="Read-only discovery proxy for authoritative planetary-science archives.",
)

pds_client = PdsClient()
lalt_client = LaltClient()


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

    next_search_after = extract_next_search_after(upstream_payload, page_limit=limit)
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



@app.get("/api/v1/pds3/lola/gdr/ldem-85s-40m/pixel")
async def get_lola_gdr_sample_pixel(
    line_index: Annotated[int, Query(ge=0, le=7_583)],
    sample_index: Annotated[int, Query(ge=0, le=7_583)],
) -> dict[str, Any]:
    """Retrieve one real LOLA GDR DN using a strict two-byte HTTP Range request."""
    try:
        label_url, label_text = await pds_client.fetch_lola_gdr_sample_label()
        metadata = parse_pds3_label(label_text)
        lines, samples, _ = validate_lola_gdr_label(metadata)
        if lines != 7_584 or samples != 7_584:
            raise LolaRasterError("The selected LOLA source label does not match the validated 7584 x 7584 product")
        raster_url, dn, byte_range = await pds_client.fetch_lola_gdr_sample_dn(
            line_index=line_index,
            sample_index=sample_index,
        )
        latitude, longitude = lola_polar_pixel_to_latlon(
            metadata,
            line_index=line_index,
            sample_index=sample_index,
        )
        height_m = lola_dn_to_height_m(dn, metadata)
        planetary_radius_m = lola_dn_to_planetary_radius_m(dn, metadata)
    except PdsApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except (PdsLabelError, LolaRasterError) as exc:
        raise HTTPException(status_code=502, detail=f"NASA LOLA source metadata failed validation: {exc}") from exc

    return {
        "source": "NASA PDS Geosciences Node",
        "source_url": raster_url,
        "label_source_url": label_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "product_file": metadata["FILE_NAME"],
        "line_index": line_index,
        "sample_index": sample_index,
        "byte_range_inclusive": {"start": byte_range[0], "end": byte_range[1]},
        "raw_dn": dn,
        "height_m": height_m,
        "planetary_radius_m": planetary_radius_m,
        "planetocentric_latitude_degrees": latitude,
        "east_longitude_degrees": longitude,
        "units": {"raw_dn": "signed 16-bit integer", "height": "m", "planetary_radius": "m"},
        "coordinate_reference": metadata["COORDINATE_SYSTEM_NAME"],
        "validation_scope": (
            "One source-backed raw sample retrieved with an exact two-byte HTTP Range response. "
            "Height and radius use the LOLA GDR SIS scaling and offset. This is not a terrain tile, "
            "a full-raster integrity check, or independent geodetic ground truth."
        ),
    }


@app.get("/api/v1/pds3/lola/gdr/ldem-85s-40m/profile")
async def get_lola_gdr_row_profile(
    line_index: Annotated[int, Query(ge=0, le=7_583)],
    start_sample_index: Annotated[int, Query(ge=0, le=7_583)] = 0,
    sample_count: Annotated[int, Query(ge=1, le=512)] = 128,
) -> dict[str, Any]:
    """Return a bounded, source-backed height profile from one LOLA image row."""
    try:
        label_url, label_text = await pds_client.fetch_lola_gdr_sample_label()
        metadata = parse_pds3_label(label_text)
        lines, samples, _ = validate_lola_gdr_label(metadata)
        if lines != 7_584 or samples != 7_584:
            raise LolaRasterError("The selected LOLA source label does not match the validated 7584 x 7584 product")
        raster_url, raw_samples, byte_range = await pds_client.fetch_lola_gdr_row_segment(
            line_index=line_index,
            start_sample_index=start_sample_index,
            sample_count=sample_count,
        )
        sample_spacing_m = lola_map_scale_m_per_pixel(metadata)
        points = []
        for offset, dn in enumerate(raw_samples):
            sample_index = start_sample_index + offset
            latitude, longitude = lola_polar_pixel_to_latlon(
                metadata,
                line_index=line_index,
                sample_index=sample_index,
            )
            points.append({
                "sample_index": sample_index,
                "raw_dn": dn,
                "height_m": lola_dn_to_height_m(dn, metadata),
                "planetary_radius_m": lola_dn_to_planetary_radius_m(dn, metadata),
                "planetocentric_latitude_degrees": latitude,
                "east_longitude_degrees": longitude,
            })
    except PdsApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except (PdsLabelError, LolaRasterError) as exc:
        raise HTTPException(status_code=502, detail=f"NASA LOLA source metadata failed validation: {exc}") from exc

    return {
        "source": "NASA PDS Geosciences Node",
        "source_url": raster_url,
        "label_source_url": label_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "product_file": metadata["FILE_NAME"],
        "line_index": line_index,
        "start_sample_index": start_sample_index,
        "sample_count": len(points),
        "sample_spacing_m": sample_spacing_m,
        "profile_span_m": (len(points) - 1) * sample_spacing_m,
        "byte_range_inclusive": {"start": byte_range[0], "end": byte_range[1]},
        "coordinate_reference": metadata["COORDINATE_SYSTEM_NAME"],
        "units": {"raw_dn": "signed 16-bit integer", "height": "m", "planetary_radius": "m"},
        "points": points,
        "validation_scope": (
            "A bounded contiguous row segment retrieved using an exact HTTP 206 Range response. "
            "Height and radius use the LOLA GDR SIS scaling and offset; coordinates use the PDS "
            "DSMAP_POLAR equations. This is a source-backed profile, not a complete raster "
            "integrity check or independent geodetic ground truth."
        ),
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
        "note": "This label endpoint returns source metadata only. Related pixel and bounded row-profile endpoints retrieve original raster bytes through fixed-source HTTP Range requests; they do not download the full IMG. The LOLA GDR SIS defines HEIGHT = DN * SCALING_FACTOR and PLANETARY_RADIUS = DN * SCALING_FACTOR + OFFSET.",
    }


@app.get("/api/v1/pds3/kaguya/lalt/gt-sp/label")
async def get_kaguya_lalt_gt_sp_label() -> dict[str, Any]:
    """Retrieve and validate the fixed JAXA DARTS LALT south-polar PDS3 label."""
    try:
        source_url, label_text = await lalt_client.fetch_gt_sp_label()
        metadata = parse_and_validate_lalt_gt_sp_label(label_text)
    except LaltApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except LaltPdsError as exc:
        raise HTTPException(status_code=502, detail=f"JAXA LALT source metadata failed validation: {exc}") from exc

    return {
        "source": "JAXA / DARTS SELENE Data Archive",
        "source_url": source_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "product_file": metadata["source_label"]["FILE_NAME"],
        "metadata": {key: value for key, value in metadata.items() if key != "source_label"},
        "validation_scope": (
            "This is the PDS3 LALT_GT_SP_IMG interpolated south-polar grid, derived from "
            "LALT_LGT_TS by spherical interpolation. It is not raw laser-shot data or "
            "independent geodetic ground truth."
        ),
    }


@app.get("/api/v1/pds3/kaguya/lalt/gt-sp/pixel")
async def get_kaguya_lalt_gt_sp_pixel(
    line_index: Annotated[int, Query(ge=0, le=1_407)],
    sample_index: Annotated[int, Query(ge=0, le=11_519)],
) -> dict[str, Any]:
    """Retrieve one real LALT interpolated-grid sample using an exact four-byte Range."""
    try:
        label_url, label_text = await lalt_client.fetch_gt_sp_label()
        metadata = parse_and_validate_lalt_gt_sp_label(label_text)
        raster_url, raw_bytes, byte_range = await lalt_client.fetch_gt_sp_sample(
            line_index=line_index,
            sample_index=sample_index,
        )
        elevation_km = decode_lalt_pc_real_sample(raw_bytes)
        latitude, longitude = lalt_grid_node_to_lat_lon(line_index, sample_index)
    except LaltApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except LaltPdsError as exc:
        raise HTTPException(status_code=502, detail=f"JAXA LALT source metadata or sample failed validation: {exc}") from exc

    return {
        "source": "JAXA / DARTS SELENE Data Archive",
        "source_url": raster_url,
        "label_source_url": label_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": metadata["dataset_id"],
        "product_id": metadata["product_id"],
        "line_index": line_index,
        "sample_index": sample_index,
        "byte_range_inclusive": {"start": byte_range[0], "end": byte_range[1]},
        "raw_sample_bytes_hex": raw_bytes.hex(),
        "elevation_km": elevation_km,
        "elevation_m": elevation_km * 1000.0 if elevation_km is not None else None,
        "is_dummy": elevation_km is None,
        "planetocentric_latitude_degrees": latitude,
        "east_longitude_degrees": longitude,
        "coordinate_reference": metadata["coordinate_system"],
        "reference_sphere_radius_km": metadata["reference_sphere_radius_km"],
        "units": {"elevation": "km", "elevation_converted": "m"},
        "validation_scope": (
            "One bounded four-byte sample retrieved using an exact HTTP 206 Range response. "
            "This PDS3 product is a spherical-interpolation grid derived from LALT_LGT_TS, "
            "not a raw laser shot. It is a cross-sensor comparison candidate, not independent "
            "geodetic ground truth; orbit/frame provenance and interpolation uncertainty remain "
            "relevant."
        ),
    }
