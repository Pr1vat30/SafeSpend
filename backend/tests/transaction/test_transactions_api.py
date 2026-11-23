"""Transaction endpoints: insert, list/filter/totals, edit, delete and user isolation."""

from decimal import Decimal

from sqlalchemy import text

from tests.transaction.helpers import days_ago, headers, payload

URL = "/api/v1/transactions"


async def create(client, user, body):
    response = await client.post(URL, json=body, headers=headers(user))
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def totals(client, user, **params):
    response = await client.get(URL, params=params, headers=headers(user))
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    return Decimal(data["totals"]["income"]), Decimal(data["totals"]["expense"])


async def test_requires_a_user(db_client):
    response = await db_client.get(URL)
    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_unknown_user_is_rejected(db_client, default_ids):
    category = default_ids[("Casa", "expense")]
    response = await db_client.post(URL, json=payload(category), headers=headers(999999999))
    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_create_income(db_client, user_id, default_ids):
    body = payload(default_ids[("Stipendio", "income")], type="income", amount="1500.00")
    data = await create(db_client, user_id, body)
    assert data["type"] == "income"
    assert Decimal(data["amount"]) == Decimal("1500.00")
    assert data["category_name"] == "Stipendio"
    assert data["origin"] == "manual"


async def test_create_expense_with_optional_description(db_client, user_id, default_ids):
    body = payload(default_ids[("Alimentari", "expense")], description=None)
    data = await create(db_client, user_id, body)
    assert data["type"] == "expense"
    assert data["description"] is None
    assert data["category_name"] == "Alimentari"


async def test_invalid_amount_is_rejected(db_client, user_id, default_ids):
    category = default_ids[("Casa", "expense")]
    for amount in ("0", "-5", "1.234"):
        response = await db_client.post(
            URL, json=payload(category, amount=amount), headers=headers(user_id)
        )
        assert response.status_code == 422


async def test_future_date_is_rejected(db_client, user_id, default_ids):
    body = payload(default_ids[("Casa", "expense")], transaction_date=days_ago(-1))
    response = await db_client.post(URL, json=body, headers=headers(user_id))
    assert response.status_code == 422


async def test_missing_required_fields_are_rejected(db_client, user_id):
    response = await db_client.post(URL, json={"type": "expense"}, headers=headers(user_id))
    assert response.status_code == 422
    assert response.json()["success"] is False


async def test_category_must_exist_and_match_the_type(db_client, user_id, default_ids):
    unknown = await db_client.post(URL, json=payload(999999), headers=headers(user_id))
    assert unknown.status_code == 404

    wrong_type = payload(default_ids[("Stipendio", "income")], type="expense")
    response = await db_client.post(URL, json=wrong_type, headers=headers(user_id))
    assert response.status_code == 400


async def test_cannot_use_another_users_category(db_client, user_id, other_user_id, default_ids):
    created = await db_client.post(
        "/api/v1/categories",
        json={"name": "Solo mia", "type": "expense"},
        headers=headers(other_user_id),
    )
    foreign_category = created.json()["data"]["id_category"]
    response = await db_client.post(
        URL, json=payload(foreign_category), headers=headers(user_id)
    )
    assert response.status_code == 404


async def test_list_is_ordered_from_newest_to_oldest(db_client, user_id, default_ids):
    category = default_ids[("Casa", "expense")]
    for days in (5, 1, 3):
        await create(db_client, user_id, payload(category, transaction_date=days_ago(days)))
    response = await db_client.get(URL, headers=headers(user_id))
    dates = [item["transaction_date"] for item in response.json()["data"]["items"]]
    assert dates == [days_ago(1), days_ago(3), days_ago(5)]


async def test_filters_and_totals(db_client, user_id, default_ids):
    food = default_ids[("Alimentari", "expense")]
    home = default_ids[("Casa", "expense")]
    salary = default_ids[("Stipendio", "income")]
    await create(db_client, user_id, payload(food, amount="10.00", transaction_date=days_ago(2)))
    await create(db_client, user_id, payload(home, amount="40.00", transaction_date=days_ago(10)))
    await create(
        db_client,
        user_id,
        payload(salary, type="income", amount="1000.00", transaction_date=days_ago(4)),
    )

    assert await totals(db_client, user_id) == (Decimal("1000.00"), Decimal("50.00"))

    by_type = await db_client.get(URL, params={"type": "expense"}, headers=headers(user_id))
    assert by_type.json()["data"]["count"] == 2
    assert await totals(db_client, user_id, type="expense") == (Decimal("0"), Decimal("50.00"))

    by_category = await totals(db_client, user_id, id_category=home)
    assert by_category == (Decimal("0"), Decimal("40.00"))

    period = {"date_from": days_ago(5), "date_to": days_ago(0)}
    assert await totals(db_client, user_id, **period) == (Decimal("1000.00"), Decimal("10.00"))

    combined = await totals(db_client, user_id, type="expense", id_category=food, **period)
    assert combined == (Decimal("0"), Decimal("10.00"))

    empty = await db_client.get(URL, params={"id_category": 999999}, headers=headers(user_id))
    assert empty.json()["data"]["count"] == 0
    assert empty.json()["data"]["totals"] == {"income": "0.00", "expense": "0.00"}


async def test_period_boundaries_are_inclusive(db_client, user_id, default_ids):
    category = default_ids[("Casa", "expense")]
    await create(db_client, user_id, payload(category, transaction_date=days_ago(3)))
    params = {"date_from": days_ago(3), "date_to": days_ago(3)}
    response = await db_client.get(URL, params=params, headers=headers(user_id))
    assert response.json()["data"]["count"] == 1


async def test_inverted_period_is_rejected(db_client, user_id):
    params = {"date_from": days_ago(0), "date_to": days_ago(5)}
    response = await db_client.get(URL, params=params, headers=headers(user_id))
    assert response.status_code == 400


async def test_update_changes_every_field_and_totals(db_client, user_id, default_ids):
    expense_category = default_ids[("Casa", "expense")]
    income_category = default_ids[("Stipendio", "income")]
    created = await create(db_client, user_id, payload(expense_category, amount="30.00"))
    assert await totals(db_client, user_id) == (Decimal("0"), Decimal("30.00"))

    body = payload(
        income_category,
        type="income",
        amount="80.25",
        transaction_date=days_ago(2),
        description="Rimborso",
    )
    response = await db_client.put(
        f"{URL}/{created['id_transaction']}", json=body, headers=headers(user_id)
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["type"] == "income"
    assert Decimal(data["amount"]) == Decimal("80.25")
    assert data["transaction_date"] == days_ago(2)
    assert data["category_name"] == "Stipendio"
    assert data["description"] == "Rimborso"
    assert await totals(db_client, user_id) == (Decimal("80.25"), Decimal("0"))


async def test_update_keeps_the_insertion_validations(db_client, user_id, default_ids):
    category = default_ids[("Casa", "expense")]
    created = await create(db_client, user_id, payload(category))
    url = f"{URL}/{created['id_transaction']}"
    for override in ({"amount": "0"}, {"amount": "1.001"}, {"transaction_date": days_ago(-1)}):
        response = await db_client.put(
            url, json=payload(category, **override), headers=headers(user_id)
        )
        assert response.status_code == 422
    wrong_type = payload(default_ids[("Stipendio", "income")], type="expense")
    response = await db_client.put(url, json=wrong_type, headers=headers(user_id))
    assert response.status_code == 400


async def test_delete_removes_the_transaction_and_updates_totals(
    db_client, user_id, default_ids
):
    category = default_ids[("Casa", "expense")]
    keep = await create(db_client, user_id, payload(category, amount="10.00"))
    gone = await create(db_client, user_id, payload(category, amount="15.00"))
    assert await totals(db_client, user_id) == (Decimal("0"), Decimal("25.00"))

    response = await db_client.delete(f"{URL}/{gone['id_transaction']}", headers=headers(user_id))
    assert response.status_code == 200
    again = await db_client.get(f"{URL}/{gone['id_transaction']}", headers=headers(user_id))
    assert again.status_code == 404
    kept = await db_client.get(f"{URL}/{keep['id_transaction']}", headers=headers(user_id))
    assert kept.status_code == 200
    assert await totals(db_client, user_id) == (Decimal("0"), Decimal("10.00"))


async def test_users_cannot_see_or_touch_each_others_transactions(
    db_client, user_id, other_user_id, default_ids
):
    category = default_ids[("Casa", "expense")]
    mine = await create(db_client, user_id, payload(category, amount="99.00"))
    url = f"{URL}/{mine['id_transaction']}"

    listing = await db_client.get(URL, headers=headers(other_user_id))
    assert listing.json()["data"]["count"] == 0
    assert await totals(db_client, other_user_id) == (Decimal("0"), Decimal("0"))

    assert (await db_client.get(url, headers=headers(other_user_id))).status_code == 404
    update = await db_client.put(url, json=payload(category), headers=headers(other_user_id))
    assert update.status_code == 404
    assert (await db_client.delete(url, headers=headers(other_user_id))).status_code == 404

    still_there = await db_client.get(url, headers=headers(user_id))
    assert still_there.status_code == 200
    assert Decimal(still_there.json()["data"]["amount"]) == Decimal("99.00")


async def test_reconciliation_adjustments_cannot_be_edited_here(
    db_client, db_session, user_id, default_ids
):
    result = await db_session.execute(
        text(
            "INSERT INTO transaction (id_user, type, amount, transaction_date, origin)"
            " VALUES (:u, 'adjustment', -5, CURRENT_DATE, 'reconciliation')"
            " RETURNING id_transaction"
        ),
        {"u": user_id},
    )
    adjustment_id = result.scalar_one()
    category = default_ids[("Casa", "expense")]
    url = f"{URL}/{adjustment_id}"
    update = await db_client.put(url, json=payload(category), headers=headers(user_id))
    assert update.status_code == 400
    assert (await db_client.delete(url, headers=headers(user_id))).status_code == 400
