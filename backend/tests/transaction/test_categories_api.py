"""Category endpoints: defaults, custom categories and deletion with reassignment."""

from sqlalchemy import text

from tests.transaction.helpers import headers, payload

CATEGORIES = "/api/v1/categories"
TRANSACTIONS = "/api/v1/transactions"

EXPENSE_DEFAULTS = {
    "Alimentari",
    "Casa",
    "Trasporti",
    "Salute",
    "Abbigliamento",
    "Svago",
    "Altro",
}
INCOME_DEFAULTS = {"Stipendio", "Altro"}


async def create_category(client, user, name, category_type="expense"):
    response = await client.post(
        CATEGORIES, json={"name": name, "type": category_type}, headers=headers(user)
    )
    return response


async def test_default_categories_are_listed(db_client, user_id):
    response = await db_client.get(CATEGORIES, headers=headers(user_id))
    assert response.status_code == 200
    items = response.json()["data"]
    defaults = [c for c in items if c["is_default"]]
    expense = {c["name"] for c in defaults if c["type"] == "expense"}
    income = {c["name"] for c in defaults if c["type"] == "income"}
    assert EXPENSE_DEFAULTS <= expense
    assert INCOME_DEFAULTS <= income


async def test_create_custom_category(db_client, user_id):
    response = await create_category(db_client, user_id, "  Hobby  ")
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Hobby"
    assert data["type"] == "expense"
    assert data["is_default"] is False

    listing = await db_client.get(CATEGORIES, headers=headers(user_id))
    assert "Hobby" in [c["name"] for c in listing.json()["data"]]


async def test_invalid_category_names_are_rejected(db_client, user_id):
    assert (await create_category(db_client, user_id, "   ")).status_code == 422
    assert (await create_category(db_client, user_id, "x" * 101)).status_code == 422
    assert (await create_category(db_client, user_id, "Valida", "other")).status_code == 422


async def test_duplicate_names_are_rejected(db_client, user_id, other_user_id):
    assert (await create_category(db_client, user_id, "Hobby")).status_code == 201
    assert (await create_category(db_client, user_id, "hobby")).status_code == 409
    assert (await create_category(db_client, user_id, "Casa")).status_code == 409
    assert (await create_category(db_client, user_id, "Hobby", "income")).status_code == 201
    # Another user may reuse the name.
    assert (await create_category(db_client, other_user_id, "Hobby")).status_code == 201


async def test_rename_custom_category(db_client, user_id):
    created = (await create_category(db_client, user_id, "Hobby")).json()["data"]
    response = await db_client.put(
        f"{CATEGORIES}/{created['id_category']}", json={"name": "Sport"}, headers=headers(user_id)
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Sport"


async def test_rename_to_an_existing_name_is_rejected(db_client, user_id):
    await create_category(db_client, user_id, "Hobby")
    other = (await create_category(db_client, user_id, "Sport")).json()["data"]
    response = await db_client.put(
        f"{CATEGORIES}/{other['id_category']}", json={"name": "Hobby"}, headers=headers(user_id)
    )
    assert response.status_code == 409


async def test_default_categories_are_protected(db_client, user_id, default_ids):
    category_id = default_ids[("Casa", "expense")]
    url = f"{CATEGORIES}/{category_id}"
    renamed = await db_client.put(url, json={"name": "Altro nome"}, headers=headers(user_id))
    assert renamed.status_code == 403
    assert (await db_client.delete(url, headers=headers(user_id))).status_code == 403


async def test_custom_categories_are_private(db_client, user_id, other_user_id):
    created = (await create_category(db_client, user_id, "Segreta")).json()["data"]
    url = f"{CATEGORIES}/{created['id_category']}"

    names = [
        c["name"]
        for c in (await db_client.get(CATEGORIES, headers=headers(other_user_id))).json()["data"]
    ]
    assert "Segreta" not in names
    renamed = await db_client.put(url, json={"name": "Rubata"}, headers=headers(other_user_id))
    assert renamed.status_code == 404
    assert (await db_client.delete(url, headers=headers(other_user_id))).status_code == 404
    assert (await db_client.get(CATEGORIES, headers=headers(user_id))).status_code == 200


async def test_delete_reassigns_transactions_to_altro(db_client, user_id, default_ids):
    created = (await create_category(db_client, user_id, "Hobby")).json()["data"]
    category_id = created["id_category"]
    transactions = []
    for amount in ("12.50", "7.00"):
        response = await db_client.post(
            TRANSACTIONS, json=payload(category_id, amount=amount), headers=headers(user_id)
        )
        assert response.status_code == 201
        transactions.append(response.json()["data"])

    response = await db_client.delete(f"{CATEGORIES}/{category_id}", headers=headers(user_id))
    assert response.status_code == 200
    assert response.json()["data"]["reassigned_transactions"] == 2

    listing = (await db_client.get(TRANSACTIONS, headers=headers(user_id))).json()["data"]
    assert listing["count"] == 2
    for item in listing["items"]:
        assert item["id_category"] == default_ids[("Altro", "expense")]
        assert item["category_name"] == "Altro"
    assert sorted(item["amount"] for item in listing["items"]) == ["12.50", "7.00"]
    assert listing["totals"]["expense"] == "19.50"

    listing = await db_client.get(CATEGORIES, headers=headers(user_id))
    assert "Hobby" not in [c["name"] for c in listing.json()["data"]]


async def test_delete_of_a_both_category_uses_the_altro_of_each_type(
    db_client, user_id, default_ids
):
    created = (await create_category(db_client, user_id, "Varie", "both")).json()["data"]
    category_id = created["id_category"]
    await db_client.post(
        TRANSACTIONS, json=payload(category_id, type="expense"), headers=headers(user_id)
    )
    await db_client.post(
        TRANSACTIONS, json=payload(category_id, type="income"), headers=headers(user_id)
    )
    response = await db_client.delete(f"{CATEGORIES}/{category_id}", headers=headers(user_id))
    assert response.json()["data"]["reassigned_transactions"] == 2

    items = (await db_client.get(TRANSACTIONS, headers=headers(user_id))).json()["data"]["items"]
    by_type = {item["type"]: item["id_category"] for item in items}
    assert by_type == {
        "expense": default_ids[("Altro", "expense")],
        "income": default_ids[("Altro", "income")],
    }


async def test_delete_does_not_touch_other_users_data(
    db_client, user_id, other_user_id, default_ids
):
    altro = default_ids[("Altro", "expense")]
    await db_client.post(TRANSACTIONS, json=payload(altro), headers=headers(other_user_id))
    created = (await create_category(db_client, user_id, "Hobby")).json()["data"]
    await db_client.delete(f"{CATEGORIES}/{created['id_category']}", headers=headers(user_id))
    other = (await db_client.get(TRANSACTIONS, headers=headers(other_user_id))).json()["data"]
    assert other["count"] == 1
    assert other["items"][0]["category_name"] == "Altro"


async def test_category_used_by_a_recurring_rule_cannot_be_deleted(
    db_client, db_session, user_id
):
    created = (await create_category(db_client, user_id, "Abbonamenti")).json()["data"]
    category_id = created["id_category"]
    await db_session.execute(
        text(
            "INSERT INTO recurring_rule (id_user, id_category, name, type, amount, frequency,"
            " first_occurrence_date) VALUES (:u, :c, 'Netflix', 'expense', 10, 'monthly',"
            " CURRENT_DATE)"
        ),
        {"u": user_id, "c": category_id},
    )
    response = await db_client.delete(f"{CATEGORIES}/{category_id}", headers=headers(user_id))
    assert response.status_code == 409
