from fastapi.testclient import TestClient

import app.main as api
from app.services.pds_client import PdsApiError


class StubPdsClient:
    async def search_products(self, *, keywords: str, limit: int):
        return (
            "https://pds.nasa.gov/api/search/1/products?keywords=LOLA&limit=10",
            {"products": [{"lid": "urn:nasa:pds:example"}]},
        )

    async def list_members(self, *, identifier: str, depth: int = 1):
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
    response = client.get("/api/v1/pds/products/" + identifier + "/members?depth=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["identifier"] == identifier
    assert payload["depth"] == 1
    assert payload["response"][0]["id"] == "urn:nasa:pds:example:collection:item::1.0"
    assert payload["retrieved_at"]


def test_members_endpoint_rejects_depth_above_two():
    client = TestClient(api.app)
    response = client.get(
        "/api/v1/pds/products/urn:nasa:pds:example::1.0/members?depth=3"
    )
    assert response.status_code == 422
