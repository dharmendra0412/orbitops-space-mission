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
        assert request.url.params.get_list("fields") == ["lidvid", "title", "product_class", "start_date_time", "stop_date_time"]
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
