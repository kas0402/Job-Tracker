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