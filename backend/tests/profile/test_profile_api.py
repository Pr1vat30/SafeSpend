"""API tests of the financial profile (RF_AUT_4–5, RF_CF_3, RNF_PV_2–3). Use PostgreSQL."""

from tests.profile.conftest import PASSWORD

PROFILE = "/api/v1/profile"
SETUP = "/api/v1/profile/setup"
EXPORT = "/api/v1/profile/export"
LOGIN = "/api/v1/auth/login"


async def test_new_user_has_setup_not_completed(api, user):
    response = await api.get(PROFILE, headers=user["headers"])

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["setup_completed"] is False
    assert data["financial_profile"]["estimated_variable_expenses"] is None


async def test_initial_setup_saves_balance_buffer_and_estimate(api, user, sql):
    body = {
        "current_balance": "1250.40",
        "safety_buffer": "300",
        "estimated_variable_expenses": "400",
    }
    response = await api.post(SETUP, json=body, headers=user["headers"])

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["setup_completed"] is True
    assert data["financial_profile"]["safety_buffer"] == "300.00"
    snapshot = await sql(
        "SELECT real_balance, calculated_balance, id_adjustment_transaction "
        "FROM balance_snapshot WHERE id_user = :id",
        id=user["id"],
    )
    assert [tuple(map(str, row)) for row in snapshot] == [("1250.40", "1250.40", "None")]


async def test_initial_setup_estimate_is_optional(api, user):
    body = {"current_balance": "100", "safety_buffer": "0"}
    response = await api.post(SETUP, json=body, headers=user["headers"])

    assert response.status_code == 200
    assert response.json()["data"]["financial_profile"]["estimated_variable_expenses"] is None


async def test_initial_setup_cannot_be_repeated(api, user):
    body = {"current_balance": "100", "safety_buffer": "50"}
    assert (await api.post(SETUP, json=body, headers=user["headers"])).status_code == 200

    again = await api.post(SETUP, json=body, headers=user["headers"])
    assert again.status_code == 409


async def test_update_safety_buffer_horizon_and_consent(api, user):
    changes = {"safety_buffer": "500.00", "horizon_days": 60, "ai_consent": True}
    response = await api.patch(PROFILE, json=changes, headers=user["headers"])

    assert response.status_code == 200
    profile = response.json()["data"]["financial_profile"]
    assert (profile["safety_buffer"], profile["horizon_days"], profile["ai_consent"]) == (
        "500.00",
        60,
        True,
    )

    # The consent is revocable (RNF_PV_2) and the other fields are left untouched
    revoked = await api.patch(PROFILE, json={"ai_consent": False}, headers=user["headers"])
    profile = revoked.json()["data"]["financial_profile"]
    assert (profile["ai_consent"], profile["safety_buffer"]) == (False, "500.00")


async def test_update_rejects_invalid_values(api, user):
    for body in ({"safety_buffer": "-1"}, {"safety_buffer": "1.234"}, {"horizon_days": 45}):
        response = await api.patch(PROFILE, json=body, headers=user["headers"])
        assert response.status_code == 422, body


async def test_export_csv_contains_user_data(api, user):
    await api.post(
        SETUP, json={"current_balance": "1234.56", "safety_buffer": "300"}, headers=user["headers"]
    )
    response = await api.get(EXPORT, headers=user["headers"])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    text = response.text
    assert user["email"] in text
    assert "1234,56" in text  # Italian decimal format
    assert "# balance_snapshot" in text and "# transaction" in text
    assert "argon2" not in text  # the password hash is never exported


async def test_delete_account_needs_the_right_password(api, user, sql):
    wrong = await api.request(
        "DELETE", PROFILE, json={"password": "Sbagliata1"}, headers=user["headers"]
    )
    assert wrong.status_code == 401
    assert await sql("SELECT 1 FROM _user WHERE id_user = :id", id=user["id"])


async def test_delete_account_removes_every_record(api, user, sql):
    await api.post(
        SETUP, json={"current_balance": "100", "safety_buffer": "50"}, headers=user["headers"]
    )
    response = await api.request(
        "DELETE", PROFILE, json={"password": PASSWORD}, headers=user["headers"]
    )

    assert response.status_code == 200
    for table in ("_user", "financial_profile", "balance_snapshot"):
        assert await sql(f"SELECT 1 FROM {table} WHERE id_user = :id", id=user["id"]) == []
    login = await api.post(LOGIN, json={"email": user["email"], "password": PASSWORD})
    assert login.status_code == 401
