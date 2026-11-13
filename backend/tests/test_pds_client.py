import httpx
import pytest

from app.services.pds_client import PDS_SEARCH_BASE_URL, PdsApiError, PdsClient


@pytest.mark.asyncio
async def test_search_preserves_upstream_json_and_query_parameters():
    expected_payload = {"summary": {"hits": 1}, "data": [{"lidvid": "urn:nasa:pds:example::1.0", "title": "Example PDS product"}]}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/search/1/products"
        assert request.url.params["keywords"] == "LOLA"
        assert request.url.params["limit"] == "5"
        assert request.headers["accept"] == "application/kvp+json"
        assert request.url.params.get_list("fields") == ["lidvid", "title"]
        return httpx.Response(200, json=expected_payload)

    client = PdsClient(transport=httpx.MockTransport(handler))
    request_url, payload = await client.search_products(keywords="LOLA", limit=5)

    assert request_url.startswith(PDS_SEARCH_BASE_URL)
    assert payload == expected_payload


@pytest.mark.asyncio
async def test_resolve_encodes_product_identifier_and_preserves_response():
    expected_payload = {"lidvid": "urn:nasa:pds:example::1.0"}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/urn:nasa:pds:example::1.0")
        assert request.headers["accept"] == "application/vnd.nasa.pds.pds4+json"
        return httpx.Response(200, json=expected_payload)

    client = PdsClient(transport=httpx.MockTransport(handler))
    _, payload = await client.resolve_product(identifier="urn:nasa:pds:example::1.0")

    assert payload == expected_payload


@pytest.mark.asyncio
async def test_upstream_errors_are_not_converted_into_empty_results():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "temporarily unavailable"})

    client = PdsClient(transport=httpx.MockTransport(handler))
    with pytest.raises(PdsApiError, match="HTTP 503"):
        await client.search_products(keywords="LOLA", limit=5)


@pytest.mark.asyncio
async def test_invalid_json_is_reported_as_an_upstream_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    client = PdsClient(transport=httpx.MockTransport(handler))
    with pytest.raises(PdsApiError, match="invalid JSON"):
        await client.search_products(keywords="LOLA", limit=5)

@pytest.mark.asyncio
async def test_product_not_found_keeps_upstream_404_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"errors": ["not found"]})

    client = PdsClient(transport=httpx.MockTransport(handler))
    with pytest.raises(PdsApiError) as error:
        await client.resolve_product(identifier="urn:nasa:pds:missing")

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_list_members_requests_the_official_hierarchy_endpoint():
    expected_payload = [
        {"id": "urn:nasa:pds:lro_lola_rdr:data_gridded:map_1::1.0", "title": "Example LOLA grid"},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/urn:nasa:pds:lro_lola_rdr:data_gridded::1.0/members")
        assert request.headers["accept"] == "application/json"
        assert request.url.params["limit"] == "100"
        assert request.url.params["sort"] == "ops:Harvest_Info.ops:harvest_date_time"
        return httpx.Response(200, json=expected_payload)

    client = PdsClient(transport=httpx.MockTransport(handler))
    request_url, payload = await client.list_members(
        identifier="urn:nasa:pds:lro_lola_rdr:data_gridded::1.0",
        depth=1,
    )

    assert request_url.startswith(PDS_SEARCH_BASE_URL)
    assert payload == expected_payload


@pytest.mark.asyncio
async def test_list_members_supports_two_levels_for_bundle_observations():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/urn:nasa:pds:example::1.0/members/members")
        return httpx.Response(200, json=[])

    client = PdsClient(transport=httpx.MockTransport(handler))
    _, payload = await client.list_members(identifier="urn:nasa:pds:example::1.0", depth=2, limit=100)
    assert payload == []


@pytest.mark.asyncio
async def test_list_members_rejects_unsupported_depth():
    client = PdsClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[])))
    with pytest.raises(ValueError, match="depth must be 1 or 2"):
        await client.list_members(identifier="urn:nasa:pds:example::1.0", depth=3)


@pytest.mark.asyncio
async def test_list_members_passes_search_after_cursor_for_next_page():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["search-after"] == "2026-10-16T22:13:29.801Z"
        assert request.url.params["sort"] == "ops:Harvest_Info.ops:harvest_date_time"
        return httpx.Response(200, json=[])

    client = PdsClient(transport=httpx.MockTransport(handler))
    _, payload = await client.list_members(
        identifier="urn:nasa:pds:example::1.0",
        search_after="2026-10-16T22:13:29.801Z",
    )
    assert payload == []


def test_extract_next_search_after_reads_documented_harvest_time_from_last_record():
    from app.services.pds_client import extract_next_search_after

    payload = [
        {"id": "urn:nasa:pds:example:item-1::1.0", "ops:Harvest_Info.ops:harvest_date_time": ["2026-10-15T10:00:00Z"]},
        {"id": "urn:nasa:pds:example:item-2::1.0", "ops:Harvest_Info.ops:harvest_date_time": ["2026-10-16T10:00:00Z"]},
    ]
    assert extract_next_search_after(payload) == "2026-10-16T10:00:00Z"


def test_extract_next_search_after_does_not_invent_cursor_when_missing():
    from app.services.pds_client import extract_next_search_after

    assert extract_next_search_after([{"id": "urn:nasa:pds:example:item::1.0"}]) is None
