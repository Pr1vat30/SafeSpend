"""API tests for balance reconciliation (`RF_SAL_1`, `RF_SAL_2`) against real PostgreSQL."""

from decimal import Decimal

from sqlalchemy import text

from tests.transaction.helpers import days_ago, headers, payload

URL = "/api/v1/reconciliations"
TRANSACTIONS = "/api/v1/transactions"


async def test_reconciliations_require_authenticated_user(db_client, user_id):
    assert (await db_client.get(f"{URL}/preview")).status_code == 401
    assert (await db_client.get(URL)).status_code == 401
    assert (await db_client.post(URL, json={"real_balance": "10.00"})).status_code == 401
    assert (await db_client.get(f"{URL}/preview", headers=headers(999_999_999))).status_code == 401
    assert (await db_client.get(f"{URL}/preview", headers=headers(user_id))).status_code == 200


async def test_preview_computes_calculated_balance_and_respects_date(
    db_client, user_id, default_ids
):
    food = default_ids[("Alimentari", "expense")]
    salary = default_ids[("Stipendio", "income")]

    empty = await db_client.get(f"{URL}/preview", headers=headers(user_id))
    assert empty.status_code == 200
    assert Decimal(empty.json()["data"]["calculated_balance"]) == Decimal("0.00")
    assert empty.json()["data"]["last_reconciliation"] is None

    await db_client.post(
        TRANSACTIONS,
        json=payload(salary, type="income", amount="1000.00", transaction_date=days_ago(5)),
        headers=headers(user_id),
    )
    await db_client.post(
        TRANSACTIONS,
        json=payload(food, type="expense", amount="120.50", transaction_date=days_ago(1)),
        headers=headers(user_id),
    )

    today_preview = await db_client.get(f"{URL}/preview", headers=headers(user_id))
    assert Decimal(today_preview.json()["data"]["calculated_balance"]) == Decimal("879.50")

    past_preview = await db_client.get(
        f"{URL}/preview", params={"reconciliation_date": days_ago(3)}, headers=headers(user_id)
    )
    assert Decimal(past_preview.json()["data"]["calculated_balance"]) == Decimal("1000.00")

    future_preview = await db_client.get(
        f"{URL}/preview", params={"reconciliation_date": days_ago(-1)}, headers=headers(user_id)
    )
    assert future_preview.status_code == 400


async def test_reconcile_positive_and_negative_differences_update_balance(
    db_client, user_id, default_ids
):
    salary = default_ids[("Stipendio", "income")]
    food = default_ids[("Alimentari", "expense")]

    await db_client.post(
        TRANSACTIONS,
        json=payload(salary, type="income", amount="500.00", transaction_date=days_ago(2)),
        headers=headers(user_id),
    )
    await db_client.post(
        TRANSACTIONS,
        json=payload(food, type="expense", amount="100.00", transaction_date=days_ago(1)),
        headers=headers(user_id),
    )

    # Calculated = 400.00; real = 350.00 -> adjustment of -50.00
    neg = await db_client.post(
        URL,
        json={"real_balance": "350.00", "description": "Verifica conto"},
        headers=headers(user_id),
    )
    assert neg.status_code == 201, neg.text
    neg_data = neg.json()["data"]
    assert Decimal(neg_data["calculated_balance"]) == Decimal("400.00")
    assert Decimal(neg_data["real_balance"]) == Decimal("350.00")
    assert Decimal(neg_data["difference"]) == Decimal("-50.00")
    assert neg_data["id_adjustment_transaction"] is not None

    # Subsequent calculated balance matches 350.00
    after_neg = await db_client.get(f"{URL}/preview", headers=headers(user_id))
    assert Decimal(after_neg.json()["data"]["calculated_balance"]) == Decimal("350.00")
    assert after_neg.json()["data"]["last_reconciliation"]["id_snapshot"] == neg_data["id_snapshot"]

    # Real = 425.25 -> positive adjustment of +75.25
    pos = await db_client.post(URL, json={"real_balance": "425.25"}, headers=headers(user_id))
    assert pos.status_code == 201
    pos_data = pos.json()["data"]
    assert Decimal(pos_data["calculated_balance"]) == Decimal("350.00")
    assert Decimal(pos_data["difference"]) == Decimal("75.25")
    assert pos_data["id_adjustment_transaction"] is not None

    # The adjustment transactions appear in /transactions (uneditable), without altering totals
    tx_list = (await db_client.get(TRANSACTIONS, headers=headers(user_id))).json()["data"]
    assert tx_list["totals"] == {"income": "500.00", "expense": "100.00"}
    adjustments = [item for item in tx_list["items"] if item["type"] == "adjustment"]
    assert len(adjustments) == 2
    assert all(item["origin"] == "reconciliation" for item in adjustments)
    assert all(item["id_category"] is None for item in adjustments)

    adj_id = pos_data["id_adjustment_transaction"]
    assert (
        await db_client.put(
            f"{TRANSACTIONS}/{adj_id}", json=payload(food), headers=headers(user_id)
        )
    ).status_code == 400


async def test_reconcile_when_already_aligned_creates_no_adjustment(
    db_client, db_session, user_id, default_ids
):
    salary = default_ids[("Stipendio", "income")]
    await db_client.post(
        TRANSACTIONS,
        json=payload(salary, type="income", amount="200.00", transaction_date=days_ago(0)),
        headers=headers(user_id),
    )
    response = await db_client.post(URL, json={"real_balance": "200.00"}, headers=headers(user_id))
    assert response.status_code == 201
    data = response.json()["data"]
    assert Decimal(data["difference"]) == Decimal("0.00")
    assert data["id_adjustment_transaction"] is None

    adj_count = await db_session.scalar(
        text("SELECT count(*) FROM transaction WHERE id_user = :u AND type = 'adjustment'"),
        {"u": user_id},
    )
    assert adj_count == 0


async def test_reconcile_supports_zero_and_negative_real_balance(db_client, user_id):
    zero = await db_client.post(URL, json={"real_balance": "0.00"}, headers=headers(user_id))
    assert zero.status_code == 201
    assert zero.json()["data"]["id_adjustment_transaction"] is None

    overdraft = await db_client.post(
        URL, json={"real_balance": "-120.50"}, headers=headers(user_id)
    )
    assert overdraft.status_code == 201
    assert Decimal(overdraft.json()["data"]["difference"]) == Decimal("-120.50")

    preview = await db_client.get(f"{URL}/preview", headers=headers(user_id))
    assert Decimal(preview.json()["data"]["calculated_balance"]) == Decimal("-120.50")


async def test_history_order_detail_and_user_isolation(db_client, user_id, other_user_id):
    older = (
        await db_client.post(
            URL,
            json={"real_balance": "100.00", "reconciliation_date": days_ago(3)},
            headers=headers(user_id),
        )
    ).json()["data"]
    newer = (
        await db_client.post(
            URL,
            json={"real_balance": "150.00", "reconciliation_date": days_ago(0)},
            headers=headers(user_id),
        )
    ).json()["data"]

    history = (await db_client.get(URL, headers=headers(user_id))).json()["data"]
    assert history["count"] == 2
    assert [item["id_snapshot"] for item in history["items"]] == [
        newer["id_snapshot"],
        older["id_snapshot"],
    ]
    assert Decimal(history["current_calculated_balance"]) == Decimal("150.00")

    detail = await db_client.get(f"{URL}/{newer['id_snapshot']}", headers=headers(user_id))
    assert detail.status_code == 200
    assert detail.json()["data"]["id_snapshot"] == newer["id_snapshot"]

    # Another user sees empty history and gets 404 on the first user's snapshot.
    other_history = (await db_client.get(URL, headers=headers(other_user_id))).json()["data"]
    assert other_history["count"] == 0
    assert Decimal(other_history["current_calculated_balance"]) == Decimal("0.00")
    assert (
        await db_client.get(f"{URL}/{newer['id_snapshot']}", headers=headers(other_user_id))
    ).status_code == 404
