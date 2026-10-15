def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_and_duplicate(client):
    body = {"email": "x@example.com", "password": "password123"}
    assert client.post("/register", json=body).status_code == 201
    assert client.post("/register", json=body).status_code == 400


def test_short_password_rejected(client):
    r = client.post("/register", json={"email": "y@example.com", "password": "abc"})
    assert r.status_code == 422


def test_login_wrong_password(client):
    client.post("/register", json={"email": "z@example.com", "password": "password123"})
    r = client.post("/login", data={"username": "z@example.com", "password": "wrongpass1"})
    assert r.status_code == 401


def test_applications_require_auth(client):
    assert client.get("/applications").status_code == 401


def test_create_and_list_application(client, auth_headers):
    body = {"company": "SAP", "role": "Backend Developer"}
    r = client.post("/applications", json=body, headers=auth_headers)
    assert r.status_code == 201
    listing = client.get("/applications", headers=auth_headers).json()
    assert len(listing) == 1
    assert listing[0]["company"] == "SAP"


def test_users_cannot_see_each_others_data(client, auth_headers):
    created = client.post(
        "/applications", json={"company": "SAP", "role": "Dev"}, headers=auth_headers
    ).json()

    client.post("/register", json={"email": "b@example.com", "password": "password123"})
    login = client.post("/login", data={"username": "b@example.com", "password": "password123"})
    other = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get("/applications", headers=other).json() == []
    r = client.patch(f"/applications/{created['id']}", json={"status": "offer"}, headers=other)
    assert r.status_code == 404

def test_status_history_recorded(client, auth_headers):
    app_id = client.post(
        "/applications", json={"company": "SAP", "role": "Dev"}, headers=auth_headers
    ).json()["id"]
    client.patch(f"/applications/{app_id}", json={"status": "applied"}, headers=auth_headers)
    client.patch(f"/applications/{app_id}", json={"status": "applied"}, headers=auth_headers)

    history = client.get(f"/applications/{app_id}/history", headers=auth_headers).json()
    assert [h["new_status"] for h in history] == ["saved", "applied"]


def test_stats_counts_per_status(client, auth_headers):
    for status_value in ["applied", "applied", "interview"]:
        client.post(
            "/applications",
            json={"company": "X", "role": "Dev", "status": status_value},
            headers=auth_headers,
        )
    stats = client.get("/stats", headers=auth_headers).json()
    assert stats == {"total": 3, "by_status": {"applied": 2, "interview": 1}}


def test_history_is_private(client, auth_headers):
    app_id = client.post(
        "/applications", json={"company": "SAP", "role": "Dev"}, headers=auth_headers
    ).json()["id"]
    client.post("/register", json={"email": "b@example.com", "password": "password123"})
    login = client.post("/login", data={"username": "b@example.com", "password": "password123"})
    other = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get(f"/applications/{app_id}/history", headers=other).status_code == 404

def test_invalid_status_rejected(client, auth_headers):
    r = client.post(
        "/applications",
        json={"company": "SAP", "role": "Dev", "status": "banana"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_negative_salary_rejected(client, auth_headers):
    r = client.post(
        "/applications",
        json={"company": "SAP", "role": "Dev", "salary": -5},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_empty_company_rejected(client, auth_headers):
    r = client.post(
        "/applications", json={"company": "", "role": "Dev"}, headers=auth_headers
    )
    assert r.status_code == 422


def test_patch_invalid_status_rejected(client, auth_headers):
    app_id = client.post(
        "/applications", json={"company": "SAP", "role": "Dev"}, headers=auth_headers
    ).json()["id"]
    r = client.patch(
        f"/applications/{app_id}", json={"status": "banana"}, headers=auth_headers
    )
    assert r.status_code == 422

def test_stats_cached_and_invalidated(client, auth_headers):
    client.post(
        "/applications", json={"company": "A", "role": "Dev", "status": "applied"},
        headers=auth_headers,
    )
    first = client.get("/stats", headers=auth_headers).json()
    assert first == {"total": 1, "by_status": {"applied": 1}}

    from app import cache
    assert cache._client.keys("stats:*"), "stats should be cached after the first call"

    client.post(
        "/applications", json={"company": "B", "role": "Dev", "status": "applied"},
        headers=auth_headers,
    )
    assert not cache._client.keys("stats:*"), "a write should clear the cache"
    second = client.get("/stats", headers=auth_headers).json()
    assert second == {"total": 2, "by_status": {"applied": 2}}


def test_stats_cache_is_per_user(client, auth_headers):
    client.post("/applications", json={"company": "A", "role": "Dev"}, headers=auth_headers)
    client.get("/stats", headers=auth_headers)

    client.post("/register", json={"email": "b@example.com", "password": "password123"})
    login = client.post("/login", data={"username": "b@example.com", "password": "password123"})
    other = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/stats", headers=other).json() == {"total": 0, "by_status": {}}


def test_stats_work_when_redis_is_down(client, auth_headers, monkeypatch):
    import redis
    from app import cache

    def broken(*args, **kwargs):
        raise redis.RedisError("down")

    monkeypatch.setattr(cache._client, "get", broken)
    monkeypatch.setattr(cache._client, "set", broken)
    monkeypatch.setattr(cache._client, "delete", broken)

    client.post("/applications", json={"company": "A", "role": "Dev"}, headers=auth_headers)
    r = client.get("/stats", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1