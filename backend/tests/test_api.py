from fastapi.testclient import TestClient

import app.main as api
from app.services.pds_client import PdsApiError


class StubPdsClient:
    async def search_products(self, *, keywords: str, limit: int):
        return (
            "https://pds.nasa.gov/api/search/1/products?keywords=LOLA&limit=10",
            {"products": [{"lid": "urn:nasa:pds:example"}]},
        )

    async def list_members(self, *, identifier: str, depth: int = 1, limit: int = 100, search_after: str | None = None):
        return (
            f"https://pds.nasa.gov/api/search/1/products/{identifier}/members",
            [{"id": "urn:nasa:pds:example:collection:item::1.0", "title": "Source child product"}],
        )

    async def resolve_product(self, *, identifier: str):
        return (
            f"https://pds.nasa.gov/api/search/1/products/{identifier}",
            {"lidvid": identifier},
        )


def test_health_endpoint():
    client = TestClient(api.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_endpoint_returns_unmodified_source_payload_and_provenance(monkeypatch):
    monkeypatch.setattr(api, "pds_client", StubPdsClient())
    client = TestClient(api.app)

    response = client.get("/api/v1/pds/search", params={"keywords": "LOLA", "limit": 10})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "NASA Planetary Data System Search API"
    assert payload["source_url"].startswith("https://pds.nasa.gov/api/search/1/products")
    assert payload["query"] == {"keywords": "LOLA", "limit": 10}
    assert payload["response"] == {"products": [{"lid": "urn:nasa:pds:example"}]}
    assert payload["retrieved_at"]


def test_search_rejects_whitespace_only_keywords():
    client = TestClient(api.app)
    response = client.get("/api/v1/pds/search", params={"keywords": "   "})
    assert response.status_code == 422


def test_upstream_not_found_is_not_reported_as_empty_success(monkeypatch):
    class MissingProductClient:
        async def resolve_product(self, *, identifier: str):
            raise PdsApiError("NASA PDS Search API returned HTTP 404", status_code=404)

    monkeypatch.setattr(api, "pds_client", MissingProductClient())
    client = TestClient(api.app)

    response = client.get("/api/v1/pds/products/urn:nasa:pds:missing")
    assert response.status_code == 404

def test_product_lookup_endpoint_returns_upstream_metadata_and_provenance(monkeypatch):
    monkeypatch.setattr(api, "pds_client", StubPdsClient())
    client = TestClient(api.app)

    identifier = "urn:nasa:pds:example::1.0"
    response = client.get("/api/v1/pds/products/" + identifier)

    assert response.status_code == 200
    payload = response.json()
    assert payload["identifier"] == identifier
    assert payload["response"] == {"lidvid": identifier}
    assert payload["retrieved_at"]


def test_members_endpoint_returns_original_hierarchy_records_and_provenance(monkeypatch):
    monkeypatch.setattr(api, "pds_client", StubPdsClient())
    client = TestClient(api.app)

    identifier = "urn:nasa:pds:example::1.0"
    response = client.get("/api/v1/pds/products/" + identifier + "/members?depth=1&limit=100")

    assert response.status_code == 200
    payload = response.json()
    assert payload["identifier"] == identifier
    assert payload["depth"] == 1
    assert payload["page"]["limit"] == 100
    assert payload["next_search_after"] is None
    assert payload["response"][0]["id"] == "urn:nasa:pds:example:collection:item::1.0"
    assert payload["retrieved_at"]


def test_members_endpoint_rejects_depth_above_two():
    client = TestClient(api.app)
    response = client.get(
        "/api/v1/pds/products/urn:nasa:pds:example::1.0/members?depth=3"
    )
    assert response.status_code == 422



def test_members_endpoint_forwards_search_after_and_exposes_only_source_cursor(monkeypatch):
    class PaginatedPdsClient:
        async def list_members(self, *, identifier: str, depth: int = 1, limit: int = 100, search_after: str | None = None):
            assert search_after == "2026-10-16T10:00:00Z"
            return (
                "https://pds.nasa.gov/api/search/1/products/example/members?search-after=2026-10-16T10%3A00%3A00Z",
                [{
                    "id": "urn:nasa:pds:example:item::1.0",
                    "ops:Harvest_Info.ops:harvest_date_time": ["2026-10-17T10:00:00Z"],
                }],
            )

    monkeypatch.setattr(api, "pds_client", PaginatedPdsClient())
    client = TestClient(api.app)

    response = client.get(
        "/api/v1/pds/products/urn:nasa:pds:example::1.0/members",
        params={"search_after": "2026-10-16T10:00:00Z", "limit": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"]["search_after"] == "2026-10-16T10:00:00Z"
    assert payload["next_search_after"] == "2026-10-17T10:00:00Z"




def test_members_endpoint_does_not_offer_next_page_for_short_pds_result(monkeypatch):
    class ShortPagePdsClient:
        async def list_members(self, *, identifier: str, depth: int = 1, limit: int = 100, search_after: str | None = None):
            return (
                "https://pds.nasa.gov/api/search/1/products/example/members",
                [
                    {
                        "id": "urn:nasa:pds:example:item::1.0",
                        "ops:Harvest_Info.ops:harvest_date_time": ["2026-10-17T10:00:00Z"],
                    }
                ],
            )

    monkeypatch.setattr(api, "pds_client", ShortPagePdsClient())
    client = TestClient(api.app)
    response = client.get(
        "/api/v1/pds/products/urn:nasa:pds:example::1.0/members",
        params={"limit": 2},
    )

    assert response.status_code == 200
    assert response.json()["next_search_after"] is None


def test_members_endpoint_hides_non_advancing_pagination_cursor(monkeypatch):
    class RepeatingCursorPdsClient:
        async def list_members(self, *, identifier: str, depth: int = 1, limit: int = 100, search_after: str | None = None):
            return (
                "https://pds.nasa.gov/api/search/1/products/example/members",
                [{
                    "id": "urn:nasa:pds:example:item::1.0",
                    "ops:Harvest_Info.ops:harvest_date_time": [search_after],
                }],
            )

    monkeypatch.setattr(api, "pds_client", RepeatingCursorPdsClient())
    client = TestClient(api.app)
    cursor = "2026-10-17T10:00:00Z"

    response = client.get(
        "/api/v1/pds/products/urn:nasa:pds:example::1.0/members",
        params={"search_after": cursor, "limit": 1},
    )

    assert response.status_code == 200
    assert response.json()["next_search_after"] is None


def test_lola_pds3_label_endpoint_returns_parsed_source_metadata(monkeypatch):
    from pathlib import Path

    fixture = Path(__file__).parent / "fixtures" / "lola_ldem_85s_40m.lbl"
    label_text = fixture.read_text(encoding="ascii")

    class LabelClient:
        async def fetch_lola_gdr_sample_label(self):
            return (
                "https://pds-geosciences.wustl.edu/lro/sample/ldem_85s_40m.lbl",
                label_text,
            )

    monkeypatch.setattr(api, "pds_client", LabelClient())
    client = TestClient(api.app)

    response = client.get("/api/v1/pds3/lola/gdr/ldem-85s-40m/label")

    assert response.status_code == 200
    payload = response.json()
    assert payload["label_format"] == "PDS3"
    assert payload["product_file"] == "LDEM_85S_40M.IMG"
    assert payload["metadata"]["SCALING_FACTOR"] == "0.5"
    assert payload["metadata"]["OFFSET"] == "1737400."
    assert payload["metadata"]["NAME"] == "HEIGHT"
    assert payload["metadata"]["FILE_RECORDS"] == "7584"
    assert payload["metadata"]["RECORD_BYTES"] == "15168"
    assert payload["metadata"]["MAP_SCALE"] == "40 <m/pix>"
    assert "downloaded and validated" in payload["note"]
    assert "HEIGHT = DN * SCALING_FACTOR" in payload["note"]
    assert "PLANETARY_RADIUS = DN * SCALING_FACTOR + OFFSET" in payload["note"]
    assert "downloaded and validated" in payload["note"]


def test_lola_pds3_label_endpoint_reports_malformed_upstream_label(monkeypatch):
    class InvalidLabelClient:
        async def fetch_lola_gdr_sample_label(self):
            return ("https://pds-geosciences.wustl.edu/sample.lbl", "not a PDS label")

    monkeypatch.setattr(api, "pds_client", InvalidLabelClient())
    client = TestClient(api.app)

    response = client.get("/api/v1/pds3/lola/gdr/ldem-85s-40m/label")

    assert response.status_code == 502


def test_lola_pixel_endpoint_returns_source_dn_height_radius_and_coordinates(monkeypatch):
    from pathlib import Path

    fixture = Path(__file__).parent / "fixtures" / "lola_ldem_85s_40m.lbl"
    label_text = fixture.read_text(encoding="ascii")

    class PixelClient:
        async def fetch_lola_gdr_sample_label(self):
            return ("https://pds-geosciences.wustl.edu/sample.lbl", label_text)

        async def fetch_lola_gdr_sample_dn(self, *, line_index: int, sample_index: int):
            assert (line_index, sample_index) == (3791, 3791)
            return (
                "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_85s_40m.img",
                -11002,
                (57_509_470, 57_509_471),
            )

    monkeypatch.setattr(api, "pds_client", PixelClient())
    client = TestClient(api.app)
    response = client.get(
        "/api/v1/pds3/lola/gdr/ldem-85s-40m/pixel",
        params={"line_index": 3791, "sample_index": 3791},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["raw_dn"] == -11002
    assert payload["height_m"] == -5501.0
    assert payload["planetary_radius_m"] == 1_731_899.0
    assert payload["planetocentric_latitude_degrees"] < -89.99
    assert payload["east_longitude_degrees"] == 315.0
    assert payload["byte_range_inclusive"] == {"start": 57_509_470, "end": 57_509_471}
    assert payload["source_url"].endswith("ldem_85s_40m.img")
    assert "not a terrain tile" in payload["validation_scope"]


def test_lola_pixel_endpoint_rejects_out_of_bounds_indices():
    client = TestClient(api.app)
    response = client.get(
        "/api/v1/pds3/lola/gdr/ldem-85s-40m/pixel",
        params={"line_index": 7584, "sample_index": 0},
    )
    assert response.status_code == 422


def test_lola_pixel_endpoint_rejects_wrong_source_label(monkeypatch):
    class WrongLabelClient:
        async def fetch_lola_gdr_sample_label(self):
            return (
                "https://pds-geosciences.wustl.edu/wrong.lbl",
                'PDS_VERSION_ID = "PDS3"\\nFILE_NAME = "OTHER.IMG"\\nEND\\n',
            )

    monkeypatch.setattr(api, "pds_client", WrongLabelClient())
    client = TestClient(api.app)
    response = client.get(
        "/api/v1/pds3/lola/gdr/ldem-85s-40m/pixel",
        params={"line_index": 0, "sample_index": 0},
    )
    assert response.status_code == 502
    assert "source metadata failed validation" in response.json()["detail"]
