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

    
def test_extract_next_search_after_stops_when_pds_returns_a_short_page():
    from app.services.pds_client import extract_next_search_after

    payload = [
        {"id": "urn:nasa:pds:example:item-1::1.0", "ops:Harvest_Info.ops:harvest_date_time": ["2026-10-16T10:00:00Z"]},
        {"id": "urn:nasa:pds:example:item-2::1.0", "ops:Harvest_Info.ops:harvest_date_time": ["2026-10-17T10:00:00Z"]},
    ]
    assert extract_next_search_after(payload, page_limit=3) is None


def test_extract_next_search_after_keeps_cursor_for_a_full_page():
    from app.services.pds_client import extract_next_search_after

    payload = [
        {"id": "urn:nasa:pds:example:item-1::1.0", "ops:Harvest_Info.ops:harvest_date_time": ["2026-10-16T10:00:00Z"]},
        {"id": "urn:nasa:pds:example:item-2::1.0", "ops:Harvest_Info.ops:harvest_date_time": ["2026-10-17T10:00:00Z"]},
    ]
    assert extract_next_search_after(payload, page_limit=2) == "2026-10-17T10:00:00Z"



def test_extract_next_search_after_supports_nested_harvest_info_shape():
    from app.services.pds_client import extract_next_search_after

    payload = {
        "data": [
            {"id": "urn:nasa:pds:example:item::1.0"},
            {
                "id": "urn:nasa:pds:example:item-2::1.0",
                "ops:Harvest_Info": {"ops:harvest_date_time": [" 2026-10-16T10:00:00Z "]},
            },
        ],
    }
    assert extract_next_search_after(payload) == "2026-10-16T10:00:00Z"


def test_extract_next_search_after_rejects_empty_or_non_string_cursor():
    from app.services.pds_client import extract_next_search_after

    assert extract_next_search_after([{"ops:Harvest_Info.ops:harvest_date_time": []}]) is None
    assert extract_next_search_after([{"ops:Harvest_Info.ops:harvest_date_time": 123}]) is None
    assert extract_next_search_after({"data": []}) is None


def test_parse_real_lola_pds3_label_preserves_source_units_and_reference_frame():
    from pathlib import Path

    from app.services.pds3_label import parse_pds3_label

    fixture = Path(__file__).parent / "fixtures" / "lola_ldem_85s_40m.lbl"
    metadata = parse_pds3_label(fixture.read_text(encoding="utf-8"))

    assert metadata["PDS_VERSION_ID"] == "PDS3"
    assert metadata["PRODUCT_VERSION_ID"] == "V2.0"
    assert metadata["DATA_SET_ID"] == "LRO-L-LOLA-4-GDR-V1.0"
    assert metadata["FILE_NAME"] == "LDEM_85S_40M.IMG"
    assert metadata["FILE_RECORDS"] == "7584"
    assert metadata["RECORD_BYTES"] == "15168"
    assert metadata["NAME"] == "HEIGHT"
    assert metadata["DERIVED_MINIMUM"] == "-11002"
    assert metadata["DERIVED_MAXIMUM"] == "14054"
    # The detached label is internally consistent about its fixed-length layout.
    assert int(metadata["FILE_RECORDS"]) * int(metadata["RECORD_BYTES"]) == 115_034_112
    assert int(metadata["LINES"]) * int(metadata["LINE_SAMPLES"]) * (int(metadata["SAMPLE_BITS"]) // 8) == 115_034_112
    assert metadata["SAMPLE_TYPE"] == "LSB_INTEGER"
    assert metadata["SAMPLE_BITS"] == "16"
    assert metadata["UNIT"] == "METER"
    assert metadata["SCALING_FACTOR"] == "0.5"
    assert metadata["OFFSET"] == "1737400."
    assert metadata["MAP_PROJECTION_TYPE"] == "POLAR STEREOGRAPHIC"
    assert metadata["MAP_SCALE"] == "40 <m/pix>"
    assert metadata["RECORD_TYPE"] == "FIXED_LENGTH"
    assert metadata["^IMAGE"] == "LDEM_85S_40M.IMG"
    assert metadata["A_AXIS_RADIUS"] == "1737.4 <km>"
    assert metadata["LINE_PROJECTION_OFFSET"] == "3791.5 <pix>"
    assert metadata["SAMPLE_PROJECTION_OFFSET"] == "3791.5 <pix>"
    assert metadata["MAP_PROJECTION_ROTATION"] == "0.0"
    assert metadata["CENTER_LATITUDE"] == "-90 <deg>"
    assert metadata["MINIMUM_LATITUDE"] == "-90 <deg>"
    assert metadata["MAXIMUM_LATITUDE"] == "-85 <deg>"
    assert metadata["COORDINATE_SYSTEM_NAME"] == "MEAN EARTH/POLAR AXIS OF DE421"


def test_pds3_label_parser_rejects_wrong_format_and_oversized_input():
    from app.services.pds3_label import PdsLabelError, parse_pds3_label

    with pytest.raises(PdsLabelError, match="PDS_VERSION_ID"):
        parse_pds3_label('PDS_VERSION_ID = "PDS4"\\nFILE_NAME = "data.img"')
    with pytest.raises(PdsLabelError, match="size limit"):
        parse_pds3_label('PDS_VERSION_ID = "PDS3"\\nFILE_NAME = "data.img"', max_characters=10)


@pytest.mark.asyncio
async def test_fetch_lola_sample_label_uses_fixed_source_and_preserves_text():
    from app.services.pds_client import PDS_LOLA_GDR_SAMPLE_LABEL_URL

    label = 'PDS_VERSION_ID = "PDS3"\\nFILE_NAME = "LDEM_85S_40M.IMG"\\nEND\\n'

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == PDS_LOLA_GDR_SAMPLE_LABEL_URL
        assert request.headers["accept"] == "text/plain"
        return httpx.Response(200, content=label.encode("ascii"), headers={"content-type": "text/plain"})

    client = PdsClient(transport=httpx.MockTransport(handler))
    source_url, returned_label = await client.fetch_lola_gdr_sample_label()

    assert source_url == PDS_LOLA_GDR_SAMPLE_LABEL_URL
    assert returned_label == label


@pytest.mark.asyncio
async def test_fetch_lola_sample_label_rejects_oversized_and_non_ascii_content():
    client = PdsClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=b"x" * 1_000_001)
    ))
    with pytest.raises(PdsApiError, match="size limit"):
        await client.fetch_lola_gdr_sample_label()

    non_ascii_client = PdsClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=bytes([255]))
    ))
    with pytest.raises(PdsApiError, match="ASCII"):
        await non_ascii_client.fetch_lola_gdr_sample_label()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_method",
    ["search_products", "resolve_product", "list_members"],
)
async def test_pds_api_redirects_are_not_followed(request_method: str):
    requests_seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        return httpx.Response(
            302,
            headers={"Location": "http://127.0.0.1:8000/internal"},
        )

    client = PdsClient(transport=httpx.MockTransport(handler))
    with pytest.raises(PdsApiError, match="HTTP 302"):
        if request_method == "search_products":
            await client.search_products(keywords="LOLA")
        elif request_method == "resolve_product":
            await client.resolve_product(identifier="urn:nasa:pds:example::1.0")
        else:
            await client.list_members(identifier="urn:nasa:pds:example::1.0")

    # Only the fixed NASA PDS host is contacted; redirect targets are not fetched.
    assert len(requests_seen) == 1
    assert requests_seen[0].url.host == "pds.nasa.gov"


@pytest.mark.asyncio
async def test_lola_label_redirects_are_not_followed():
    from app.services.pds_client import PDS_LOLA_GDR_SAMPLE_LABEL_URL

    requests_seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        return httpx.Response(
            302,
            headers={"Location": "http://127.0.0.1:8000/internal-label"},
        )

    client = PdsClient(transport=httpx.MockTransport(handler))
    with pytest.raises(PdsApiError, match="HTTP 302"):
        await client.fetch_lola_gdr_sample_label()

    assert len(requests_seen) == 1
    assert str(requests_seen[0].url) == PDS_LOLA_GDR_SAMPLE_LABEL_URL
