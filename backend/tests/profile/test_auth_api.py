"""API tests of authentication (RF_AUT_1–3, RNF_SE_1). They use PostgreSQL (see conftest)."""

from tests.profile.conftest import PASSWORD, registration

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
PROFILE = "/api/v1/profile"


async def test_register_creates_user_and_empty_profile(api, sql):
    body = registration()
    response = await api.post(REGISTER, json=body)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["email"] == body["email"]
    assert "password" not in data

    rows = await sql(
        "SELECT u.password, p.safety_buffer, p.horizon_days, p.ai_consent "
        "FROM _user u JOIN financial_profile p USING (id_user) WHERE u.id_user = :id",
        id=data["id_user"],
    )
    hashed, buffer, horizon, consent = rows[0]
    assert hashed.startswith("$argon2") and PASSWORD not in hashed  # RNF_SE_1
    assert (buffer, horizon, consent) == (0, 30, False)


async def test_register_duplicate_email_is_rejected(api):
    body = registration()
    assert (await api.post(REGISTER, json=body)).status_code == 201

    again = await api.post(REGISTER, json={**body, "email": body["email"].upper()})
    assert again.status_code == 409
    assert again.json()["success"] is False


async def test_register_invalid_payload_returns_422(api):
    response = await api.post(REGISTER, json=registration(password="corta1"))
    assert response.status_code == 422


async def test_login_returns_jwt_valid_60_minutes(api, user):
    response = await api.post(LOGIN, json={"email": user["email"], "password": PASSWORD})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600
    me = await api.get(ME, headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.json()["data"]["email"] == user["email"]


async def test_login_wrong_password_or_unknown_email_gives_same_error(api, user):
    wrong = await api.post(LOGIN, json={"email": user["email"], "password": "Sbagliata1"})
    unknown = await api.post(LOGIN, json={"email": "nessuno@example.com", "password": PASSWORD})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"] == unknown.json()["error"]


async def test_login_locked_after_five_consecutive_failures(api, user, sql):
    for _ in range(4):
        response = await api.post(LOGIN, json={"email": user["email"], "password": "Sbagliata1"})
        assert response.status_code == 401
    fifth = await api.post(LOGIN, json={"email": user["email"], "password": "Sbagliata1"})
    assert fifth.status_code == 423

    # Locked for 15 minutes even with the right password
    correct = await api.post(LOGIN, json={"email": user["email"], "password": PASSWORD})
    assert correct.status_code == 423
    rows = await sql("SELECT locked_until - now() FROM _user WHERE id_user = :id", id=user["id"])
    remaining = rows[0][0].total_seconds()
    assert 14 * 60 < remaining <= 15 * 60


async def test_successful_login_resets_failed_attempts(api, user, sql):
    for _ in range(4):
        await api.post(LOGIN, json={"email": user["email"], "password": "Sbagliata1"})
    assert (await api.post(LOGIN, json={"email": user["email"], "password": PASSWORD})).is_success

    rows = await sql("SELECT failed_login_attempts FROM _user WHERE id_user = :id", id=user["id"])
    assert rows[0][0] == 0


async def test_logout_revokes_the_token(api, user):
    assert (await api.get(ME, headers=user["headers"])).status_code == 200

    assert (await api.post(LOGOUT, headers=user["headers"])).status_code == 200

    assert (await api.get(ME, headers=user["headers"])).status_code == 401
    assert (await api.get(PROFILE, headers=user["headers"])).status_code == 401


async def test_protected_routes_need_a_valid_token(api):
    assert (await api.get(PROFILE)).status_code == 401
    bad = await api.get(PROFILE, headers={"Authorization": "Bearer non-un-token"})
    assert bad.status_code == 401
    assert bad.json()["success"] is False


async def test_after_logout_a_new_login_works(api, user):
    await api.post(LOGOUT, headers=user["headers"])

    login = await api.post(LOGIN, json={"email": user["email"], "password": PASSWORD})
    token = login.json()["data"]["access_token"]
    assert (await api.get(ME, headers={"Authorization": f"Bearer {token}"})).status_code == 200
