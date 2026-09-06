# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

### Example 3 — Python: Pytest + httpx (FastAPI)

```python
# tests/api/test_items.py
import pytest
import httpx
from datetime import datetime, timedelta
import jwt

BASE_URL = "http://localhost:8000"
JWT_SECRET = "test-secret"  # use test config, never production secret


def make_token(user_id: str, role: str = "user", expired: bool = False) -> str:
    exp = datetime.utcnow() + (timedelta(hours=-1) if expired else timedelta(hours=1))
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": exp},
        JWT_SECRET,
        algorithm="HS256",
    )


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL) as c:
        yield c


@pytest.fixture
def valid_token():
    return make_token("user-123", role="user")


@pytest.fixture
def admin_token():
    return make_token("admin-456", role="admin")


@pytest.fixture
def expired_token():
    return make_token("user-123", expired=True)


class TestGetItem:
    def test_returns_401_without_auth(self, client):
        res = client.get("/api/items/1")
        assert res.status_code == 401

    def test_returns_401_with_invalid_token(self, client):
        res = client.get("/api/items/1", headers={"Authorization": "Bearer garbage"})
        assert res.status_code == 401

    def test_returns_401_with_expired_token(self, client, expired_token):
        res = client.get("/api/items/1", headers={"Authorization": f"Bearer {expired_token}"})
        assert res.status_code == 401
        assert "expired" in res.json().get("detail", "").lower()

    def test_returns_404_for_nonexistent_item(self, client, valid_token):
        res = client.get(
            "/api/items/99999999",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert res.status_code == 404

    def test_returns_400_for_invalid_id_format(self, client, valid_token):
        res = client.get(
            "/api/items/not-a-number",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert res.status_code in (400, 422)

    def test_returns_200_with_valid_auth(self, client, valid_token, test_item):
        res = client.get(
            f"/api/items/{test_item['id']}",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == test_item["id"]
        assert "password" not in data


class TestCreateItem:
    def test_returns_422_with_empty_body(self, client, admin_token):
        res = client.post(
            "/api/items",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 422
        errors = res.json()["detail"]
        assert len(errors) > 0

    def test_returns_422_with_missing_required_field(self, client, admin_token):
        res = client.post(
            "/api/items",
            json={"description": "no name field"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 422
        fields = [e["loc"][-1] for e in res.json()["detail"]]
        assert "name" in fields

    def test_returns_422_with_wrong_type(self, client, admin_token):
        res = client.post(
            "/api/items",
            json={"name": "test", "price": "not-a-number"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 422

    @pytest.mark.parametrize("price", [-1, -0.01])
    def test_returns_422_for_negative_price(self, client, admin_token, price):
        res = client.post(
            "/api/items",
            json={"name": "test", "price": price},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 422

    def test_returns_422_for_price_exceeding_max(self, client, admin_token):
        res = client.post(
            "/api/items",
            json={"name": "test", "price": 1_000_001},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 422

    def test_creates_item_successfully(self, client, admin_token):
        res = client.post(
            "/api/items",
            json={"name": "New Widget", "price": 9.99, "category": "tools"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        assert data["name"] == "New Widget"

    def test_returns_403_for_non_admin(self, client, valid_token):
        res = client.post(
            "/api/items",
            json={"name": "test", "price": 1.0},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert res.status_code == 403


class TestPagination:
    def test_returns_paginated_response(self, client, valid_token):
        res = client.get(
            "/api/items?page=1&size=10",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert len(data["items"]) <= 10

    def test_empty_result_for_out_of_range_page(self, client, valid_token):
        res = client.get(
            "/api/items?page=99999",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert res.status_code == 200
        assert res.json()["items"] == []

    def test_returns_422_for_page_zero(self, client, valid_token):
        res = client.get(
            "/api/items?page=0",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert res.status_code == 422

    def test_caps_page_size_at_maximum(self, client, valid_token):
        res = client.get(
            "/api/items?size=9999",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert res.status_code == 200
        assert len(res.json()["items"]) <= 100  # max page size


class TestRateLimiting:
    def test_rate_limit_after_burst(self, client, valid_token):
        responses = []
        for _ in range(60):  # exceed typical 50/min limit
            res = client.get(
                "/api/items",
                headers={"Authorization": f"Bearer {valid_token}"},
            )
            responses.append(res.status_code)
            if res.status_code == 429:
                break
        assert 429 in responses, "Rate limit was not triggered"

    def test_rate_limit_response_has_retry_after(self, client, valid_token):
        for _ in range(60):
            res = client.get("/api/items", headers={"Authorization": f"Bearer {valid_token}"})
            if res.status_code == 429:
                assert "Retry-After" in res.headers or "retry_after" in res.json()
                break
```

---
